# Sincronización mensual automática — Plan de implementación

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** un timer diario baja del portal la liquidación nueva y los comprobantes y los ingesta al panel por la API; publicar sigue siendo manual.

**Architecture:** `Redconar` (portal.py) gana la descarga del PDF de Expensas; un módulo nuevo `sincronizar.py` orquesta con estado local en JSON (`$CT_PRIVADO/sincronizacion.json`), un cliente urllib de la API (usuario bot) y un ZIP determinista; systemd corre `python -m ct sincronizar` a las 06:30. Todo idempotente: la corrida del día siguiente es el reintento.

**Tech Stack:** stdlib puro en el engine (regla del proyecto); systemd; la API no cambia.

**Spec:** `docs/superpowers/specs/2026-09-05-sincronizacion-mensual-design.md`.

**Contexto de la máquina:** venv `engine/.venv` (suite hoy: 31 passed — la carpeta privada está presente). Credenciales de Redconar en `/opt/consorcios-transparentes/.env` (`USER_REDCONAR`/`PASSWORD_REDCONAR`). Rama de trabajo: `sincronizacion-mensual` desde `main`. Commits en español + trailer de la sesión. Producción en vivo: cuidado con no ingestar basura — las corridas reales contra la API solo en la Task 5, con confirmación del usuario.

**Formatos de período — leer antes de empezar:** el portal usa `2026-8` (sin cero); la API y las carpetas usan `2026-08`. Helper `periodo_api("2026-8") → "2026-08"` en sincronizar.py. Los PDF locales se mapean a período por el prefijo del nombre (`2026-08-31-...pdf` → `2026-08`).

---

### Task 1: Spike — estructura real de la página de Expensas (SIN commit de HTML real)

**Files:**
- Ninguno commiteado. Entregable: reporte de estructura + fixture sintético propuesto (se usa en Task 2).

- [ ] **Step 1:** Script efímero (NO commitear; borrarlo al final) `/tmp/explorar-expensas.py`:

```python
import os, re, sys
sys.path.insert(0, "/opt/consorcios-transparentes/engine")
from ct.portal import Redconar

r = Redconar()
r.login(os.environ["USER_REDCONAR"], os.environ["PASSWORD_REDCONAR"])
# La sección de expensas del propietario: probar las rutas candidatas y reportar cuál responde.
for path in ("/props/propHtml/panels/p_expensas_props.php",
             "/props/propHtml/panels/p_liquidaciones_props.php",
             "/props/propHtml/ventanaPrincipal.php"):
    try:
        raw, _ = r._req(path)
        html = raw.decode("utf-8", "ignore")
        print(f"== {path}: {len(html)} bytes")
        print("  selects:", re.findall(r'<select[^>]*id="([^"]+)"', html))
        print("  pdf/att:", re.findall(r'(attachViewer[^"\']{0,80}|expensas[^"\']{0,60}|liquidacion[^"\']{0,60})', html)[:10])
    except Exception as e:
        print(f"== {path}: ERROR {e}")
```

Correrlo: `cd /opt/consorcios-transparentes && set -a && source .env && set +a && engine/.venv/bin/python /tmp/explorar-expensas.py`. Si ninguna ruta candidata muestra la liquidación, inspeccionar `ventanaPrincipal.php` (imprime los links/iframes) hasta ubicar el panel de expensas — el usuario confirmó que es scrapeable con este login.

- [ ] **Step 2:** Con la página encontrada, identificar: cómo se elige el período, y el link/id del PDF de la liquidación. Redactar el reporte: ruta, parámetros del POST si los hay, estructura del HTML alrededor del link del PDF, y un **fixture sintético mínimo** con esa misma estructura (estilo `TABLA` en `engine/tests/test_portal.py` — datos inventados, NADA del consorcio real).

- [ ] **Step 3:** Verificar la descarga real de un PDF (el de agosto ya lo tenemos para comparar): bajarlo con `r.descargar(<url>)` y chequear `raw[:5] == b"%PDF-"` y que el tamaño sea ~300-400 KB. Borrar el script y cualquier HTML guardado en /tmp.

### Task 2: `Redconar.liquidacion()` + subcomando `descargar-liquidacion`

**Files:**
- Modify: `engine/ct/portal.py`, `engine/ct/cli.py`
- Test: `engine/tests/test_portal.py`

**Nota:** el parser exacto sale del reporte de la Task 1; la interfaz es fija, el HTML interno del fixture es el que la Task 1 haya definido. La spec decía `ct descargar liquidacion`; como `descargar` ya toma el período posicional, el subcomando es `descargar-liquidacion` (anotarlo al actualizar ESTADO en la Task 5).

- [ ] **Step 1: Tests que fallan.** En `engine/tests/test_portal.py`, con el fixture sintético de la Task 1 (nombre `EXPENSAS`):

```python
EXPENSAS = """<html>…estructura real sintetizada por la Task 1, período 2026-8 con link a un PDF…</html>"""


def test_parse_liquidacion_encuentra_el_pdf_del_periodo():
    from ct.portal import parse_liquidacion
    url = parse_liquidacion(EXPENSAS, "2026-8")
    assert url and "attachViewer" in url  # o el patrón real que documente la Task 1


def test_parse_liquidacion_periodo_ausente_da_none():
    from ct.portal import parse_liquidacion
    assert parse_liquidacion(EXPENSAS, "2019-1") is None
```

- [ ] **Step 2:** `cd engine && .venv/bin/python -m pytest -q tests/test_portal.py` → FAIL (no existe `parse_liquidacion`).

- [ ] **Step 3: Implementar.** En `portal.py`:
  - `parse_liquidacion(html: str, periodo: str) -> Optional[str]` — función pura de parseo (estilo `parse_tabla_egresos`), devuelve la URL del PDF o None.
  - Método `Redconar.liquidacion(self, periodo: str) -> Optional[tuple[bytes, str]]`: trae la página de expensas (la ruta/POST del reporte de Task 1), llama `parse_liquidacion`, si hay URL usa `self.descargar(url)` y devuelve `(bytes, nombre_de_archivo)`; si no, None. El nombre: el que dé el portal (Content-Disposition) o, si viene vacío, `f"{periodo_api(periodo)}-liquidacion.pdf"`.
  - En `cli.py`: subparser `descargar-liquidacion` con `periodo` posicional y `--carpeta` (default `os.path.expanduser("~/consorcio-transparente-privado")` + `/liquidaciones` — mirar cómo `descargar` resuelve la carpeta y seguir el mismo patrón, incluida la toma de credenciales por env o consola). Guarda el PDF; si `liquidacion()` dio None imprime "todavía no hay liquidación de <periodo> en el portal" y devuelve 0.

- [ ] **Step 4:** Suite: `cd engine && .venv/bin/python -m pytest -q tests` → 33 passed (31 + 2).

- [ ] **Step 5: Prueba real (lectura pura, sin API):** `set -a && source ../.env && set +a && CT_REDCONAR_USUARIO=$USER_REDCONAR CT_REDCONAR_CLAVE=$PASSWORD_REDCONAR .venv/bin/python -m ct descargar-liquidacion 2026-8 --carpeta /tmp/liq-test` → baja el PDF de agosto; compararlo con el real: `cmp /tmp/liq-test/*.pdf ~/consorcio-transparente-privado/liquidaciones/2026-08-31-190613-RIVADAVIA_2069.pdf` (si difiere en nombre pero el contenido es PDF válido del mismo tamaño ±1%, está OK — reportarlo). Limpiar /tmp/liq-test.

- [ ] **Step 6: Commit.**

```bash
git add engine/ct/portal.py engine/ct/cli.py engine/tests/test_portal.py
git commit -m "Engine: descarga de la liquidación del portal (descargar-liquidacion)"
```

### Task 3: `sincronizar.py` — orquestador con portal y API inyectados

**Files:**
- Create: `engine/ct/sincronizar.py`
- Test: `engine/tests/test_sincronizar.py`

- [ ] **Step 1: Tests que fallan.** Crear `engine/tests/test_sincronizar.py` (portal y API falsos, sin red ni disco real salvo tmp_path):

```python
"""Lógica de sincronización con portal y API falsos (sin red)."""
import json

import pytest

from ct.sincronizar import Sincronizador, periodo_api, zip_determinista


class PortalFalso:
    def __init__(self, periodos, liquidaciones):
        self._periodos = periodos          # [("2026-8", "Agosto 2026"), ...]
        self._liq = liquidaciones          # {"2026-8": (b"%PDF-...", "2026-08-31-x.pdf")}
        self.descargas_mes = []
    def periodos(self):
        return self._periodos
    def liquidacion(self, periodo):
        return self._liq.get(periodo)
    def descargar_mes(self, periodo, carpeta, log=print):
        self.descargas_mes.append(periodo)
        return []


class ApiFalsa:
    def __init__(self):
        self.liqs = {}                     # periodo -> dict de la API
        self.subidas = []                  # (tipo, periodo)
        self.zips = []
    def login(self): pass
    def liquidaciones(self):
        return list(self.liqs.values())
    def subir_liquidacion(self, periodo, pdf_bytes, nombre):
        self.subidas.append(("liq", periodo))
        self.liqs[periodo] = {"id": len(self.liqs) + 1, "periodo": periodo, "estado": "procesada",
                              "cuadra": True, "error": ""}
        return self.liqs[periodo]
    def detalle(self, liq_id):
        return next(l for l in self.liqs.values() if l["id"] == liq_id) | {"checks_ok": 30, "checks_mal": 0}
    def subir_comprobantes(self, liq_id, zip_bytes):
        self.zips.append(liq_id)
        return {"ok": True, "documentos": 2, "hallazgos_cruce": 1}


def armar_carpetas(tmp_path, periodo_carpeta="2026-08 Agosto"):
    (tmp_path / "liquidaciones").mkdir()
    mes = tmp_path / "Comprobantes Rivadavia 2069" / periodo_carpeta
    mes.mkdir(parents=True)
    (mes / "01-1 doc.pdf").write_bytes(b"%PDF-doc")
    (tmp_path / "Comprobantes Rivadavia 2069" / "manifest.json").write_text("[]")
    return tmp_path


def test_mes_nuevo_baja_e_ingesta_todo(tmp_path):
    armar_carpetas(tmp_path)
    portal = PortalFalso([("2026-8", "Agosto 2026")], {"2026-8": (b"%PDF-agosto", "2026-08-31-liq.pdf")})
    api = ApiFalsa()
    s = Sincronizador(portal, api, str(tmp_path))
    rc = s.correr()
    assert rc == 0
    assert (tmp_path / "liquidaciones" / "2026-08-31-liq.pdf").read_bytes() == b"%PDF-agosto"
    assert portal.descargas_mes == ["2026-8"]
    assert ("liq", "2026-08") in api.subidas and api.zips  # subió PDF y ZIP
    estado = json.loads((tmp_path / "sincronizacion.json").read_text())
    assert estado["2026-08"]["liquidacion_subida"] and estado["2026-08"]["zip_hash"]


def test_sin_cambios_no_resube_nada(tmp_path):
    armar_carpetas(tmp_path)
    portal = PortalFalso([("2026-8", "Agosto 2026")], {"2026-8": (b"%PDF-agosto", "2026-08-31-liq.pdf")})
    api = ApiFalsa()
    s = Sincronizador(portal, api, str(tmp_path))
    assert s.correr() == 0
    subidas = list(api.subidas); zips = list(api.zips)
    assert s.correr() == 0                      # segunda corrida, nada cambió
    assert api.subidas == subidas and api.zips == zips


def test_comprobante_nuevo_resube_solo_el_zip(tmp_path):
    armar_carpetas(tmp_path)
    portal = PortalFalso([("2026-8", "Agosto 2026")], {"2026-8": (b"%PDF-agosto", "2026-08-31-liq.pdf")})
    api = ApiFalsa()
    s = Sincronizador(portal, api, str(tmp_path))
    s.correr()
    (tmp_path / "Comprobantes Rivadavia 2069" / "2026-08 Agosto" / "02-1 nuevo.pdf").write_bytes(b"%PDF-n")
    n_liq = len([x for x in api.subidas if x[0] == "liq"])
    s.correr()
    assert len([x for x in api.subidas if x[0] == "liq"]) == n_liq   # liquidación no se re-sube
    assert len(api.zips) == 2                                        # el ZIP sí


def test_no_cuadra_corta_con_error(tmp_path):
    armar_carpetas(tmp_path)
    portal = PortalFalso([("2026-8", "Agosto 2026")], {"2026-8": (b"%PDF-agosto", "2026-08-31-liq.pdf")})
    api = ApiFalsa()
    def subir_mal(periodo, pdf_bytes, nombre):
        api.subidas.append(("liq", periodo))
        api.liqs[periodo] = {"id": 1, "periodo": periodo, "estado": "no_cuadra", "cuadra": False,
                             "error": "no cuadra"}
        return api.liqs[periodo]
    api.subir_liquidacion = subir_mal
    s = Sincronizador(portal, api, str(tmp_path))
    assert s.correr() != 0
    assert not api.zips                                              # no siguió con comprobantes
    estado = json.loads((tmp_path / "sincronizacion.json").read_text())
    assert not estado.get("2026-08", {}).get("liquidacion_subida")   # queda pendiente para reintentar


def test_reconcilia_con_liquidaciones_ya_ingresadas_a_mano(tmp_path):
    armar_carpetas(tmp_path)
    (tmp_path / "liquidaciones" / "2026-08-31-liq.pdf").write_bytes(b"%PDF-agosto")
    portal = PortalFalso([("2026-8", "Agosto 2026")], {})
    api = ApiFalsa()
    api.liqs["2026-08"] = {"id": 7, "periodo": "2026-08", "estado": "publicada", "cuadra": True, "error": ""}
    s = Sincronizador(portal, api, str(tmp_path))
    assert s.correr() == 0
    assert not [x for x in api.subidas if x[0] == "liq"]             # no re-sube lo que la API ya tiene
    assert api.zips                                                  # pero el ZIP inicial sí (hash nuevo)


def test_periodo_api():
    assert periodo_api("2026-8") == "2026-08"
    assert periodo_api("2026-11") == "2026-11"


def test_zip_determinista(tmp_path):
    d = tmp_path / "m"; d.mkdir()
    (d / "b.pdf").write_bytes(b"B"); (d / "a.pdf").write_bytes(b"A")
    z1 = zip_determinista(str(d))
    z2 = zip_determinista(str(d))
    assert z1 == z2 and len(z1) > 0
```

- [ ] **Step 2:** `cd engine && .venv/bin/python -m pytest -q tests/test_sincronizar.py` → FAIL (módulo inexistente).

- [ ] **Step 3: Implementar** `engine/ct/sincronizar.py` (solo stdlib). Piezas:

```python
def periodo_api(periodo_portal: str) -> str:
    """'2026-8' del portal → '2026-08' de la API y las carpetas."""
    a, m = periodo_portal.split("-")
    return f"{a}-{int(m):02d}"


def zip_determinista(carpeta: str, extra: dict[str, bytes] | None = None) -> bytes:
    """ZIP con entradas ordenadas y timestamp fijo: mismos archivos → mismos bytes (y hash)."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        nombres = sorted(os.listdir(carpeta))
        for n in nombres:
            info = zipfile.ZipInfo(n, date_time=(1980, 1, 1, 0, 0, 0))
            with open(os.path.join(carpeta, n), "rb") as f:
                z.writestr(info, f.read())
        for nombre, data in sorted((extra or {}).items()):
            z.writestr(zipfile.ZipInfo(nombre, date_time=(1980, 1, 1, 0, 0, 0)), data)
    return buf.getvalue()
```

`Sincronizador(portal, api, carpeta_privada, log=print)` con `correr() -> int`:
1. `api.login()`; leer `sincronizacion.json` (dict por período; `{}` si no existe).
2. **Reconciliar**: para cada liquidación de `api.liquidaciones()` con estado `procesada`/`publicada`, marcar `liquidacion_subida=True` en el estado local (sin tocar `zip_hash`).
3. Período más reciente del portal (`portal.periodos()[0]`), `per = periodo_api(...)`.
4. Si no hay PDF local cuyo nombre empiece con `per` en `liquidaciones/`: pedir `portal.liquidacion(periodo_portal)`; si devuelve `(bytes, nombre)`, guardarlo; si None, log "todavía no hay" y no es error.
5. `portal.descargar_mes(periodo_portal, carpeta_comprobantes)` (la subcarpeta `Comprobantes Rivadavia 2069` — constante del módulo, misma que usa el resto del tooling).
6. Si hay PDF local de `per` y `not estado[per]["liquidacion_subida"]`: `api.subir_liquidacion(per, pdf_bytes, nombre)` → poll `api.detalle(id)` (con `time.sleep` cortito entre intentos, máx ~60 s) hasta salir de `procesando`. `procesada`/`publicada` → marcar subida y guardar estado. Otro estado → log del error y `return 1` **sin** marcar subida.
7. ZIP: `zip_determinista(carpeta_del_mes, extra={"manifest.json": <manifest filtrado o completo>})` — incluir el `manifest.json` (la API lo exige adentro del ZIP). `sha256` del ZIP ≠ `estado[per]["zip_hash"]` y la liquidación está subida → `api.subir_comprobantes(id, zip)` → actualizar hash y guardar estado; log del resumen (documentos, hallazgos_cruce).
8. Guardar `sincronizacion.json` (escritura atómica: tmp + rename) SOLO tras cada paso exitoso. `return 0`.

`ApiPanel` (cliente urllib de la API real, misma interfaz que `ApiFalsa`): `login()` POST `/auth/login` (json) guardando cookie en un `http.cookiejar.CookieJar`; `liquidaciones()` GET; `subir_liquidacion(periodo, pdf_bytes, nombre)` POST multipart (campo `archivo` + form `periodo` — armar multipart a mano como hace `Redconar._req`, pero con parte de archivo: `Content-Disposition: form-data; name="archivo"; filename="<nombre>"` + `Content-Type: application/pdf`); `detalle(id)` GET; `subir_comprobantes(id, zip_bytes)` POST multipart análogo. Errores HTTP → excepción con el `detail` del JSON si lo hay.

- [ ] **Step 4:** `cd engine && .venv/bin/python -m pytest -q tests` → 41 passed (33 + 8).

- [ ] **Step 5: Commit.**

```bash
git add engine/ct/sincronizar.py engine/tests/test_sincronizar.py
git commit -m "Engine: sincronizador mensual (portal → carpeta privada → API, idempotente)"
```

### Task 4: CLI `ct sincronizar` + systemd + DEPLOY.md

**Files:**
- Modify: `engine/ct/cli.py`
- Create: `deploy/systemd/ct-sincronizar.service`, `deploy/systemd/ct-sincronizar.timer`
- Modify: `docs/DEPLOY.md`

- [ ] **Step 1:** En `cli.py`, subparser `sincronizar` sin argumentos obligatorios; config por env:
  - Portal: `CT_REDCONAR_USUARIO`/`CT_REDCONAR_CLAVE` o `USER_REDCONAR`/`PASSWORD_REDCONAR` (aceptar ambos; el `.env` raíz usa los segundos).
  - API: `CT_API_URL` (default `https://api-consorcio.neuralcore.dev`), `CT_API_BOT_EMAIL`, `CT_API_BOT_CLAVE` — si faltan, error claro y exit 2.
  - Carpeta: `CT_PRIVADO` o `~/consorcio-transparente-privado`.
  Instancia `Redconar` + login, `ApiPanel`, `Sincronizador(...).correr()` y devuelve su código.

- [ ] **Step 2:** `deploy/systemd/ct-sincronizar.service`:

```ini
[Unit]
Description=Consorcio Transparente - sincronizacion diaria del portal al panel
After=network-online.target
Wants=network-online.target

[Service]
Type=oneshot
User=ltaverna
EnvironmentFile=/opt/consorcios-transparentes/.env
Environment=CT_API_BOT_EMAIL=robot@consorcio-transparente.local
ExecStart=/opt/consorcios-transparentes/engine/.venv/bin/python -m ct sincronizar
WorkingDirectory=/opt/consorcios-transparentes/engine
```

(`CT_API_BOT_CLAVE` y `CT_API_URL` van en el `.env` raíz, no acá.) `deploy/systemd/ct-sincronizar.timer`:

```ini
[Unit]
Description=Corrida diaria de la sincronizacion del consorcio

[Timer]
OnCalendar=*-*-* 06:30:00
Persistent=true

[Install]
WantedBy=timers.target
```

- [ ] **Step 3:** `docs/DEPLOY.md`, sección nueva "8. Sincronización mensual automática": crear el usuario bot (`docker compose exec -it api python cli.py usuario robot@consorcio-transparente.local "Robot de carga" auditor`), agregar `CT_API_BOT_CLAVE` (y opcional `CT_API_URL`) al `.env` raíz, instalar las units (`sudo cp deploy/systemd/ct-sincronizar.* /etc/systemd/system/ && sudo systemctl daemon-reload && sudo systemctl enable --now ct-sincronizar.timer`), probar a mano (`systemctl start ct-sincronizar.service && journalctl -u ct-sincronizar -n 50`), y la nota: nunca publica; el triage sigue en el panel.

- [ ] **Step 4:** Verificar: suite engine sigue 41 passed; `python -m ct sincronizar` sin env de API → exit 2 con mensaje claro (probarlo).

- [ ] **Step 5: Commit.**

```bash
git add engine/ct/cli.py deploy/systemd/ docs/DEPLOY.md
git commit -m "CLI sincronizar + timer de systemd y runbook"
```

### Task 5: Cierre — suites, estado, merge y puesta en marcha

- [ ] **Step 1:** Suites: engine 41 passed · api 98 passed · web 36 passed (api/web no se tocaron — correr igual).
- [ ] **Step 2:** `docs/ESTADO.md`: pendiente nuevo resuelto — anotar la sincronización diaria (timer `ct-sincronizar`, bot `robot@…`, subcomando real `descargar-liquidacion`, estado en `$CT_PRIVADO/sincronizacion.json`, nunca publica). Actualizar también la spec §1 con el nombre real del subcomando.
- [ ] **Step 3:** Commit docs + merge a `main`.
- [ ] **Step 4: Puesta en marcha (CON confirmación del usuario, es producción):** crear el bot por CLI (clave generada, via stdin ×2 como se hizo antes), agregar `CT_API_BOT_CLAVE` al `.env` raíz (chmod 600), push, instalar units con sudo, y **primera corrida real supervisada**: `systemctl start ct-sincronizar.service` + journal — con julio/agosto ya ingestados debe reconciliar, refrescar comprobantes de agosto y (si el hash cambió) re-cruzar; nada más. Verificar en el panel que no pasó nada raro.
