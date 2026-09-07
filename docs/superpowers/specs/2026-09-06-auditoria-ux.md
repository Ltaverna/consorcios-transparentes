# Auditoría UX/UI del panel (06-09-2026) — spec del ciclo de mejoras

Auditoría de solo lectura sobre `web/` (metodología frontend-design-audit, 15 principios,
severidad 0-4). Alcance aprobado por el dueño: **arreglar todo de severidad 4 a 2** (22 ítems).
Los de severidad 1 quedan anotados al final, no se hacen en este ciclo.

Resumen: 1×Sev4 · 8×Sev3 · 13×Sev2 · 6×Sev1. Contexto que fija severidades: 366 hallazgos
abiertos en el triage (la página se diseñó para ~30); ~100 propietarios no técnicos, muchos
mayores, mobile-first vía PWA; la evidencia (comprobantes PDF) es el corazón del producto.

## Frente A — Hallazgos: la herramienta diaria escala a 366 (Sev 4 + cinco Sev 3 + dos Sev 2)

1. **[S4] Lista sin orden/búsqueda/conteo/lote** (`app/panel/hallazgos/page.tsx:117-151`,
   `components/hallazgos/lista.tsx:20-55`): agregar client-side (las filas ya están cargadas):
   input de búsqueda por título/regla en memoria; orden por defecto severidad desc + monto desc
   con control para cambiar (fecha/monto/severidad); contador "N hallazgos · $ total" sobre la
   lista; multi-selección en los chips de filtro (array, no valor único); chips por `regla`
   derivados de las filas cargadas (la API ya filtra por regla: `lib/api.ts:271-279`).
2. **[S3] Recarga colapsa la lista y pierde el scroll** (`page.tsx:84-96,135-143`): skeleton
   solo en primera carga (`filas.length === 0 && cargando`); tras triage, actualizar la fila en
   memoria y recargar en segundo plano (la lista nunca se desmonta).
3. **[S3] Estado elegido invisible en SelectorEstado** (`components/hallazgos/ficha.tsx:59-70`):
   resaltar `elegido` (ring-2/relleno distinto), encabezado "Estado" al bloque, y el panel de
   confirmación debe decir "Cambiar a **{estado}**".
4. **[S3] Filtros no persisten al navegar** (`page.tsx:79-81`): filtros en la URL
   (`useSearchParams` + `router.replace`), restaurados al montar.
5. **[S3] Falla de carga se muestra como "No hay hallazgos"** (`page.tsx:92-93`,
   `lista.tsx:16-18`): estado `error` + card con "Reintentar" (patrón de `[id]/page.tsx:60-68`).
6. **[S3] Sin operaciones en lote** (`lista.tsx`, `ficha.tsx:24-83`): checkboxes en tarjetas +
   barra "N seleccionados: cambiar estado · publicar" (loop client-side sobre los endpoints
   existentes; confirmación única con el conteo).
7. **[S2] KPIs cambian de significado según filtro** (`page.tsx:113-124`): KPIs globales (pedido
   sin filtros o cálculo aparte) + "mostrando N de M" sobre la lista.
8. **[S2] Carrera en el drawer** (`components/hallazgos/drawer.tsx:34-60`): guard de vigencia
   (contador de pedido o AbortController) al abrir A y enseguida B.

## Frente B — Mi unidad (propietario, móvil primero) (dos Sev 3 + tres Sev 2)

9. **[S3] N+1 secuencial + todo expandido con iframes** (`app/mi-unidad/page.tsx:45-64,245-298`):
   paralelizar con `Promise.all`; hallazgos publicados **colapsados** (título + severidad +
   monto; expandir al tocar) y el iframe del PDF se carga solo al expandir; si la carga falla:
   "No pudimos cargar los hallazgos publicados. Reintentar" (no silencio).
10. **[S3] `grid-cols-3` fijo rompe en 320-375px** (`page.tsx:121-136`): `grid-cols-1
    sm:grid-cols-3` (o 2+1), etiquetas a `text-sm`. Aplicar el mismo criterio al `grid-cols-3`
    de KPIs de hallazgos.
11. **[S2] Informe de 70vh entierra los hallazgos** (`page.tsx:239-298`): "Hallazgos publicados"
    arriba del informe; el iframe con título + link "abrir informe completo".
12. **[S2] Visores PDF de 256px ilegibles** (`components/hallazgos/ficha.tsx:213-219`,
    `mi-unidad/page.tsx:284-288`): reemplazar por botón/miniatura "Ver comprobante" que abre
    Dialog a pantalla casi completa; en móvil, link directo.
13. **[S2] "Descargar Excel" con clases manuales**: usar `buttonVariants()` (va junto con el
    trabajo en esta página aunque era Sev 1 — barato acá).

## Frente C — PWA y login (un Sev 3 + un Sev 2)

14. **[S3] PWA arranca en `/entrar` con sesión activa** (`app/manifest.ts:8`): `start_url: "/"`;
    además `/entrar` consulta `api.yo()` y redirige si ya hay sesión.
15. **[S2] Login: tab por defecto "Equipo" y sin ayuda del código**
    (`components/login-forms.tsx:187,156-182`): `defaultValue="propietario"`; texto de ayuda
    bajo el código ("Es el código que te entregó el consejo/auditor; si no lo tenés, pedilo…").

## Frente D — Transversales (Sev 2 restantes)

16. **[S2] Transparencia: `<tr onClick>` sin teclado ni afordance** (`app/panel/transparencia/
    page.tsx:152-166`): `role="button"` + `tabIndex` + Enter/Espacio (patrón de
    `hallazgos/lista.tsx:25-33`) y fila activa con borde + chip "filtrando".
17. **[S2] Carrera en drill-down de transparencia** (`page.tsx:325-373`): guard de vigencia.
18. **[S2] Badge de pendientes desactualizado** (`app/panel/layout.tsx:10-16`,
    `components/sidebar.tsx:53-55`): `router.refresh()` tras triage exitoso (o contador en
    contexto de cliente invalidado por `alCambiar`).
19. **[S2] Períodos como texto libre** (`app/panel/analisis/page.tsx:152-169`,
    `components/liquidaciones/subir-liquidacion.tsx:45-51`): `type="month"` o
    `pattern="\d{4}-\d{2}"` + mensaje; precargar mes actual al subir liquidación.
20. **[S2] Dialog Publicar: error deja Confirmar muerto** (`app/panel/liquidaciones/[id]/
    page.tsx:104`): sacar `!!error` del `disabled`; se puede reintentar.
21. **[S2] Título del documento único para todo** (`app/layout.tsx:9-12`): `metadata` por página
    ("Hallazgos — Consorcio Transparente", "Mi unidad — …"); layout raíz neutro.
22. **[S2] Etiquetas de 10px** (`components/kpi.tsx:21`, `hallazgos/page.tsx:58`): a `text-xs`.
    **Sidebar sin `aria-current`** (`components/sidebar.tsx:41-57`): `aria-current="page"` +
    `aria-label` en el badge.

## Fortalezas a NO romper

Skeletons y polling de "procesando"; lenguaje del mundo real y `mensajeError`; accesibilidad de
las tarjetas de hallazgos (`role`, teclado, focus ring); el dialog de publicar que lista lo que
sale; cards de error con Reintentar; el pie "ninguna cifra la genera una IA".

## Sev 1 anotados (no en este ciclo)

Tokens de color vs hex sueltos (falta `--color-peligro`); emoji vs Lucide en estados de gasto;
`font-mono` inconsistente en proveedores; tooltip de "Var."; select nativo de período con estilo
propio.

## Criterio de aceptación del ciclo

Suite web completa verde (tests actualizados/extendidos donde cambia el comportamiento: búsqueda,
orden, lote, error real, colapsado de mi-unidad, start_url no testeable — verificar a mano);
`tsc --noEmit` limpio; ninguna regresión en los flujos existentes; deploy con confirmación.
