# Self-service: convocatoria → mociones con LLM

**Fecha:** 2026-10-05
**Estado:** en revisión del usuario

## Objetivo

Que el moderador pueda **subir la convocatoria** (PDF, DOC o DOCX) desde la app de asamblea y que un LLM
**proponga automáticamente** el orden del día y las mociones votables, que el moderador **revisa y edita**
antes de cargarlas en la votación. Reemplaza el flujo manual de cargar `asamblea_content.py` a mano.

## No-objetivos

- **No** decide ni vota nada: solo **propone**; el moderador siempre revisa y confirma.
- **No** toca el motor de análisis de expensas ni el índice de transparencia (siguen deterministas, sin
  LLM — principio del proyecto). El LLM acá solo asiste a armar la asamblea.
- **No** publica ni modifica liquidaciones. Es una utilidad de la app de asamblea.

## Arquitectura

```
App asamblea (Pages, estática)
  └─ (mod-only) "Subir convocatoria" → POST multipart al endpoint
        │  (token compartido + CORS asamblea.neuralcore.dev)
        ▼
API del panel (FastAPI)  POST /asamblea/convocatoria
  1. extrae texto del archivo (pdf/doc/docx) con el extractor ya existente
  2. llama a la Claude API con un prompt + structured output (JSON schema)
  3. devuelve { metadatos, agenda[], mociones[] }
        ▼
App: pantalla de REVISIÓN → el moderador edita/borra/agrega → "Cargar" → S.mociones (sincroniza por Code.gs)
```

- **El backend es la API del panel** porque ya tiene `pdftotext`, LibreOffice y
  `apps/asamblea/tools/extraer_convocatoria.py` (los 3 formatos). Un Cloudflare Worker no puede convertir
  doc/docx, por eso se descartó.
- La **Claude API key** vive en el `.env` de la API (`CT_ANTHROPIC_API_KEY`), nunca en el cliente.

## Componentes

### 1. Endpoint `POST /asamblea/convocatoria` (nuevo, API del panel)
- Recibe el archivo (multipart). Valida extensión (`.pdf/.doc/.docx`) y tamaño (máx. p. ej. 15 MB).
- Extrae texto reutilizando la lógica de `extraer_convocatoria.py` (moverla/importarla a un módulo de la
  API, p. ej. `api/app/convocatoria.py`, para no duplicar; el script de `apps/asamblea/tools/` puede pasar
  a importar de ahí o quedar como CLI fino).
- Llama a Claude (modelo actual, p. ej. `claude-opus-4-8` o uno más económico) con **structured output**
  (tool/JSON schema) para devolver:
  - `metadatos`: `{tipo, fecha, hora, lugar, administracion, art2060}` (lo que detecte; campos vacíos si no
    están).
  - `agenda`: lista de `{n, titulo, tipo}` donde `tipo ∈ procedimental|informativo|deliberativo`.
  - `mociones`: lista de `{titulo, opciones:["A favor","En contra","Abstención"], regla}` — una por cada
    punto deliberativo; `regla` por defecto `abs` (doble mayoría), editable.
- Devuelve ese JSON. Maneja errores (archivo ilegible, Claude caído/timeout, respuesta no válida) con
  mensajes claros.

### 2. Seguridad del endpoint
- La app de asamblea está en **otro dominio** (`asamblea.neuralcore.dev`) sin la cookie del panel.
- Protección: un **token compartido** (`CT_ASAMBLEA_TOKEN` en el `.env`), que la app manda en un header;
  el endpoint lo valida. Además, en la app el botón es **mod-only** (PIN del moderador) y **CORS**
  restringido al dominio de asamblea. Rate limit básico (reusar el `RateLimiter` existente).
- El token se embebe en el build de la app (como `CT_MCP_TOKEN`/otros) — es de bajo riesgo (solo habilita
  proponer mociones desde un PDF; no lee datos del consorcio). Revisar en el plan si conviene algo más
  fuerte.

### 3. UI en la app (make_votacion.py)
- En la pestaña **Votar** (o en "Más opciones"), botón **mod-only** "Subir convocatoria…".
- Al subir: spinner → llama al endpoint → recibe la propuesta.
- **Pantalla de revisión**: muestra metadatos, la agenda clasificada y las mociones propuestas, todas
  **editables** (título, opciones, regla; borrar; agregar una a mano). Botón **"Cargar estas mociones"**
  que reemplaza `S.mociones` (con confirmación, porque pisa las actuales) y sincroniza (Code.gs).
- Nada se carga sin el paso de revisión.

## Flujo de datos y errores

- Éxito: archivo → texto → Claude → JSON → revisión → `S.mociones`.
- Archivo no soportado / vacío → 400 con mensaje.
- Claude falla o devuelve algo inválido → el endpoint responde error; la app lo muestra y el moderador
  puede reintentar o cargar mociones a mano (el flujo manual sigue existiendo).
- La app offline en la asamblea: esto se usa **antes** (al preparar), con red; no en vivo.

## Testing

- **Extractor** (ya testeable): los 3 formatos → texto.
- **Parseo de la respuesta de Claude**: función pura que valida/normaliza el JSON del LLM (campos,
  defaults, mociones bien formadas) — tests con respuestas mockeadas (válida, incompleta, basura).
- **Endpoint**: test con la llamada a Claude **mockeada** (no pega a la API real en tests), verificando
  extracción + forma de la respuesta + validación del token + CORS.
- **Prompt**: un test de integración opcional (marcado, no en CI) con un PDF real y la API real, para
  calibrar el prompt; no corre por defecto.
- **UI**: verificación manual (subir un PDF de convocatoria real y revisar la propuesta).

## Archivos

- Crear: `api/app/convocatoria.py` (extracción multi-formato + cliente Claude + parseo/validación).
- Crear: `api/app/routers/asamblea.py` (endpoint `POST /asamblea/convocatoria`, token, CORS).
- Modificar: `api/app/main.py` (registrar router + CORS del dominio de asamblea), `api/pyproject.toml`
  (dependencia del SDK de Anthropic), `.env.example` (`CT_ANTHROPIC_API_KEY`, `CT_ASAMBLEA_TOKEN`).
- Modificar: `apps/asamblea/make_votacion.py` (botón mod-only + pantalla de revisión + carga a S.mociones).
- Test: `api/tests/test_convocatoria.py` (parseo + endpoint con Claude mockeado).
- Reusar: `apps/asamblea/tools/extraer_convocatoria.py` (su lógica pasa a `api/app/convocatoria.py`).

## Verificación

- Suites en verde (API + la lógica de parseo).
- Manual: subir una convocatoria (pdf/doc/docx) desde la app en modo moderador, revisar que proponga las
  mociones correctas, editarlas y cargarlas; confirmar que se sincronizan a otros dispositivos.
- Deploy: API (rebuild) + app (redeploy a Pages).
