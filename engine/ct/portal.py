"""Descarga de comprobantes desde el portal de propietarios de Redconar ("Mis Expensas").

Sin dependencias externas (urllib + cookies). Reproduce lo que hace el navegador:
  1. POST userValidator.php (usuario, contrasena; formulario de login/ingresar.php)
  2. GET  props/propHtml/ventanaPrincipal.php (abre la sesión del consorcio)
  3. POST props/propHtml/panels/p_egresos_props.php (periodSelectGasto=AAAA-M) → tabla #exampleGasto
  4. POST ajax/attachment/attachList.php (idOwner, type=Egreso|Ticket, mode=no_delete) → adjuntos por gasto
  5. GET  viewers/attachViewer.php?... → el PDF/imagen

Genera la carpeta "<AAAA-MM Mes>/" con un archivo por adjunto y un manifest.json con una fila por adjunto,
en el formato que consume ct.comprobantes.cargar_manifiesto_redconar.
"""
from __future__ import annotations
import html as htmllib
import json
import os
import re
import unicodedata
import urllib.parse
import urllib.request
from dataclasses import dataclass, field, asdict
from http.cookiejar import CookieJar
from typing import Optional

BASE = "https://redconar.net"
MESES = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]


class PortalError(Exception):
    pass


@dataclass
class Adjunto:
    nombre: str
    url: str


@dataclass
class Egreso:
    n: int
    fecha: str
    desc: str
    valor: str
    caja: str
    factura: str
    proveedor: str
    categoria: str
    id_egreso: Optional[str] = None
    id_ticket: Optional[str] = None
    adjuntos: list = field(default_factory=list)  # [(src, Adjunto)]


# ------------------------------------------------------------------ parseo (sin red)
def _strip_tags(s: str) -> str:
    s = re.sub(r"<script.*?</script>", "", s, flags=re.S)
    s = re.sub(r"<br\s*/?>", " ", s)
    s = re.sub(r"<[^>]+>", "", s)
    return re.sub(r"\s+", " ", htmllib.unescape(s)).strip()


def opciones_select(html: str, id_select: str) -> list[tuple[str, str]]:
    """[(value, texto)] de un <select id=...>."""
    m = re.search(r'<select[^>]*id=["\']%s["\'][^>]*>(.*?)</select>' % re.escape(id_select), html, flags=re.S)
    if not m:
        return []
    return [(htmllib.unescape(v), _strip_tags(t)) for v, t in re.findall(r'<option[^>]*value=["\']([^"\']*)["\'][^>]*>(.*?)</option>', m.group(1), flags=re.S)]


def parse_tabla_egresos(html: str) -> list[Egreso]:
    """Filas de la tabla #exampleGasto: fecha, descripción, valor, caja, factura, proveedor, categoría, adjuntos."""
    m = re.search(r'<table[^>]*id=["\']exampleGasto["\'][^>]*>(.*?)</table>', html, flags=re.S)
    if not m:
        raise PortalError("no se encontró la tabla de gastos (#exampleGasto); ¿sesión vencida?")
    body = m.group(1)
    if "<tbody" in body:
        body = body.split("<tbody", 1)[1]
    out = []
    for tr in re.findall(r"<tr[^>]*>(.*?)</tr>", body, flags=re.S):
        tds = re.findall(r"<td[^>]*>(.*?)</td>", tr, flags=re.S)
        if len(tds) < 7:
            continue
        cells = [_strip_tags(t) for t in tds[:7]]
        if not cells[0]:
            continue
        oc = re.search(r"attachList_outflow\('(\d+)','Egreso','no_delete','(\d*)'", tr)
        out.append(Egreso(len(out) + 1, *cells, id_egreso=oc.group(1) if oc else None, id_ticket=(oc.group(2) or None) if oc else None))
    return out


def parse_adjuntos(html: str) -> list[Adjunto]:
    h = re.sub(r"<script.*?</script>", "", html, flags=re.S)
    out = []
    for name, url in re.findall(r"<span>([^<]*?)</span></td>.*?href=['\"]([^'\"]*attachViewer\.php[^'\"]*)['\"]", h, flags=re.S):
        out.append(Adjunto(htmllib.unescape(name).strip(), htmllib.unescape(url)))
    return out


def parse_liquidacion(html: str, periodo: str) -> Optional[dict]:
    """POST para /fees/expensesViewer.php del período ('2026-8'), o None si todavía no está publicado.

    Las options del select #dateExp llevan la fecha de emisión en value y el período legible
    ('Agosto 2026') como texto; se mapea por texto, que es inequívoco aun con dos emisiones
    en el mismo mes calendario. bId y adminId salen de los hidden del form expensesView.
    """
    y, m = periodo.split("-")
    if not 1 <= int(m) <= 12:
        raise ValueError(f"período inválido: {periodo}")
    texto = f"{MESES[int(m) - 1]} {int(y)}"
    fecha = next((v for v, t in opciones_select(html, "dateExp") if t == texto), None)
    if fecha is None:
        return None
    datos = {"date": fecha}
    for campo in ("bId", "adminId"):
        tag = re.search(rf'<input[^>]*name=[\'"]{campo}[\'"][^>]*>', html)
        if not tag:
            raise PortalError(f"no se encontró el campo {campo} en el panel de expensas; ¿cambió el portal?")
        hv = re.search(r"value=['\"]([^'\"]*)", tag.group(0))
        datos[campo] = hv.group(1) if hv else ""
    return datos


def etiqueta_mes(periodo: str) -> str:
    """'2026-7' → '2026-07 Julio'."""
    y, m = periodo.split("-")
    return f"{int(y):04d}-{int(m):02d} {MESES[int(m) - 1]}"


def _cd_filename(headers: dict) -> str:
    """Nombre de archivo del Content-Disposition, sin directorios (el portal es semi-confiable)."""
    m = re.search(r'filename="?([^";]+)', headers.get("Content-Disposition", ""))
    return os.path.basename(m.group(1)) if m else ""


def _ascii(s: str) -> str:
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode()
    return re.sub(r'[\\/:*?"<>|]+', "", s).strip()


def nombre_archivo(e: Egreso, k: int, src: str, nombre_adj: str, ext: str) -> str:
    valor = e.valor.replace("$", "").strip()
    base = _ascii(re.sub(r"\.(pdf|jpe?g|png)$", "", nombre_adj, flags=re.I))
    return f"{e.n:02d}-{k} {e.fecha} {_ascii(e.proveedor)} {valor} {src[0]} {base}{ext}"[:180]


# ------------------------------------------------------------------ cliente
class Redconar:
    def __init__(self, timeout: int = 60):
        self.jar = CookieJar()
        self.opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(self.jar))
        self.opener.addheaders = [("User-Agent", "Mozilla/5.0 ConsorcioTransparente/0.1"), ("Accept-Language", "es-AR,es;q=0.9")]
        self.timeout = timeout

    def _req(self, path: str, data: Optional[dict] = None, multipart: bool = False) -> tuple[bytes, dict]:
        url = path if path.startswith("http") else BASE + path
        body = None; headers = {}
        if data is not None and multipart:
            boundary = "----CT" + os.urandom(8).hex()
            parts = []
            for k, v in data.items():
                parts.append(f"--{boundary}\r\nContent-Disposition: form-data; name=\"{k}\"\r\n\r\n{v}\r\n")
            body = ("".join(parts) + f"--{boundary}--\r\n").encode()
            headers["Content-Type"] = f"multipart/form-data; boundary={boundary}"
        elif data is not None:
            body = urllib.parse.urlencode(data).encode()
            headers["Content-Type"] = "application/x-www-form-urlencoded"
        req = urllib.request.Request(url, data=body, headers=headers)
        with self.opener.open(req, timeout=self.timeout) as r:
            return r.read(), dict(r.headers)

    def login(self, usuario: str, clave: str) -> None:
        self._req("/login/ingresar.php")  # cookie de sesión
        raw, _ = self._req("/userValidator.php", dict(home_=BASE + "/login/ingresar.php?", usuario=usuario, contrasena=clave))
        page = raw.decode("utf-8", "ignore")
        if 'name="contrasena"' in page:
            m = re.search(r'alert-danger[^>]*>(.*?)</div>', page, flags=re.S)
            raise PortalError("login rechazado: " + (_strip_tags(m.group(1)) if m else "revisá usuario y contraseña"))
        raw2, _ = self._req("/props/propHtml/ventanaPrincipal.php")
        if "ops-401" in raw2.decode("utf-8", "ignore"):
            raise PortalError("el portal no abrió la sesión del propietario (401)")
        self._panel_cache = None

    def panel(self, periodo: Optional[str] = None) -> str:
        data = {}
        if periodo:
            base = self.panel()  # para tomar los valores por defecto de categoría y cuenta
            cat = opciones_select(base, "categorySelectGasto"); acc = opciones_select(base, "accountSelectGasto")
            data = dict(periodSelectGasto=periodo, categorySelectGasto=cat[0][0] if cat else "", accountSelectGasto=acc[0][0] if acc else "")
        raw, _ = self._req("/props/propHtml/panels/p_egresos_props.php", data or None)
        return raw.decode("utf-8", "ignore")

    def periodos(self) -> list[tuple[str, str]]:
        return opciones_select(self.panel(), "periodSelectGasto")

    def egresos(self, periodo: str) -> list[Egreso]:
        return parse_tabla_egresos(self.panel(periodo))

    def adjuntos(self, id_owner: str, tipo: str) -> list[Adjunto]:
        raw, _ = self._req("/ajax/attachment/attachList.php", dict(idOwner=id_owner, type=tipo, mode="no_delete"), multipart=True)
        return parse_adjuntos(raw.decode("utf-8", "ignore"))

    def descargar(self, url: str) -> tuple[bytes, str]:
        raw, h = self._req(url)
        ct = h.get("Content-Type", "").lower()
        fname = _cd_filename(h)
        if raw[:5] == b"%PDF-":
            ext = ".pdf"
        elif raw[:3] == b"\xff\xd8\xff":
            ext = ".jpg"
        elif raw[:8] == b"\x89PNG\r\n\x1a\n":
            ext = ".png"
        elif "pdf" in ct:
            ext = ".pdf"
        else:
            raise PortalError(f"el visor no devolvió un documento (Content-Type {ct or '?'}); ¿sesión vencida?")
        return raw, (os.path.splitext(fname)[0] if fname else "") + ext

    def liquidacion(self, periodo: str) -> Optional[tuple[bytes, str]]:
        """PDF de la liquidación del período ('2026-8') y su nombre de archivo, o None si no está publicada."""
        raw, _ = self._req("/props/propHtml/panels/p_expensas.php")
        datos = parse_liquidacion(raw.decode("utf-8", "ignore"), periodo)
        if datos is None:
            return None
        raw, h = self._req("/fees/expensesViewer.php", datos)
        if raw[:5] != b"%PDF-":
            raise PortalError("el visor de expensas no devolvió un PDF; ¿sesión vencida?")
        fname = _cd_filename(h)
        a, mes = periodo.split("-")
        return raw, (fname if fname else f"{a}-{int(mes):02d}-liquidacion.pdf")

    def descargar_mes(self, periodo: str, carpeta: str, manifiesto: Optional[str] = None, log=print) -> list[dict]:
        """Baja todos los adjuntos del período a <carpeta>/<AAAA-MM Mes>/ y actualiza manifest.json (una fila por adjunto)."""
        mes = etiqueta_mes(periodo)
        destino = os.path.join(carpeta, mes); os.makedirs(destino, exist_ok=True)
        manifiesto = manifiesto or os.path.join(carpeta, "manifest.json")
        rows = [r for r in (json.load(open(manifiesto, encoding="utf-8")) if os.path.exists(manifiesto) else []) if r.get("mes") != mes]
        egresos = self.egresos(periodo)
        log(f"{mes}: {len(egresos)} gastos en el portal")
        for e in egresos:
            k = 0
            fuentes = [(e.id_ticket, "Ticket"), (e.id_egreso, "Egreso")]
            for id_owner, src in fuentes:
                if not id_owner:
                    continue
                for a in self.adjuntos(id_owner, src):
                    k += 1
                    try:
                        raw, fname = self.descargar(a.url)
                    except PortalError as ex:
                        log(f"  {e.n:02d}-{k} {e.proveedor}: {ex}"); continue
                    archivo = nombre_archivo(e, k, src, a.nombre or fname, os.path.splitext(fname)[1] or ".pdf")
                    with open(os.path.join(destino, archivo), "wb") as f:
                        f.write(raw)
                    rows.append(dict(mes=mes, n=e.n, k=k, fecha=e.fecha, proveedor=e.proveedor, valor=e.valor, caja=e.caja, factura=e.factura,
                                     categoria=e.categoria, desc=e.desc, src=src, nombre=a.nombre, archivo=archivo))
            if k == 0:
                rows.append(dict(mes=mes, n=e.n, k=0, fecha=e.fecha, proveedor=e.proveedor, valor=e.valor, caja=e.caja, factura=e.factura,
                                 categoria=e.categoria, desc=e.desc, src="", nombre="", archivo=""))
                log(f"  {e.n:02d} {e.fecha} {e.proveedor} {e.valor}: sin adjuntos")
            else:
                log(f"  {e.n:02d} {e.fecha} {e.proveedor} {e.valor}: {k} adjunto(s)")
        rows.sort(key=lambda r: (r["mes"], r["n"], r["k"]))
        json.dump(rows, open(manifiesto, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        return [r for r in rows if r["mes"] == mes]
