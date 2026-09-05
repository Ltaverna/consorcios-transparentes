# Portabilidad total: el stack en compose (diseño aprobado 05-09-2026)

Objetivo: mover el sistema de máquina = copiar el repo + los secretos (`.env` raíz, `api/.env`, carpeta
`cloudflared/`) + los datos (`datos-api/`, carpeta privada) y `docker compose up -d`. Cero systemd, cero
instalaciones de host. Reemplaza el timer `ct-sincronizar` y el servicio `cloudflared-consorcio` del host.

## 1. Worker con APScheduler

- Servicio `worker` en `docker-compose.yml`: misma imagen que la API (ya instala engine + api), comando
  `python worker.py`, `restart: unless-stopped`, `env_file` con el `.env` raíz (credenciales del portal y
  del bot) y volumen de la carpeta privada (`${CT_PRIVADO_HOST:-~/consorcio-transparente-privado}` →
  `/srv/privado`, con `CT_PRIVADO=/srv/privado`).
- `api/worker.py` (dependencia nueva `apscheduler>=3.10` en `api/pyproject.toml`): scheduler con cron
  06:30 `America/Argentina/Buenos_Aires` que corre la sincronización **in-process** (arma `Redconar` +
  `ApiPanel` + `Sincronizador` como el CLI `ct sincronizar`, sin subprocess), **más una corrida al
  arrancar el contenedor** — idempotente, reemplaza con ventaja al `Persistent=true` de systemd.
- `misfire_grace_time` generoso (1 h); una corrida a la vez (`max_instances=1`, `coalesce=True`).
- El worker le habla a la API por la URL pública (`CT_API_URL`, default producción): la cookie de sesión
  es `Secure` y no viajaría por `http://api:8080` interno.
- Logs por stdout (`docker logs`); una corrida fallida se loguea y el cron reintenta al día siguiente
  (más el reintento implícito de cada restart del contenedor).

## 2. Tunnel cloudflared en compose

- Servicio `tunnel`: imagen oficial `cloudflare/cloudflared`, `restart: unless-stopped`, corre el tunnel
  `consorcio` EXISTENTE con credenciales montadas desde `./cloudflared/` (carpeta gitignoreada):
  `config.yml` con ingress `api-consorcio.neuralcore.dev → http://api:8080` (red interna de compose)
  + el JSON de credenciales copiado de `~/.cloudflared/`.
- Template no-secreto en `deploy/cloudflared/config.yml.example`.
- Los demás tunnels de la máquina no se tocan.
- Con el tunnel adentro de la red de compose, evaluar en el plan dejar de publicar el puerto 8080 en el
  host (hoy loopback); si se mantiene, sigue siendo solo loopback.

## 3. Retiro de lo atado al host (con el stack nuevo verificado en producción)

- `systemctl disable --now ct-sincronizar.timer cloudflared-consorcio` + borrar esas units de
  `/etc/systemd/system/` (los OTROS servicios del host quedan como están).
- `deploy/systemd/` sale del repo.
- `docs/DEPLOY.md`: §6 (tunnel) y §8 (sincronización) pasan a compose; sección nueva **"Migrar de
  máquina"** con la lista exacta de qué copiar (repo, `.env` raíz, `api/.env`,
  `docker-compose.override.yml` si aplica, `cloudflared/`, `datos-api/`, carpeta privada) y el
  `docker compose up -d` final.

## 4. Bordes

- Reinicios múltiples del contenedor en el día → corridas múltiples: inocuo (hash del ZIP,
  reconciliación, estado idempotente).
- El `.env` raíz pasa a ser leído también por el worker vía `env_file` — sin cambios de formato.
- Zona horaria: fijada en el trigger del scheduler, no depende del TZ del host ni del contenedor.

## 5. Pruebas

- Test unitario del worker: el job invoca la sincronización con la config esperada (mock del
  `Sincronizador`/factoría); el arranque agenda cron + corrida inicial. La suite api no se ve afectada.
- Verificación real (puesta en marcha supervisada): `docker compose up -d` → corrida inicial visible en
  `docker logs` → salud pública por el tunnel dockerizado → systemd retirado → salud pública de nuevo.

## Fuera de alcance

Migrar los otros tunnels del host, Neon/R2 (pendiente aparte), alta disponibilidad, panel de estado de
los jobs.
