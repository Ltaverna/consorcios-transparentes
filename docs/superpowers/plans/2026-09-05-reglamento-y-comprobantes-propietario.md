# Reglamento en el panel + comprobantes para propietarios — Plan de implementación

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** el reglamento de copropiedad consultable desde el panel (transcripción + PDF), y los propietarios pueden ver los hallazgos publicados con sus comprobantes descargables.

**Architecture:** tres endpoints de reglamento en el router de consorcio (subida auditor, PDF con descarga forzada vía `_servir`, transcripción servida directa); los routers de hallazgos y documentos ganan el rol propietario con filtro `publicado=true` (detalle sin eventos; documentos solo si su `gasto_n` está en las refs de un hallazgo publicado). Front: página `/reglamento` (react-markdown), subida en Consorcio, y sección "Hallazgos publicados" en `/mi-unidad`.

**Tech Stack:** lo existente + `react-markdown` en web.

**Spec:** `docs/superpowers/specs/2026-09-05-reglamento-y-comprobantes-propietario-design.md`. **Ajuste a la spec detectado al planificar** (anotar en el cierre): el propietario también necesita `GET /documentos?liquidacion_id=` para descubrir los IDs — se abre con el mismo predicado de publicación que `contenido`.

**Contexto de la máquina:** venvs listos (api hoy: 98 passed · web: 36 passed con `NODE_OPTIONS='--experimental-require-module' npm test` — Node 22.11). Rama: `reglamento-propietarios` desde `main`. Commits en español + trailer. Producción en vivo: nada se deploya hasta el cierre con confirmación del usuario.

---

### Task 1: API — endpoints del reglamento

**Files:**
- Modify: `api/app/routers/consorcio.py`
- Test: `api/tests/test_consorcio_api.py` (verificar el nombre real: `ls api/tests/` — usar el archivo de tests del router de consorcio existente)

- [ ] **Step 1: Tests que fallan.** En el archivo de tests del consorcio (reusar fixtures `db`/`cliente`/`auditor` de `conftest.py`; para el rol propietario, copiar el patrón de login-unidad que ya usan los tests de la API — grep `login-unidad` en `api/tests/`):

```python
def test_reglamento_subir_requiere_auditor_y_sirve_a_cualquier_sesion(db, auditor, cliente):
    import io
    r = auditor.post("/consorcio/reglamento",
                     files={"pdf": ("reglamento.pdf", io.BytesIO(b"%PDF-reglamento"), "application/pdf"),
                            "transcripcion": ("reglamento.md", io.BytesIO("# Reglamento\ntexto".encode()), "text/markdown")})
    assert r.status_code == 200 and r.json() == {"ok": True, "pdf": True, "transcripcion": True}
    est = auditor.get("/consorcio/reglamento")
    assert est.json() == {"pdf": True, "transcripcion": True}
    pdf = auditor.get("/consorcio/reglamento/pdf")
    assert pdf.status_code == 200
    assert "attachment" in pdf.headers.get("content-disposition", "")
    md = auditor.get("/consorcio/reglamento/transcripcion")
    assert md.status_code == 200 and "Reglamento" in md.text
    assert md.headers["content-type"].startswith("text/markdown")


def test_reglamento_sin_subir_da_404_y_estado_false(db, auditor):
    assert auditor.get("/consorcio/reglamento").json() == {"pdf": False, "transcripcion": False}
    assert auditor.get("/consorcio/reglamento/pdf").status_code == 404
    assert auditor.get("/consorcio/reglamento/transcripcion").status_code == 404


def test_reglamento_subir_sin_archivos_o_sin_rol_falla(db, auditor, cliente):
    assert auditor.post("/consorcio/reglamento").status_code == 422
    # sin sesión → 401
    assert cliente.post("/consorcio/reglamento").status_code in (401, 403)
```

(Si el fixture `cliente` conserva la cookie del auditor por orden de fixtures, usar un TestClient limpio para el caso sin sesión — mirar cómo lo resuelven los tests vecinos.)

- [ ] **Step 2:** `cd api && .venv/bin/python -m pytest -q tests/<archivo>` → FAIL (rutas inexistentes).

- [ ] **Step 3: Implementar.** En `api/app/routers/consorcio.py` (imports nuevos: `Request`, `Response`, `UploadFile`, `File` de fastapi; `from .documentos import _servir`):

```python
RUTA_REGLAMENTO = {"pdf": "consorcio/reglamento.pdf", "transcripcion": "consorcio/reglamento.md"}
MAX_REGLAMENTO_MB = 20


@router.get("/consorcio/reglamento")
def estado_reglamento(request: Request, s: dict = Depends(security.sesion)):
    st = request.app.state.storage
    return {tipo: st.existe(key) for tipo, key in RUTA_REGLAMENTO.items()}


@router.post("/consorcio/reglamento")
def subir_reglamento(request: Request, pdf: UploadFile | None = File(None),
                     transcripcion: UploadFile | None = File(None),
                     s: dict = Depends(security.requiere("auditor"))):
    if not pdf and not transcripcion:
        raise HTTPException(422, "Subí el PDF, la transcripción o ambos")
    st = request.app.state.storage
    tope = MAX_REGLAMENTO_MB * 1024 * 1024
    for archivo, tipo in ((pdf, "pdf"), (transcripcion, "transcripcion")):
        if not archivo:
            continue
        data = archivo.file.read(tope + 1)
        if len(data) > tope:
            raise HTTPException(413, f"El archivo supera los {MAX_REGLAMENTO_MB} MB")
        st.guardar(RUTA_REGLAMENTO[tipo], data)
    return {"ok": True, **{t: st.existe(k) for t, k in RUTA_REGLAMENTO.items()}}


@router.get("/consorcio/reglamento/{tipo}")
def ver_reglamento(tipo: str, request: Request, s: dict = Depends(security.sesion)):
    key = RUTA_REGLAMENTO.get(tipo)
    if not key:
        raise HTTPException(404, "No existe ese tipo de documento")
    st = request.app.state.storage
    if not st.existe(key):
        raise HTTPException(404, "El reglamento todavía no está cargado")
    if tipo == "pdf":
        return _servir(request, key)  # descarga forzada, local o R2
    # La transcripción se sirve directa (sin redirect a R2): el front la lee con fetch y es chica.
    return Response(st.leer(key), media_type="text/markdown; charset=utf-8",
                    headers={"X-Content-Type-Options": "nosniff"})
```

Nota de orden: la ruta `GET /consorcio/reglamento` (estado) debe declararse ANTES de `GET /consorcio/reglamento/{tipo}` si el router matchea en orden; verificar que `/consorcio` (el `ver` existente) no capture `/consorcio/reglamento` (son paths distintos en FastAPI, no hay conflicto).

- [ ] **Step 4:** Suite api completa → 101 passed (98 + 3).

- [ ] **Step 5: Commit.**

```bash
git add api/app/routers/consorcio.py api/tests/
git commit -m "API: reglamento del consorcio (subida del auditor, consulta de cualquier sesión)"
```

### Task 2: API — hallazgos publicados y documentos para propietarios

**Files:**
- Modify: `api/app/routers/hallazgos.py`, `api/app/routers/documentos.py`
- Test: `api/tests/test_hallazgos_api.py`, `api/tests/test_documentos_api.py` (nombres reales: verificar con `ls api/tests/`)

- [ ] **Step 1: Tests que fallan.** Reusar el patrón de propietario de los tests existentes (login-unidad). Comportamientos a fijar (adaptar el armado de datos al estilo del archivo — hay helpers como `subir` en `test_liquidaciones_api`):

```python
def test_propietario_lista_solo_hallazgos_publicados(db, auditor, propietario):
    # dado un hallazgo publicado y otro no (crearlos por modelo o publicar vía POST del auditor)
    r = propietario.get("/hallazgos")
    assert r.status_code == 200
    assert all(h["publicado"] for h in r.json())
    assert len(r.json()) == 1


def test_propietario_detalle_sin_eventos_y_404_para_no_publicado(db, auditor, propietario):
    r = propietario.get(f"/hallazgos/{id_publicado}")
    assert r.status_code == 200
    assert "eventos" not in r.json()
    assert "evidencia" in r.json() and "recomendacion" in r.json()
    assert propietario.get(f"/hallazgos/{id_no_publicado}").status_code == 404


def test_propietario_descarga_documento_de_hallazgo_publicado(db, auditor, propietario):
    # documento con gasto_n presente en las refs del hallazgo publicado → 200 attachment
    r = propietario.get(f"/documentos/{doc_ok.id}/contenido", follow_redirects=False)
    assert r.status_code in (200, 307)
    # documento de un gasto sin hallazgo publicado → 403; con vista=1 → 403 aunque esté publicado
    assert propietario.get(f"/documentos/{doc_no.id}/contenido").status_code == 403
    assert propietario.get(f"/documentos/{doc_ok.id}/contenido?vista=1").status_code == 403


def test_propietario_lista_documentos_de_publicados(db, auditor, propietario):
    r = propietario.get(f"/documentos?liquidacion_id={liq_id}")
    assert r.status_code == 200
    assert {d["id"] for d in r.json()} == {doc_ok.id}   # solo los de hallazgos publicados
```

Los nombres `id_publicado`, `doc_ok`, etc. son del armado de datos de cada test (hallazgo con `refs=["2"]` y documento con `gasto_n=2` en la misma liquidación; el no-permitido con `gasto_n=3`). Escribir el armado completo en el test real.

- [ ] **Step 2:** correr esos archivos → FAIL (403 del `requiere` actual).

- [ ] **Step 3: Implementar.**
- `hallazgos.py`:
  - `listar`: `requiere("auditor", "consejo", "moderador", "propietario")`; tras armar `q`, si `s["rol"] == "propietario"`: `q = q.filter(models.Hallazgo.publicado == True)`.
  - `detalle`: mismo `requiere` ampliado; si `s["rol"] == "propietario"` y (`not h` o `not h.publicado`) → 404 (mismo mensaje que el 404 normal — no revela existencia); la respuesta del propietario omite la clave `eventos` (y no consulta usuarios).
- `documentos.py`:
  - Helper del módulo:

```python
def _accesible_para_propietario(db: Session, d: models.Documento) -> bool:
    """Un propietario solo ve documentos citados por un hallazgo publicado (gasto_n en refs)."""
    if d.gasto_n is None:
        return False
    filas = db.query(models.Hallazgo).filter_by(liquidacion_id=d.liquidacion_id, publicado=True).all()
    return any(str(d.gasto_n) in (h.refs or []) for h in filas)
```

  - `listar` (`GET /documentos`): `requiere(..., "propietario")`; si propietario, filtrar la lista con `_accesible_para_propietario`.
  - `contenido`: `requiere(..., "propietario")`; si propietario: `vista` pedida → 403 "Solo el equipo puede ver documentos embebidos"; documento no accesible → 403 "No autorizado para este documento". El attachment ya es el default.

- [ ] **Step 4:** Suite api completa → 105 passed (101 + 4).

- [ ] **Step 5: Commit.**

```bash
git add api/app/routers/hallazgos.py api/app/routers/documentos.py api/tests/
git commit -m "API: hallazgos publicados y sus comprobantes visibles para propietarios"
```

### Task 3: Web — página `/reglamento`, subida en Consorcio y accesos

**Files:**
- Create: `web/app/reglamento/page.tsx`
- Modify: `web/proxy.ts` (matcher), `web/lib/api.ts`, `web/components/sidebar.tsx`, `web/app/mi-unidad/page.tsx` (link), `web/app/panel/consorcio/page.tsx` (subida, gated auditor), `web/package.json` (+react-markdown)
- Test: `web/tests/reglamento.test.tsx`, `web/tests/consorcio.test.tsx`

- [ ] **Step 1:** `cd web && npm i react-markdown` (dependencia de runtime).

- [ ] **Step 2: Tests que fallan.** Crear `web/tests/reglamento.test.tsx` (patrón MSW de los tests vecinos):

```tsx
import { render, screen } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { servidor, API } from "./msw";
import PaginaReglamento from "@/app/reglamento/page";

test("renderiza la transcripción y el botón del PDF", async () => {
  servidor.use(
    http.get(`${API}/consorcio/reglamento`, () => HttpResponse.json({ pdf: true, transcripcion: true })),
    http.get(`${API}/consorcio/reglamento/transcripcion`, () => HttpResponse.text("# Reglamento de Copropiedad\n\nArtículo primero.")),
  );
  render(<PaginaReglamento />);
  expect(await screen.findByText("Reglamento de Copropiedad")).toBeInTheDocument();
  expect(screen.getByText(/Artículo primero/)).toBeInTheDocument();
  expect(screen.getByRole("link", { name: /Descargar el PDF/ })).toBeInTheDocument();
});

test("sin reglamento cargado muestra el estado vacío", async () => {
  servidor.use(http.get(`${API}/consorcio/reglamento`, () => HttpResponse.json({ pdf: false, transcripcion: false })));
  render(<PaginaReglamento />);
  expect(await screen.findByText(/todavía no está cargado/)).toBeInTheDocument();
});
```

En `web/tests/consorcio.test.tsx`, agregar al test de consejo existente el assert de que la subida del reglamento NO aparece, y un test nuevo de que para auditor SÍ (los textos exactos según lo que implementes — reportarlos):

```tsx
expect(screen.queryByText(/Reglamento/)).not.toBeInTheDocument();   // en el test de consejo
```

- [ ] **Step 3:** `NODE_OPTIONS='--experimental-require-module' npm test` → FAIL.

- [ ] **Step 4: Implementar.**
- `web/lib/api.ts`: `urlReglamento(tipo: "pdf" | "transcripcion")` (estilo `urlInforme`); en el objeto `api`: `estadoReglamento()` (GET), `textoReglamento()` (GET que devuelve `res.text()` — mirar el helper `pedir`; si `pedir` solo hace JSON, agregar un `pedirTexto` mínimo), `subirReglamento(form: FormData)` (POST multipart, estilo `subirLiquidacion`).
- `web/app/reglamento/page.tsx` (client): carga estado + transcripción; render con `<ReactMarkdown>{texto}</ReactMarkdown>` dentro de un contenedor con la tipografía del panel (`prose` no existe — usar clases propias sobrias, mirar mi-unidad); botón/link "Descargar el PDF escaneado" → `urlReglamento("pdf")` (solo si `estado.pdf`); estado vacío: "El reglamento todavía no está cargado." y, si `useRol()` da un rol de equipo, link a `/panel/consorcio`.
- `web/proxy.ts`: matcher pasa a `["/panel/:path*", "/panel", "/mi-unidad", "/reglamento"]`.
- `web/components/sidebar.tsx`: ítem "Reglamento" → `/reglamento` (mirar cómo se definen los ítems existentes y seguir el patrón, ícono de lucide a elección coherente, p.ej. `BookOpen`).
- `web/app/mi-unidad/page.tsx`: link/tarjeta "Reglamento de copropiedad" → `/reglamento` (estilo de las cards existentes).
- `web/app/panel/consorcio/page.tsx`: dentro del bloque ya gated por `rol === "auditor"`, Card "Reglamento" con dos `<input type="file">` (pdf, transcripcion) y botón subir → `api.subirReglamento(formData)` + toast; mostrar el estado actual (`estadoReglamento`).

- [ ] **Step 5:** `NODE_OPTIONS='--experimental-require-module' npm test` → 40 passed (36 + 3 nuevos + el assert agregado no suma test). `npm run build` → OK.

- [ ] **Step 6: Commit.**

```bash
git add web/app/reglamento web/proxy.ts web/lib/api.ts web/components/sidebar.tsx web/app/mi-unidad/page.tsx web/app/panel/consorcio/page.tsx web/package.json web/package-lock.json web/tests/reglamento.test.tsx web/tests/consorcio.test.tsx
git commit -m "Web: el reglamento consultable desde el panel y la vista del propietario"
```

### Task 4: Web — "Hallazgos publicados" en `/mi-unidad`

**Files:**
- Modify: `web/app/mi-unidad/page.tsx`, `web/lib/api.ts` (si falta el helper de documentos por liquidación para el rol)
- Test: `web/tests/mi-unidad.test.tsx`

- [ ] **Step 1: Test que falla.** En `web/tests/mi-unidad.test.tsx` (sumar handlers a los existentes del archivo):

```tsx
test("muestra los hallazgos publicados con sus comprobantes", async () => {
  servidor.use(
    http.get(`${API}/hallazgos`, () => HttpResponse.json([
      { id: 61, liquidacion_id: 2, periodo: "2026-08", regla: "comprobantes", origen: "comprobantes",
        severidad: "CRÍTICO", area: "Comprobantes", titulo: "Pago a un tercero distinto del proveedor",
        monto: 2552000, estado: "pendiente", publicado: true },
    ])),
    http.get(`${API}/hallazgos/61`, () => HttpResponse.json({
      id: 61, liquidacion_id: 2, periodo: "2026-08", regla: "comprobantes", origen: "comprobantes",
      severidad: "CRÍTICO", area: "Comprobantes", titulo: "Pago a un tercero distinto del proveedor",
      monto: 2552000, estado: "pendiente", publicado: true, refs: ["32"],
      evidencia: "El pago fue a otro CUIT", recomendacion: "Pedir explicación", respuesta_admin: "",
    })),
    http.get(`${API}/documentos`, () => HttpResponse.json([
      { id: 400, gasto_n: 32, tipo: "pago", hash: "x", metadatos: {} },
    ])),
  );
  render(<PaginaMiUnidad />);
  expect(await screen.findByText(/Pago a un tercero/)).toBeInTheDocument();
  expect(screen.getByText(/El pago fue a otro CUIT/)).toBeInTheDocument();
  expect(screen.getByRole("link", { name: /pago/i })).toHaveAttribute("href", expect.stringContaining("/documentos/400/contenido"));
});
```

(Ajustar el componente importado y los handlers base al contenido real del archivo — los tests existentes de mi-unidad ya mockean `/mi-unidad` y el informe; mantenerlos.)

- [ ] **Step 2:** correr → FAIL.

- [ ] **Step 3: Implementar.** En `web/app/mi-unidad/page.tsx`, debajo del informe embebido: sección "Hallazgos publicados" que hace `api.listarHallazgos()` (el back ya filtra para el rol) y por cada uno trae el detalle + documentos de su liquidación (`api.listarDocumentos(liquidacion_id)` filtrando por `refs`/`gasto_n`, mismo criterio que usa la página de hallazgos del panel — leerla). Render por hallazgo: chip de severidad (reusar el componente existente de chips si es importable sin el contexto del panel), título, monto, evidencia, qué pedir, respuesta de la administración si no está vacía, y links de descarga por documento (`urlContenidoDocumento(d.id)` — SIN `vista`). Sin botones de acción. Si no hay hallazgos publicados, la sección no se muestra.

- [ ] **Step 4:** `NODE_OPTIONS='--experimental-require-module' npm test` → 41 passed. `npm run build` → OK.

- [ ] **Step 5: Commit.**

```bash
git add web/app/mi-unidad/page.tsx web/lib/api.ts web/tests/mi-unidad.test.tsx
git commit -m "Web: hallazgos publicados con comprobantes en la vista del propietario"
```

### Task 5: Cierre — suites, spec/estado, merge y puesta en producción

- [ ] **Step 1:** Suites: api 105 · web 41 · engine 45 (no se tocó — correr igual). `npm run build` OK.
- [ ] **Step 2:** Spec: agregar en §3 la línea del ajuste (`GET /documentos` abierto al propietario con el mismo predicado). `docs/ESTADO.md`: anotar reglamento consultable + hallazgos publicados con comprobantes para propietarios (rama, spec, conteos de tests).
- [ ] **Step 3:** Commit docs + merge a `main`.
- [ ] **Step 4: Producción (CON confirmación del usuario):** push; `docker compose build && docker compose up -d`; `cd web && npm run deploy:cf`. Después, **subir el reglamento real** vía la API con la sesión del auditor (los archivos están en `~/consorcio-transparente-privado/reglamento/`: `Reglamento de Copropiedad - Rivadavia 2069.pdf` y `reglamento-articulos.md`). Smoke: como propietario (código de prueba) ver `/reglamento`, descargar el PDF, y en `/mi-unidad` ver los hallazgos publicados y bajar un comprobante; verificar que un documento de un hallazgo NO publicado da 403.
