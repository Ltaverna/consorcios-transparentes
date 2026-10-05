# Self-service convocatoria → mociones — Plan de implementación

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** El moderador sube la convocatoria (PDF/DOC/DOCX) desde la app de asamblea y un LLM propone orden del día + mociones, que el moderador revisa/edita antes de cargar en la votación.

**Architecture:** Endpoint nuevo en la **API del panel** (FastAPI): extrae texto (PDF→Claude nativo; DOCX→zipfile; DOC→LibreOffice) y llama a la **Claude API** con salida estructurada (tool/JSON schema) que devuelve `{metadatos, agenda, mociones}`. La app (botón mod-only) muestra una pantalla de revisión y, al confirmar, reemplaza `S.mociones`. Protegido con token compartido + CORS.

**Tech Stack:** Python/FastAPI, SDK `anthropic`, extractor existente (`apps/asamblea/tools/extraer_convocatoria.py`), HTML/JS de la app. Spec: `docs/superpowers/specs/2026-10-05-convocatoria-a-mociones-design.md`.

**Comandos de test:** `cd api && .venv/bin/python -m pytest -q` · app: `cd apps/asamblea && node --test`

**Orden sugerido:** 1 (parseo puro) → 2 (cliente Claude) → 3 (endpoint) → 4 (infra) → 5 (UI) → 6 (deploy, con el dueño). 1–3 tienen tests; 5 es UI; 6 es prod.

---

## Task 1: Módulo `convocatoria.py` — extracción + normalización del JSON del LLM

**Files:**
- Create: `api/app/convocatoria.py`
- Test: `api/tests/test_convocatoria.py`

La extracción reusa la lógica de `apps/asamblea/tools/extraer_convocatoria.py` (pdftotext/zipfile/libreoffice). La **normalización** es una función pura testeable que valida/completa lo que devuelve el LLM.

- [ ] **Step 1: Test de `normalizar_propuesta` (falla)**

Crear `api/tests/test_convocatoria.py`:

```python
from app.convocatoria import normalizar_propuesta

OPC = ["A favor", "En contra", "Abstención"]

def test_normaliza_mociones_completas():
    crudo = {"metadatos": {"fecha": "3/09/26"},
             "agenda": [{"n": 1, "titulo": "Designación", "tipo": "procedimental"},
                        {"n": 3, "titulo": "Continuidad del encargado", "tipo": "deliberativo"}],
             "mociones": [{"titulo": "Que el encargado continúe"}]}
    out = normalizar_propuesta(crudo)
    assert out["mociones"][0]["titulo"] == "Que el encargado continúe"
    assert out["mociones"][0]["opciones"] == OPC          # default
    assert out["mociones"][0]["regla"] == "abs"           # default
    assert out["agenda"][1]["tipo"] == "deliberativo"

def test_descarta_mociones_sin_titulo():
    out = normalizar_propuesta({"mociones": [{"titulo": ""}, {"opciones": OPC}, {"titulo": "Válida"}]})
    assert [m["titulo"] for m in out["mociones"]] == ["Válida"]

def test_tolera_json_incompleto():
    out = normalizar_propuesta({})
    assert out["mociones"] == [] and out["agenda"] == [] and isinstance(out["metadatos"], dict)

def test_regla_invalida_cae_a_abs():
    out = normalizar_propuesta({"mociones": [{"titulo": "X", "regla": "cualquiera"}]})
    assert out["mociones"][0]["regla"] == "abs"
```

- [ ] **Step 2: Correr para verlo fallar**

Run: `cd /opt/consorcios-transparentes/api && .venv/bin/python -m pytest -q tests/test_convocatoria.py`
Expected: FAIL (ImportError).

- [ ] **Step 3: Implementar extracción + `normalizar_propuesta`**

Crear `api/app/convocatoria.py`:

```python
"""Convocatoria → propuesta de mociones. Extracción multi-formato + normalización del JSON del LLM.
El LLM solo PROPONE; el moderador revisa. No toca el motor de análisis."""
import html
import os
import re
import subprocess
import tempfile
import zipfile

OPCIONES_DEF = ["A favor", "En contra", "Abstención"]
REGLAS = {"abs", "pres", "2/3"}


def texto_de_docx(data: bytes) -> str:
    with tempfile.NamedTemporaryFile(suffix=".docx", delete=False) as f:
        f.write(data); ruta = f.name
    try:
        with zipfile.ZipFile(ruta) as z:
            xml = z.read("word/document.xml").decode("utf-8", "ignore")
        xml = re.sub(r"</w:p>", "\n", xml)
        xml = re.sub(r"<w:tab[^>]*/>", "\t", xml)
        return html.unescape(re.sub(r"<[^>]+>", "", xml))
    finally:
        os.unlink(ruta)


def texto_de_doc(data: bytes) -> str:
    with tempfile.TemporaryDirectory() as d:
        ruta = os.path.join(d, "conv.doc")
        with open(ruta, "wb") as f:
            f.write(data)
        subprocess.run(["libreoffice", "--headless", "--convert-to", "txt:Text", "--outdir", d, ruta],
                       capture_output=True, timeout=180)
        salida = os.path.join(d, "conv.txt")
        if not os.path.exists(salida):
            raise ValueError("no se pudo convertir el .doc (¿LibreOffice instalado?)")
        with open(salida, encoding="utf-8", errors="ignore") as f:
            return f.read()


def texto_de_pdf(data: bytes) -> str:
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
        f.write(data); ruta = f.name
    try:
        r = subprocess.run(["pdftotext", "-layout", ruta, "-"], capture_output=True, text=True, timeout=120)
        return r.stdout
    finally:
        os.unlink(ruta)


def normalizar_propuesta(crudo: dict) -> dict:
    """Valida y completa el JSON del LLM: defaults de opciones/regla, descarta mociones sin título."""
    crudo = crudo or {}
    mociones = []
    for m in (crudo.get("mociones") or []):
        titulo = (m.get("titulo") or "").strip()
        if not titulo:
            continue
        regla = m.get("regla") if m.get("regla") in REGLAS else "abs"
        opciones = m.get("opciones") if isinstance(m.get("opciones"), list) and m.get("opciones") else OPCIONES_DEF
        mociones.append({"titulo": titulo, "opciones": opciones, "regla": regla})
    agenda = [{"n": a.get("n"), "titulo": (a.get("titulo") or "").strip(), "tipo": a.get("tipo") or ""}
              for a in (crudo.get("agenda") or []) if (a.get("titulo") or "").strip()]
    return {"metadatos": crudo.get("metadatos") or {}, "agenda": agenda, "mociones": mociones}
```

- [ ] **Step 4: Correr — pasan**

Run: `cd /opt/consorcios-transparentes/api && .venv/bin/python -m pytest -q tests/test_convocatoria.py`
Expected: PASS (4).

- [ ] **Step 5: Commit**

```bash
cd /opt/consorcios-transparentes
git add api/app/convocatoria.py api/tests/test_convocatoria.py
git commit -m "API: módulo convocatoria — extracción multi-formato y normalización de la propuesta"
```

---

## Task 2: Cliente Claude — `proponer_mociones`

**Files:**
- Modify: `api/app/convocatoria.py`
- Modify: `api/pyproject.toml` (dependencia `anthropic`)
- Test: `api/tests/test_convocatoria.py`

- [ ] **Step 1: Agregar la dependencia**

En `api/pyproject.toml`, agregar a `dependencies` (lista principal, no dev): `"anthropic>=0.40"`. Luego `cd /opt/consorcios-transparentes/api && .venv/bin/pip install -e .` (o `.venv/bin/pip install "anthropic>=0.40"`).

- [ ] **Step 2: Test de `proponer_mociones` con el cliente Claude mockeado (falla)**

Agregar a `api/tests/test_convocatoria.py`:

```python
from unittest.mock import MagicMock
from app import convocatoria

def _fake_claude(tool_input):
    # Simula la respuesta del SDK: un content block de tipo tool_use con .input = tool_input
    msg = MagicMock()
    bloque = MagicMock(); bloque.type = "tool_use"; bloque.input = tool_input
    msg.content = [bloque]
    cli = MagicMock(); cli.messages.create.return_value = msg
    return cli

def test_proponer_mociones_usa_el_tool_output(monkeypatch):
    cli = _fake_claude({"metadatos": {"fecha": "3/09/26"},
                        "agenda": [{"n": 3, "titulo": "Encargado", "tipo": "deliberativo"}],
                        "mociones": [{"titulo": "Que continúe el encargado"}]})
    monkeypatch.setattr(convocatoria, "_cliente", lambda: cli)
    out = convocatoria.proponer_mociones(b"%PDF-1.4 ...", "conv.pdf")
    assert out["mociones"][0]["titulo"] == "Que continúe el encargado"
    assert out["mociones"][0]["opciones"] == ["A favor", "En contra", "Abstención"]
    # pdf => se manda como documento, no como texto plano
    _, kwargs = cli.messages.create.call_args
    assert kwargs["model"]  # se pasó un modelo
```

- [ ] **Step 3: Correr para verlo fallar**

Run: `cd /opt/consorcios-transparentes/api && .venv/bin/python -m pytest -q tests/test_convocatoria.py::test_proponer_mociones_usa_el_tool_output`
Expected: FAIL (no existe `proponer_mociones`/`_cliente`).

- [ ] **Step 4: Implementar el cliente y `proponer_mociones`**

Agregar a `api/app/convocatoria.py`:

```python
import base64
import json
from .config import settings

_TOOL = {
    "name": "registrar_convocatoria",
    "description": "Devuelve el orden del día y las mociones votables extraídas de la convocatoria.",
    "input_schema": {
        "type": "object",
        "properties": {
            "metadatos": {"type": "object", "description": "fecha, hora, lugar, administracion, art2060 si aparecen"},
            "agenda": {"type": "array", "items": {"type": "object", "properties": {
                "n": {"type": "integer"}, "titulo": {"type": "string"},
                "tipo": {"type": "string", "enum": ["procedimental", "informativo", "deliberativo"]}}}},
            "mociones": {"type": "array", "items": {"type": "object", "properties": {
                "titulo": {"type": "string", "description": "moción afirmativa y concreta para votar"}}}},
        },
        "required": ["agenda", "mociones"],
    },
}
_PROMPT = ("Sos asistente de una asamblea de consorcio. De esta convocatoria, extraé el orden del día "
           "(clasificando cada punto como procedimental, informativo o deliberativo) y, por cada punto "
           "deliberativo, una moción afirmativa y concreta para votar. Devolvé todo con la herramienta "
           "registrar_convocatoria. No inventes puntos que no estén.")


def _cliente():
    import anthropic
    return anthropic.Anthropic(api_key=settings.anthropic_api_key)


def _contenido(data: bytes, nombre: str):
    ext = os.path.splitext(nombre)[1].lower()
    if ext == ".pdf":
        b64 = base64.standard_b64encode(data).decode()
        return [{"type": "document", "source": {"type": "base64", "media_type": "application/pdf", "data": b64}},
                {"type": "text", "text": _PROMPT}]
    texto = texto_de_docx(data) if ext == ".docx" else texto_de_doc(data) if ext == ".doc" else texto_de_pdf(data)
    return [{"type": "text", "text": _PROMPT + "\n\n--- CONVOCATORIA ---\n" + texto}]


def proponer_mociones(data: bytes, nombre: str) -> dict:
    msg = _cliente().messages.create(
        model=settings.anthropic_modelo, max_tokens=2000,
        tools=[_TOOL], tool_choice={"type": "tool", "name": "registrar_convocatoria"},
        messages=[{"role": "user", "content": _contenido(data, nombre)}])
    for bloque in msg.content:
        if getattr(bloque, "type", None) == "tool_use":
            return normalizar_propuesta(bloque.input)
    raise ValueError("el modelo no devolvió la herramienta esperada")
```

En `api/app/config.py` agregar los settings: `anthropic_api_key` (de `CT_ANTHROPIC_API_KEY`) y `anthropic_modelo` (de `CT_ANTHROPIC_MODELO`, default `"claude-sonnet-4-6"`). Seguir el patrón de los settings existentes.

- [ ] **Step 5: Correr — pasa**

Run: `cd /opt/consorcios-transparentes/api && .venv/bin/python -m pytest -q tests/test_convocatoria.py`
Expected: PASS (todos; Claude está mockeado, no pega a la API real).

- [ ] **Step 6: Commit**

```bash
cd /opt/consorcios-transparentes
git add api/app/convocatoria.py api/app/config.py api/pyproject.toml api/tests/test_convocatoria.py
git commit -m "API: cliente Claude para proponer mociones (salida estructurada por tool)"
```

---

## Task 3: Endpoint `POST /asamblea/convocatoria` (token + CORS)

**Files:**
- Create: `api/app/routers/asamblea.py`
- Modify: `api/app/main.py` (registrar router + CORS del dominio de asamblea)
- Modify: `api/app/config.py` (`asamblea_token`, `asamblea_origin`)
- Test: `api/tests/test_convocatoria.py`

- [ ] **Step 1: Test del endpoint con Claude mockeado (falla)**

Agregar a `api/tests/test_convocatoria.py` (usa el fixture `cliente` de conftest; `monkeypatch` sobre `proponer_mociones`):

```python
def test_endpoint_propone_con_token(cliente, monkeypatch):
    from app import convocatoria as conv
    monkeypatch.setattr(conv, "proponer_mociones",
                        lambda data, nombre: {"metadatos": {}, "agenda": [],
                                              "mociones": [{"titulo": "M", "opciones": ["A favor","En contra","Abstención"], "regla": "abs"}]})
    from app.config import settings
    monkeypatch.setattr(settings, "asamblea_token", "secreto")
    r = cliente.post("/asamblea/convocatoria",
                     files={"archivo": ("conv.pdf", b"%PDF-1.4 x", "application/pdf")},
                     headers={"X-Asamblea-Token": "secreto"})
    assert r.status_code == 200
    assert r.json()["mociones"][0]["titulo"] == "M"

def test_endpoint_sin_token_da_401(cliente, monkeypatch):
    from app.config import settings
    monkeypatch.setattr(settings, "asamblea_token", "secreto")
    r = cliente.post("/asamblea/convocatoria",
                     files={"archivo": ("conv.pdf", b"x", "application/pdf")})
    assert r.status_code == 401

def test_endpoint_formato_no_soportado_da_400(cliente, monkeypatch):
    from app.config import settings
    monkeypatch.setattr(settings, "asamblea_token", "secreto")
    r = cliente.post("/asamblea/convocatoria",
                     files={"archivo": ("conv.txt", b"x", "text/plain")},
                     headers={"X-Asamblea-Token": "secreto"})
    assert r.status_code == 400
```

- [ ] **Step 2: Correr para verlo fallar**

Run: `cd /opt/consorcios-transparentes/api && .venv/bin/python -m pytest -q tests/test_convocatoria.py`
Expected: FAIL (404 en el endpoint; no existe).

- [ ] **Step 3: Implementar el router**

Crear `api/app/routers/asamblea.py`:

```python
import os
from fastapi import APIRouter, File, Header, HTTPException, UploadFile

from .. import convocatoria
from ..config import settings

router = APIRouter(tags=["asamblea"])
MAX_MB = 15
EXT_OK = {".pdf", ".doc", ".docx"}


@router.post("/asamblea/convocatoria")
def convocatoria_a_mociones(archivo: UploadFile = File(...),
                            x_asamblea_token: str | None = Header(default=None)):
    if not settings.asamblea_token or x_asamblea_token != settings.asamblea_token:
        raise HTTPException(401, "Token inválido")
    ext = os.path.splitext(archivo.filename or "")[1].lower()
    if ext not in EXT_OK:
        raise HTTPException(400, "Formato no soportado; subí PDF, DOC o DOCX")
    data = archivo.file.read(MAX_MB * 1024 * 1024 + 1)
    if len(data) > MAX_MB * 1024 * 1024:
        raise HTTPException(413, f"El archivo supera los {MAX_MB} MB")
    try:
        return convocatoria.proponer_mociones(data, archivo.filename)
    except Exception as e:
        raise HTTPException(502, f"No se pudo procesar la convocatoria: {e}")
```

En `api/app/config.py`: `asamblea_token` (de `CT_ASAMBLEA_TOKEN`, default `""`) y `asamblea_origin` (de `CT_ASAMBLEA_ORIGIN`, default `"https://asamblea.neuralcore.dev"`).

En `api/app/main.py`: `from .routers import asamblea` y `app.include_router(asamblea.router)`; y en el `CORSMiddleware`, pasar `allow_origins=[settings.cors_origin, settings.asamblea_origin]` (lista) en vez de uno solo.

- [ ] **Step 4: Correr — pasan**

Run: `cd /opt/consorcios-transparentes/api && .venv/bin/python -m pytest -q`
Expected: PASS (toda la suite; los nuevos + los previos).

- [ ] **Step 5: Commit**

```bash
cd /opt/consorcios-transparentes
git add api/app/routers/asamblea.py api/app/main.py api/app/config.py api/tests/test_convocatoria.py
git commit -m "API: endpoint /asamblea/convocatoria con token y CORS para la app de asamblea"
```

---

## Task 4: Infra — LibreOffice en la imagen + variables de entorno

**Files:**
- Modify: `api/Dockerfile`
- Modify: `api/.env.example`
- Modify: `docs/DEPLOY.md`

- [ ] **Step 1: LibreOffice en la imagen (para .doc)**

En `api/Dockerfile`, en la línea de `apt-get install`, agregar `libreoffice-writer` (más liviano que `libreoffice` completo) a la lista: `poppler-utils postgresql-client libzbar0 libreoffice-writer`. Nota en el plan: suma ~300-400 MB a la imagen; es el costo de soportar `.doc` en el server (PDF y DOCX no lo necesitan).

- [ ] **Step 2: Variables de entorno**

En `api/.env.example` agregar, con comentario:
```
CT_ANTHROPIC_API_KEY=   # key de la Claude API (para proponer mociones desde la convocatoria)
CT_ANTHROPIC_MODELO=claude-sonnet-4-6
CT_ASAMBLEA_TOKEN=      # token que la app de asamblea manda en X-Asamblea-Token
CT_ASAMBLEA_ORIGIN=https://asamblea.neuralcore.dev
```

- [ ] **Step 3: Documentar en DEPLOY.md**

Agregar una nota breve en `docs/DEPLOY.md` (sección de notas): el endpoint `/asamblea/convocatoria` usa la Claude API (`CT_ANTHROPIC_API_KEY`) y un token (`CT_ASAMBLEA_TOKEN`) que debe coincidir con el embebido en la app de asamblea; la imagen incluye `libreoffice-writer` para los `.doc`.

- [ ] **Step 4: Commit**

```bash
cd /opt/consorcios-transparentes
git add api/Dockerfile api/.env.example docs/DEPLOY.md
git commit -m "Infra: LibreOffice en la imagen de la API y variables para convocatoria→mociones"
```

---

## Task 5: UI en la app — subir convocatoria + pantalla de revisión

**Files:**
- Modify: `apps/asamblea/make_votacion.py`

El `CT_ASAMBLEA_TOKEN` y la URL de la API se embeben en el build (como ya se hace con otras constantes). La API es `https://api-consorcio.neuralcore.dev`.

- [ ] **Step 1: Botón mod-only "Subir convocatoria…"**

En "Más opciones" (`#dlgMas`, junto a los otros botones mod-only), agregar `<button class="btn" id="btnConvocatoria">Subir convocatoria (IA)…</button>` y un `<input type="file" id="convFile" accept=".pdf,.doc,.docx" hidden>`. Agregar `'btnConvocatoria'` al guard de `needMod` (línea de `['btnPresentes',...]`).

- [ ] **Step 2: Subida + llamada al endpoint**

En el JS, al click en `#btnConvocatoria` → `convFile.click()`; al `change` del input, subir el archivo:
```javascript
async function subirConvocatoria(file){
  toast('Analizando la convocatoria…');
  const fd = new FormData(); fd.append('archivo', file);
  try{
    const r = await fetch(API_URL + '/asamblea/convocatoria', {method:'POST', headers:{'X-Asamblea-Token': ASAMBLEA_TOKEN}, body: fd});
    if(!r.ok) throw new Error('HTTP '+r.status);
    const prop = await r.json();
    abrirRevisionMociones(prop);
  }catch(e){ toast('No se pudo analizar: '+e.message+'. Podés cargar las mociones a mano.'); }
}
```
`API_URL` y `ASAMBLEA_TOKEN` se inyectan desde el generador (nuevos marcadores `__API_URL__`/`__ASAMBLEA_TOKEN__` reemplazados en `make_votacion.py`, leídos de variables de entorno al generar; default razonable para `API_URL`).

- [ ] **Step 3: Pantalla de revisión/edición**

Un diálogo `#dlgRevision` que liste las mociones propuestas (cada una: input de título editable, selector de regla, botón borrar) + un botón "Agregar moción" + mostrar la agenda/metadatos como referencia (solo lectura). Botón **"Cargar estas mociones"** que, con `confirm('Esto reemplaza las mociones actuales. ¿Seguir?')`, hace:
```javascript
S.mociones = mocionesEditadas.map(m=>({titulo:m.titulo, opciones:m.opciones||['A favor','En contra','Abstención'], regla:m.regla||'abs', votos:{}}));
S.activa = 0; save(); sync.send({t:'mociones', v:S.mociones}); renderAll(); $('#dlgRevision').close();
```
(usa el mismo evento `{t:'mociones'}` que ya sincroniza Code.gs).

- [ ] **Step 4: Regenerar y verificar**

Run: `cd /opt/consorcios-transparentes/apps/asamblea && python3 make_votacion.py && node --test`
Expected: `ok` + 26 pass. Greps: `grep -c "btnConvocatoria\|subirConvocatoria\|dlgRevision" pages-out/index.html` ≥1; `grep -c "__API_URL__\|__ASAMBLEA_TOKEN__\|__CONTENT__\|__LOGICA__\|__MARKED__" pages-out/index.html` == 0.

- [ ] **Step 5: Commit**

```bash
cd /opt/consorcios-transparentes
git add apps/asamblea/make_votacion.py
git commit -m "Asamblea: subir convocatoria (IA) con pantalla de revisión y carga de mociones"
```

---

## Task 6: Deploy (requiere confirmación del dueño; no lo ejecuta un subagente)

- [ ] **Step 1: Secrets en el server**

En el `.env` de la API: `CT_ANTHROPIC_API_KEY`, `CT_ANTHROPIC_MODELO`, `CT_ASAMBLEA_TOKEN` (un token largo), `CT_ASAMBLEA_ORIGIN`. El mismo `CT_ASAMBLEA_TOKEN` se usa al generar la app (Task 5) — deben coincidir.

- [ ] **Step 2: Rebuild y arranque de la API**

```bash
cd /opt/consorcios-transparentes && docker compose build api && docker compose up -d api
```

- [ ] **Step 3: Regenerar y redeployar la app**

```bash
cd apps/asamblea && python3 make_votacion.py
npx wrangler pages deploy pages-out --project-name asamblea-rivadavia --branch main --commit-dirty=true
```

- [ ] **Step 4: Prueba end-to-end**

En la app (modo moderador) subir una convocatoria real (pdf/doc/docx) y confirmar que propone las mociones, que se pueden editar y cargar, y que se sincronizan. Verificar también una convocatoria mala (archivo no soportado → mensaje claro).

---

## Notas de cierre
- Actualizar `docs/ESTADO.md` con el ciclo (convocatoria→mociones).
- La memoria `app-asamblea-ciclo` ya tiene la arquitectura; al terminar, marcar implementado.
