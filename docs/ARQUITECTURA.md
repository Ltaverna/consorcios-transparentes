# Arquitectura

Estado del documento: 7 de septiembre de 2026. Describe el sistema tal como está en producción.
Para el flujo de datos paso a paso ver [PIPELINE.md](PIPELINE.md); para qué hace cada superficie,
[FUNCIONALIDADES.md](FUNCIONALIDADES.md).

## 1. Vista de conjunto

Cuatro piezas de software y una frontera de datos privados:

```
  Portal Redconar ("Mis Expensas")          Carpeta privada (~/consorcio-transparente-privado)
   liquidación PDF + comprobantes            PDFs, ZIPs, manifiestos, reglamento, estado de sync
            │                                              │
            │  ct descargar / ct sincronizar               │ (nunca entra al repo)
            ▼                                              ▼
  ┌───────────────────────────────────────────────────────────────┐
  │ MOTOR  engine/ct  ·  Python puro, sin estado, sin base        │
  │ parseo → cuadre → reglas → cruce de comprobantes → informes   │
  └───────────────────────────────────────────────────────────────┘
            │ importado como biblioteca
            ▼
  ┌───────────────────────────────────────────────────────────────┐          ┌──────────────┐
  │ API  api/app  ·  FastAPI + SQLAlchemy                         │◀────────▶│ Postgres 16  │
  │ ingesta · triage · publicación · analítica · auth por rol     │          │ + pgvector   │
  └───────────────────────────────────────────────────────────────┘          └──────────────┘
        │                    │                    │                                  │
        │                    │                    │                          ┌──────────────┐
        │                    │                    │                          │ Storage      │
        │                    │                    │                          │ R2 o disco   │
        ▼                    ▼                    ▼                          └──────────────┘
  ┌────────────┐      ┌────────────┐      ┌────────────┐
  │ WEB        │      │ MCP        │      │ WORKER     │
  │ Next.js 16 │      │ 16 tools   │      │ APScheduler│
  │ Cloudflare │      │ read-only  │      │ 06:30 sync │
  │ Worker     │      │            │      │ 07:00 dump │
  └────────────┘      └────────────┘      └────────────┘
   panel-consorcio     mcp-consorcio       (sin puerto expuesto)
   .neuralcore.dev     .neuralcore.dev
```

Todo lo que se publica sale del motor. La API no inventa cifras, el front no calcula montos y el MCP
no escribe: cada número que ve un propietario es reproducible corriendo el motor sobre el mismo PDF.

## 2. Motor (`engine/ct/`)

Biblioteca Python sin estado, sin base de datos y sin dependencias duras más allá de la stdlib.
Es el corazón del proyecto y la única pieza que decide qué es un hallazgo.

| Módulo | Responsabilidad |
|---|---|
| `model.py` | Modelo de datos independiente del sistema emisor: `Liquidacion`, `Gasto`, `Pago`, `Unidad`, `Deudor`, `Cuenta`, `EstadoFinanciero`, `Patrimonial`, `MesEvolucion`, `Check`. Dataclasses puras con `to_dict()`. |
| `redconar.py` | Parser de liquidaciones Redconar / "Mis Expensas" (plantillas 2024 y 2025+). Convierte PDF → texto (`pdftotext -layout`) → `Liquidacion`, y emite los `Check` de cuadre. |
| `rules.py` | Registro de reglas sobre la liquidación (decorador `@rule`), dataclass `Hallazgo` y dataclass `Config` con todos los umbrales. 15 reglas. |
| `historia.py` | Reglas sobre la **serie** de meses (`@rule_h`): duplicados entre meses, saltos de precio, concentración de proveedores. 3 reglas. |
| `comprobantes.py` | Lectura, clasificación e interpretación de adjuntos; cruce factura ↔ pago ↔ gasto. Emite los hallazgos documentales. |
| `escritura.py` | Compara el prorrateo de la liquidación contra los porcentuales de dominio del reglamento. 1 regla (`prorrateo_escritura`). |
| `qr.py` | Lee el QR de ARCA de las facturas. Dependencia **opcional** (`pyzbar` + `Pillow` + `libzbar`): sin ella el motor funciona igual. |
| `portal.py` | Cliente HTTP del portal Redconar (urllib + cookies): login, períodos, egresos, adjuntos, PDF de liquidación. |
| `sincronizar.py` | Orquestador idempotente portal → carpeta privada → API. Soporta backfill (`--desde AAAA-MM`). |
| `informe.py` | Informe Excel (openpyxl) y HTML autocontenido, con marca. |
| `cli.py` | Línea de comandos: `analizar`, `descargar`, `descargar-liquidacion`, `sincronizar`. |

**Dependencias externas**: `pdftotext` y `pdftoppm` (poppler) como binarios; `openpyxl` solo para el
Excel; `pyzbar`/`Pillow` solo para el QR. Ninguna regla necesita red.

**Principios de diseño del motor**

- *Una regla rota no tumba el análisis*: `evaluar()` captura la excepción de cada regla por separado.
- *Clave estable*: cada `Hallazgo` declara una `clave` (por ejemplo `dup-fact|…`, `pago-sin-comp|2026-08-21`,
  `escritura|13`) que sobrevive al reprocesamiento. Es lo que permite que el triage del auditor no se pierda
  cuando se vuelve a procesar el mismo mes.
- *El documento manda*: cuando una factura trae QR de ARCA, sus datos pisan lo parseado del texto y la
  divergencia queda registrada como nota (y como hallazgo `qr-texto` si es material).

## 3. API (`api/`)

FastAPI + SQLAlchemy 2. Importa el motor como biblioteca (`pip install ./engine`). Postgres 16 con
pgvector en producción; SQLite en memoria en los tests.

### Módulos

| Archivo | Responsabilidad |
|---|---|
| `app/main.py` | App FastAPI, CORS, `/salud`, montaje de routers, guardas de arranque. |
| `app/models.py` | ORM: 10 tablas (ver abajo). Tipos propios `JSONDict`/`JSONList` (JSONB en Postgres), `FechaUTC`, `VectorDual` (pgvector en PG, JSON en SQLite). |
| `app/ingesta.py` | El corazón del backend: `procesar()` y `cruzar_comprobantes()`, upsert idempotente de hallazgos, recálculo de la historia. |
| `app/publicar.py` | Genera y versiona los informes HTML/XLSX y marca la liquidación como publicada. |
| `app/analitica.py` | Módulo **puro**: estados por gasto e índice de transparencia compuesto. No almacena nada. |
| `app/security.py` | Argon2id, JWT en cookie httpOnly, gating por rol, rate limiting, verificación de ID token de Google, IP real detrás del proxy. |
| `app/storage.py` | Abstracción de almacenamiento: `LocalStorage` (disco, con protección de path traversal) o `R2Storage` (boto3/S3, con URLs firmadas). |
| `app/texto.py` | Extracción de texto de documentos (`pdftotext`), con cache por hash, y selección del fragmento relevante de una factura. |
| `app/embeddings.py` | Cliente de embeddings compatible con OpenAI. Degradable: sin API key todo sigue funcionando. |
| `app/admin.py` | Alta de consorcio, usuarios, códigos por unidad y tokens del MCP. |
| `app/config.py` | Todas las variables `CT_*` con sus defaults. |
| `app/routers/` | `auth`, `consorcio`, `consulta`, `documentos`, `hallazgos`, `liquidaciones`, `analitica`. |
| `cli.py` | `init`, `usuario`, `codigo`, `embeddings`, `mcp-token {crear,listar,revocar}`. |
| `worker.py` | APScheduler: sincronización 06:30 y `pg_dump` 07:00 (hora de Buenos Aires). |
| `servidor_mcp.py` | Servidor MCP read-only + wrapper ASGI de tokens por persona. |

### Modelo de datos

| Tabla | Claves y notas |
|---|---|
| `consorcio` | Datos del consorcio y `umbrales` (JSONB): los campos de `Config` del motor editables desde el panel. |
| `unidades` | `uf` único; `porcentuales` por clase; `codigo_hash` (argon2) para el acceso del propietario. |
| `usuarios` | `email` único, `clave_hash` (argon2), `rol` ∈ {auditor, consejo, moderador}. |
| `mcp_tokens` | `nombre` único, `token_sha256` indexado, `activo`. El token en claro **nunca** se guarda. |
| `liquidaciones` | `periodo` único (AAAA-MM), `estado` ∈ {procesando, procesada, no_cuadra, error, publicada}, `cuadra`, `datos` (JSONB con el `to_dict()` completo del motor), `archivo_key`. |
| `gastos` | Único `(liquidacion_id, n)`. `pagos` como JSONB. Borrado en cascada. |
| `documentos` | `gasto_n`, `tipo` ∈ {factura, pago, recibo, imagen, otro}, `hash` SHA256, `metadatos` (el `to_dict()` del `Documento` del motor, incluido el QR), `embedding` vector(1536) nullable. |
| `hallazgos` | Único `(liquidacion_id, origen, clave)` — la identidad estable. `origen` ∈ {liquidacion, comprobantes, historia}; `estado` ∈ {pendiente, preguntado, respondido, descartado, cerrado}; `publicado`; `refs`; `respuesta_admin`. |
| `hallazgo_eventos` | Historial de triage: `de` → `a`, `nota`, `usuario_id`, `ts`. Nada se pisa sin dejar rastro. |
| `informes` | Único `(liquidacion_id, tipo)`, `archivo_key` versionada por timestamp+uuid, `marca`. |

Migraciones Alembic en `api/migrations/versions/`: `866ed55c8961` (esquema inicial etapa 1),
`a413127a14eb` (columna `embedding`, pgvector), `5733961d6f19` (tokens del MCP por persona).
El `create_all` del arranque es inofensivo después de `alembic upgrade head` (usa `checkfirst`).

### Autenticación y roles

- **Equipo**: `POST /auth/login` (email + clave, argon2id) o `POST /auth/login-google` (ID token
  verificado contra el JWKS de Google, RS256, `email_verified` obligatorio; la identidad se ancla al
  email y el alta previa es obligatoria — no hay auto-registro).
- **Propietario**: `POST /auth/login-unidad` con UF + código de 8 caracteres (sin 0/O/1/I para poder
  dictarlo). Del código solo vive el hash argon2; se muestra una única vez al generarlo.
- **Sesión**: JWT HS256 en cookie httpOnly `ct_sesion`, `samesite=lax`, `secure` según entorno,
  `sub` = `u:{id}` o `uf:{uf}`, expiración `CT_JWT_HORAS` (12 por defecto).
- **Roles**: `auditor` (escribe), `consejo` y `moderador` (solo lectura del panel), `propietario`
  (solo lo publicado, y solo lo suyo).
- **Rate limiting** en memoria, ventana deslizante: login 10/300 s por IP+identidad; validación de
  token del MCP 60/300 s por IP. Detrás del tunnel la IP real sale de `CF-Connecting-IP` **solo** si
  `CT_CONFIAR_PROXY=true`, y eso es seguro porque el contenedor publica el puerto en loopback.

### Índice de transparencia (`app/analitica.py`)

Módulo puro, sin almacenamiento: todo se deriva en tiempo real de gastos + documentos + hallazgos + triage.

Cada gasto recibe un estado por precedencia estricta:

1. `inconsistencia` — tiene un hallazgo **CRÍTICO** abierto
2. `anomalia` — tiene un hallazgo **ALTO** abierto
3. `sin_informacion` — no tiene ningún documento adjunto
4. `requiere_explicacion` — tiene hallazgos abiertos de menor severidad
5. `verificado` — nada abierto y con documentos

El índice compuesto 0–100:

```
documentacion = dinero_con_factura      / dinero_total     × 0,30
conciliacion  = dinero_pago_respaldado  / dinero_total     × 0,30
trazabilidad  = dinero_verificado       / dinero_total     × 0,20
consistencia  = periodos_que_cuadran    / periodos_totales × 0,10
explicaciones = resueltos / (abiertos + resueltos)         × 0,10

penalizacion = min(25, 2 × hallazgos_CRÍTICOS_abiertos)
indice       = max(0, min(100, round(Σ componentes − penalizacion)))
```

Detalles que importan:

- El índice se redondea **sobre los productos crudos**, no sobre los puntos redondeados que se muestran.
  Así el número publicado es reproducible al entero desde la fórmula.
- `consistencia` cuenta las `no_cuadra` en el denominador: ocultar un mes que no cuadra no mejora el score.
- `explicaciones` vale 1,0 si no hay ningún hallazgo, pero 0,0 si el rango no tiene liquidaciones
  (un rango vacío da índice 0, no 10).
- `_pago_respaldado()`: el efectivo nunca cuenta como respaldado; el débito automático siempre (queda
  en el resumen bancario); las transferencias exigen comprobante adjunto y ningún hallazgo
  `pago-sin-comp` abierto.
- Las reglas cuyas refs son UFs y no números de gasto (`morosidad`, `prorrateo_escritura`) están en
  `REGLAS_REFS_UF` y no clasifican gastos.

## 4. Web (`web/`)

Next.js 16.3.4 (App Router) + React 19 + Tailwind 4 + shadcn/ui, desplegado como Cloudflare Worker
mediante OpenNext (`@opennextjs/cloudflare`), worker `panel-consorcio`, dominio
`panel-consorcio.neuralcore.dev`.

- **Guard de servidor** en `app/panel/layout.tsx`: pide `/auth/yo` con la cookie reenviada
  (`lib/api-server.ts`), redirige propietarios a `/mi-unidad` y monta `RolProvider`.
- **Cliente tipado** en `lib/api.ts`: `fetch` con `credentials: "include"`, `ApiError` con status y
  detail, redirección a `/entrar` ante 401.
- Rutas: `/entrar`, `/panel/hallazgos` (+ `/[id]`), `/panel/liquidaciones` (+ `/[id]`),
  `/panel/analisis`, `/panel/transparencia`, `/panel/consorcio`, `/mi-unidad`, `/reglamento`.
- PWA instalable (`app/manifest.ts`, `start_url: "/"`), metadata por ruta con un `layout.tsx` por sección.

El front solo consume la API: no habla con la base, no toca storage y no recalcula ningún monto.

## 5. MCP (`api/servidor_mcp.py`)

Servidor MCP de **solo lectura** en `mcp-consorcio.neuralcore.dev`. 16 herramientas: 14 de dominio
(`consultar_gastos`, `agregados`, `listar_hallazgos`, `detalle_hallazgo`, `estado_liquidaciones`,
`reglamento`, `leer_comprobante`, `buscar_en_comprobantes`, `buscar_semantico`, `deudores`,
`detalle_liquidacion`, `resumen_mensual`, `indice_transparencia`, `estado_gastos`) más `search` y
`fetch` para compatibilidad con el modo investigación de ChatGPT.

No habla con la base: consulta la API pública con una sesión de bot, así que hereda exactamente las
mismas reglas de negocio.

**Autenticación**: el token viaja en el path (`/mcp/<token>`). Un wrapper ASGI lo valida contra el
token maestro (`CT_MCP_TOKEN`, comparación en tiempo constante) o contra la tabla `mcp_tokens` vía
`POST /auth/mcp-token/validar`, con cache de 60 s. Ante un error de red, una entrada positiva vencida
se reutiliza con warning (*stale-while-error*), pero un token nunca visto se rechaza sin cachear el
negativo. Token inválido → 404 pelado. Revocar tarda ≤ 1 minuto en hacer efecto.

## 6. Infraestructura

`docker compose` con cinco servicios (el quinto llega por el override local):

| Servicio | Imagen | Qué hace |
|---|---|---|
| `api` | build de `api/Dockerfile` (python:3.12-slim + poppler + libzbar0 + postgresql-client) | uvicorn en `127.0.0.1:8080` (solo loopback). |
| `worker` | la misma imagen | `python worker.py`: sincronización 06:30 y backup 07:00. Monta la carpeta privada del host. |
| `mcp` | la misma imagen | `python servidor_mcp.py` en :8765. |
| `tunnel` | `cloudflare/cloudflared` | Publica `api-consorcio` → `api:8080` y `mcp-consorcio` → `mcp:8765`. |
| `db` | `pgvector/pgvector:pg16` (override) | Postgres con healthcheck; datos en `datos-api/db-postgres`. |

**Modo provisorio vigente** (decisión del 5/09/2026): en lugar de Neon + R2, Postgres en contenedor y
documentos a disco (`CT_STORAGE_DIR=/srv/storage` → `datos-api/storage`), configurado en un
`docker-compose.override.yml` que está fuera de git. Migrar a Neon/R2 es `pg_dump`/restore + copiar la
carpeta de storage al bucket + editar `api/.env`.

El deploy completo, la migración de máquina y el runbook están en [DEPLOY.md](DEPLOY.md).

## 7. Frontera de datos privados

Regla dura del proyecto: **ningún dato del consorcio entra al repositorio**.

- Liquidaciones PDF, comprobantes descargados, manifiestos, reglamento escaneado y planillas viven en
  `~/consorcio-transparente-privado/` (o donde apunte `CT_PRIVADO`), y se copian de máquina a máquina
  por fuera de git.
- Las credenciales del portal Redconar y de Cloudflare no se guardan en ningún archivo del repo: van
  en `.env` (gitignoreado) o se piden por consola.
- Los fixtures de los tests son textos de `pdftotext -layout` recortados y, cuando el caso lo exige,
  con valores inventados que preservan la estructura.
- Del código de unidad y de los tokens del MCP solo persiste el hash.

## 8. Decisiones de arquitectura y por qué

| Decisión | Razón |
|---|---|
| Motor sin dependencias ni base | Que cualquiera pueda reproducir un hallazgo con `python -m ct analizar` sobre el PDF, sin levantar infraestructura. Es la base de la credibilidad del informe. |
| Cuadre obligatorio antes de cualquier regla | Un hallazgo sobre una liquidación que no cierra al centavo no es un hallazgo, es ruido. |
| Clave natural en cada hallazgo | El reprocesamiento es constante (llegan comprobantes, cambia un umbral, se agrega una regla). Sin identidad estable, el triage se perdería en cada corrida. |
| Analítica derivada, nunca almacenada | El índice cambia solo cuando cambian los hechos o el triage. No hay una tabla de scores que pueda quedar desactualizada ni editarse a mano. |
| MCP contra la API, no contra la base | Hereda gating por rol y reglas de negocio sin duplicarlas. |
| Cargas opcionales con savepoint | Historia, escritura y embeddings fallan sin tumbar la ingesta: nunca se pierde un mes por una regla nueva. |
| Todo en compose | Migrar de máquina es copiar cuatro archivos y `docker compose up -d`. Sin systemd, sin venvs en producción. |

## 9. Pruebas

| Suite | Cantidad | Comando |
|---|---|---|
| Motor | 151 | `cd engine && .venv/bin/python -m pytest -q tests` |
| API | 192 | `cd api && .venv/bin/python -m pytest -q` |
| Web | 64 | `cd web && npm test` (Node 22.11 necesita `NODE_OPTIONS='--experimental-require-module'`) |

Los tests de la API corren sobre SQLite en memoria y storage en tmp: no tocan servicios externos.
Los del motor usan fixtures de texto real en `engine/tests/fixtures/`; los de comprobantes se saltean
si no está la carpeta privada.
