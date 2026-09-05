# Portabilidad total en compose — Plan de implementación

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** todo el stack (API + Postgres + worker de sincronización + tunnel) corre con `docker compose up -d`; mover de máquina es copiar secretos y datos, sin systemd ni instalaciones de host.

**Architecture:** un servicio `worker` (misma imagen que la API) corre `api/worker.py` con APScheduler — corrida al arrancar + cron 06:30 AR, invocando `ct.cli.sincronizar` in-process; un servicio `tunnel` (imagen oficial cloudflared) corre el tunnel `consorcio` existente con credenciales montadas de `./cloudflared/` (gitignoreada) e ingress `http://api:8080` por la red interna. Los units de systemd se retiran al final, con el stack nuevo verificado.

**Tech Stack:** lo existente + `apscheduler>=3.10` (api) + imagen `cloudflare/cloudflared`.

**Spec:** `docs/superpowers/specs/2026-09-05-portabilidad-compose-design.md`.

**Contexto de la máquina:** api suite hoy 106 passed. Rama: `portabilidad-compose` desde `main`. Commits en español + trailer. El tunnel `consorcio` existe (id `f35df675-d3d7-4ee3-8f50-4bdaf3afb11a`, credenciales en `~/.cloudflared/f35df675-….json`); systemd corre `cloudflared-consorcio` y `ct-sincronizar.timer` — NO tocarlos hasta la Task 4 (producción, con confirmación del usuario). El `.env` raíz ya tiene las credenciales del portal, del bot y `CT_API_BOT_CLAVE`.

---

### Task 1: `api/worker.py` con APScheduler

**Files:**
- Create: `api/worker.py`
- Modify: `api/pyproject.toml` (dep `apscheduler>=3.10`)
- Test: `api/tests/test_worker.py`

- [ ] **Step 1:** Agregar `"apscheduler>=3.10"` a dependencies en `api/pyproject.toml`; `cd api && .venv/bin/pip install -e '.[dev]'`.

- [ ] **Step 2: Tests que fallan.** Crear `api/tests/test_worker.py`:

```python
"""El worker agenda la sincronización diaria y la corre in-process."""
import worker


def test_correr_sincronizacion_invoca_el_cli(monkeypatch):
    llamadas = []
    monkeypatch.setattr("ct.cli.sincronizar", lambda args: llamadas.append(args) or 0)
    assert worker.correr_sincronizacion() == 0
    assert llamadas == [None]


def test_correr_sincronizacion_propaga_el_codigo_de_error(monkeypatch):
    monkeypatch.setattr("ct.cli.sincronizar", lambda args: 1)
    assert worker.correr_sincronizacion() == 1


def test_scheduler_agenda_el_cron_de_las_0630():
    sched = worker.armar_scheduler()
    job = sched.get_job("sincronizacion-diaria")
    assert job is not None
    campos = {f.name: str(f) for f in job.trigger.fields}
    assert campos["hour"] == "6" and campos["minute"] == "30"
    assert str(job.trigger.timezone) == "America/Argentina/Buenos_Aires"
```

(Nota: `worker.py` vive en `api/`, mismo directorio que `cli.py` de la API; el import `import worker` funciona porque los tests corren con `api/` como raíz — verificar cómo importan los tests vecinos y ajustar si hace falta `from .. import` o path. El `ct.cli` es el del ENGINE — ya instalado en el venv.)

- [ ] **Step 3:** correr → FAIL (no existe `worker`).

- [ ] **Step 4: Implementar** `api/worker.py`:

```python
"""Worker de tareas programadas del stack: la sincronización diaria corre acá adentro,
no en un cron del host — el contenedor es lo único que hay que mover de máquina."""
import logging
import sys

from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s", stream=sys.stdout)
log = logging.getLogger("worker")

TZ = "America/Argentina/Buenos_Aires"


def correr_sincronizacion() -> int:
    """Invoca el subcomando del engine in-process (lee toda su config del entorno)."""
    import ct.cli
    rc = ct.cli.sincronizar(None)
    (log.info if rc == 0 else log.error)("sincronización terminada con código %s", rc)
    return rc


def armar_scheduler() -> BlockingScheduler:
    sched = BlockingScheduler(timezone=TZ)
    # misfire de 1 h y una sola instancia: un cuelgue momentáneo no pierde el día ni superpone corridas
    sched.add_job(correr_sincronizacion, CronTrigger(hour=6, minute=30, timezone=TZ),
                  id="sincronizacion-diaria", coalesce=True, max_instances=1, misfire_grace_time=3600)
    return sched


def main() -> None:
    log.info("corrida inicial al arrancar (idempotente; reemplaza al Persistent de systemd)")
    correr_sincronizacion()
    sched = armar_scheduler()
    log.info("worker en marcha; próxima corrida diaria 06:30 (%s)", TZ)
    sched.start()


if __name__ == "__main__":
    main()
```

(El `monkeypatch.setattr("ct.cli.sincronizar", ...)` de los tests funciona porque `correr_sincronizacion` importa el módulo y llama por atributo — no cambiar a `from ct.cli import sincronizar`.)

- [ ] **Step 5:** suite api completa: `cd api && .venv/bin/python -m pytest -q` → 109 passed (106 + 3).

- [ ] **Step 6: Commit.**

```bash
git add api/worker.py api/pyproject.toml api/tests/test_worker.py
git commit -m "Worker con APScheduler: la sincronización diaria vive en el contenedor"
```

### Task 2: servicios `worker` y `tunnel` en compose

**Files:**
- Modify: `docker-compose.yml`, `.gitignore` (raíz)
- Create: `deploy/cloudflared/config.yml.example`

- [ ] **Step 1:** En `docker-compose.yml`, agregar (respetando el estilo del archivo; el servicio `api` NO cambia — sigue publicando `127.0.0.1:8080` para no romper nada hasta evaluar sacarlo en un ciclo futuro):

```yaml
  worker:
    build:
      context: .
      dockerfile: api/Dockerfile
    command: python worker.py
    env_file:
      - .env          # credenciales del portal y del bot (USER_REDCONAR, CT_API_BOT_*)
    environment:
      CT_PRIVADO: /srv/privado
    volumes:
      - ${CT_PRIVADO_HOST:?definir CT_PRIVADO_HOST en .env (ruta absoluta de la carpeta privada)}:/srv/privado
    restart: unless-stopped

  tunnel:
    image: cloudflare/cloudflared:latest
    command: tunnel --no-autoupdate --config /etc/cloudflared/config.yml run
    volumes:
      - ./cloudflared:/etc/cloudflared:ro
    depends_on:
      - api
    restart: unless-stopped
```

- [ ] **Step 2:** `deploy/cloudflared/config.yml.example` (el real va en `./cloudflared/config.yml`, gitignoreado):

```yaml
# Copiar a ./cloudflared/config.yml junto con el JSON de credenciales del tunnel
# (de ~/.cloudflared/<id>.json). El id del tunnel "consorcio" es f35df675-d3d7-4ee3-8f50-4bdaf3afb11a.
tunnel: f35df675-d3d7-4ee3-8f50-4bdaf3afb11a
credentials-file: /etc/cloudflared/f35df675-d3d7-4ee3-8f50-4bdaf3afb11a.json
ingress:
  - hostname: api-consorcio.neuralcore.dev
    service: http://api:8080
  - service: http_status:404
```

- [ ] **Step 3:** `.gitignore` raíz: agregar `cloudflared/`.

- [ ] **Step 4: Verificar SIN tocar producción:** `docker compose config` parsea OK (va a exigir `CT_PRIVADO_HOST`: correr con `CT_PRIVADO_HOST=/tmp docker compose config >/dev/null && echo OK`). NO hacer `up` de los servicios nuevos (el tunnel real sigue en systemd hasta la Task 4).

- [ ] **Step 5: Commit.**

```bash
git add docker-compose.yml .gitignore deploy/cloudflared/config.yml.example
git commit -m "Compose: servicios worker y tunnel (stack completo portable)"
```

### Task 3: DEPLOY.md a la era compose

**Files:**
- Modify: `docs/DEPLOY.md`
- Delete: `deploy/systemd/ct-sincronizar.service`, `deploy/systemd/ct-sincronizar.timer`

- [ ] **Step 1:** Reescribir en `docs/DEPLOY.md`:
  - §1 prerrequisitos: ya no hace falta `cloudflared` en el host (solo git + Docker).
  - §2: agregar `CT_PRIVADO_HOST=<ruta absoluta de la carpeta privada>` a las variables del `.env` raíz.
  - §6 (tunnel): pasos nuevos — para el tunnel existente: copiar `~/.cloudflared/<id>.json` a `./cloudflared/` + `cp deploy/cloudflared/config.yml.example cloudflared/config.yml` (ajustar id) + `docker compose up -d tunnel`; para una máquina/tunnel nuevos: `cloudflared tunnel create` puede correrse una única vez desde un contenedor efímero (`docker run --rm -v ./cloudflared:/home/nonroot/.cloudflared cloudflare/cloudflared tunnel login && ... create consorcio && ... route dns ...`) — documentar ambas variantes.
  - §8 (sincronización): el worker reemplaza al timer — `docker compose up -d worker`, logs con `docker logs -f consorcios-transparentes-worker-1`; la corrida inicial al arrancar reemplaza a `Persistent`; el bot y las credenciales siguen en el `.env` raíz.
  - Sección nueva "**9. Migrar de máquina**": lista exacta — repo (git clone) + `.env` raíz + `api/.env` + `docker-compose.override.yml` (si se usa modo local) + `cloudflared/` + `datos-api/` + carpeta privada (`CT_PRIVADO_HOST`) → `docker compose up -d --build` → verificar `/salud` público. Nada más.
- [ ] **Step 2:** `git rm deploy/systemd/ct-sincronizar.service deploy/systemd/ct-sincronizar.timer` (la carpeta `deploy/systemd/` desaparece si queda vacía).
- [ ] **Step 3: Commit.**

```bash
git add docs/DEPLOY.md
git rm deploy/systemd/ct-sincronizar.service deploy/systemd/ct-sincronizar.timer
git commit -m "DEPLOY: runbook compose-first y migración de máquina"
```

### Task 4: Cierre — merge y switchover en producción (CON confirmación del usuario)

- [ ] **Step 1:** Suites: api 109 · web 40 · engine 45. `docker compose config` OK.
- [ ] **Step 2:** `docs/ESTADO.md`: portabilidad total (worker APScheduler, tunnel dockerizado, migrar = copiar y `up -d`); commit + merge a `main`.
- [ ] **Step 3: Switchover (pedir confirmación explícita — corta el tunnel unos segundos):**
  1. Preparar `./cloudflared/`: `mkdir cloudflared && cp ~/.cloudflared/f35df675-*.json cloudflared/ && cp deploy/cloudflared/config.yml.example cloudflared/config.yml && chmod 600 cloudflared/*`.
  2. Agregar `CT_PRIVADO_HOST=/home/ltaverna/consorcio-transparente-privado` al `.env` raíz.
  3. `docker compose build` → `docker compose up -d worker` → `docker logs` muestra la corrida inicial de sincronización OK.
  4. `sudo systemctl disable --now cloudflared-consorcio` → `docker compose up -d tunnel` → `curl -s https://api-consorcio.neuralcore.dev/salud` → `{"ok":true}` (si falla: `systemctl start cloudflared-consorcio` vuelve atrás).
  5. `sudo systemctl disable --now ct-sincronizar.timer` y `sudo rm /etc/systemd/system/ct-sincronizar.* /etc/systemd/system/cloudflared-consorcio.service /etc/cloudflared/config-consorcio.yml` + `daemon-reload`.
  6. Push. Verificación final: salud pública, panel, y al día siguiente el journal ya no corre — la corrida de las 06:30 se ve en `docker logs`.
