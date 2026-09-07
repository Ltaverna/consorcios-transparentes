# Estado del proyecto (6 de septiembre de 2026)

## Ciclo D-QR (7/09/2026)
- El motor lee el QR de ARCA de facturas e imágenes (`engine/ct/qr.py`, spec
  `docs/superpowers/specs/2026-09-07-qr-arca-design.md`): datos autoritativos (emisor, importe,
  fecha, numeración, receptor) que pisan lo parseado del texto, con dos cross-checks nuevos
  (`qr-texto` ALTO: el texto no coincide con el QR; `qr-numeracion` MEDIO: la factura adjunta no
  es la citada — tolera citas sin punto de venta). Dependencia opcional (pyzbar/libzbar0 en la
  imagen; sin ella el motor sigue igual). Motor: 135 tests.
- Re-cruce real: 26/575 documentos con QR legible a 200 dpi (mejora futura: más DPI/páginas);
  1 hallazgo nuevo (Maxicopy abril). Los 2 falsos positivos del 6/09 (EDESUR/Tecno Sim) fueron
  además corregidos de raíz en el parser. OCR de manuscritos: solo ~5 docs ciegos quedan,
  se evalúa si hace falta. Pendiente opcional: constatación online ARCA (WSCDC).

## Ciclo de UX (6/09/2026)
- Auditoría completa (`docs/superpowers/specs/2026-09-06-auditoria-ux.md`: 28 hallazgos, 15 principios)
  y arreglados los 22 de severidad 4-2 + 4 menores de las revisiones, en 4 frentes: hallazgos escala al
  triage real (búsqueda, orden, lote, filtros en URL, sin pérdida de scroll), mi-unidad móvil (carga
  paralela, hallazgos colapsados, visor de comprobantes en dialog), PWA/login (start_url "/", tab
  propietario por defecto), y transversales (teclado en transparencia, guards de carrera, títulos por
  página, aria). Web: 64 tests. Sev 1 anotados en la spec, no hechos.
- Backlog motor (caso Saczewiczyk, 6/09): extraer "inicio de actividades" del texto de la factura para
  enriquecer la regla de numeración baja; regla simple de correlatividad (mismo emisor, números
  consecutivos en meses consecutivos). Los 3 hallazgos de numeración quedaron en "preguntado" con la
  pregunta para la administración.

## Índice de transparencia compuesto (6/09/2026)
- El índice pasa a score compuesto 0-100: documentación 30% + conciliación 30% + trazabilidad 20% +
  consistencia 10% (las `no_cuadra` cuentan en el denominador) + explicaciones 10%, menos 2 puntos por
  CRÍTICO abierto (tope 25). Constantes con nombre en `analitica.py`; el índice se redondea sobre los
  productos crudos (reproducible al entero desde la fórmula publicada). Spec:
  `docs/superpowers/specs/2026-09-06-indice-compuesto-design.md`.
- Desglose visible en el panel, en mi-unidad y en el MCP (con la cuenta de la penalización).
  Vista propietario: solo sobre publicadas, sin conteos de no_cuadra. API 188 · web 44 tests.
- Pendiente de deploy. Pesos configurables desde el panel: anotado para después.

## Backfill de la serie histórica (6/09/2026)
- `ct sincronizar --desde AAAA-MM` (spec `docs/superpowers/specs/2026-09-06-backfill-sincronizacion-design.md`):
  el pipeline mensual corre para todos los períodos del portal desde la fecha, del más viejo al más nuevo.
  El worker diario no cambia. Motor: 106 tests.
- Corrido el 6/09 con `--desde 2025-11`: **2026-01 a 2026-08 procesadas y cuadradas al centavo** (serie de
  8 meses en la base; julio y agosto reprocesadas con la serie completa). **2025-11 y 2025-12 en `no_cuadra`
  por diferencias reales del documento** (noviembre: +$149.000 entre gastos y egresos; diciembre: $300
  corridos entre columnas A y B). El 6/09 el dueño decidió **eliminarlas de la base**: el período auditable
  arranca en 2026-01. Los PDFs quedan en la carpeta privada; futuros backfills usar `--desde 2026-01`.
  El reclamo a la administración por esos dos meses puede hacerse por fuera del sistema.
- Foto post-backfill: índice de transparencia 15/100 (ene-ago), 366 hallazgos abiertos
  (36 CRÍTICO · 121 ALTO · 199 MEDIO · 10 BAJO), triage pendiente.

## Qué existe y funciona
- **API del panel** (`api/`, rama `panel-api`): FastAPI + SQLAlchemy sobre Postgres (SQLite en dev/tests). Persiste
  liquidaciones, gastos, documentos y hallazgos con estados (pendiente/preguntado/respondido/descartado/cerrado) e
  historial; auth por roles (auditor/consejo/moderador) y por código de unidad; ingesta con cuadre obligatorio
  (también en el reproceso: no_cuadra limpia y despublica, reprocesar retira informes); comprobantes por ZIP con
  cruce; publicación de informes HTML/Excel a storage (R2 o disco); vista del propietario. 168 pruebas de API +
  73 del motor. Ver `api/README.md`. Spec: `docs/superpowers/specs/2026-09-04-panel-rivadavia-design.md`.
- **Panel web** (`web/`, rama `panel-web`): Next.js + Tailwind + shadcn/ui, theme institucional claro elegido con
  mockups. Login doble (equipo y código de unidad), liquidaciones con subida de PDF/ZIP y detalle con cuadre,
  hallazgos con filtros/drawer/página propia y acciones de auditor, consorcio (umbrales, códigos), vista del
  propietario con informe embebido. 29 pruebas (Vitest+MSW). Ver `web/README.md`. Deploy: `docs/DEPLOY.md` (API)
  + Plan 3 pendiente para el front.
  Nota deploy: setear `CT_COOKIE_DOMINIO=.neuralcore.dev` (sin eso el panel no recibe la cookie — ver docs/DEPLOY.md).
- **Motor** (`engine/ct`): parser de liquidaciones Redconar/"Mis Expensas" (formatos 2024 y 2025+), ~30 verificaciones de cuadre,
  reglas de detección (`rules.py`, catálogo en `docs/reglas.md`), cruce de comprobantes factura ↔ pago ↔ liquidación (`comprobantes.py`),
  descarga de comprobantes desde el portal (`portal.py`, comando `ct descargar`), informe Excel y HTML con marca (`informe.py`).
- **Caso piloto**: Consorcio Rivadavia 2069 (CABA), administración Almazare. Julio y agosto 2026 cuadran 100 %; el motor reproduce
  los 20 hallazgos de la auditoría manual (10 críticos en agosto, entre ellos pagos a la propietaria de 13-B por facturas de terceros,
  factura de Flow a nombre del encargado pagada como sueldo, 68 % de la liquidez en efectivo, 34 % del gasto en unidades privadas).
- **App de asamblea** (`apps/asamblea`): votación por doble mayoría (unidades + porcentual), presentes, mociones en pestañas, agenda de la
  convocatoria del 3/09/2026, preguntas con comprobante, proposiciones art. 2060 con objeciones, documentos, PIN de moderador 2069,
  exportación xlsx/PDF, sincronización entre teléfonos vía Apps Script + Google Sheet.
  - Publicada en https://asamblea.neuralcore.dev (Cloudflare Pages, proyecto `votacion-rivadavia`, cuenta 2fc07d6ef1fc55d3ed725a811cc572fb).
    Deploy: `npx wrangler login` y luego `npx wrangler pages deploy apps/asamblea --project-name votacion-rivadavia --branch main`
    (subir solo `index.html`; ver `apps/asamblea/deploy/LEEME.txt`).
  - Sheet de datos: https://docs.google.com/spreadsheets/d/1_FDA3-h5mtFomq_cERUPTrWFgaYHF2G1Fap_G2Xo-Tw/edit
  - Apps Script /exec: la URL está embebida en `index.html`. El `Code.gs` vigente ya está pegado en Apps Script (4/09/2026).
- **Plan de producto**: `docs/plan-producto.html`. Tres puertas: consejo de propietarios (autoservicio), servicio de auditoría, administrador
  transparente. Competencia relevada (Octopus, Redconar, ConsorcioAbierto, Dominium, AsambleasVirtuales, etc.): nadie cruza comprobantes ni
  trabaja para el propietario. Ventaja: independencia + del hallazgo a la decisión en asamblea.

## Decisiones tomadas
- Repo personal (Ltaverna), no Bold. Datos del consorcio fuera del repo (`~/consorcio-transparente-privado`).
- Stack objetivo (plan, sección técnica): web en Cloudflare Pages + Workers, Postgres (Neon/Supabase) con filas por consorcio,
  documentos en R2 con enlace firmado, roles consejo / propietario / moderador / auditor, propietarios entran con código por unidad.
- Backend del motor en Python; la generación de informes sale del modelo, no de datos a mano.
- Hallazgos = hechos con documento + qué pedir. Sin conclusiones acusatorias.
- Nombre "Consorcio Transparente" es provisorio.
- Etapa 1 (4/09/2026): panel solo para Rivadavia 2069; multi-consorcio después. Dominios same-site:
  `panel-consorcio.neuralcore.dev` (front, Plan 2) y `api-consorcio.neuralcore.dev` (API; arranca en máquina
  propia con cloudflared tunnel, Fly.io `eze` como upgrade). Los hallazgos declaran clave estable en el motor
  para sobrevivir reprocesos. Diferidos conscientes: revocación de tokens, Alembic y lock por período (van con el deploy/multiusuario).
- El reglamento de copropiedad (escaneado, 38 págs) está bajado del portal y digitalizado por OCR en
  `~/consorcio-transparente-privado/reglamento/` (4/09/2026).

## Artefactos publicados en claude.ai (referencia)
- Informe de expensas agosto 2026 (id 376c810b…), app votación/asamblea (64d40cb3…), plan de producto (50335d0b…).

## Producción (5/09/2026) — Plan 3 completo, EN VIVO
- **Panel**: https://panel-consorcio.neuralcore.dev (Cloudflare Worker `panel-consorcio`, deploy `cd web && npm run deploy:cf`;
  custom domain declarado en `web/wrangler.jsonc`). **API**: https://api-consorcio.neuralcore.dev (tunnel cloudflared
  `consorcio`, servicio systemd `cloudflared-consorcio` — esta máquina usa el patrón un-servicio-por-tunnel).
- **Modo provisorio en esta máquina** (decisión 5/09): en lugar de Neon/R2, Postgres 16 en contenedor + documentos a
  disco (`CT_STORAGE_DIR=/srv/storage`), vía `docker-compose.override.yml` (fuera de git) y volúmenes en `datos-api/`.
  Migrar a Neon/R2 después = `pg_dump`/restore + copiar `datos-api/storage` al bucket + editar `api/.env`.
- **Datos reales cargados por la API pública**: julio y agosto 2026 procesados (cuadre 30/30 ambos), comprobantes
  cruzados (68 y 82 documentos), informes HTML y xlsx publicados, 84 hallazgos (ago: 10 CRÍTICOS — coincide con la
  auditoría manual), vista del propietario verificada (informe inline, xlsx descarga, comprobante con attachment).
- **ZIP real medido**: 5–7 s (19 MB, vía Cloudflare) — el endpoint sincrónico queda como está (umbral era 90 s).
- Usuario auditor: taverna.lucas@gmail.com. Cuenta de Cloudflare real: 115a2f9419ee3033fde16851a506c0d6 (la nota
  anterior decía 2fc07d6…; el tunnel y el worker viven en 115a2f94…). Fase A mergeada a main: IP real tras proxy,
  descarga forzada, `proxy.ts`, Alembic (`866ed55c8961`; orden build → migrate → up), adapter OpenNext.

- **Reglamento + transparencia al propietario** (5/09, rama `reglamento-propietarios`; spec
  `docs/superpowers/specs/2026-09-05-reglamento-y-comprobantes-propietario-design.md`): el reglamento de
  copropiedad es consultable en `/reglamento` (transcripción con react-markdown + PDF descargable; subida
  del auditor en Consorcio), y los propietarios ven los hallazgos publicados en `/mi-unidad` con sus
  comprobantes descargables (solo refs de origen "comprobantes" — el review cazó la colisión con las UFs
  de morosidad). Tests: api 106 · web 40.
- **Consulta de datos** (5/09, rama `consulta-datos`; spec
  `docs/superpowers/specs/2026-09-05-consulta-datos-design.md`): endpoints `/consulta/gastos` y
  `/consulta/agregados` (variación intra-rango), vista analítica en `/panel/analisis` (ranking de
  proveedores, categorías, buscador con total), y servidor MCP read-only en
  `mcp-consorcio.neuralcore.dev` (13 tools: gastos, agregados, hallazgos, liquidaciones, reglamento, comprobantes con texto extraído, deudores y resumen mensual; token secreto en el path,
  DEPLOY.md §10) para consultar en lenguaje natural desde Claude Code, claude.ai y ChatGPT.
- **Búsqueda semántica** (6/09, rama `busqueda-semantica`; spec
  `docs/superpowers/specs/2026-09-06-busqueda-semantica-design.md`): embeddings OpenAI
  (`text-embedding-3-small`) guardados en pgvector en la columna `documentos.embedding`; se
  pueblan solos en cada ingesta de comprobantes. Endpoint `/consulta/semantica?q=&k=5` (equipo).
  Tool MCP `buscar_semantico` (14 tools en total). Backfill con `python cli.py embeddings`
  (solo NULL) o `python cli.py embeddings --todos` (re-embeber todo al cambiar de modelo).
  Requiere `CT_EMBEDDINGS_API_KEY` en `api/.env`; sin ella la búsqueda degrada a 503 y la
  ingesta sigue sin romper. Ver DEPLOY.md §10 para la configuración de la key.
- **Reglas históricas — ciclo A** (6/09, rama `main`; spec
  `docs/superpowers/specs/2026-09-06-reglas-historicas-design.md`): tres reglas nuevas del motor
  (`historia_duplicado`, `historia_salto`, `historia_concentracion`) que comparan la liquidación actual
  contra toda la serie acumulada; umbrales editables en la configuración del panel (`salto_puntos_medio`,
  `salto_puntos_alto`, `salto_importe_min`, `concentracion_proveedor`); recálculo automático e idempotente
  al final de `procesar()` y de `cruzar_comprobantes()` (origen `"historia"`). Motor 73 tests · API 168 tests.
- **Cruce endurecido — ciclo C** (6/09, rama `main`; spec
  `docs/superpowers/specs/2026-09-06-endurecer-cruce-design.md`): cinco endurecimientos calibrados con
  los casos reales de agosto 2026: (1) `historia_duplicado` re-etiqueta duplicados donde la suma cabe en
  el total facturado como posible pago en cuotas (MEDIO, clave estable); (2) `chequear_pagos_declarados`
  detecta transferencias declaradas sin comprobante propio de esa fecha (caso Roth 21-08); (3)
  `chequear_importe_factura` cruza el importe leído de las facturas adjuntas contra el gasto, el
  `factura_importe` y el total del proveedor en el mes (caso Flow, CSI); (4) `_match_gasto` desempata
  por número de factura o fecha antes de marcar atribución incierta (hallazgo BAJO); (5) regla
  `certificador` sobre la liquidación sola (Roth certifica y ejecuta — MEDIO, área Obras / contratación).
  Motor 99 tests · API 168 tests. **Pendiente de deploy + reproceso de julio y agosto** (re-etiqueta
  los duplicados de Roth y Saczewiczyk como cuotas MEDIO y agrega los hallazgos nuevos).
- **Índice de transparencia — ciclo E** (6/09, rama `main`; spec
  `docs/superpowers/specs/2026-09-06-indice-transparencia-design.md`): módulo puro
  `api/app/analitica.py` con 5 estados por gasto (`verificado`, `requiere_explicacion`,
  `anomalia`, `inconsistencia`, `sin_informacion`) calculados en tiempo real a partir de
  documentos + hallazgos abiertos + triage, sin almacenar nada; índice = % del dinero
  trazable de punta a punta (gastos verificados sobre total). Endpoints `/analitica/indice`
  (métricas globales y por período, con rango opcional) y `/analitica/gastos?periodo&estado`
  (drill-down por gasto con hallazgos y documentos) — misma compuerta de rol que `/hallazgos`;
  propietario recibe solo lo publicado. Dos tools MCP: `indice_transparencia` y `estado_gastos`
  (total: 16 herramientas; ver `docs/MCP.md`). En el panel web: página `panel/transparencia`
  con índice grande, tres barras de progreso (trazable / con factura / pagos respaldados),
  tabla de estados con drill-down interactivo y card de cuestiones por severidad; en `mi-unidad`:
  card Transparencia visible al propietario con el índice y los conteos (se oculta en silencio
  si no hay períodos publicados o hay error de red). Motor 99 tests · API 180 tests · web 44.
  **Pendiente de deploy** (api + worker + mcp + web con `npm run deploy:cf`).
  Próximos ciclos: B (prorrateo vs escritura del reglamento) → D (OCR de imágenes/recibos manuscritos).
- **Reglas de mercado + normativa + PWA** (5/09, rama `reglas-mercado`; spec
  `docs/superpowers/specs/2026-09-05-reglas-mercado-design.md`): tres reglas nuevas del motor calibradas
  contra los gastos reales (`sueldo_mercado` con detección de SAC, `honorarios_mercado`, `abonos_mercado`
  con exclusión de pólizas) — referencias en la Config del panel, 0 = apagada; biblioteca de normativa
  (escala SUTERH/acuerdo/honorarios, legible por cualquier sesión, subida del auditor); visor embebido
  para propietarios en hallazgos publicados; panel instalable como PWA (manifest + monograma CT).
  Referencias cargadas y validadas el 5/09 (escala SUTERH ago-2026, honorarios AIERH Clase C, topes de abonos); julio/agosto reprocesados: 2 hallazgos de mercado nuevos en julio (SAC anotado, ascensores sobre tope), agosto limpio.
  La transcripción del reglamento fue revisada contra el escaneo (5/09): porcentuales reconstruidos
  suman 100,0000% exacto; re-subir al panel.
- **Portabilidad total en compose** (5/09, rama `portabilidad-compose`; spec
  `docs/superpowers/specs/2026-09-05-portabilidad-compose-design.md`): el stack entero (API + Postgres +
  worker + tunnel) corre con `docker compose up -d`; la sincronización diaria vive en el servicio `worker`
  (APScheduler 06:30 AR + corrida al arrancar, `api/worker.py`) y el tunnel en el servicio `tunnel`
  (cloudflared con credenciales en `./cloudflared/`, gitignoreada). Migrar de máquina = DEPLOY.md §9.
  Sin systemd: los units `ct-sincronizar` y `cloudflared-consorcio` se retiran en el switchover.
- **Sincronización mensual automática** (5/09, rama `sincronizacion-mensual`; spec
  `docs/superpowers/specs/2026-09-05-sincronizacion-mensual-design.md`): worker diario 06:30
  (servicio `worker` de compose, DEPLOY.md §8) corre `ct sincronizar` — baja del portal la liquidación nueva
  (`ct descargar-liquidacion`, POST a `/fees/expensesViewer.php`) y los comprobantes, y los ingesta a la API
  con el bot `robot@consorcio-transparente.local` (estado idempotente en `$CT_PRIVADO/sincronizacion.json`,
  ZIP determinista por hash). **Nunca publica.** El engine pasa de 31 a 45 tests.

## Pendientes inmediatos
0. **OAuth 2.1 del MCP (etapa 2, diseño pendiente)**: hoy el acceso individual es por tokens con nombre
   revocables (`cli.py mcp-token`, 6/09); si el grupo de usuarios del MCP crece, subir a OAuth con login
   del panel (authorization server + PKCE + registro dinámico — anotado en la spec de tokens).
1. **Triage de hallazgos en el panel**: los 84 están `pendiente`; revisar y publicar los que correspondan.
2. **Migrar a Neon + R2** cuando Lucas cree las cuentas (hoy todo local en esta máquina; ver "Modo provisorio").
3. **SSO de Google del equipo: implementado** (5/09, rama `sso-google`; spec
   `docs/superpowers/specs/2026-09-05-sso-google-design.md`): botón de GIS en `/entrar` + `POST /auth/login-google`
   con verificación del ID token (JWKS, RS256) y alta previa obligatoria; identidad anclada al email (decisión
   registrada). Convive con la clave; propietarios siguen con código. Para encenderlo: `CT_GOOGLE_CLIENT_ID` en
   `api/.env` y `NEXT_PUBLIC_GOOGLE_CLIENT_ID` en `web/.env.production` (el client ID está en el `.env` raíz;
   el secret de al lado no se usa). Requiere los JavaScript origins del panel en el OAuth client de Google.
4. Segundo sistema de liquidación (hace falta un PDF de una administración que no use Redconar).
5. Reglas por comparación con mercado (escala SUTERH, honorarios de referencia, abonos).
6. La contraseña de Redconar se cambia al terminar el proyecto (decisión del usuario); mientras tanto `ct descargar` la pide por consola o
   la toma de `CT_REDCONAR_USUARIO` / `CT_REDCONAR_CLAVE`, sin guardarla.

**Seguimiento post-merge**: KPIs/badge en vivo durante el triage. Resueltos el 5/09 (rama `visor-gating-rol`,
spec `docs/superpowers/specs/2026-09-05-visor-y-gating-rol-design.md`): el visor de comprobantes volvió con
`?vista=1` (inline solo para roles del equipo; descarga forzada intacta) y el panel es de solo lectura para
consejo/moderador (contexto `useRol`). Suites: api 94 · web 34. Nota de máquina: Node 22.11 (los tests de web
necesitan `NODE_OPTIONS='--experimental-require-module'`; conviene ≥ 22.12).

## Cómo correr
```bash
cd engine
python3 -m pytest -q tests
python3 -m ct analizar "$CT_PRIVADO/liquidaciones/2026-08-31-19_06_13-RIVADAVIA 2069.pdf" \
  --anterior "$CT_PRIVADO/liquidaciones/2026-07-28-120402-RIVADAVIA 2069.pdf" \
  --comprobantes "$CT_PRIVADO/Comprobantes Rivadavia 2069" --manifiesto "$CT_PRIVADO/Comprobantes Rivadavia 2069/manifest.json" \
  --mes 2026-08 --excel informe.xlsx --html informe.html --marca "Consorcio Transparente"
python3 -m ct descargar listar --carpeta "$CT_PRIVADO/Comprobantes Rivadavia 2069"
```
Requisitos: Python 3.10+, `poppler-utils` (pdftotext), `pip install openpyxl pytest`. Para la app: Node (npx wrangler).
