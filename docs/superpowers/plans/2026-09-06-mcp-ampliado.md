# MCP ampliado — Plan de implementación

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** el MCP (y la API) ganan texto de comprobantes, búsqueda dentro de facturas, deudores, detalle de cuadre y resumen mensual — todo read-only.

**Architecture:** dos endpoints nuevos en la API (`/documentos/{id}/texto` con pdftotext + cache por hash; `/consulta/comprobantes` de búsqueda; `/consulta/deudores` desde `liq.datos`); cinco tools nuevas en `servidor_mcp.py`, de las cuales `detalle_liquidacion` y `resumen_mensual` solo orquestan endpoints existentes.

**Tech Stack:** lo existente (poppler ya está en la imagen de la API).

**Spec:** `docs/superpowers/specs/2026-09-06-mcp-ampliado-design.md`.

**Contexto de la máquina:** suites hoy: api 123 · engine 53 · web 42. Rama: `mcp-ampliado` desde `main`. Commits en español + trailer. Deploy solo en el cierre con confirmación.

---

### Task 1: API — texto de comprobantes, búsqueda y deudores

**Files:**
- Modify: `api/app/routers/documentos.py` (endpoint texto), `api/app/routers/consulta.py` (comprobantes y deudores)
- Test: `api/tests/test_documentos_api.py`, `api/tests/test_consulta_api.py`

- [x] **Step 0: Verificar el shape de `liq.datos`.** Leer `api/app/ingesta.py` y el endpoint `/mi-unidad` (`api/app/routers/documentos.py`) para ver EXACTAMENTE cómo está guardado el estado de cuenta por unidad (deuda, expensas del mes, piso_depto). Los campos del endpoint de deudores salen de ahí — reportar el shape encontrado.

- [x] **Step 1: Tests que fallan.**

En `api/tests/test_documentos_api.py` (generar un PDF sintético con texto conocido — sin dependencias: un PDF mínimo válido se puede armar a mano con el esqueleto clásico de objetos + stream `BT /F1 12 Tf (CUIT 30-11222333-4 IMPERMEABILIZACION) Tj ET`; si resulta frágil, usar `pdftotext` inverso no existe — alternativa robusta: generar con `fpdf2`? NO — sin deps nuevas: el PDF mínimo a mano es estándar y estable; probalo primero en un script efímero):

```python
def test_texto_de_documento_pdf(db, auditor):
    # documento con un PDF sintético en el storage que contiene "IMPERMEABILIZACION"
    r = auditor.get(f"/documentos/{doc_id}/texto")
    assert r.status_code == 200
    assert r.json()["extraible"] is True
    assert "IMPERMEABILIZACION" in r.json()["texto"]


def test_texto_de_documento_no_extraible(db, auditor):
    # documento cuyo contenido es b"\x89PNG..." (no PDF)
    r = auditor.get(f"/documentos/{doc_png_id}/texto")
    assert r.status_code == 200
    assert r.json() == {"texto": "", "extraible": False}
```

En `api/tests/test_consulta_api.py`:

```python
def test_busca_en_comprobantes(db, auditor):
    # con el PDF sintético de arriba asociado a un gasto del período
    r = auditor.get("/consulta/comprobantes?q=impermeabilizacion")
    assert r.status_code == 200
    res = r.json()["resultados"]
    assert len(res) == 1 and res[0]["documento_id"] == doc_id
    assert "IMPERMEABILIZACION" in res[0]["fragmento"]


def test_deudores_ordenados(db, auditor):
    # la liquidación real subida tiene deudores en datos (verificar en Step 0 cuántos y elegir asserts)
    r = auditor.get("/consulta/deudores?periodo=<el de la liquidación subida>")
    assert r.status_code == 200
    ds = r.json()["deudores"]
    assert ds == sorted(ds, key=lambda d: -d["deuda"])
    assert {"uf", "piso_depto", "deuda", "meses_equivalentes"} <= set(ds[0].keys())
    assert r.json()["total"] > 0
```

(Y el 403 de propietario para los tres endpoints, sumado al test de roles existente.)

- [x] **Step 2:** correr → FAIL.

- [x] **Step 3: Implementar.**
- `documentos.py`: `GET /documentos/{d_id}/texto` (equipo-only, mismo `requiere` que listar):

```python
_CACHE_TEXTO: dict[str, str] = {}   # hash del documento → texto extraído (contenido inmutable)


@router.get("/documentos/{d_id}/texto")
def texto(d_id: int, request: Request, db: Session = Depends(get_db),
          s: dict = Depends(security.requiere("auditor", "consejo", "moderador"))):
    d = db.get(models.Documento, d_id)
    if not d:
        raise HTTPException(404, "No existe ese documento")
    if d.hash in _CACHE_TEXTO:
        t = _CACHE_TEXTO[d.hash]
        return {"texto": t, "extraible": bool(t)}
    raw = request.app.state.storage.leer(d.archivo_key)
    t = ""
    if raw[:5] == b"%PDF-":
        with tempfile.NamedTemporaryFile(suffix=".pdf") as f:
            f.write(raw); f.flush()
            try:
                out = subprocess.run(["pdftotext", "-layout", f.name, "-"],
                                     capture_output=True, timeout=10)
                t = out.stdout.decode("utf-8", "ignore")[:100_000].strip()
            except (subprocess.TimeoutExpired, OSError):
                t = ""
    _CACHE_TEXTO[d.hash] = t
    return {"texto": t, "extraible": bool(t)}
```

- `consulta.py`: `GET /consulta/comprobantes?q=&periodo=` — itera los documentos (del período si se dio, join con Liquidacion), reusa la MISMA extracción/cache (factorizar la función de extracción a `documentos.py` y exportarla, o moverla a un helper compartido — decidir por claridad, sin duplicar); por cada doc cuyo texto contenga `q` (case-insensitive), armar el fragmento ±200 chars del primer match; shape del spec. `GET /consulta/deudores?periodo=` — del `datos` de la liquidación del período (o la última), según el shape del Step 0; `meses_equivalentes = deuda / total_mes` de esa unidad (guarda de división por cero → None), orden deuda desc, incluir `{"deudores": [...], "total": suma}`.

- [x] **Step 4:** suite api completa → 123 + 5 = 128 passed (ajustar al número real).

- [x] **Step 5: Commit.**

```bash
git add api/app/routers/documentos.py api/app/routers/consulta.py api/tests/
git commit -m "API: texto de comprobantes con búsqueda y consulta de deudores"
```

### Task 2: MCP — cinco tools nuevas

**Files:**
- Modify: `api/servidor_mcp.py`
- Test: `api/tests/test_mcp.py`

- [ ] **Step 1: Tests que fallan.** Extender `ClienteFalso` con los paths nuevos (`/documentos/N/texto`, `/consulta/comprobantes`, `/consulta/deudores`, `/liquidaciones/2` detalle con checks) y tests:

```python
def test_leer_comprobante(monkeypatch): ...      # texto presente; y el caso extraible=False → aviso claro
def test_buscar_en_comprobantes(monkeypatch): ...  # fragmento en la salida con documento y gasto
def test_deudores_y_resumen(monkeypatch): ...    # deudores tabla legible; resumen_mensual contiene cuadre,
                                                  # top gastos, hallazgos y deudores; y con una fuente rota
                                                  # (get que lanza para /hallazgos) el resumen igual sale
                                                  # con "hallazgos: no disponible"
```

(Escribir los tests completos con asserts concretos sobre los strings, siguiendo el estilo del archivo.)

- [ ] **Step 2:** correr → FAIL.

- [ ] **Step 3: Implementar** las tools (todas `_con_api`, registradas en el loop):
- `leer_comprobante(documento_id: int) -> str`
- `buscar_en_comprobantes(texto: str, periodo: str = "") -> str`
- `deudores(periodo: str = "") -> str`
- `detalle_liquidacion(periodo: str) -> str` — `GET /liquidaciones` para mapear período→id, después `GET /liquidaciones/{id}`: estado, cuadra, checks_ok/mal (y los checks fallidos si hay), totales por categoría.
- `resumen_mensual(periodo: str = "") -> str` — período default: el más reciente de `GET /liquidaciones`. Compone: detalle_liquidacion + top 10 de `/consulta/gastos` del período + hallazgos del período + agregados por proveedor con |variacion| > 0.2 + total de deudores. CADA sección en su propio try/except → "sección: no disponible" si falla (degradación por partes, spec §4).

- [ ] **Step 4:** suite api → +3 (reportar número). Smoke local del server como en C3 (arranca, tools/list incluye las 12).

- [ ] **Step 5: Commit.**

```bash
git add api/servidor_mcp.py api/tests/test_mcp.py
git commit -m "MCP: comprobantes, deudores, cuadre y resumen mensual"
```

### Task 3: Cierre — merge, deploy y prueba real (CON confirmación)

- [ ] **Step 1:** Suites completas; revisión final de la rama; ESTADO.md al día; merge a `main`.
- [ ] **Step 2 (confirmación):** push → `docker compose build && docker compose up -d api mcp` (la API cambia: recrearla; el panel no se toca — sin deploy de front).
- [ ] **Step 3: Smoke real:** vía MCP en producción: `resumen_mensual()` devuelve el resumen de agosto; `buscar_en_comprobantes("impermeabilizacion")` encuentra las facturas de Saczewiczyk; `deudores()` lista a DEL VALLE arriba. Avisar al usuario que reconecte los conectores para ver las tools nuevas.
