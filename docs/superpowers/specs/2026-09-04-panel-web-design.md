# Front del panel de auditoría — `web/` (diseño aprobado 04-09-2026)

Plan 2 de la etapa 1: la interfaz del panel sobre la API ya construida (`api/`, 88 tests, mergeada a main).
Público: el auditor (Lucas) a diario; consejo/moderador en lectura; propietarios de Rivadavia 2069 con código de unidad.

## Decisiones tomadas (con Lucas, mockups en visual companion, 04-09-2026)

- **Identidad visual: institucional claro** (elegida entre 3 direcciones): azul marino `#123A5C`, fondo `#F6F8FB`,
  tarjetas blancas con borde `#E3E8EF`, tipografía **Lexend** (títulos) + **Source Sans 3** (cuerpo), chips de severidad
  (CRÍTICO rojo `#B42318` sobre `#FEE4E2`, ALTO ámbar `#93540B`/`#FEF0C7`, MEDIO azul, BAJO gris), verde `#0E7A4E`
  para cuadre/éxito. Lenguaje de banco/escribanía: serio sin ser frío. Íconos Lucide (SVG, nunca emojis).
- **Navegación: barra lateral** azul fija con contadores (p. ej. críticos pendientes); colapsa a hamburguesa en mobile.
- **Ficha de hallazgo: drawer + página propia.** Drawer lateral sobre la lista para el triage; botón "abrir completo"
  a `/panel/hallazgos/[id]` (URL linkeable para compartir con el consejo) con visor lado a lado e historial.
- **Comprobantes online** (pedido explícito): carga del ZIP con drag & drop y progreso; visor de PDF embebido
  en ficha y gastos (URL firmada / streaming de la API). Nada se descarga para poder mirarlo.

## Stack y arquitectura

- `web/`: **Next.js (App Router) + TypeScript + Tailwind + shadcn/ui** con el theme institucional. Deploy futuro:
  Cloudflare Workers vía OpenNext como `panel-consorcio.neuralcore.dev` (Plan 3).
- **Toda la data viene de la API** (`http://localhost:8080` en dev; `https://api-consorcio.neuralcore.dev` en prod,
  configurable por `NEXT_PUBLIC_API_URL`). Fetch con `credentials: "include"`; la sesión es la cookie httpOnly de la API.
- `lib/api.ts`: cliente tipado fino (tipos de las respuestas reales de la API; sin codegen).
- Middleware de Next chequea presencia de sesión y rol por ruta vía `GET /auth/yo`; la autoridad real siempre es la API.
- Server components para lectura; client components solo en interacción (drawer, formularios, subidas).
- Sin estado global (no Redux/Zustand): la escala no lo pide.

## Rutas

- `/entrar` — tabs "Equipo" (email + clave) y "Propietario" (UF + código). Errores de la API en castellano tal cual.
- `/panel` — layout con sidebar (secciones: Hallazgos, Liquidaciones, Consorcio; "Asamblea (pronto)" deshabilitada;
  usuario + salir). Redirige a `/panel/hallazgos`.
  - `/panel/liquidaciones` — lista por mes: período, estado con semáforo (procesando/no_cuadra/error/procesada/publicada),
    sistema. Subir PDF (con período AAAA-MM) y subir ZIP de comprobantes; ambos con progreso y resultado
    (checks OK, documentos leídos, hallazgos del cruce). Detalle: checks fallidos si los hay, totales por categoría,
    tabla de gastos (proveedor, concepto, importe, factura, pagos) con acceso a los comprobantes de cada gasto.
  - `/panel/hallazgos` — filtros por severidad/estado/regla/mes (chips), lista ordenada (severidad, monto),
    contadores. Drawer al click: evidencia completa, monto, recomendación, documentos citados con visor embebido,
    botones de estado (pendiente/preguntado/respondido/descartado/cerrado) con nota, campo respuesta de la
    administración, toggle publicar, historial resumido, "abrir completo".
  - `/panel/hallazgos/[id]` — página propia: lo mismo con visor grande lado a lado (factura ↔ transferencia) e
    historial completo con usuario y fecha.
  - `/panel/consorcio` — datos del consorcio y administración; umbrales editables mostrando defaults
    (el PUT manda el dict completo — semántica documentada en api/README); unidades (UF, piso, propietario,
    tiene_codigo) con "generar código" que lo muestra UNA vez con botón copiar; **publicar informe** del mes:
    confirmación que lista los hallazgos que van a entrar antes del POST.
- `/mi-unidad` — propietario: informe HTML embebido del último mes publicado, botón de descarga del Excel,
  su estado de cuenta (expensas del mes, saldo, deuda). Sin menú ni navegación del panel.

## Errores, carga y bordes

- Mensajes de error: los `detail` de la API se muestran tal cual (ya están en castellano y son accionables).
- 401 en cualquier fetch → redirección a `/entrar`. 403 → pantalla "no autorizado" con el rol actual.
- Estados de carga: skeletons (no spinners a pantalla completa). `procesando` se refresca con polling suave (2 s)
  hasta salir del estado.
- Subidas: deshabilitar el botón durante el POST, mostrar tamaño máximo (30 MB PDF / 100 MB ZIP) antes de intentar.
- Accesibilidad: contraste AA, foco visible, targets ≥44px, `prefers-reduced-motion`.

## Pruebas

- Vitest + Testing Library: login (ambos tabs, error), lista+drawer de hallazgos (cambio de estado, publicar),
  subida de liquidación (éxito, 413, 409), guardia de rutas del middleware. API mockeada con MSW usando
  respuestas copiadas de la API real.
- Verificación E2E manual contra la API local con los fixtures del motor antes de cerrar el plan.

## Fuera de alcance (Plan 2)

Asamblea desde la base, multi-consorcio, preguntas/seguimiento del propietario, deploy e infraestructura (Plan 3),
edición de usuarios desde la UI (queda la CLI).
