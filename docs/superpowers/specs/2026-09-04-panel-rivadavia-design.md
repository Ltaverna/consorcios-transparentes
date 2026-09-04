# Panel de auditoría con base de datos — Rivadavia 2069 (diseño aprobado 04-09-2026)

Etapa 1 del plan de producto: pasar del motor "one-shot" (CLI que reparsea PDF y no recuerda nada)
a un panel en la nube con persistencia, estados de hallazgos y publicación controlada.
Alcance: **un solo consorcio** (Rivadavia 2069). Multi-consorcio queda para cuando exista el segundo caso
(migración prevista: agregar `consorcio_id` con default a las tablas).

## Decisiones tomadas (con Lucas, 04-09-2026)

- En la nube desde el arranque (no panel local).
- Front separado: **Next.js** (App Router, TypeScript, Tailwind + shadcn/ui) en **Cloudflare Workers (OpenNext)**, dominio tipo `panel-consorcio.neuralcore.dev`.
- API: **FastAPI + SQLAlchemy/Alembic** con Python + poppler. Hosting (Plan 3): **máquina propia de Lucas con `cloudflared tunnel`**
  como arranque (costo cero; cloudflared ya instalado), Fly.io región `eze` (o Railway) cuando haga falta 24/7,
  publicada como **`api-consorcio.neuralcore.dev`** (ruta del tunnel cloudflared, o CNAME a Fly). Decisión del 04-09: front y API deben ser same-site
  (`panel-consorcio.neuralcore.dev` ↔ `api-consorcio.neuralcore.dev`) para que la cookie de sesión `SameSite=Lax` viaje en los fetch;
  con un dominio `*.fly.dev` el login no funcionaría. En el deploy, el rate limit debe tomar la IP real de `Fly-Client-IP`.
- Base: **Neon Postgres** (AWS São Paulo). Documentos: **Cloudflare R2** privado con URL firmada.
- **Auth completa ya**: roles auditor/consejo/moderador con email+contraseña, propietarios con código por unidad.
- Primer entregable: **núcleo auditor** (ingesta + panel de hallazgos con estados). El propietario entra con código y ve solo el informe publicado. La app de asamblea actual no se toca.
- Sin cola de trabajos: `BackgroundTasks` de FastAPI alcanza (parsear < 1 s, cruce de ~150 comprobantes en segundos).

## Estructura del repo

```
engine/          → intacto: biblioteca Python pura + CLI. Único cambio: Config construible desde dict.
api/             → NUEVO: FastAPI, SQLAlchemy 2 + Alembic, importa engine. Dockerfile con poppler.
web/             → NUEVO: Next.js.
apps/asamblea/   → intacto (demo en producción).
```

## Modelo de datos (Postgres)

**Configuración**
- `consorcio` — una sola fila: nombre, dirección, CUIT, administración (nombre y CUIT como campos), `umbrales` JSONB (la `Config` de `rules.py`).
- `unidades` — UF, piso/depto, tipo, propietario, porcentuales por clase (JSONB), `codigo_acceso` hasheado (se muestra una vez al generarlo). Fuente inicial: el parse de la liquidación (116 unidades).

**Acceso**
- `usuarios` — email, nombre, hash de contraseña, rol directo (`auditor | consejo | moderador`). Sin membresías. Creación por comando, sin registro abierto.
- Propietarios: sin usuario; entran con el código de su unidad.

**Datos del motor**
- `liquidaciones` — período `AAAA-MM`, sistema, estado (`procesando | no_cuadra | procesada | publicada`), clave R2 del PDF, `datos` JSONB (el `Liquidacion.to_dict()` completo), `cuadra` bool.
- `gastos` — normalizados: nº, categoría, proveedor, concepto, clase, importe, datos de factura, pagos JSONB. Permite consultas por proveedor entre meses. Unidades y deudores del mes quedan en el JSONB de la liquidación.
- `documentos` — gasto/liquidación asociados, tipo (factura/pago/recibo/imagen/otro), clave R2, hash del archivo, metadatos extraídos JSONB (CUITs, importes, fechas).

**Hallazgos con estado**
- `hallazgos` — regla, severidad, área, título, evidencia, monto, recomendación, `clave_natural` (regla + referencia estable) para upsert al reprocesar **sin pisar el estado**; estado `pendiente | preguntado | respondido | descartado | cerrado`; flag `publicado`; respuesta de la administración.
- `hallazgo_eventos` — historial: usuario, cambio de estado, nota, timestamp.

**Publicación**
- `informes` — liquidacion_id, tipo (html/xlsx), clave R2, fecha de publicación, marca. Lo único visible para el propietario.

## Flujo de ingesta y publicación

1. **Subir liquidación** (auditor): PDF → R2 → fila `procesando` → en background: pdftotext → `parse_pdf` → checks → `evaluar` con umbrales del consorcio.
   - Falla un check → `no_cuadra`: se ven los checks fallidos, no se puede publicar.
   - Cuadra → `procesada`: inserta gastos, upsert de hallazgos por `clave_natural`.
2. **Subir comprobantes**: ZIP con la carpeta del mes + `manifest.json` (formato de `ct descargar`) → R2 → cruce (`comprobantes.py`) → documentos + hallazgos de cruce (upsert, re-subir no duplica).
3. **Mes anterior automático**: al procesar un período la API busca la liquidación `procesada` del mes previo y se la pasa a `evaluar`.
4. **Publicar** (acción explícita): genera informe HTML y Excel con `informe.py`, sube a R2, marca `publicada`. Solo entran los hallazgos con flag `publicado`, revisados uno por uno.
5. Procesamiento fallido → estado visible con error; reintentar = re-subir (idempotente por hash + upsert).

## Auth

- La API es dueña de la auth: JWT en cookie httpOnly. Sin Auth.js ni proveedor externo.
- Login 1: email + contraseña → auditor / consejo / moderador.
- Login 2: código de unidad → sesión de propietario ligada a su UF, solo lectura de lo publicado.
- Next.js: middleware que chequea cookie y rol por ruta.

## Pantallas

**Auditor** (`/panel`)
1. **Liquidaciones** — lista por mes con estado y semáforo de cuadre; subir PDF / ZIP; detalle con checks, gastos y documentos (visor PDF por URL firmada).
2. **Hallazgos** — pantalla central: tabla filtrable (severidad, estado, regla, mes), detalle con evidencia y documentos citados, cambio de estado con nota, respuesta de la administración, toggle publicar.
3. **Consorcio** — datos, umbrales editables, unidades con generación de códigos, usuarios.

**Propietario** (`/mi-unidad`) — informe HTML publicado, descarga del Excel, su estado de cuenta. Nada más en esta etapa.

## Seguridad

- R2 privado; URLs firmadas de 15 min emitidas por la API tras chequear rol. PDF nunca públicos (Ley 25.326).
- Códigos y contraseñas con argon2/bcrypt; rate limit en ambos logins.
- Secretos (Neon, R2, JWT) solo en variables de entorno de Fly/Cloudflare.

## Pruebas

- Las 27 del motor, intactas.
- API: pytest contra Postgres local (docker), ingesta completa con los fixtures de `engine/tests/fixtures` (sin datos privados).

## Fuera de alcance (etapa 1)

Multi-consorcio, app de asamblea desde la base, experiencia plena del propietario (preguntas, seguimiento),
cola de trabajos, segundo formato de liquidación, reglas de mercado (SUTERH/CAPHAI).
