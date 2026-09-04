# Plan 2: Front del panel de auditoría (`web/`)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Panel web Next.js sobre la API existente: login doble, liquidaciones con subida de PDF/ZIP, hallazgos con drawer + página propia, consorcio con umbrales y códigos, vista del propietario.

**Architecture:** `web/` Next.js App Router + TypeScript + Tailwind + shadcn/ui con theme institucional claro (spec `docs/superpowers/specs/2026-09-04-panel-web-design.md`). Toda la data viene de la API (`NEXT_PUBLIC_API_URL`, dev `http://localhost:8080`) con `credentials: "include"`; la cookie httpOnly de la API es la sesión. Middleware chequea presencia de cookie; el layout de `/panel` resuelve el rol con `GET /auth/yo` (server-side, forwarding de cookie); la autoridad siempre es la API. Páginas interactivas como client components con el cliente tipado `lib/api.ts`.

**Tech Stack:** Next.js (App Router), TypeScript, Tailwind, shadcn/ui, Lucide, next/font (Lexend + Source Sans 3), Vitest + Testing Library + MSW v2.

**Convenciones:** todo en castellano (UI, comentarios, commits con trailer `Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>`). Rama `panel-web`. Comandos desde `web/` salvo indicación. La API de referencia está en `api/` (leer `api/app/routers/*.py` ante cualquier duda de contrato: esa es la verdad, no este plan). No usar emojis como íconos (Lucide). Los tests de componentes definen el contrato: NO debilitarlos; si un test del plan contradice a la API real, reportar DONE_WITH_CONCERNS con la evidencia.

**Theme (decidido con mockups — usar SIEMPRE estos tokens):**
- Azul institucional `#123A5C` (primary), fondo página `#F6F8FB`, tarjeta blanca borde `#E3E8EF`, texto `#1A2B3C`, texto secundario `#5B6B7C`.
- Éxito/cuadre `#0E7A4E`; CRÍTICO texto `#B42318` fondo `#FEE4E2`; ALTO `#93540B`/`#FEF0C7`; MEDIO `#1D4ED8`/`#DBEAFE`; BAJO `#475569`/`#E2E8F0`.
- Títulos Lexend, cuerpo Source Sans 3. Bordes redondeados suaves (`rounded-lg`), sombras mínimas.

---

### Task 1: Andamiaje de `web/`

**Files:**
- Create: `web/` completo (create-next-app), `web/vitest.config.ts`, `web/vitest.setup.ts`, `web/tests/msw.ts`, `web/tests/humo.test.tsx`, `web/.env.local.example`
- Modify: `web/app/globals.css`, `web/app/layout.tsx`, `web/package.json` (scripts)

- [ ] **Step 1: Crear la app** (desde la raíz del repo)

```bash
npx --yes create-next-app@latest web --typescript --tailwind --app --no-src-dir --import-alias "@/*" --use-npm --eslint --no-turbopack
```
Si el instalador pregunta algo más, elegir los defaults. Verificar que `web/app/page.tsx` existe.

- [ ] **Step 2: shadcn/ui + componentes**

```bash
cd web
npx --yes shadcn@latest init -d
npx --yes shadcn@latest add button card badge dialog sheet tabs input label textarea switch table skeleton sonner select
npm install lucide-react
```

- [ ] **Step 3: Theme y fuentes.** En `web/app/layout.tsx`, usar next/font y metadata en castellano:

```tsx
import type { Metadata } from "next";
import { Lexend, Source_Sans_3 } from "next/font/google";
import { Toaster } from "@/components/ui/sonner";
import "./globals.css";

const lexend = Lexend({ subsets: ["latin"], variable: "--font-titulos" });
const sourceSans = Source_Sans_3({ subsets: ["latin"], variable: "--font-cuerpo" });

export const metadata: Metadata = {
  title: "Consorcio Transparente — Panel",
  description: "Panel de auditoría de expensas del Consorcio Rivadavia 2069",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="es-AR">
      <body className={`${lexend.variable} ${sourceSans.variable} font-cuerpo bg-fondo text-tinta antialiased`}>
        {children}
        <Toaster position="top-right" />
      </body>
    </html>
  );
}
```

En `web/app/globals.css`, DESPUÉS de lo que generó shadcn, agregar los tokens del proyecto (adaptar a la sintaxis Tailwind que haya generado create-next-app — v4 usa `@theme`):

```css
@theme inline {
  --color-fondo: #F6F8FB;
  --color-tinta: #1A2B3C;
  --color-tinta-suave: #5B6B7C;
  --color-institucional: #123A5C;
  --color-borde-suave: #E3E8EF;
  --color-exito: #0E7A4E;
  --font-titulos: var(--font-titulos);
  --font-cuerpo: var(--font-cuerpo);
}
```
Además, mapear los tokens de shadcn: `--primary` al azul institucional (editar las variables que shadcn puso en `:root`: `--primary: #123A5C; --primary-foreground: #ffffff; --background: #F6F8FB; --foreground: #1A2B3C; --border: #E3E8EF; --ring: #123A5C;` respetando el formato que shadcn haya usado — hsl u oklch: convertir los hex si hace falta).

- [ ] **Step 4: Vitest + Testing Library + MSW**

```bash
npm install -D vitest @vitejs/plugin-react jsdom @testing-library/react @testing-library/user-event @testing-library/jest-dom msw
```

`web/vitest.config.ts`:
```ts
import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";
import path from "path";

export default defineConfig({
  plugins: [react()],
  resolve: { alias: { "@": path.resolve(__dirname, ".") } },
  test: { environment: "jsdom", setupFiles: ["./vitest.setup.ts"], globals: true },
});
```

`web/vitest.setup.ts`:
```ts
import "@testing-library/jest-dom/vitest";
import { afterAll, afterEach, beforeAll } from "vitest";
import { servidor } from "./tests/msw";

beforeAll(() => servidor.listen({ onUnhandledRequest: "error" }));
afterEach(() => servidor.resetHandlers());
afterAll(() => servidor.close());
```

`web/tests/msw.ts`:
```ts
import { setupServer } from "msw/node";
export const servidor = setupServer();
export const API = "http://localhost:8080";
```

Script en `web/package.json`: `"test": "vitest run", "test:watch": "vitest"`.

`web/tests/humo.test.tsx`:
```tsx
import { render, screen } from "@testing-library/react";

function Hola() { return <h1>Consorcio Transparente</h1>; }

test("el entorno de tests renderiza React", () => {
  render(<Hola />);
  expect(screen.getByText("Consorcio Transparente")).toBeInTheDocument();
});
```

- [ ] **Step 5: `web/.env.local.example`**

```bash
# URL de la API (dev: uvicorn local; prod: https://api-consorcio.neuralcore.dev)
NEXT_PUBLIC_API_URL=http://localhost:8080
```

- [ ] **Step 6: Verificar**

```bash
npm test          # 1 passed
npm run build     # build OK (o `npm run dev` responde en :3000 si build falla por red)
```
Nota: si `create-next-app` no pudo descargar fuentes en build sin red, no bloquear: reportarlo.

- [ ] **Step 7: Commit** (la raíz ya ignora `node_modules/`; verificar que `web/node_modules` y `web/.next` no entren; agregar a `.gitignore` raíz `web/.next/` y `.env*.local` si hace falta)

```bash
git add web .gitignore
git commit -m "Web: andamiaje Next.js con theme institucional, shadcn y Vitest+MSW" -m "Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

### Task 2: Cliente tipado de la API (`lib/api.ts`)

**Files:**
- Create: `web/lib/api.ts`
- Test: `web/tests/api.test.ts`

El contrato real vive en `api/app/routers/*.py` — leerlos antes de escribir los tipos. Resumen de endpoints usados por el front:
`POST /auth/login {email,clave}→{rol,nombre}` · `POST /auth/login-unidad {uf,codigo}→{rol,uf,piso_depto}` · `POST /auth/salir` · `GET /auth/yo→{rol,uf?}` · `GET /liquidaciones→[{id,periodo,estado,cuadra,sistema,error}]` · `POST /liquidaciones (FormData archivo+periodo)→{id,periodo,estado}` · `GET /liquidaciones/{id}→{...checks_ok,checks_mal,checks,totales_categoria,gastos[]}` · `POST /liquidaciones/{id}/comprobantes (FormData archivo)→{ok,documentos,hallazgos_cruce}` · `POST /liquidaciones/{id}/publicar→{ok,hallazgos_publicados}` · `GET /hallazgos?severidad&estado&regla&periodo→[resumen]` · `GET /hallazgos/{id}→detalle con eventos` · `POST /hallazgos/{id}/estado {estado,nota}` · `POST /hallazgos/{id}/publicar {publicado}` · `POST /hallazgos/{id}/respuesta {texto}` · `GET /consorcio` · `PUT /consorcio` · `GET /unidades` · `POST /unidades/{uf}/codigo→{uf,codigo}` · `GET /documentos?liquidacion_id→[{id,gasto_n,tipo,hash,metadatos}]` · `GET /mi-unidad→{uf,periodo,estado_cuenta,informes}`.

- [ ] **Step 1: Test que falla** — `web/tests/api.test.ts`:

```ts
import { http, HttpResponse } from "msw";
import { servidor, API } from "./msw";
import { api, ApiError, urlInforme, urlContenidoDocumento } from "@/lib/api";

test("un GET devuelve el JSON tipado", async () => {
  servidor.use(http.get(`${API}/liquidaciones`, () =>
    HttpResponse.json([{ id: 1, periodo: "2026-08", estado: "procesada", cuadra: true, sistema: "redconar", error: "" }])));
  const liqs = await api.listarLiquidaciones();
  expect(liqs[0].periodo).toBe("2026-08");
});

test("un error de la API se convierte en ApiError con el detail", async () => {
  servidor.use(http.post(`${API}/auth/login`, () =>
    HttpResponse.json({ detail: "Email o clave incorrectos" }, { status: 401 })));
  await expect(api.login("a@b.com", "mala")).rejects.toMatchObject({ status: 401, detail: "Email o clave incorrectos" });
});

test("subir liquidación manda FormData con archivo y periodo", async () => {
  let form: FormData | null = null;
  servidor.use(http.post(`${API}/liquidaciones`, async ({ request }) => {
    form = await request.formData();
    return HttpResponse.json({ id: 1, periodo: "2026-08", estado: "procesando" });
  }));
  const archivo = new File([new Blob(["x"])], "agosto.pdf");
  await api.subirLiquidacion(archivo, "2026-08");
  expect(form!.get("periodo")).toBe("2026-08");
  expect((form!.get("archivo") as File).name).toBe("agosto.pdf");
});

test("las URLs de archivos apuntan a la API", () => {
  expect(urlInforme("2026-08", "html")).toBe(`${API}/informes/2026-08/html`);
  expect(urlContenidoDocumento(7)).toBe(`${API}/documentos/7/contenido`);
});
```

- [ ] **Step 2: Correr y ver fallar** — `npm test` → FAIL (no existe `@/lib/api`).

- [ ] **Step 3: Implementar `web/lib/api.ts`.** Requisitos exactos:
  - `const BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8080";`
  - `export class ApiError extends Error { status: number; detail: string }`.
  - Helper interno `pedir<T>(path, init?)`: `fetch(BASE+path, { credentials: "include", ...init })`; si `!ok`, intenta leer `detail` del JSON (fallback `statusText`) y lanza `ApiError`; si `status === 401` y hay `window` y no estamos en `/entrar`, además hace `window.location.href = "/entrar"`. JSON helper `json(body)` que setea `Content-Type: application/json`.
  - Tipos exportados (con estos NOMBRES, los usan las tareas siguientes): `Rol` (`"auditor"|"consejo"|"moderador"|"propietario"`), `Yo`, `LiquidacionResumen`, `Check`, `GastoFila`, `LiquidacionDetalle`, `HallazgoResumen`, `EventoHallazgo`, `HallazgoDetalle`, `ConsorcioInfo`, `UnidadFila`, `DocumentoInfo`, `MiUnidad`. Campos: copiarlos de las respuestas reales de los routers.
  - Objeto `export const api = {...}` con: `login(email, clave)`, `loginUnidad(uf, codigo)`, `salir()`, `yo()`, `listarLiquidaciones()`, `detalleLiquidacion(id)`, `subirLiquidacion(archivo: File, periodo: string)` (FormData), `subirComprobantes(id, archivo: File)` (FormData), `publicarLiquidacion(id)`, `listarHallazgos(filtros?: {severidad?, estado?, regla?, periodo?})` (query string solo con los presentes), `detalleHallazgo(id)`, `cambiarEstado(id, estado, nota)`, `publicarHallazgo(id, publicado)`, `registrarRespuesta(id, texto)`, `verConsorcio()`, `editarConsorcio(cambio)`, `listarUnidades()`, `generarCodigo(uf)`, `listarDocumentos(liquidacionId)`, `miUnidad()`.
  - `export function urlInforme(periodo, tipo)` y `export function urlContenidoDocumento(id)` → URLs absolutas a la API (el navegador las abre con la cookie; son para `<a>`/`<iframe>`).

- [ ] **Step 4: Verificar** — `npm test` → 5 passed (humo + 4).

- [ ] **Step 5: Commit**

```bash
git add web/lib/api.ts web/tests/api.test.ts
git commit -m "Web: cliente tipado de la API con manejo de errores y sesión" -m "Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

### Task 3: Átomos visuales (chips, KPI, moneda)

**Files:**
- Create: `web/components/severidad.tsx`, `web/components/estado-hallazgo.tsx`, `web/components/kpi.tsx`, `web/lib/formato.ts`
- Test: `web/tests/atomos.test.tsx`

- [ ] **Step 1: Test que falla** — `web/tests/atomos.test.tsx`:

```tsx
import { render, screen } from "@testing-library/react";
import { ChipSeveridad } from "@/components/severidad";
import { ChipEstado } from "@/components/estado-hallazgo";
import { Kpi } from "@/components/kpi";
import { moneda } from "@/lib/formato";

test("moneda formatea en pesos argentinos", () => {
  expect(moneda(4700000)).toBe("$ 4.700.000");   // Intl es-AR con espacio duro
  expect(moneda(-1500.5)).toContain("1.500,5");
});

test("el chip de severidad usa el color correcto", () => {
  render(<ChipSeveridad severidad="CRÍTICO" />);
  const chip = screen.getByText("CRÍTICO");
  expect(chip).toHaveClass("text-[#B42318]");
});

test("el chip de estado muestra el estado", () => {
  render(<ChipEstado estado="preguntado" />);
  expect(screen.getByText("preguntado")).toBeInTheDocument();
});

test("el KPI muestra etiqueta y valor", () => {
  render(<Kpi etiqueta="Críticos" valor="10" tono="critico" />);
  expect(screen.getByText("Críticos")).toBeInTheDocument();
  expect(screen.getByText("10")).toBeInTheDocument();
});
```

- [ ] **Step 2: Ver fallar** — `npm test` → FAIL.

- [ ] **Step 3: Implementar.**
  - `web/lib/formato.ts`: `moneda(v)` con `new Intl.NumberFormat("es-AR", { style: "currency", currency: "ARS", maximumFractionDigits: v % 1 ? 2 : 0 })` (ajustar hasta que el test pase con el output real de Node; si el separador difiere, corregir EL TEST con el output verdadero de `Intl` y documentarlo) y `fecha(iso)` → `DD/MM/AAAA HH:mm`.
  - `ChipSeveridad`: span redondeado `text-[11px] font-bold px-2 py-0.5 rounded-full` con mapa de clases: CRÍTICO `bg-[#FEE4E2] text-[#B42318]`, ALTO `bg-[#FEF0C7] text-[#93540B]`, MEDIO `bg-[#DBEAFE] text-[#1D4ED8]`, BAJO `bg-[#E2E8F0] text-[#475569]`.
  - `ChipEstado`: mismo formato, tonos neutros; `pendiente` azul institucional invertido, `preguntado` ámbar suave, `respondido` azul claro, `descartado` gris, `cerrado` verde suave.
  - `Kpi`: tarjeta blanca borde `#E3E8EF`, etiqueta uppercase 10px `text-tinta-suave`, valor `font-titulos text-2xl font-bold`; prop `tono` (`"normal"|"critico"|"exito"`) colorea el valor.

- [ ] **Step 4: Verificar** — `npm test` → verde.

- [ ] **Step 5: Commit**

```bash
git add web/components web/lib/formato.ts web/tests/atomos.test.tsx
git commit -m "Web: átomos visuales (severidad, estado, KPI, formato de moneda)" -m "Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

### Task 4: Login (`/entrar`) y middleware

**Files:**
- Create: `web/app/entrar/page.tsx`, `web/middleware.ts`, `web/components/login-forms.tsx`
- Modify: `web/app/page.tsx` (redirige a `/panel`)
- Test: `web/tests/entrar.test.tsx`

- [ ] **Step 1: Test que falla** — `web/tests/entrar.test.tsx`:

```tsx
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { servidor, API } from "./msw";
import { FormulariosEntrar } from "@/components/login-forms";

const irA = vi.fn();

test("login de equipo exitoso llama al callback con el rol", async () => {
  servidor.use(http.post(`${API}/auth/login`, () => HttpResponse.json({ rol: "auditor", nombre: "Lucas" })));
  render(<FormulariosEntrar alEntrar={irA} />);
  await userEvent.type(screen.getByLabelText("Email"), "lucas@example.com");
  await userEvent.type(screen.getByLabelText("Clave"), "clave-larga");
  await userEvent.click(screen.getByRole("button", { name: "Entrar" }));
  expect(irA).toHaveBeenCalledWith("auditor");
});

test("login incorrecto muestra el mensaje de la API", async () => {
  servidor.use(http.post(`${API}/auth/login`, () =>
    HttpResponse.json({ detail: "Email o clave incorrectos" }, { status: 401 })));
  render(<FormulariosEntrar alEntrar={irA} />);
  await userEvent.type(screen.getByLabelText("Email"), "x@x.com");
  await userEvent.type(screen.getByLabelText("Clave"), "mala-clave");
  await userEvent.click(screen.getByRole("button", { name: "Entrar" }));
  expect(await screen.findByText("Email o clave incorrectos")).toBeInTheDocument();
});

test("la pestaña Propietario pide UF y código y entra", async () => {
  servidor.use(http.post(`${API}/auth/login-unidad`, () =>
    HttpResponse.json({ rol: "propietario", uf: 27, piso_depto: "13-B" })));
  render(<FormulariosEntrar alEntrar={irA} />);
  await userEvent.click(screen.getByRole("tab", { name: "Propietario" }));
  await userEvent.type(screen.getByLabelText("Unidad funcional (UF)"), "27");
  await userEvent.type(screen.getByLabelText("Código de acceso"), "abc23456");
  await userEvent.click(screen.getByRole("button", { name: "Entrar a mi unidad" }));
  expect(irA).toHaveBeenCalledWith("propietario");
});
```

- [ ] **Step 2: Ver fallar.**

- [ ] **Step 3: Implementar.**
  - `FormulariosEntrar` (`"use client"`): shadcn `Tabs` con "Equipo" y "Propietario"; inputs con `Label` asociado por `htmlFor`; botón deshabilitado mientras envía; error de `ApiError.detail` visible en un `<p role="alert" className="text-[#B42318]">`. Prop `alEntrar: (rol: Rol) => void`.
  - `web/app/entrar/page.tsx` (client): tarjeta centrada con el título "Consorcio Transparente" (font-titulos, azul institucional) y `<FormulariosEntrar alEntrar={(rol) => router.push(rol === "propietario" ? "/mi-unidad" : "/panel")} />`.
  - `web/middleware.ts`: si la ruta empieza con `/panel` o `/mi-unidad` y NO existe la cookie `ct_sesion`, `NextResponse.redirect(new URL("/entrar", req.url))`. `config.matcher = ["/panel/:path*", "/mi-unidad"]`.
  - `web/app/page.tsx`: server component que hace `redirect("/panel")`.

- [ ] **Step 4: Verificar** — `npm test` verde; `npm run build` OK.

- [ ] **Step 5: Commit**

```bash
git add web/app web/middleware.ts web/components/login-forms.tsx web/tests/entrar.test.tsx
git commit -m "Web: pantalla de entrada con doble login y guardia de sesión" -m "Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

### Task 5: Layout del panel con sidebar

**Files:**
- Create: `web/app/panel/layout.tsx`, `web/components/sidebar.tsx`, `web/lib/api-server.ts`
- Create: `web/app/panel/page.tsx` (redirect a `/panel/hallazgos`)
- Test: `web/tests/sidebar.test.tsx`

- [ ] **Step 1: Test que falla** — `web/tests/sidebar.test.tsx`:

```tsx
import { render, screen } from "@testing-library/react";
import { Sidebar } from "@/components/sidebar";

test("la sidebar muestra las secciones y el contador de pendientes", () => {
  render(<Sidebar rol="auditor" nombre="Lucas" pendientes={10} activa="/panel/hallazgos" />);
  expect(screen.getByText("Hallazgos")).toBeInTheDocument();
  expect(screen.getByText("10")).toBeInTheDocument();
  expect(screen.getByText("Liquidaciones")).toBeInTheDocument();
  expect(screen.getByText("Consorcio")).toBeInTheDocument();
  expect(screen.getByText(/Asamblea/)).toBeInTheDocument();
  expect(screen.getByText(/Lucas/)).toBeInTheDocument();
  expect(screen.getByRole("button", { name: "Salir" })).toBeInTheDocument();
});
```

- [ ] **Step 2: Ver fallar.**

- [ ] **Step 3: Implementar.**
  - `web/lib/api-server.ts`: helper para server components — `pedirServidor<T>(path)`: lee `cookies()` de `next/headers`, hace fetch a la API con header `Cookie` reenviado y `cache: "no-store"`; si 401 lanza un error especial que el layout convierte en `redirect("/entrar")`.
  - `Sidebar` (client): fondo `#123A5C`, texto blanco; logo/título arriba; links con `next/link` (Hallazgos con badge rojo `pendientes` si > 0, Liquidaciones, Consorcio), item "Asamblea (pronto)" con `opacity-40` sin link; abajo `{nombre} · {rol}` y botón "Salir" que llama `api.salir()` y redirige a `/entrar`. Item activo: fondo `rgba(255,255,255,.12)` + borde izquierdo verde. En mobile (`md:`): sidebar oculta tras botón hamburguesa (shadcn `Sheet`).
  - `web/app/panel/layout.tsx` (server): llama `pedirServidor` a `/auth/yo`; si rol es `propietario` → `redirect("/mi-unidad")`; obtiene pendientes con `GET /hallazgos?estado=pendiente` (largo del array, tolerar error → 0); renderiza `<div class="flex min-h-screen"><Sidebar .../><main class="flex-1 p-6">{children}</main></div>`. Nota: `GET /auth/yo` devuelve solo el rol (no el nombre), así que el layout pasa `nombre={yo.rol}` y `rol={yo.rol}`; el test de la Sidebar le pasa "Lucas" como prop directa y sigue siendo válido como test de componente.
  - `web/app/panel/page.tsx`: `redirect("/panel/hallazgos")`.

- [ ] **Step 4: Verificar** — `npm test` verde; `npm run build` OK.

- [ ] **Step 5: Commit**

```bash
git add web/app/panel web/components/sidebar.tsx web/lib/api-server.ts web/tests/sidebar.test.tsx
git commit -m "Web: layout del panel con sidebar institucional y guardia por rol" -m "Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

### Task 6: Liquidaciones — lista y subidas

**Files:**
- Create: `web/app/panel/liquidaciones/page.tsx`, `web/components/liquidaciones/lista.tsx`, `web/components/liquidaciones/subir-liquidacion.tsx`, `web/components/liquidaciones/subir-comprobantes.tsx`
- Test: `web/tests/liquidaciones.test.tsx`

- [ ] **Step 1: Test que falla** — `web/tests/liquidaciones.test.tsx`:

```tsx
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { servidor, API } from "./msw";
import { ListaLiquidaciones } from "@/components/liquidaciones/lista";
import { SubirLiquidacion } from "@/components/liquidaciones/subir-liquidacion";

const FILAS = [
  { id: 1, periodo: "2026-08", estado: "procesada", cuadra: true, sistema: "redconar", error: "" },
  { id: 2, periodo: "2026-07", estado: "no_cuadra", cuadra: false, sistema: "redconar", error: "" },
  { id: 3, periodo: "2026-06", estado: "error", cuadra: false, sistema: "", error: "El documento es de 2026-05, no de 2026-06" },
];

test("la lista muestra período, estado y el error cuando lo hay", () => {
  render(<ListaLiquidaciones filas={FILAS as any} alCambiar={() => {}} />);
  expect(screen.getByText("2026-08")).toBeInTheDocument();
  expect(screen.getByText("procesada")).toBeInTheDocument();
  expect(screen.getByText("no cuadra")).toBeInTheDocument();
  expect(screen.getByText(/El documento es de 2026-05/)).toBeInTheDocument();
});

test("subir una liquidación manda el archivo y avisa el resultado", async () => {
  servidor.use(http.post(`${API}/liquidaciones`, () =>
    HttpResponse.json({ id: 9, periodo: "2026-09", estado: "procesando" })));
  const alSubir = vi.fn();
  render(<SubirLiquidacion alSubir={alSubir} />);
  await userEvent.type(screen.getByLabelText("Período (AAAA-MM)"), "2026-09");
  const archivo = new File(["contenido"], "septiembre.pdf", { type: "application/pdf" });
  await userEvent.upload(screen.getByLabelText(/Liquidación en PDF/), archivo);
  await userEvent.click(screen.getByRole("button", { name: "Subir y procesar" }));
  expect(await screen.findByText(/procesando/i)).toBeInTheDocument();
  expect(alSubir).toHaveBeenCalled();
});

test("un 413 de la API se muestra tal cual", async () => {
  servidor.use(http.post(`${API}/liquidaciones`, () =>
    HttpResponse.json({ detail: "El archivo supera los 30 MB" }, { status: 413 })));
  render(<SubirLiquidacion alSubir={() => {}} />);
  await userEvent.type(screen.getByLabelText("Período (AAAA-MM)"), "2026-09");
  await userEvent.upload(screen.getByLabelText(/Liquidación en PDF/), new File(["x"], "x.pdf"));
  await userEvent.click(screen.getByRole("button", { name: "Subir y procesar" }));
  expect(await screen.findByText("El archivo supera los 30 MB")).toBeInTheDocument();
});
```

- [ ] **Step 2: Ver fallar.**

- [ ] **Step 3: Implementar.**
  - `ListaLiquidaciones` (client): tabla shadcn con columnas Período / Estado / Sistema / Acciones. Estado como chip: `publicada` verde, `procesada` azul, `procesando` gris con spinner chico, `no_cuadra` (mostrar "no cuadra") rojo, `error` rojo con el texto de `error` debajo en `text-tinta-suave text-sm`. Acción por fila: link "Ver detalle" a `/panel/liquidaciones/{id}` y `<SubirComprobantes liquidacionId periodo />` cuando estado ∈ {procesada, publicada}. Prop `alCambiar` para refrescar.
  - `SubirLiquidacion` (client): input período con `Label`, file input `accept=".pdf,.txt"` con `Label` "Liquidación en PDF", texto de ayuda "Hasta 30 MB", botón "Subir y procesar" (deshabilitado sin archivo/período o mientras sube, con texto "Subiendo…"), resultado con estado (`procesando` → toast + banner), errores `ApiError.detail` en `role="alert"`.
  - `SubirComprobantes` (client): botón que abre `Dialog` con file input `accept=".zip"` "ZIP de comprobantes (hasta 100 MB)", explica que sale de `ct descargar`; al éxito muestra "N documentos leídos, M hallazgos del cruce" y llama `alCambiar`.
  - `web/app/panel/liquidaciones/page.tsx` (client): carga `api.listarLiquidaciones()` en `useEffect` + estado; polling cada 2 s mientras alguna fila esté `procesando` (limpiar interval); layout: título "Liquidaciones", `SubirLiquidacion` en tarjeta arriba, `ListaLiquidaciones` abajo; skeletons de carga.

- [ ] **Step 4: Verificar** — `npm test` verde.

- [ ] **Step 5: Commit**

```bash
git add web/app/panel/liquidaciones web/components/liquidaciones web/tests/liquidaciones.test.tsx
git commit -m "Web: liquidaciones con subida de PDF y ZIP de comprobantes" -m "Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

### Task 7: Liquidación — detalle con checks y gastos

**Files:**
- Create: `web/app/panel/liquidaciones/[id]/page.tsx`, `web/components/liquidaciones/detalle.tsx`
- Test: `web/tests/liquidacion-detalle.test.tsx`

- [ ] **Step 1: Test que falla** — `web/tests/liquidacion-detalle.test.tsx`:

```tsx
import { render, screen } from "@testing-library/react";
import { DetalleLiquidacion } from "@/components/liquidaciones/detalle";

const DETALLE = {
  id: 1, periodo: "2026-08", estado: "procesada", cuadra: true, sistema: "redconar", error: "",
  checks_ok: 30, checks_mal: 0, checks: [],
  totales_categoria: { "Sueldos": 5000000, "Abonos": 1200000 },
  gastos: [
    { n: 1, categoria: "Sueldos", proveedor: "Encargado", concepto: "Sueldo agosto", columna: "A",
      importe: 900000, factura_nro: null, pagos: [{ fecha: "2026-08-05", importe: 900000, caja: "BANCO", forma: "Transferencia" }] },
  ],
};

const DOCS = [{ id: 4, gasto_n: 1, tipo: "pago", hash: "abc", metadatos: {} }];

test("muestra el cuadre en verde y los totales", () => {
  render(<DetalleLiquidacion detalle={DETALLE as any} documentos={DOCS as any} />);
  expect(screen.getByText("30/30")).toBeInTheDocument();
  expect(screen.getByText("Sueldos")).toBeInTheDocument();
});

test("cada gasto con documentos linkea su comprobante", () => {
  render(<DetalleLiquidacion detalle={DETALLE as any} documentos={DOCS as any} />);
  const link = screen.getByRole("link", { name: /comprobante/i });
  expect(link).toHaveAttribute("href", expect.stringContaining("/documentos/4/contenido"));
});

test("una liquidación que no cuadra muestra los checks fallidos", () => {
  const roto = { ...DETALLE, estado: "no_cuadra", cuadra: false, checks_ok: 28, checks_mal: 2,
    checks: [{ nombre: "total de gastos", ok: false, esperado: 100, obtenido: 90, detalle: "" }] };
  render(<DetalleLiquidacion detalle={roto as any} documentos={[]} />);
  expect(screen.getByText(/total de gastos/)).toBeInTheDocument();
  expect(screen.getByText(/no cuadra/i)).toBeInTheDocument();
});
```

- [ ] **Step 2: Ver fallar.**

- [ ] **Step 3: Implementar.**
  - `DetalleLiquidacion` (client, recibe data por props): fila de `Kpi` (Cuadre `checks_ok/(checks_ok+checks_mal)` en verde si cuadra; si no, banner rojo "Esta liquidación no cuadra — no se puede publicar" + tabla de checks fallidos con esperado/obtenido en `moneda`). Totales por categoría (tarjetas chicas o tabla de dos columnas con `moneda`). Tabla de gastos: n, categoría, proveedor, concepto (truncado con title), importe (`moneda`, alineado a la derecha, `tabular-nums`), factura, forma de pago; si hay documentos del gasto (`documentos.filter(d => d.gasto_n === g.n)`), links "comprobante" (`urlContenidoDocumento(d.id)`, `target="_blank"`), con ícono Lucide `FileText`.
  - `web/app/panel/liquidaciones/[id]/page.tsx` (client): carga `api.detalleLiquidacion(id)` y `api.listarDocumentos(id)` en paralelo; breadcrumb "← Liquidaciones"; botón "Publicar informe" solo si estado ∈ {procesada, publicada} — abre confirmación (Dialog) que primero trae `api.listarHallazgos({ periodo })` y lista los que tienen `publicado: true` ("Van a publicarse N hallazgos: …títulos…; los demás quedan internos"), botón confirmar llama `api.publicarLiquidacion(id)` y muestra el resultado; si la API devuelve 409, mostrar `detail`.

- [ ] **Step 4: Verificar** — `npm test` verde.

- [ ] **Step 5: Commit**

```bash
git add web/app/panel/liquidaciones web/components/liquidaciones/detalle.tsx web/tests/liquidacion-detalle.test.tsx
git commit -m "Web: detalle de liquidación con cuadre, gastos, comprobantes y publicación" -m "Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

### Task 8: Hallazgos — lista, filtros y drawer

**Files:**
- Create: `web/app/panel/hallazgos/page.tsx`, `web/components/hallazgos/lista.tsx`, `web/components/hallazgos/drawer.tsx`, `web/components/hallazgos/ficha.tsx`
- Test: `web/tests/hallazgos.test.tsx`

`ficha.tsx` es el cuerpo compartido entre drawer y página propia (Task 9): recibe `detalle`, `documentos` y callbacks; el drawer y la página solo lo envuelven.

- [ ] **Step 1: Test que falla** — `web/tests/hallazgos.test.tsx`:

```tsx
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { servidor, API } from "./msw";
import { ListaHallazgos } from "@/components/hallazgos/lista";
import { FichaHallazgo } from "@/components/hallazgos/ficha";

const RESUMEN = [
  { id: 1, liquidacion_id: 1, periodo: "2026-08", regla: "comprobantes", origen: "comprobantes",
    severidad: "CRÍTICO", area: "Comprobantes", titulo: "Pagos a la propietaria de 13-B", monto: 4700000,
    estado: "pendiente", publicado: false },
  { id: 2, liquidacion_id: 1, periodo: "2026-08", regla: "efectivo", origen: "liquidacion",
    severidad: "ALTO", area: "Caja", titulo: "68 % de la liquidez en efectivo", monto: 6700000,
    estado: "preguntado", publicado: true },
];

const DETALLE = { ...RESUMEN[0], evidencia: "CUIT destino ≠ CUIT emisor", recomendacion: "Pedir explicación",
  refs: ["2"], respuesta_admin: "", eventos: [{ de: "", a: "pendiente", nota: "", ts: "2026-09-04T10:00:00+00:00", usuario: "Lucas" }] };

test("la lista muestra severidad, título y monto", () => {
  render(<ListaHallazgos filas={RESUMEN as any} alAbrir={() => {}} />);
  expect(screen.getByText("CRÍTICO")).toBeInTheDocument();
  expect(screen.getByText(/Pagos a la propietaria/)).toBeInTheDocument();
  expect(screen.getByText(/4\.700\.000/)).toBeInTheDocument();
});

test("cambiar el estado pide nota y llama a la API", async () => {
  let cuerpo: any = null;
  servidor.use(http.post(`${API}/hallazgos/1/estado`, async ({ request }) => {
    cuerpo = await request.json();
    return HttpResponse.json({ ok: true, estado: "preguntado" });
  }));
  const alCambiar = vi.fn();
  render(<FichaHallazgo detalle={DETALLE as any} documentos={[]} alCambiar={alCambiar} />);
  await userEvent.click(screen.getByRole("button", { name: "preguntado" }));
  await userEvent.type(screen.getByLabelText(/Nota/), "Se preguntó en la asamblea");
  await userEvent.click(screen.getByRole("button", { name: "Confirmar cambio" }));
  expect(cuerpo).toEqual({ estado: "preguntado", nota: "Se preguntó en la asamblea" });
  expect(alCambiar).toHaveBeenCalled();
});

test("el toggle de publicar llama a la API", async () => {
  let cuerpo: any = null;
  servidor.use(http.post(`${API}/hallazgos/1/publicar`, async ({ request }) => {
    cuerpo = await request.json();
    return HttpResponse.json({ ok: true, publicado: true });
  }));
  render(<FichaHallazgo detalle={DETALLE as any} documentos={[]} alCambiar={() => {}} />);
  await userEvent.click(screen.getByRole("switch", { name: /Publicar en el informe/ }));
  expect(cuerpo).toEqual({ publicado: true });
});

test("la respuesta de la administración se registra", async () => {
  let cuerpo: any = null;
  servidor.use(http.post(`${API}/hallazgos/1/respuesta`, async ({ request }) => {
    cuerpo = await request.json();
    return HttpResponse.json({ ok: true });
  }));
  render(<FichaHallazgo detalle={DETALLE as any} documentos={[]} alCambiar={() => {}} />);
  await userEvent.type(screen.getByLabelText(/Respuesta de la administración/), "Dijeron que lo revisan");
  await userEvent.click(screen.getByRole("button", { name: "Guardar respuesta" }));
  expect(cuerpo).toEqual({ texto: "Dijeron que lo revisan" });
});
```

- [ ] **Step 2: Ver fallar.**

- [ ] **Step 3: Implementar.**
  - `ListaHallazgos`: tarjetas apiladas (como el mockup elegido): chip severidad + título + `moneda(monto)` + `ChipEstado` + chip "publicado" verde si corresponde + período; click en la tarjeta → `alAbrir(id)`; `cursor-pointer`, hover con borde azul.
  - `FichaHallazgo` (client, corazón compartido): título + chips; evidencia en `<p>` legible; recomendación bajo "Qué pedir"; documentos citados: para cada `DocumentoInfo` un link con ícono a `urlContenidoDocumento(id)` (target _blank) y, si `tipo === "factura" || tipo === "pago"`, `<iframe src={urlContenidoDocumento(id)} className="w-full h-64 border rounded" title={...} />` (prop `conVisor?: boolean` default true; el drawer pasa `conVisor={false}` y muestra solo links para no cargar N iframes). Estados: 5 botones (el actual resaltado, los demás outline); al elegir uno distinto aparece `Textarea` "Nota (opcional)" + botón "Confirmar cambio" → `api.cambiarEstado`. Switch shadcn con `Label` "Publicar en el informe" → `api.publicarHallazgo`. `Textarea` "Respuesta de la administración" precargada con `respuesta_admin` + botón "Guardar respuesta". Historial: lista compacta `fecha(ts) · usuario · de→a · nota`. Todo error `ApiError` → toast con `detail`. Prop `alCambiar` tras cada mutación exitosa.
  - `DrawerHallazgo`: shadcn `Sheet` lado derecho (ancho `sm:max-w-xl`); carga `api.detalleHallazgo(id)` + `api.listarDocumentos(liquidacion_id)` filtrados por refs del hallazgo (los `refs` son n de gasto cuando `origen === "comprobantes"`: filtrar `documentos.filter(d => detalle.refs.includes(String(d.gasto_n)))`; si `origen === "liquidacion"`, no mostrar documentos); `FichaHallazgo conVisor={false}`; link "Abrir completo →" a `/panel/hallazgos/{id}`.
  - `web/app/panel/hallazgos/page.tsx` (client): filtros como chips clickeables (severidades, estados, período de las liquidaciones existentes) que rearman `api.listarHallazgos(filtros)`; contadores arriba (`Kpi` Críticos / Pendientes / Publicados); lista + drawer controlado por estado `abiertoId`.

- [ ] **Step 4: Verificar** — `npm test` verde.

- [ ] **Step 5: Commit**

```bash
git add web/app/panel/hallazgos web/components/hallazgos web/tests/hallazgos.test.tsx
git commit -m "Web: hallazgos con filtros, drawer de triage y acciones de auditor" -m "Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

### Task 9: Hallazgo — página propia linkeable

**Files:**
- Create: `web/app/panel/hallazgos/[id]/page.tsx`
- Test: `web/tests/hallazgo-pagina.test.tsx`

- [ ] **Step 1: Test que falla** — `web/tests/hallazgo-pagina.test.tsx`:

```tsx
import { render, screen } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { servidor, API } from "./msw";
import PaginaHallazgo from "@/app/panel/hallazgos/[id]/page";

const DETALLE = { id: 1, liquidacion_id: 1, periodo: "2026-08", regla: "comprobantes", origen: "comprobantes",
  severidad: "CRÍTICO", area: "Comprobantes", titulo: "Pagos a la propietaria de 13-B", monto: 4700000,
  estado: "pendiente", publicado: false, evidencia: "CUIT destino ≠ CUIT emisor", recomendacion: "Pedir explicación",
  refs: ["2"], respuesta_admin: "",
  eventos: [{ de: "pendiente", a: "preguntado", nota: "en asamblea", ts: "2026-09-04T10:00:00+00:00", usuario: "Lucas" }] };

test("la página carga el hallazgo con evidencia e historial", async () => {
  servidor.use(
    http.get(`${API}/hallazgos/1`, () => HttpResponse.json(DETALLE)),
    http.get(`${API}/documentos`, () => HttpResponse.json([
      { id: 4, gasto_n: 2, tipo: "factura", hash: "a", metadatos: {} },
      { id: 5, gasto_n: 2, tipo: "pago", hash: "b", metadatos: {} },
    ])),
  );
  render(<PaginaHallazgo params={Promise.resolve({ id: "1" })} />);
  expect(await screen.findByText(/Pagos a la propietaria/)).toBeInTheDocument();
  expect(screen.getByText(/CUIT destino/)).toBeInTheDocument();
  expect(screen.getByText(/en asamblea/)).toBeInTheDocument();
  // visor lado a lado: dos iframes (factura y pago del gasto 2)
  expect(document.querySelectorAll("iframe").length).toBe(2);
});
```
(Nota: `params` es Promise en Next 15+; usar `use(params)` o `await` según la versión generada — verificar cómo lo tipa el proyecto creado y ajustar el test/página coherentemente.)

- [ ] **Step 2: Ver fallar.**

- [ ] **Step 3: Implementar** `web/app/panel/hallazgos/[id]/page.tsx` (client): breadcrumb "← Hallazgos"; `FichaHallazgo` con `conVisor` (iframes de los documentos citados, factura y pago lado a lado en grid de 2 columnas cuando hay ambos); historial completo. Reutiliza el filtrado por refs/origen de la Task 8 (extraerlo a `web/components/hallazgos/documentos-de.ts` si quedó inline: `documentosDelHallazgo(detalle, documentos)`).

- [ ] **Step 4: Verificar** — `npm test` verde.

- [ ] **Step 5: Commit**

```bash
git add web/app/panel/hallazgos web/components/hallazgos web/tests/hallazgo-pagina.test.tsx
git commit -m "Web: página propia del hallazgo con visor lado a lado e historial" -m "Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

### Task 10: Consorcio — datos, umbrales, unidades y códigos

**Files:**
- Create: `web/app/panel/consorcio/page.tsx`, `web/components/consorcio/umbrales.tsx`, `web/components/consorcio/unidades.tsx`
- Test: `web/tests/consorcio.test.tsx`

- [ ] **Step 1: Test que falla** — `web/tests/consorcio.test.tsx`:

```tsx
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { servidor, API } from "./msw";
import { FormularioUmbrales } from "@/components/consorcio/umbrales";
import { TablaUnidades } from "@/components/consorcio/unidades";

test("el formulario de umbrales manda el dict completo (semántica PUT)", async () => {
  let cuerpo: any = null;
  servidor.use(http.put(`${API}/consorcio`, async ({ request }) => {
    cuerpo = await request.json();
    return HttpResponse.json({ ok: true });
  }));
  render(<FormularioUmbrales
    umbrales={{ efectivo_linea_alta: 300000 }}
    defaults={{ efectivo_linea_alta: 300000, dias_factura_pago_max: 60 }}
    alGuardar={() => {}} />);
  const campo = screen.getByLabelText("efectivo_linea_alta");
  await userEvent.clear(campo);
  await userEvent.type(campo, "500000");
  await userEvent.click(screen.getByRole("button", { name: "Guardar umbrales" }));
  expect(cuerpo.umbrales.efectivo_linea_alta).toBe(500000);
  expect(cuerpo.umbrales.dias_factura_pago_max).toBe(60); // completa con los defaults
});

test("generar un código lo muestra una sola vez con botón copiar", async () => {
  servidor.use(http.post(`${API}/unidades/27/codigo`, () =>
    HttpResponse.json({ uf: 27, codigo: "abc23456" })));
  render(<TablaUnidades unidades={[{ uf: 27, piso_depto: "13-B", tipo: "", propietario: "X", tiene_codigo: false }] as any} alCambiar={() => {}} />);
  await userEvent.click(screen.getByRole("button", { name: /Generar código/ }));
  expect(await screen.findByText("abc23456")).toBeInTheDocument();
  expect(screen.getByRole("button", { name: /Copiar/ })).toBeInTheDocument();
  expect(screen.getByText(/no se vuelve a mostrar/i)).toBeInTheDocument();
});
```

- [ ] **Step 2: Ver fallar.**

- [ ] **Step 3: Implementar.**
  - `FormularioUmbrales`: un input numérico por campo de `defaults` (labels con el nombre del umbral y el default como placeholder/ayuda), valores iniciales = `defaults` con overrides de `umbrales`; al guardar arma el dict COMPLETO (todos los campos, numéricos) y llama `api.editarConsorcio({ umbrales })`; errores 422 con `detail` visible.
  - `TablaUnidades`: tabla UF / piso / propietario / código; si `tiene_codigo`, texto "emitido" con botón "Regenerar"; si no, botón "Generar código". Al generar: `Dialog` con el código en grande (`font-mono text-2xl`), aviso "Guardalo ahora: no se vuelve a mostrar", botón "Copiar" (`navigator.clipboard.writeText`). Luego `alCambiar`.
  - `web/app/panel/consorcio/page.tsx` (client): carga `api.verConsorcio()` + `api.listarUnidades()`; secciones: datos del consorcio (tarjeta de solo lectura con nombre/dirección/CUIT/administración/marca — edición con inputs y "Guardar datos" via `editarConsorcio`), umbrales, unidades. Errores por toast.

- [ ] **Step 4: Verificar** — `npm test` verde.

- [ ] **Step 5: Commit**

```bash
git add web/app/panel/consorcio web/components/consorcio web/tests/consorcio.test.tsx
git commit -m "Web: configuración del consorcio, umbrales completos y códigos por unidad" -m "Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

### Task 11: Vista del propietario (`/mi-unidad`)

**Files:**
- Create: `web/app/mi-unidad/page.tsx`
- Test: `web/tests/mi-unidad.test.tsx`

- [ ] **Step 1: Test que falla** — `web/tests/mi-unidad.test.tsx`:

```tsx
import { render, screen } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { servidor, API } from "./msw";
import PaginaMiUnidad from "@/app/mi-unidad/page";

test("muestra el informe publicado, la descarga y el estado de cuenta", async () => {
  servidor.use(http.get(`${API}/mi-unidad`, () => HttpResponse.json({
    uf: 27, periodo: "2026-08",
    estado_cuenta: { uf: 27, piso_depto: "13-B", propietario: "X", total_mes: 120000, a_pagar: 125000, deuda: 5000 },
    informes: ["/informes/2026-08/html", "/informes/2026-08/xlsx"],
  })));
  render(<PaginaMiUnidad />);
  expect(await screen.findByText(/13-B/)).toBeInTheDocument();
  expect(screen.getByText(/Agosto|2026-08/)).toBeInTheDocument();
  expect(screen.getByRole("link", { name: /Descargar Excel/ })).toHaveAttribute("href", expect.stringContaining("/informes/2026-08/xlsx"));
  expect(document.querySelector("iframe")!.getAttribute("src")).toContain("/informes/2026-08/html");
});

test("sin informe publicado muestra un mensaje amable", async () => {
  servidor.use(http.get(`${API}/mi-unidad`, () =>
    HttpResponse.json({ detail: "Todavía no hay ningún informe publicado" }, { status: 404 })));
  render(<PaginaMiUnidad />);
  expect(await screen.findByText(/Todavía no hay ningún informe publicado/)).toBeInTheDocument();
});
```

- [ ] **Step 2: Ver fallar.**

- [ ] **Step 3: Implementar** `web/app/mi-unidad/page.tsx` (client): header simple (título + "Salir"); tarjeta "Tu unidad" con piso_depto, expensas del mes (`moneda(total_mes)`), a pagar y deuda si > 0; botones/link "Descargar Excel" (`urlInforme(periodo, "xlsx")`) y el informe embebido `<iframe src={urlInforme(periodo, "html")} className="w-full min-h-[70vh] bg-white border rounded-lg" title="Informe de expensas" />`. El 404 del endpoint → pantalla con el `detail` y nada más. Sin sidebar.

- [ ] **Step 4: Verificar** — `npm test` verde; `npm run build` OK.

- [ ] **Step 5: Commit**

```bash
git add web/app/mi-unidad web/tests/mi-unidad.test.tsx
git commit -m "Web: vista del propietario con informe embebido y estado de cuenta" -m "Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

### Task 12: Pulido, E2E manual y documentación

**Files:**
- Create: `web/README.md`
- Modify: `docs/ESTADO.md`, lo que surja del checklist

- [ ] **Step 1: Checklist de calidad ui-ux-pro-max sobre TODO lo construido.** Revisar y corregir (commits chicos si hay fixes):
  - `cursor-pointer` en todo lo clickeable; hover con transición 150-300ms sin layout shift.
  - Contraste AA en texto (nada de gris claro sobre blanco); foco visible en inputs/botones; labels asociados.
  - Targets táctiles ≥44px en botones de estado y chips de filtro.
  - Ningún emoji como ícono (solo Lucide); tamaños de ícono consistentes (`w-4 h-4` / `w-5 h-5`).
  - `tabular-nums` en columnas de montos; alineación derecha en números.
  - Responsive: probar 375px (sidebar → hamburguesa, tablas con `overflow-x-auto`), 768px, 1440px.
  - `prefers-reduced-motion` respetado (las transiciones de shadcn ya lo hacen; no agregar animaciones custom que no).

- [ ] **Step 2: E2E manual contra la API real.** Levantar la API con fixtures y recorrer todo:

```bash
cd api
CT_STORAGE_DIR=/tmp/ct-e2e CT_DATABASE_URL=sqlite:////tmp/ct-e2e.db .venv/bin/python cli.py init "Rivadavia 2069"
CT_STORAGE_DIR=/tmp/ct-e2e CT_DATABASE_URL=sqlite:////tmp/ct-e2e.db CT_REDCONAR_E2E=1 \
  .venv/bin/python -c "
from app.db import Base, SessionLocal, engine
from app import admin
Base.metadata.create_all(engine)
db = SessionLocal()
admin.crear_usuario(db, 'lucas@example.com', 'Lucas', 'auditor', 'clave-de-e2e')
print('usuario listo')"
CT_STORAGE_DIR=/tmp/ct-e2e CT_DATABASE_URL=sqlite:////tmp/ct-e2e.db .venv/bin/uvicorn app.main:app --port 8080 &
cd ../web && npm run dev
```
Recorrido (anotar cualquier rotura y arreglarla antes de cerrar): entrar como auditor → subir `engine/tests/fixtures/redconar_202607.txt` como 2026-07 y `redconar_202608.txt` como 2026-08 → ver detalle y cuadre 30/30 → hallazgos: cambiar un estado con nota, publicar 2 → publicar informe de 2026-08 → consorcio: generar código de una UF → salir → entrar como propietario con ese código → ver informe embebido y estado de cuenta → matar uvicorn.

- [ ] **Step 3: `web/README.md`**

```markdown
# Panel web (Consorcio Transparente)

Next.js + Tailwind + shadcn/ui sobre la API (`api/`). Theme institucional claro (spec en
`docs/superpowers/specs/2026-09-04-panel-web-design.md`).

## Desarrollo
    npm install
    cp .env.local.example .env.local        # apunta a la API (dev: http://localhost:8080)
    npm run dev                              # necesita la API corriendo (ver api/README.md)
    npm test                                 # Vitest + Testing Library (API mockeada con MSW)

## Rutas
`/entrar` (equipo o propietario) · `/panel/hallazgos` (triage con drawer; ficha linkeable en
`/panel/hallazgos/[id]`) · `/panel/liquidaciones` (subir PDF y ZIP de comprobantes; detalle con
cuadre y gastos) · `/panel/consorcio` (umbrales, unidades, códigos, publicar informe) ·
`/mi-unidad` (propietario: informe embebido + estado de cuenta).

Deploy (Plan 3): Cloudflare Workers vía OpenNext como `panel-consorcio.neuralcore.dev`.
```

- [ ] **Step 4: Actualizar `docs/ESTADO.md`**: en "Qué existe y funciona" agregar un bullet del panel web (rama `panel-web`, rutas, tests, spec) y en pendientes dejar el Plan 3 (deploy) como próximo paso con el detalle ya anotado (tunnel, Neon, R2, Alembic, IP real, medir ZIP real).

- [ ] **Step 5: Verificación final completa**

```bash
cd web && npm test && npm run build
cd ../api && .venv/bin/python -m pytest -q      # 88 passed (no debe haberse tocado)
cd ../engine && .venv/bin/python -m pytest -q tests   # 29 passed, 2 skipped
```

- [ ] **Step 6: Commit**

```bash
git add web/README.md docs/ESTADO.md web
git commit -m "Web: pulido de accesibilidad, E2E manual contra la API y documentación" -m "Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```
