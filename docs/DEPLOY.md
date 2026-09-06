# Deploy de la API en la máquina del tunnel

Checklist para dejar el stack completo (API + worker de sincronización + tunnel `cloudflared`) corriendo
con `docker compose` en una máquina nueva, publicado como `api-consorcio.neuralcore.dev`.
(El front `web/` NO corre acá: va a Cloudflare Workers — Plan 3.)

## 1. Prerrequisitos en la máquina nueva

- git y Docker (con el daemon corriendo). Nada más: `cloudflared` corre en un contenedor del compose,
  no hace falta instalarlo en el host.
- Acceso a la cuenta de Cloudflare dueña de `neuralcore.dev` (solo si hay que crear un tunnel nuevo).

## 2. Clonar y configurar

```bash
git clone https://github.com/LTaverna/consorcios-transparentes.git
cd consorcios-transparentes
cp api/.env.example api/.env    # completar (ver abajo)
```

`api/.env` — **nada de esto va al repo**:
- `CT_DATABASE_URL`: la connection string de Neon (`postgresql+psycopg://...`). Para arrancar sin Neon,
  modo local con SQLite: ver los comentarios de `docker-compose.yml`.
- `CT_JWT_SECRET`: generar uno largo: `python3 -c "import secrets; print(secrets.token_urlsafe(48))"`.
- `CT_R2_*`: credenciales del bucket R2 (privado). Sin R2, setear `CT_STORAGE_DIR` (modo local).
- `CT_CORS_ORIGIN=https://panel-consorcio.neuralcore.dev`
- `CT_CONFIAR_PROXY=true` — detrás del tunnel, el rate limit usa la IP real de `CF-Connecting-IP`.
- `CT_COOKIE_SEGURA=true`
- `CT_COOKIE_DOMINIO=.neuralcore.dev` — front y API viven en subdominios distintos (`panel-consorcio` y
  `api-consorcio`); sin esto la cookie queda host-only y el panel nunca la recibe, lo que produce un loop
  infinito de redirects al login.

`.env` raíz (en la raíz del repo) — lo lee el servicio `worker`; **tampoco va al repo**:
- `USER_REDCONAR` / `PASSWORD_REDCONAR`: credenciales del portal Redconar.
- `CT_PRIVADO_HOST`: ruta absoluta de la carpeta privada **en el host** (p.ej.
  `/home/ltaverna/consorcio-transparente-privado`) — la usa el volumen del worker; sin ella
  `docker compose` se niega a arrancar.
- `CT_API_BOT_EMAIL`: email del usuario bot (no es secreto; p.ej. `robot@consorcio-transparente.local`).
- `CT_API_BOT_CLAVE`: la clave del bot (se crea en §8.1).
- `CT_API_URL` (opcional, default `https://api-consorcio.neuralcore.dev`).

```bash
chmod 600 .env api/.env
```

**Guardas de arranque**: con R2 configurado, la API se niega a arrancar si `CT_JWT_SECRET` sigue en el
default o si `CT_COOKIE_SEGURA` no está en true. Es intencional.

## 3. Lo que se copia a mano (nunca por git)

- `~/consorcio-transparente-privado/` completa (liquidaciones PDF, comprobantes, reglamento, planillas).
- Las credenciales de Redconar: `USER_REDCONAR` / `PASSWORD_REDCONAR` en el `.env` raíz (§2). Si se va a
  usar `ct descargar` a mano desde esa máquina, también sirven las variables
  `CT_REDCONAR_USUARIO` / `CT_REDCONAR_CLAVE` o el ingreso por consola. No se guardan en archivos del repo.

## 4. Build y arranque

```bash
docker compose build
docker compose run --rm api alembic upgrade head   # crea/versiona el esquema antes de arrancar
docker compose up -d api
curl -s localhost:8080/salud     # → {"ok":true}
```

El `create_all` que ejecuta la API al arrancar es inofensivo después de `alembic upgrade head`:
usa `checkfirst=True` y el esquema ya coincide, así que no toca nada.

## 5. Datos iniciales (una sola vez)

```bash
docker compose exec api python cli.py init "Rivadavia 2069" --direccion "Av. Rivadavia 2069, CABA"
docker compose exec -it api python cli.py usuario <tu-email> "Lucas" auditor   # pide la clave por consola
# Los códigos por unidad se generan después desde el panel (Consorcio → Generar código),
# o por CLI: docker compose exec api python cli.py codigo <uf>
```

## 6. Tunnel cloudflared

El tunnel corre como servicio `tunnel` del compose y lee su config de `./cloudflared/`
(carpeta gitignoreada: adentro van las credenciales del tunnel).

### 6a. Tunnel existente (migración de máquina)

```bash
mkdir -p cloudflared
cp ~/.cloudflared/<id-del-tunnel>.json cloudflared/     # o copiarlo desde la máquina vieja
cp deploy/cloudflared/config.yml.example cloudflared/config.yml   # ajustar el id si difiere
# la imagen de cloudflared corre como uid 65532; los archivos deben ser legibles por ese usuario (y por nadie más)
sudo chown -R 65532:65532 cloudflared && sudo chmod -R u=rX,go= cloudflared
docker compose up -d tunnel
```

### 6b. Tunnel nuevo (máquina desde cero)

Crearlo con un contenedor efímero — las credenciales quedan directo en `./cloudflared/`:

```bash
mkdir -p cloudflared
sudo chown 65532:65532 cloudflared   # la imagen de cloudflared corre como uid 65532; sin esto los contenedores efímeros no pueden escribir las credenciales
docker run --rm -it -v ./cloudflared:/home/nonroot/.cloudflared cloudflare/cloudflared tunnel login
docker run --rm -it -v ./cloudflared:/home/nonroot/.cloudflared cloudflare/cloudflared tunnel create consorcio
docker run --rm -it -v ./cloudflared:/home/nonroot/.cloudflared cloudflare/cloudflared tunnel route dns consorcio api-consorcio.neuralcore.dev
sudo cp deploy/cloudflared/config.yml.example cloudflared/config.yml   # poner el id del tunnel nuevo (dos líneas)
# las credenciales ya quedaron con el dueño correcto (las escribió el propio contenedor);
# esto cubre el config recién copiado y cierra los permisos al resto:
sudo chown -R 65532:65532 cloudflared && sudo chmod -R u=rX,go= cloudflared
docker compose up -d tunnel
```

En cualquiera de las dos variantes, verificar:
`curl -s https://api-consorcio.neuralcore.dev/salud` → `{"ok":true}`.

## 7. Notas

- **Rate limit detrás del tunnel**: con `CT_CONFIAR_PROXY=true` la API toma la IP real del header
  `CF-Connecting-IP`. Ese header es confiable solo si la API no es alcanzable de forma directa:
  el contenedor publica el puerto solo en localhost y el único camino externo es el tunnel.
- **Warning esperado en el deploy del front**: `npm run deploy:cf` avisa "Node.js middleware support is
  experimental in cloudflare" — es por `proxy.ts`, que solo lee la cookie y redirige; no bloquea. Ante
  dudas, probar antes con `npm run preview:cf` (requiere la API de producción accesible).
- **Actualizar**: `git pull && docker compose build && docker compose run --rm api alembic upgrade head
  && docker compose up -d`.
- **Backup**: la base es Neon (backups propios) o `datos-api/` en modo local; los documentos, R2 o `datos-api/storage`.
- **Primer uso real**: medir la subida del ZIP de comprobantes de un mes real (el endpoint es sincrónico;
  si tarda más de ~90 s habrá que moverlo a background — anotado).

## 8. Sincronización mensual automática

El comando `ct sincronizar` baja la liquidación y los comprobantes más recientes del portal Redconar,
los ingesta en la API del panel y registra el resultado en `$CT_PRIVADO/sincronizacion.json`.
**Nunca publica**: el triage sigue en el panel. Cada corrida fallida reintenta al día siguiente.

Corre adentro del servicio `worker` del compose (APScheduler): nada de cron ni systemd en el host.

### 8.1 Crear el usuario bot en la API

```bash
docker compose exec -it api python cli.py usuario robot@consorcio-transparente.local "Robot de carga" auditor
# (la CLI pide la clave por consola; va en CT_API_BOT_CLAVE del .env raíz — ver §2)
```

### 8.2 Arrancar el worker

Con el `.env` raíz completo (§2: credenciales del portal, `CT_PRIVADO_HOST`, `CT_API_BOT_EMAIL`,
`CT_API_BOT_CLAVE`):

```bash
docker compose up -d worker
docker compose logs -f worker
```

Al arrancar, el contenedor hace **una corrida inicial** (idempotente) y después programa la diaria:
en los logs tiene que verse esa corrida y el "worker en marcha".

### 8.3 Notas de operación

- La corrida diaria es a las 06:30 (hora de Buenos Aires), programada adentro del worker.
- La corrida inicial al arrancar el contenedor cubre el caso "la máquina estuvo apagada"
  (reemplaza al `Persistent=true` que tenía el timer de systemd).
- El estado de cada período (qué está subido, el hash del ZIP) vive en `$CT_PRIVADO/sincronizacion.json`.
- Logs: `docker compose logs -f worker` (van a stdout del contenedor).
- Probar a mano una corrida: `docker compose run --rm worker python -m ct sincronizar`.

### 8.4 Backup diario de la base

A las 07:00 (después de la sincronización), el worker hace `pg_dump` de la base y lo deja comprimido en
`datos-api/backups/` del host (montado en `/srv/backups` dentro del contenedor), con el formato
`consorcio-AAAA-MM-DD.sql.gz`. Se conservan los **últimos 14** y se borran automáticamente los más viejos.

Para restaurar un backup:
```bash
gunzip -c datos-api/backups/consorcio-AAAA-MM-DD.sql.gz | docker compose exec -T db psql -U consorcio -d consorcio
```

## 9. Migrar de máquina

Todo el estado vive en el repo + un puñado de archivos fuera de git. Para mover el stack:

1. En la máquina nueva: git y Docker (§1) y `git clone` del repo.
2. Copiar desde la máquina vieja (por `scp`/disco, nunca por git):
   - `.env` raíz y `api/.env` (§2).
   - `docker-compose.override.yml` — solo si se usa el modo Postgres local (base en contenedor +
     documentos a disco).
   - `cloudflared/` completa (config + JSON de credenciales del tunnel). Después de copiarla, dejarla
     legible para el uid del contenedor (y para nadie más) — la imagen de cloudflared corre como uid 65532:
     `sudo chown -R 65532:65532 cloudflared && sudo chmod -R u=rX,go= cloudflared`.
   - `datos-api/` — solo en modo local: es la base Postgres/SQLite y los documentos. Copiarla con los
     contenedores de la máquina vieja **parados** (`docker compose down`) para no llevarse una base a
     medio escribir. Con Neon + R2 no hay nada que copiar acá.
   - La carpeta privada (`~/consorcio-transparente-privado/` o donde esté) y ajustar `CT_PRIVADO_HOST`
     en el `.env` raíz a la ruta nueva.
3. Arrancar y verificar:

```bash
docker compose up -d --build
curl -s https://api-consorcio.neuralcore.dev/salud   # → {"ok":true}
docker compose logs -f worker                        # corrida inicial de sincronización OK
```

Nada de systemd, nada de venvs: los venvs (`engine/.venv`, `api/.venv`) son solo para desarrollo y
tests, en producción todo corre en los contenedores.

## 10. MCP de consultas

El contenedor `mcp` expone las consultas del consorcio como servidor MCP (read-only) para Claude Code,
claude.ai y ChatGPT, en `https://mcp-consorcio.neuralcore.dev/mcp/<CT_MCP_TOKEN>`.

1. Generar el token y agregarlo al `.env` raíz: `CT_MCP_TOKEN=$(python3 -c "import secrets; print(secrets.token_urlsafe(24))")`.
2. Agregar el ingress al `cloudflared/config.yml` real (el example ya lo trae): hostname
   `mcp-consorcio.neuralcore.dev` → `service: http://mcp:8765`, antes del catch-all. (La carpeta es del
   uid 65532: editar con sudo.)
3. Una única vez: `cloudflared tunnel route dns consorcio mcp-consorcio.neuralcore.dev`.
4. `docker compose up -d mcp && docker compose restart tunnel`.
5. Alta en los clientes con la URL completa (con token): claude.ai → Configuración → Conectores;
   ChatGPT → Conectores / modo desarrollador; Claude Code → `claude mcp add --transport http consorcio <URL>`.
6. Rotar el token = cambiarlo en `.env` + `docker compose up -d mcp` + actualizar los clientes.
