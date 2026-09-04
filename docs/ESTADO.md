# Estado del proyecto (4 de septiembre de 2026)

## Qué existe y funciona
- **API del panel** (`api/`, rama `panel-api`): FastAPI + SQLAlchemy sobre Postgres (SQLite en dev/tests). Persiste
  liquidaciones, gastos, documentos y hallazgos con estados (pendiente/preguntado/respondido/descartado/cerrado) e
  historial; auth por roles (auditor/consejo/moderador) y por código de unidad; ingesta con cuadre obligatorio
  (también en el reproceso: no_cuadra limpia y despublica, reprocesar retira informes); comprobantes por ZIP con
  cruce; publicación de informes HTML/Excel a storage (R2 o disco); vista del propietario. 88 pruebas de API +
  29 del motor. Ver `api/README.md`. Spec: `docs/superpowers/specs/2026-09-04-panel-rivadavia-design.md`.
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

## Pendientes inmediatos
1. **Plan 2: front Next.js del panel** (`panel-consorcio.neuralcore.dev`, usar la skill ui-ux-pro-max) y
   **Plan 3: deploy** (tunnel cloudflared o Fly, Neon, R2, Alembic, IP real en rate limit). La API (Plan 1) está hecha en la rama `panel-api`.
2. Segundo sistema de liquidación (hace falta un PDF de una administración que no use Redconar).
3. Reglas por comparación con mercado (escala SUTERH, honorarios de referencia, abonos).
4. La contraseña de Redconar se cambia al terminar el proyecto (decisión del usuario); mientras tanto `ct descargar` la pide por consola o
   la toma de `CT_REDCONAR_USUARIO` / `CT_REDCONAR_CLAVE`, sin guardarla.

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
