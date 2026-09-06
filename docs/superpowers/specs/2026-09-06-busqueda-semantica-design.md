# Búsqueda semántica: pgvector + embeddings por API (diseño aprobado 06-09-2026)

Los textos de los comprobantes se embeben con una API externa y se guardan en Postgres (pgvector);
la ingesta mensual puebla los nuevos automáticamente. Tool MCP `buscar_semantico` y endpoint de equipo.

## 1. Base de datos

- Imagen del servicio `db` → `pgvector/pgvector:pg16` (mismo Postgres 16, el volumen actual se conserva;
  solo agrega la extensión disponible). En el `docker-compose.override.yml` local de la máquina.
- Migración Alembic: `CREATE EXTENSION IF NOT EXISTS vector` (solo en dialecto postgresql) + columna
  `embedding` en `documentos`: tipo `Vector(1536)` en Postgres, `JSON` en SQLite (TypeDecorator propio;
  los tests siguen sin servicios). Nullable — un documento sin embedding es válido.

## 2. Cliente de embeddings (`api/app/embeddings.py`)

- OpenAI-compatible: `POST {CT_EMBEDDINGS_URL}/embeddings` con `{model, input}`; config:
  `CT_EMBEDDINGS_API_KEY` (mapear desde `OPENAI_API_KEY` del `.env` raíz en compose),
  `CT_EMBEDDINGS_MODELO` (default `text-embedding-3-small`), `CT_EMBEDDINGS_URL`
  (default `https://api.openai.com/v1`). Sin key → deshabilitado (None), nunca error.
- `embeber(textos: list[str]) -> list[list[float]] | None`: batch, texto truncado a 8000 caracteres,
  urllib puro, timeout 30 s, errores → None con log (la ingesta jamás se rompe por embeddings).

## 3. Población

- En `cruzar_comprobantes` (ingesta): tras guardar los documentos, extraer texto (helper pdftotext
  existente) y embeber en batch los que tengan texto; guardar el vector. Falla → quedan en NULL.
- Backfill: `cli.py embeddings` (api container) embebe todos los documentos con texto y embedding NULL.
  Reporta cuántos embebió/salteó.

## 4. Búsqueda

- `GET /consulta/semantica?q=&k=5` (equipo): embebe la consulta y rankea por coseno EN PROCESO sobre los
  embeddings no-nulos (a este volumen —cientos— son milisegundos; el operador nativo `<=>` + índice
  quedan como upgrade documentado para cuando haya miles). Respuesta:
  `{"resultados": [{documento_id, gasto_n, periodo, tipo, similitud, fragmento}]}` — fragmento = primeros
  300 caracteres del texto. Sin key → 503 "búsqueda semántica no configurada".
- Tool MCP `buscar_semantico(texto: str) -> str`: top 5 legible con similitud; degradación clara sin key.

## 5. Pruebas

- API (+4): TypeDecorator guarda/lee en SQLite (JSON); ingesta con cliente de embeddings stub puebla la
  columna; semantica rankea por coseno con vectores sintéticos conocidos; sin key → 503 y la ingesta
  igual persiste documentos. MCP (+1): tool con stub.
- La migración se verifica sobre SQLite (columna JSON) y con render offline a Postgres (`CREATE EXTENSION`
  y `vector(1536)` en el SQL emitido).

## Fuera de alcance

Embeddings de hallazgos/reglamento (el corpus chico se lee directo), índice pgvector nativo (documentado
como upgrade), re-embedding al cambiar de modelo (se hace con el backfill).
