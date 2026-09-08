# Guía de uso

Cómo se usa el sistema: entorno de desarrollo, CLI del motor, CLI de la API, operación diaria del panel,
conexión del MCP y resolución de problemas. Para instalar el stack en una máquina, el runbook es
[DEPLOY.md](DEPLOY.md); acá está el uso cotidiano.

---

## 1. Entorno de desarrollo

Tres subproyectos independientes, cada uno con su entorno. Los venvs están gitignoreados.

### Motor (`engine/`)

```bash
cd engine
python3 -m venv .venv
.venv/bin/pip install -e .          # solo openpyxl; pyzbar/Pillow son opcionales (QR)
.venv/bin/python -m pytest -q tests
```

Binarios del sistema que hacen falta: `pdftotext` y `pdftoppm` (paquete **poppler-utils**). Para leer el
QR de ARCA, además `libzbar0` + `pyzbar` + `Pillow`; sin eso el motor funciona igual, solo se saltea el QR.

Suite esperada: **151 passed** (las pruebas de comprobantes se saltean si no está la carpeta privada).

### API (`api/`)

```bash
cd api
python3 -m venv .venv
.venv/bin/pip install -e .
.venv/bin/python -m pytest -q       # SQLite en memoria, sin servicios externos
```

Suite esperada: **192 passed**. Los tests no necesitan Postgres, ni R2, ni red.

Para levantar la API a mano contra SQLite local:

```bash
cd api
CT_STORAGE_DIR=./datos .venv/bin/uvicorn app.main:app --reload --port 8080
curl -s localhost:8080/salud        # → {"ok":true}
```

### Web (`web/`)

```bash
cd web
npm install
npm run dev                          # http://localhost:3000
NODE_OPTIONS='--experimental-require-module' npm test
```

Suite esperada: **64 tests** en 15 archivos. El `NODE_OPTIONS` es necesario con Node 22.11 (ver
[§7 Problemas conocidos](#7-problemas-conocidos)).

---

## 2. CLI del motor (`python -m ct`)

El motor no necesita base de datos ni cuenta: alcanza con el PDF. Es la vía para reproducir cualquier
hallazgo del panel de forma independiente.

### `ct analizar` — leer, validar y evaluar una liquidación

```bash
cd engine
python -m ct analizar liquidacion.pdf
```

| Flag | Para qué |
|---|---|
| `--anterior <pdf>` | Liquidación del mes anterior: habilita las comparaciones mes contra mes. |
| `--comprobantes <carpeta>` | Activa el cruce documental contra los adjuntos del portal. |
| `--manifiesto <manifest.json>` | Manifiesto de la descarga; dice qué adjunto corresponde a qué gasto. |
| `--mes AAAA-MM` | Prefijo de mes del manifiesto a usar (p. ej. `2026-08`). |
| `--solo-cuadre` | Solo las verificaciones aritméticas. **Es la puerta de entrada**: si no cuadra, nada más importa. |
| `--json <archivo>` | Guarda el resultado completo (modelo + hallazgos) en JSON. |
| `--excel <archivo.xlsx>` | Informe Excel. |
| `--html <archivo.html>` | Informe HTML para presentar. |
| `--marca <texto>` | Nombre o marca que encabeza el informe. |

Análisis completo de un mes, con comprobantes e informes:

```bash
python -m ct analizar "$CT_PRIVADO/liquidaciones/2026-08.pdf" \
  --anterior "$CT_PRIVADO/liquidaciones/2026-07.pdf" \
  --comprobantes "$CT_PRIVADO/Comprobantes Rivadavia 2069" \
  --manifiesto "$CT_PRIVADO/Comprobantes Rivadavia 2069/manifest.json" \
  --mes 2026-08 --excel informe.xlsx --html informe.html
```

Chequeo rápido de cuadre, sin nada más:

```bash
python -m ct analizar liquidacion.pdf --solo-cuadre
```

### `ct descargar` — bajar los comprobantes del portal

```bash
python -m ct descargar listar --carpeta ~/comprobantes     # períodos disponibles
python -m ct descargar 2026-8 --carpeta ~/comprobantes     # factura + ticket de cada gasto
```

Crea una subcarpeta por mes (`2026-08 Agosto/`) con un archivo por adjunto y un `manifest.json` con una
fila por adjunto, que es lo que consume el cruce.

### `ct descargar-liquidacion` — bajar el PDF del mes

```bash
python -m ct descargar-liquidacion 2026-8 --carpeta "$CT_PRIVADO/liquidaciones"
```

### `ct sincronizar` — portal → panel

Baja la liquidación y los comprobantes más recientes, los ingesta en la API y registra el resultado en
`$CT_PRIVADO/sincronizacion.json`. **Nunca publica**: el triage sigue siendo manual en el panel.

```bash
python -m ct sincronizar                    # el período más reciente
python -m ct sincronizar --desde 2026-01    # backfill: todos los períodos desde esa fecha, del más viejo al más nuevo
```

En producción esto lo corre solo el servicio `worker` a las 06:30. `--desde` es para cargar la serie
histórica una vez.

### Credenciales del portal

Usuario y contraseña se piden por consola, o se toman de `CT_REDCONAR_USUARIO` / `CT_REDCONAR_CLAVE`
(o `USER_REDCONAR` / `PASSWORD_REDCONAR` para el worker). **Nunca se guardan en archivos del repo.**

---

## 3. CLI de la API (`python cli.py`)

Comandos administrativos. En producción se corren dentro del contenedor:
`docker compose exec api python cli.py <comando>` (con `-it` cuando pide clave por consola).

| Comando | Qué hace |
|---|---|
| `init "<nombre>" [--direccion] [--cuit]` | Crea las tablas y el consorcio. Una sola vez. Si ya existía, no lo modifica. |
| `usuario <email> "<nombre>" <rol>` | Crea un usuario. Pide la clave por consola dos veces. Roles: ver [FUNCIONALIDADES.md](FUNCIONALIDADES.md). |
| `codigo <uf>` | Genera el código de acceso de una unidad. **Se muestra una sola vez** (en la base queda el hash). |
| `embeddings [--todos]` | Backfill de embeddings de los documentos con texto. `--todos` re-embebe todo (al cambiar de modelo). |
| `mcp-token crear "<nombre>"` | Crea un token del MCP e imprime la URL. **Se muestra una sola vez.** |
| `mcp-token revocar "<nombre>"` | Revoca el token de una persona (efecto en ≤1 minuto, por el cache). |
| `mcp-token listar` | Lista nombre, estado y fecha de creación. Nunca muestra hashes. |

Ejemplos:

```bash
docker compose exec api python cli.py init "Rivadavia 2069" --direccion "Av. Rivadavia 2069, CABA"
docker compose exec -it api python cli.py usuario lucas@ejemplo.com "Lucas" auditor
docker compose exec api python cli.py codigo 13
docker compose exec api python cli.py mcp-token crear "Consejo de propietarios"
```

Los códigos por unidad también se generan desde el panel (Consorcio → Generar código).

---

## 4. Operación mensual

El ciclo real, mes a mes:

**1. La carga es automática.** A las 06:30 el worker corre `ct sincronizar`: baja la liquidación y los
comprobantes del portal, los sube a la API y dispara el pipeline. No hay que hacer nada.

Para verificar que corrió:

```bash
docker compose logs -f worker
```

**2. Revisar el cuadre.** En `/panel/liquidaciones`, el período nuevo tiene que quedar en `procesada`.
Si quedó en `no_cuadra`, el motor detectó que los totales del documento no cierran: no se generan
hallazgos y no se puede publicar. Es una diferencia real del PDF, y se reclama a la administración por
fuera del sistema. Si quedó en `error`, falló el parseo o la ingesta: mirar los logs.

**3. Triage de hallazgos.** En `/panel/hallazgos`, filtrando por severidad CRÍTICO/ALTO. Cada hallazgo
tiene cinco estados posibles:

| Estado | Cuándo se usa | ¿Cuenta como abierto? |
|---|---|---|
| `pendiente` | Recién generado, sin revisar. | Sí |
| `preguntado` | Se le preguntó a la administración; falta la respuesta. | Sí |
| `respondido` | Contestaron, falta evaluar la respuesta. | Sí |
| `descartado` | Era un falso positivo o hay una explicación que lo invalida. | No |
| `cerrado` | Explicado y conforme. | No |

Punto clave: **el índice no sube por triagear**. `preguntado` sigue abierto y sigue penalizando. El
índice sube cuando los hallazgos se cierran o se descartan.

Cuando un hallazgo es falso positivo por un error del motor, no se descarta y ya: se arregla el parser
y se agrega un test de regresión con fixture real. Es lo que mantiene creíble el catálogo de reglas.

**4. Publicar el informe.** Cuando el triage está listo, desde `/panel/liquidaciones` se publica. La
publicación es versionada: los propietarios ven la versión publicada, no el estado de trabajo. **Nunca se
publica una liquidación que no cuadra** — el sistema lo impide.

**5. Los propietarios entran a `/mi-unidad`** con su código de unidad y ven su liquidación, sus hallazgos
publicados y los comprobantes.

---

## 5. Conectar el MCP

El MCP expone la base en modo **solo lectura** para preguntar en lenguaje natural, sin que el modelo
invente cifras: las 16 herramientas devuelven lo que dice la base.

**1. Crear el token** (una URL por persona, revocable individualmente):

```bash
docker compose exec api python cli.py mcp-token crear "Nombre de la persona"
# → URL del MCP para 'Nombre de la persona': https://mcp-consorcio.neuralcore.dev/mcp/<token>
```

**2. Entregarla como una contraseña.** El token va en el path de la URL: quien tenga la URL tiene acceso
de lectura a todo. En la base solo se guarda el hash sha256; la URL no se puede recuperar. Si se pierde,
se revoca y se crea otra.

**3. Configurarla** como servidor MCP remoto en Claude o ChatGPT. El detalle de cada cliente está en
[MCP.md](MCP.md); la administración de tokens, en [MCP-TOKENS.md](MCP-TOKENS.md).

**4. Revocar** cuando alguien deja el consejo:

```bash
docker compose exec api python cli.py mcp-token revocar "Nombre de la persona"
```

El cache de tokens es de 60 segundos, así que la revocación hace efecto en ≤1 minuto.

Preguntas típicas: "¿cuánto se gastó en plomería este año?", "mostrame los hallazgos críticos abiertos",
"¿cuál es el índice de transparencia y por qué?", "¿qué dice el reglamento sobre expensas
extraordinarias?". El catálogo completo de herramientas está en [FUNCIONALIDADES.md](FUNCIONALIDADES.md).

---

## 6. Infraestructura: comandos frecuentes

```bash
docker compose ps                     # estado de api / worker / mcp / tunnel
docker compose logs -f api            # logs de la API
docker compose logs -f worker         # logs de la sincronización diaria
docker compose restart api

# actualizar a la última versión del repo
git pull && docker compose build && docker compose run --rm api alembic upgrade head && docker compose up -d

# correr una sincronización a mano
docker compose run --rm worker python -m ct sincronizar
```

**Backup**: el worker hace `pg_dump` a las 07:00 y deja `consorcio-AAAA-MM-DD.sql.gz` en
`datos-api/backups/`, conservando los últimos 14. Para restaurar:

```bash
gunzip -c datos-api/backups/consorcio-AAAA-MM-DD.sql.gz | docker compose exec -T db psql -U consorcio -d consorcio
```

**Deploy del front** (Cloudflare Worker):

```bash
cd web && npm run deploy:cf
```

El runbook completo —prerrequisitos, `.env`, tunnel, migración de máquina— está en [DEPLOY.md](DEPLOY.md).

---

## 7. Problemas conocidos

| Síntoma | Causa | Solución |
|---|---|---|
| Liquidación en **`no_cuadra`** | Los totales del PDF no cierran al centavo. No es un bug: es un problema del documento. | Reproducir con `ct analizar --solo-cuadre` para ver qué verificación falla, y reclamar a la administración. La liquidación no genera hallazgos ni se puede publicar. |
| Liquidación en **`error`** | Falló el parseo o la ingesta (plantilla nueva, PDF corrupto, ZIP inválido). | `docker compose logs api`. Si es plantilla nueva, hace falta ajustar el parser con un fixture real. |
| El worker no arranca | Falta `CT_PRIVADO_HOST` en el `.env` raíz. | Completar la ruta absoluta de la carpeta privada en el host; sin ella `docker compose` se niega a arrancar. |
| **Loop infinito de redirects al login** | Falta `CT_COOKIE_DOMINIO=.neuralcore.dev`. Front y API viven en subdominios distintos; sin eso la cookie queda host-only y el panel nunca la recibe. | Setearla en `api/.env` y reiniciar la API. |
| La API se niega a arrancar | Guarda intencional: con R2 configurado exige `CT_JWT_SECRET` distinto del default y `CT_COOKIE_SEGURA=true`. | Completar ambas. |
| Tests del front fallan al importar | Node 22.11 necesita el flag experimental. | `NODE_OPTIONS='--experimental-require-module' npm test`. |
| El QR nunca se lee | Falta `libzbar0` / `pyzbar`. | Es opcional: el motor sigue funcionando sin QR. Instalarlo si se quiere el cross-check contra ARCA. |
| Los tests de comprobantes se saltean | No está la carpeta privada. | Esperado: `CT_PRIVADO` apunta a datos que no van al repo. |
| `cd` parece resetearse entre comandos | Quirk del shell de esta máquina. | Usar rutas absolutas o `cd` dentro del mismo comando. |

---

## 8. Datos privados

Liquidaciones, comprobantes, manifiestos, reglamento y planillas viven **fuera de git**, en
`~/consorcio-transparente-privado/` (o donde apunte `CT_PRIVADO`). Estructura esperada:

```
Comprobantes Rivadavia 2069/
  2026-07 Julio/
  2026-08 Agosto/
  manifest.json
liquidaciones/*.pdf
VOTACION CONSORCIO 2026.xlsx
```

Se copian de máquina a máquina por fuera de git. Las credenciales del portal y de Cloudflare no se
guardan en ningún archivo del repositorio.

---

## Lecturas siguientes

- [ARQUITECTURA.md](ARQUITECTURA.md) — cómo está construido.
- [PIPELINE.md](PIPELINE.md) — del portal al índice, paso a paso.
- [FUNCIONALIDADES.md](FUNCIONALIDADES.md) — qué hace cada pantalla, endpoint y herramienta.
- [DEPLOY.md](DEPLOY.md) — runbook de instalación y operación de infraestructura.
- [reglas.md](reglas.md) — catálogo de reglas de detección con sus umbrales.
