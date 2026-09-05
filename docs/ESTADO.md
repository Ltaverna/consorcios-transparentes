# Estado del proyecto (5 de septiembre de 2026)

## Qué existe y funciona
- **API del panel** (`api/`, rama `panel-api`): FastAPI + SQLAlchemy sobre Postgres (SQLite en dev/tests). Persiste
  liquidaciones, gastos, documentos y hallazgos con estados (pendiente/preguntado/respondido/descartado/cerrado) e
  historial; auth por roles (auditor/consejo/moderador) y por código de unidad; ingesta con cuadre obligatorio
  (también en el reproceso: no_cuadra limpia y despublica, reprocesar retira informes); comprobantes por ZIP con
  cruce; publicación de informes HTML/Excel a storage (R2 o disco); vista del propietario. 88 pruebas de API +
  29 del motor. Ver `api/README.md`. Spec: `docs/superpowers/specs/2026-09-04-panel-rivadavia-design.md`.
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
- **Sincronización mensual automática** (5/09, rama `sincronizacion-mensual`; spec
  `docs/superpowers/specs/2026-09-05-sincronizacion-mensual-design.md`): timer diario 06:30
  (`ct-sincronizar.timer`, DEPLOY.md §8) corre `ct sincronizar` — baja del portal la liquidación nueva
  (`ct descargar-liquidacion`, POST a `/fees/expensesViewer.php`) y los comprobantes, y los ingesta a la API
  con el bot `robot@consorcio-transparente.local` (estado idempotente en `$CT_PRIVADO/sincronizacion.json`,
  ZIP determinista por hash). **Nunca publica.** El engine pasa de 31 a 45 tests.

## Pendientes inmediatos
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
