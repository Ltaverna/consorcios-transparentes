# Visor seguro + panel de solo lectura por rol — Plan de implementación

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** restaurar la vista previa embebida de comprobantes (solo equipo, sin aflojar la descarga forzada) y ocultar los controles de auditor cuando entra consejo/moderador.

**Architecture:** la API gana `?vista=1` en `/documentos/{id}/contenido` (reusa `_servir(attachment=False)`, mismo camino que los informes); el front construye la URL con `vista` para el iframe y agrega un `RolProvider` (client context montado en el layout del panel, que ya conoce `yo.rol`) con `useRol()` para condicionar los controles de escritura.

**Tech Stack:** lo existente (FastAPI + pytest · Next 16 + Vitest/MSW). Sin dependencias nuevas.

**Spec:** `docs/superpowers/specs/2026-09-05-visor-y-gating-rol-design.md`.

**Contexto de la máquina:** venv en `api/.venv` (suite hoy: 93 passed). Web: Node 22.11 → los tests corren con `NODE_OPTIONS='--experimental-require-module' npm test` (hoy: 29 passed). Rama de trabajo: `visor-gating-rol` desde `main`. Commits en español + trailer de atribución de la sesión.

---

### Task 1: API — `?vista=1` sirve inline para el equipo

**Files:**
- Modify: `api/app/routers/documentos.py`
- Test: `api/tests/test_documentos_api.py`

- [ ] **Step 1: Test que falla.** Agregar a `api/tests/test_documentos_api.py` (usa el mismo patrón de `StorageEspia` del test de descarga forzada que ya está en ese archivo):

```python
def test_contenido_con_vista_sirve_inline(db, auditor):
    from .test_liquidaciones_api import subir
    llamadas = []
    class StorageEspia:
        def url_firmada(self, key, segundos=900, descarga=False):
            llamadas.append((key, descarga))
            return "https://r2.example/" + key
        def leer(self, key): return b""
        def guardar(self, key, data): pass
        def existe(self, key): return True
        def borrar(self, key): pass
    liq_id = subir(auditor).json()["id"]
    d = models.Documento(liquidacion_id=liq_id, tipo="factura", archivo_key="comprobantes/2026-08/f.pdf")
    db.add(d)
    db.commit()
    from app.main import app
    espia = StorageEspia()
    original = app.state.storage
    app.state.storage = espia
    try:
        r_vista = auditor.get(f"/documentos/{d.id}/contenido?vista=1", follow_redirects=False)
        r_descarga = auditor.get(f"/documentos/{d.id}/contenido", follow_redirects=False)
    finally:
        app.state.storage = original
    assert (d.archivo_key, False) in llamadas   # vista=1 → URL firmada inline
    assert (d.archivo_key, True) in llamadas    # sin vista → attachment
    assert r_vista.status_code == 307
    assert "attachment" not in r_vista.headers.get("content-disposition", "")
    assert "attachment" in r_descarga.headers.get("content-disposition", "")
```

- [ ] **Step 2: Verificar que falla.** `cd api && .venv/bin/python -m pytest -q tests/test_documentos_api.py` → FAIL: `(d.archivo_key, False)` no está en `llamadas` (el endpoint ignora `vista`).

- [ ] **Step 3: Implementar.** En `api/app/routers/documentos.py`, la ruta `contenido` (línea ~35) pasa a:

```python
@router.get("/documentos/{d_id}/contenido")
def contenido(d_id: int, request: Request, vista: bool = False, db: Session = Depends(get_db),
              s: dict = Depends(security.requiere("auditor", "consejo", "moderador"))):
    d = db.get(models.Documento, d_id)
    if not d:
        raise HTTPException(404, "No existe ese documento")
    # vista=True: inline para el triage del equipo (el requiere de arriba ya excluye propietarios);
    # sin el flag, descarga forzada como siempre. Igual que los informes, inline = sin el header
    # de attachment (nosniff se conserva en _servir).
    return _servir(request, d.archivo_key, attachment=not vista)
```

- [ ] **Step 4: Suite completa.** `cd api && .venv/bin/python -m pytest -q` → 94 passed.

- [ ] **Step 5: Commit.**

```bash
git add api/app/routers/documentos.py api/tests/test_documentos_api.py
git commit -m "API: vista inline de documentos para el equipo (?vista=1)"
```

### Task 2: Web — URL con `vista` y el iframe del visor

**Files:**
- Modify: `web/lib/api.ts` (función `urlContenidoDocumento`, línea ~269), `web/components/hallazgos/ficha.tsx` (iframe, línea ~212)
- Test: `web/tests/api.test.ts`, `web/tests/hallazgo-pagina.test.tsx`

- [ ] **Step 1: Tests que fallan.** En `web/tests/api.test.ts`, junto al expect existente de `urlContenidoDocumento` (línea ~36):

```ts
expect(urlContenidoDocumento(7, { vista: true })).toBe(`${API}/documentos/7/contenido?vista=1`);
```

En `web/tests/hallazgo-pagina.test.tsx`, dentro del test `"la página carga el hallazgo con evidencia e historial"`, después del expect de los 2 iframes:

```ts
// el visor pide la vista inline; el link de al lado sigue siendo descarga
const iframes = Array.from(document.querySelectorAll("iframe"));
expect(iframes.every((f) => f.getAttribute("src")?.endsWith("?vista=1"))).toBe(true);
```

- [ ] **Step 2: Verificar que fallan.** `cd web && NODE_OPTIONS='--experimental-require-module' npm test` → 2 FAIL (la firma no acepta opciones; los src no llevan `vista=1`).

- [ ] **Step 3: Implementar.** `web/lib/api.ts`:

```ts
export function urlContenidoDocumento(id: number, opts?: { vista?: boolean }): string {
  return `${BASE}/documentos/${id}/contenido${opts?.vista ? "?vista=1" : ""}`;
}
```

`web/components/hallazgos/ficha.tsx`, en el iframe (el link `<a>` de arriba NO se toca — sigue siendo descarga):

```tsx
<iframe
  src={urlContenidoDocumento(d.id, { vista: true })}
  className="w-full h-64 border rounded"
  title={`Documento ${d.tipo}`}
/>
```

- [ ] **Step 4: Verificar.** `NODE_OPTIONS='--experimental-require-module' npm test` → 29 passed (los 2 nuevos asserts adentro de tests existentes no suman archivos ni tests: 29 tests, 1 assert nuevo por archivo tocado). `npm run build` → OK.

- [ ] **Step 5: Commit.**

```bash
git add web/lib/api.ts web/components/hallazgos/ficha.tsx web/tests/api.test.ts web/tests/hallazgo-pagina.test.tsx
git commit -m "Web: el visor de comprobantes vuelve con la vista inline del equipo"
```

### Task 3: Web — `RolProvider` + `useRol` montado en el layout

**Files:**
- Create: `web/components/rol-context.tsx`
- Modify: `web/app/panel/layout.tsx`
- Test: `web/tests/rol-context.test.tsx`

- [ ] **Step 1: Test que falla.** Crear `web/tests/rol-context.test.tsx`:

```tsx
import { render, screen } from "@testing-library/react";
import { RolProvider, useRol } from "@/components/rol-context";

function Sonda() {
  return <p>rol: {useRol()}</p>;
}

test("useRol devuelve el rol del provider", () => {
  render(
    <RolProvider rol="consejo">
      <Sonda />
    </RolProvider>
  );
  expect(screen.getByText("rol: consejo")).toBeInTheDocument();
});

test("sin provider, useRol asume auditor (los tests existentes renderizan sin provider)", () => {
  render(<Sonda />);
  expect(screen.getByText("rol: auditor")).toBeInTheDocument();
});
```

- [ ] **Step 2: Verificar que falla.** `NODE_OPTIONS='--experimental-require-module' npm test` → FAIL (no existe el módulo).

- [ ] **Step 3: Implementar.** Crear `web/components/rol-context.tsx`:

```tsx
"use client";

import { createContext, useContext } from "react";

/** Rol de la sesión del panel. Default "auditor": el provider se monta siempre en el layout
 *  del panel; el default solo aplica en tests que renderizan componentes sueltos. */
const RolContext = createContext<string>("auditor");

export function RolProvider({ rol, children }: { rol: string; children: React.ReactNode }) {
  return <RolContext.Provider value={rol}>{children}</RolContext.Provider>;
}

export function useRol(): string {
  return useContext(RolContext);
}
```

En `web/app/panel/layout.tsx`, envolver el contenido (import arriba: `import { RolProvider } from "@/components/rol-context";`):

```tsx
  return (
    <RolProvider rol={yo.rol}>
      <div className="flex min-h-screen">
        <Sidebar rol={yo.rol} nombre={yo.nombre || yo.rol} pendientes={pendientes} activa="" />
        <main className="flex-1 min-w-0 p-6 pt-14 md:pt-6">{children}</main>
      </div>
    </RolProvider>
  );
```

- [ ] **Step 4: Verificar.** `NODE_OPTIONS='--experimental-require-module' npm test` → 31 passed (29 + 2).

- [ ] **Step 5: Commit.**

```bash
git add web/components/rol-context.tsx web/app/panel/layout.tsx web/tests/rol-context.test.tsx
git commit -m "Web: contexto de rol de la sesión en el layout del panel"
```

### Task 4: Web — ficha del hallazgo de solo lectura para consejo/moderador

**Files:**
- Modify: `web/components/hallazgos/ficha.tsx` (función `FichaHallazgo`, líneas ~164-245)
- Test: `web/tests/hallazgo-pagina.test.tsx`

- [ ] **Step 1: Test que falla.** En `web/tests/hallazgo-pagina.test.tsx` (import arriba: `import { RolProvider } from "@/components/rol-context";`):

```tsx
test("consejo ve el hallazgo sin controles de auditor", async () => {
  servidor.use(
    http.get(`${API}/hallazgos/1`, () => HttpResponse.json({ ...DETALLE, respuesta_admin: "Ya respondimos" })),
    http.get(`${API}/documentos`, () => HttpResponse.json([])),
  );
  render(
    <RolProvider rol="consejo">
      <PaginaHallazgo params={Promise.resolve({ id: "1" })} />
    </RolProvider>
  );
  await screen.findAllByText(/Pagos a la propietaria/);
  expect(screen.queryByLabelText("Publicar en el informe")).not.toBeInTheDocument();
  expect(screen.queryByRole("button", { name: "pendiente" })).not.toBeInTheDocument();
  expect(screen.queryByRole("button", { name: /Guardar respuesta/ })).not.toBeInTheDocument();
  // la respuesta ya registrada sigue visible como texto
  expect(screen.getByText("Ya respondimos")).toBeInTheDocument();
});
```

- [ ] **Step 2: Verificar que falla.** `NODE_OPTIONS='--experimental-require-module' npm test` → FAIL (los controles aparecen igual).

- [ ] **Step 3: Implementar.** En `FichaHallazgo` (`web/components/hallazgos/ficha.tsx`): agregar `import { useRol } from "@/components/rol-context";` y `const rol = useRol();` al inicio de la función. Reemplazar las tres llamadas del final:

```tsx
      {rol === "auditor" ? (
        <>
          <SelectorEstado hallazgoId={detalle.id} estadoActual={detalle.estado} alCambiar={alCambiar} />
          <TogglePublicar hallazgoId={detalle.id} publicado={detalle.publicado} alCambiar={alCambiar} />
          <RespuestaAdmin hallazgoId={detalle.id} respuestaInicial={detalle.respuesta_admin} />
        </>
      ) : (
        detalle.respuesta_admin && (
          <div className="flex flex-col gap-1">
            <h3 className="text-sm font-semibold">Respuesta de la administración</h3>
            <p className="text-sm leading-relaxed">{detalle.respuesta_admin}</p>
          </div>
        )
      )}
```

- [ ] **Step 4: Verificar.** `NODE_OPTIONS='--experimental-require-module' npm test` → 32 passed.

- [ ] **Step 5: Commit.**

```bash
git add web/components/hallazgos/ficha.tsx web/tests/hallazgo-pagina.test.tsx
git commit -m "Web: ficha del hallazgo de solo lectura para consejo y moderador"
```

### Task 5: Web — gating en liquidaciones y consorcio

**Files:**
- Modify: `web/app/panel/liquidaciones/page.tsx` (envuelve `SubirLiquidacion`), `web/app/panel/liquidaciones/[id]/page.tsx` (botón publicar y `SubirComprobantes`), `web/app/panel/consorcio/page.tsx` (formulario de datos y `FormularioUmbrales`), `web/components/consorcio/unidades.tsx` (botón "Generar código")
- Test: `web/tests/liquidaciones.test.tsx`, `web/tests/consorcio.test.tsx`

- [ ] **Step 1: Tests que fallan.** En `web/tests/liquidaciones.test.tsx` (import `RolProvider`; usar los mismos handlers MSW del test existente de la lista):

```tsx
test("consejo ve la lista sin el formulario de subir", async () => {
  servidor.use(http.get(`${API}/liquidaciones`, () => HttpResponse.json([])));
  render(
    <RolProvider rol="consejo">
      <LiquidacionesPage />
    </RolProvider>
  );
  expect(await screen.findByText("Liquidaciones")).toBeInTheDocument();
  expect(screen.queryByText(/Subir liquidación/i)).not.toBeInTheDocument();
});
```

En `web/tests/consorcio.test.tsx` (mismos handlers del test existente de la página):

```tsx
test("consejo ve unidades y umbrales sin editar ni generar códigos", async () => {
  render(
    <RolProvider rol="consejo">
      <ConsorcioPage />
    </RolProvider>
  );
  expect(await screen.findByText(/Unidades/)).toBeInTheDocument();
  expect(screen.queryByRole("button", { name: /Generar código/ })).not.toBeInTheDocument();
  expect(screen.queryByRole("button", { name: /Guardar/ })).not.toBeInTheDocument();
});
```

Ajustar los textos exactos de los `queryBy*` a los que rendericen los componentes reales (leerlos antes: `SubirLiquidacion` en `web/components/liquidaciones/subir-liquidacion.tsx`, botones de `web/app/panel/consorcio/page.tsx` y `web/components/consorcio/umbrales.tsx`); el comportamiento a fijar es el del spec: sin subir, sin guardar, sin generar código.

- [ ] **Step 2: Verificar que fallan.** `NODE_OPTIONS='--experimental-require-module' npm test` → 2 FAIL.

- [ ] **Step 3: Implementar.** Patrón único — en cada componente client listado, `const rol = useRol();` y envolver el control de escritura:

```tsx
{rol === "auditor" && <SubirLiquidacion alSubir={cargar} />}
```

- `web/app/panel/liquidaciones/page.tsx`: el `<SubirLiquidacion …/>`.
- `web/app/panel/liquidaciones/[id]/page.tsx`: el botón que llama `api.publicarLiquidacion` (con su diálogo/preview de hallazgos a publicar) y el componente `SubirComprobantes` del detalle.
- `web/app/panel/consorcio/page.tsx`: el formulario de datos (inputs de `CAMPOS_DATOS` + botón guardar) y `<FormularioUmbrales …/>`; la `TablaUnidades` queda visible.
- `web/components/consorcio/unidades.tsx`: el botón "Generar código" de cada fila (la tabla se sigue viendo).

La vista de solo lectura no deja huecos raros: si el control iba dentro de un `Card` propio, ocultar el Card entero.

- [ ] **Step 4: Verificar.** `NODE_OPTIONS='--experimental-require-module' npm test` → 34 passed. `npm run build` → OK.

- [ ] **Step 5: Commit.**

```bash
git add web/app/panel/liquidaciones/page.tsx "web/app/panel/liquidaciones/[id]/page.tsx" web/app/panel/consorcio/page.tsx web/components/consorcio/unidades.tsx web/tests/liquidaciones.test.tsx web/tests/consorcio.test.tsx
git commit -m "Web: liquidaciones y consorcio de solo lectura para consejo y moderador"
```

### Task 6: Cierre — suites, estado y merge

- [ ] **Step 1:** Suites completas: `cd api && .venv/bin/python -m pytest -q` → 94 passed · `cd web && NODE_OPTIONS='--experimental-require-module' npm test` → 34 passed · `npm run build` → OK (engine no se tocó).
- [ ] **Step 2:** `docs/ESTADO.md`: en "Seguimiento post-merge", sacar el ítem del visor (resuelto) y el del gating por rol; dejar constancia breve en la sección de producción ("visor inline del equipo + panel de solo lectura por rol, 5/09").
- [ ] **Step 3: Commit docs + merge.**

```bash
git add docs/ESTADO.md
git commit -m "Estado: visor del equipo y gating por rol resueltos"
git checkout main && git merge --no-ff visor-gating-rol -m "Visor seguro de comprobantes y panel de solo lectura por rol"
```

(El push a origin y el re-deploy de API + front en producción se confirman con Lucas al final.)
