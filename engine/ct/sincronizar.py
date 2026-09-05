"""Sincronización mensual: portal (Redconar) → carpeta privada → API del panel.

Orquesta la corrida idempotente de cada mes:
  1. baja la liquidación del período más reciente si todavía no está en `liquidaciones/`,
  2. refresca los comprobantes del mes (regenera manifest.json vía `Redconar.descargar_mes`),
  3. sube la liquidación a la API si la API todavía no la tiene procesada/publicada,
  4. arma un ZIP determinista con los comprobantes + manifest y lo sube solo si cambió el hash.

El estado local vive en `<carpeta_privada>/sincronizacion.json` (dict por período con
`liquidacion_subida` y `zip_hash`); se escribe siempre de forma atómica. El portal y la API
se inyectan (los tests usan dobles sin red); `ApiPanel` es el cliente real (solo stdlib).
"""
from __future__ import annotations
import hashlib
import io
import json
import os
import time
import urllib.error
import urllib.request
import zipfile
from http.cookiejar import CookieJar

CARPETA_COMPROBANTES = "Comprobantes Rivadavia 2069"


class ApiError(Exception):
    pass


def periodo_api(periodo_portal: str) -> str:
    """'2026-8' del portal → '2026-08' de la API y las carpetas."""
    a, m = periodo_portal.split("-")
    return f"{a}-{int(m):02d}"


def zip_determinista(carpeta: str, extra: dict[str, bytes] | None = None, prefijo: str = "") -> bytes:
    """ZIP con entradas ordenadas y timestamp fijo: mismos archivos → mismos bytes (y hash).

    Layout esperado por la API (ver `api/tests/test_comprobantes_api.py` y
    `engine/ct/comprobantes.py::cargar_manifiesto_redconar`):
      - `manifest.json` en la raíz del ZIP  →  se pasa vía `extra`.
      - Los PDFs bajo `"<etiqueta_del_mes>/<archivo>"`, donde la etiqueta coincide
        con el campo `"mes"` de cada fila del manifiesto (p. ej. `"2026-08 Agosto"`).

    Si `prefijo` es no-vacío, cada entrada de `carpeta` se almacena como
    `"<prefijo>/<nombre>"` en lugar de `"<nombre>"` plano.  Las entradas de
    `extra` siempre quedan en la raíz (sin prefijo).
    """
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for n in sorted(os.listdir(carpeta)):
            nombre_zip = f"{prefijo}/{n}" if prefijo else n
            info = zipfile.ZipInfo(nombre_zip, date_time=(1980, 1, 1, 0, 0, 0))
            with open(os.path.join(carpeta, n), "rb") as f:
                z.writestr(info, f.read())
        for nombre, data in sorted((extra or {}).items()):
            z.writestr(zipfile.ZipInfo(nombre, date_time=(1980, 1, 1, 0, 0, 0)), data)
    return buf.getvalue()


# ------------------------------------------------------------------ cliente de la API del panel
class ApiPanel:
    """Cliente mínimo de la API del panel (urllib + cookies de sesión, sin dependencias)."""

    def __init__(self, base_url: str, email: str, clave: str, timeout: int = 120):
        self.base = base_url.rstrip("/")
        self.email, self.clave = email, clave
        self.timeout = timeout
        self.jar = CookieJar()
        self.opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(self.jar))
        self.opener.addheaders = [("User-Agent", "ConsorcioTransparente-sincronizador/0.1")]

    def _abrir(self, req: urllib.request.Request):
        try:
            with self.opener.open(req, timeout=self.timeout) as r:
                cuerpo = r.read().decode("utf-8", "ignore")
        except urllib.error.HTTPError as e:
            cuerpo = e.read().decode("utf-8", "ignore")
            try:
                detalle = json.loads(cuerpo).get("detail", cuerpo)
            except (ValueError, AttributeError):
                detalle = cuerpo[:300]
            raise ApiError(f"la API respondió {e.code}: {detalle}") from None
        return json.loads(cuerpo) if cuerpo else None

    def _json(self, path: str, data: dict | None = None):
        body = json.dumps(data).encode() if data is not None else None
        headers = {"Content-Type": "application/json"} if body is not None else {}
        return self._abrir(urllib.request.Request(self.base + path, data=body, headers=headers))

    def _multipart(self, path: str, campos: dict | None, nombre: str, content_type: str, data: bytes):
        """POST multipart con la parte binaria 'archivo' armada a mano (mismo estilo que Redconar._req)."""
        boundary = "----CT" + os.urandom(8).hex()
        partes = []
        for k, v in (campos or {}).items():
            partes.append(f'--{boundary}\r\nContent-Disposition: form-data; name="{k}"\r\n\r\n{v}\r\n'.encode())
        partes.append((f'--{boundary}\r\nContent-Disposition: form-data; name="archivo"; filename="{nombre}"\r\n'
                       f"Content-Type: {content_type}\r\n\r\n").encode() + data + b"\r\n")
        body = b"".join(partes) + f"--{boundary}--\r\n".encode()
        req = urllib.request.Request(self.base + path, data=body,
                                     headers={"Content-Type": f"multipart/form-data; boundary={boundary}"})
        return self._abrir(req)

    def login(self) -> None:
        self._json("/auth/login", {"email": self.email, "clave": self.clave})

    def liquidaciones(self) -> list[dict]:
        return self._json("/liquidaciones")

    def subir_liquidacion(self, periodo: str, pdf_bytes: bytes, nombre: str) -> dict:
        return self._multipart("/liquidaciones", {"periodo": periodo}, nombre, "application/pdf", pdf_bytes)

    def detalle(self, liq_id: int) -> dict:
        return self._json(f"/liquidaciones/{liq_id}")

    def subir_comprobantes(self, liq_id: int, zip_bytes: bytes) -> dict:
        return self._multipart(f"/liquidaciones/{liq_id}/comprobantes", None, "comprobantes.zip",
                               "application/zip", zip_bytes)


# ------------------------------------------------------------------ orquestador
class Sincronizador:
    """Corrida mensual idempotente. `portal` y `api` se inyectan (Redconar y ApiPanel en producción)."""

    ESPERA_POLL = 2       # segundos entre consultas mientras la API procesa
    ESPERA_MAX = 60       # tope total del poll

    def __init__(self, portal, api, carpeta_privada: str, log=print):
        self.portal, self.api, self.privada, self.log = portal, api, carpeta_privada, log
        self.ruta_estado = os.path.join(carpeta_privada, "sincronizacion.json")

    # -- estado local ------------------------------------------------
    def _leer_estado(self) -> dict:
        if not os.path.exists(self.ruta_estado):
            return {}
        with open(self.ruta_estado, encoding="utf-8") as f:
            return json.load(f)

    def _guardar(self, estado: dict) -> None:
        tmp = self.ruta_estado + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(estado, f, ensure_ascii=False, indent=1)
        os.replace(tmp, self.ruta_estado)

    # -- pasos -------------------------------------------------------
    def _pdfs_locales(self, per: str) -> list[str]:
        dir_liq = os.path.join(self.privada, "liquidaciones")
        if not os.path.isdir(dir_liq):
            return []
        return sorted(n for n in os.listdir(dir_liq) if n.startswith(per) and n.lower().endswith(".pdf"))

    def _bajar_liquidacion(self, periodo_portal: str, per: str) -> None:
        res = self.portal.liquidacion(periodo_portal)
        if res is None:
            self.log(f"todavía no hay liquidación de {per} en el portal")
            return
        raw, nombre = res
        nombre = os.path.basename(nombre)
        if not nombre.startswith(per):  # que las corridas siguientes la encuentren por período
            nombre = f"{per} {nombre}"
        dir_liq = os.path.join(self.privada, "liquidaciones")
        os.makedirs(dir_liq, exist_ok=True)
        ruta = os.path.join(dir_liq, nombre)
        ruta_tmp = ruta + ".tmp"
        with open(ruta_tmp, "wb") as f:
            f.write(raw)
        os.replace(ruta_tmp, ruta)
        self.log(f"liquidación de {per} bajada del portal: {nombre}")

    def _subir_liquidacion(self, per: str, nombre: str) -> dict:
        """Sube el PDF y espera a que la API lo procese. Devuelve el detalle final."""
        with open(os.path.join(self.privada, "liquidaciones", nombre), "rb") as f:
            pdf = f.read()
        self.log(f"subiendo liquidación {per} ({nombre})")
        fila = self.api.subir_liquidacion(per, pdf, nombre)
        limite = time.monotonic() + self.ESPERA_MAX
        det = self.api.detalle(fila["id"])
        while det.get("estado") == "procesando" and time.monotonic() < limite:
            time.sleep(self.ESPERA_POLL)
            det = self.api.detalle(fila["id"])
        return det

    def correr(self) -> int:
        self.api.login()
        estado = self._leer_estado()

        # 2. reconciliar con lo que la API ya tiene (p. ej. cargado a mano por el panel)
        for fila in self.api.liquidaciones():
            if fila.get("estado") in ("procesada", "publicada"):
                estado.setdefault(fila["periodo"], {})["liquidacion_subida"] = True

        # 3. período más reciente del portal
        periodos = self.portal.periodos()
        if not periodos:
            self.log("el portal no devolvió períodos; nada para sincronizar")
            self._guardar(estado)
            return 1
        periodo_portal = periodos[0][0]
        per = periodo_api(periodo_portal)
        self.log(f"sincronizando {per} (portal {periodo_portal})")

        # 4. liquidación local: bajarla del portal si todavía no está
        if not self._pdfs_locales(per):
            self._bajar_liquidacion(periodo_portal, per)

        # 5. refresco de comprobantes del mes (regenera manifest.json)
        carpeta_comp = os.path.join(self.privada, CARPETA_COMPROBANTES)
        os.makedirs(carpeta_comp, exist_ok=True)
        self.portal.descargar_mes(periodo_portal, carpeta_comp, log=self.log)

        # 6. subir la liquidación a la API si hace falta
        info = estado.setdefault(per, {})
        fila_subida = None
        pdfs = self._pdfs_locales(per)
        if pdfs and not info.get("liquidacion_subida"):
            det = self._subir_liquidacion(per, pdfs[-1])
            if det.get("estado") in ("procesada", "publicada"):
                info["liquidacion_subida"] = True
                self._guardar(estado)
                self.log(f"liquidación {per} {det['estado']}: {det.get('checks_ok', 0)} checks OK, "
                         f"{det.get('checks_mal', 0)} con problemas")
                fila_subida = det
            else:
                self._guardar(estado)  # queda pendiente para reintentar en la próxima corrida
                self.log(f"la liquidación {per} no quedó procesada (estado: {det.get('estado', '?')}): "
                         f"{det.get('error') or 'sin detalle'}")
                return 1

        # 7. ZIP de comprobantes: solo si cambió el hash y la liquidación ya está en la API
        carpeta_mes = next((d for d in sorted(os.listdir(carpeta_comp))
                            if d.startswith(per) and os.path.isdir(os.path.join(carpeta_comp, d))), None)
        if carpeta_mes is None:
            self.log(f"no hay carpeta de comprobantes de {per}; salteo el ZIP")
        else:
            ruta_manifest = os.path.join(carpeta_comp, "manifest.json")
            if os.path.exists(ruta_manifest):
                with open(ruta_manifest, "rb") as _mf:
                    manifest = _mf.read()
            else:
                manifest = b"[]"
            zb = zip_determinista(os.path.join(carpeta_comp, carpeta_mes),
                                  extra={"manifest.json": manifest},
                                  prefijo=carpeta_mes)
            h = hashlib.sha256(zb).hexdigest()
            if h != info.get("zip_hash") and not info.get("liquidacion_subida"):
                self.log(f"la liquidación de {per} todavía no está subida; salteo el ZIP")
            elif h != info.get("zip_hash"):
                liq_id = ((fila_subida or {}).get("id")
                          or next((l["id"] for l in self.api.liquidaciones() if l.get("periodo") == per), None))
                if liq_id is None:
                    self.log(f"la API no tiene la liquidación de {per}; salteo el ZIP")
                else:
                    res = self.api.subir_comprobantes(liq_id, zb)
                    info["zip_hash"] = h
                    self._guardar(estado)
                    self.log(f"comprobantes de {per}: {res.get('documentos', 0)} documentos, "
                             f"{res.get('hallazgos_cruce', 0)} hallazgos de cruce")

        self._guardar(estado)
        return 0
