"""Worker de tareas programadas del stack: la sincronización diaria corre acá adentro,
no en un cron del host — el contenedor es lo único que hay que mover de máquina."""
import gzip
import logging
import os
import pathlib
import subprocess
import sys
import tempfile
from urllib.parse import urlparse

from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s", stream=sys.stdout)
log = logging.getLogger("worker")

TZ = "America/Argentina/Buenos_Aires"
BACKUP_DIR = pathlib.Path("/srv/backups")
BACKUP_PREFIX = "consorcio-"
BACKUP_SUFFIX = ".sql.gz"
BACKUP_KEEP = 14


def correr_sincronizacion() -> int:
    """Invoca el subcomando del engine in-process (lee toda su config del entorno)."""
    import ct.cli
    rc = ct.cli.sincronizar(None)
    (log.info if rc == 0 else log.error)("sincronización terminada con código %s", rc)
    return rc


def correr_backup() -> int:
    """pg_dump de la base a /srv/backups/consorcio-AAAA-MM-DD.sql.gz, conservando los últimos 14.

    Si CT_DATABASE_URL no apunta a Postgres (o no está) se saltea sin error — compatible con dev/sqlite.
    Retorna 0 en éxito o si se saltea, 1 en error.
    """
    from datetime import date

    raw_url = os.environ.get("CT_DATABASE_URL", "")
    if not raw_url:
        log.info("backup: sin CT_DATABASE_URL configurada, salteado")
        return 0

    # Normalizar: postgresql+psycopg:// → postgresql://
    normalized = raw_url
    for prefix in ("postgresql+psycopg://", "postgresql+psycopg2://"):
        if normalized.startswith(prefix):
            normalized = "postgresql://" + normalized[len(prefix):]
            break

    parsed = urlparse(normalized)
    if parsed.scheme not in ("postgresql", "postgres"):
        log.info("backup: sin base Postgres configurada, salteado")
        return 0

    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    hoy = date.today().isoformat()  # AAAA-MM-DD
    nombre = f"{BACKUP_PREFIX}{hoy}{BACKUP_SUFFIX}"
    destino = BACKUP_DIR / nombre

    # Armar el comando pg_dump (sin shell; la password va por env PGPASSWORD)
    host = parsed.hostname or "localhost"
    port = str(parsed.port or 5432)
    user = parsed.username or ""
    dbname = parsed.path.lstrip("/")
    password = parsed.password or ""

    cmd = [
        "pg_dump",
        "--format=plain",
        "--host", host,
        "--port", port,
        "--username", user,
        dbname,
    ]

    env = os.environ.copy()
    if password:
        env["PGPASSWORD"] = password

    log.info("backup: iniciando pg_dump de %s/%s → %s", host, dbname, destino)
    try:
        resultado = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=env,
        )
    except FileNotFoundError:
        log.error("backup: pg_dump no encontrado en PATH; ¿postgresql-client instalado?")
        return 1

    if resultado.returncode != 0:
        log.error("backup: pg_dump falló (código %s): %s", resultado.returncode, resultado.stderr.decode(errors="replace"))
        return 1

    # Comprimir y escribir atómico (tmp + rename)
    sql_bytes = resultado.stdout
    tmp_fd, tmp_path_str = tempfile.mkstemp(dir=BACKUP_DIR, prefix=".tmp-backup-", suffix=".sql.gz")
    try:
        with os.fdopen(tmp_fd, "wb") as fh:
            with gzip.GzipFile(fileobj=fh, mode="wb") as gz:
                gz.write(sql_bytes)
        pathlib.Path(tmp_path_str).rename(destino)
    except Exception:
        log.exception("backup: error escribiendo el archivo")
        try:
            os.unlink(tmp_path_str)
        except OSError:
            pass
        return 1

    tamanio_kb = destino.stat().st_size // 1024
    log.info("backup: %s escrito (%d KB)", destino.name, tamanio_kb)

    # Rotación: conservar los últimos BACKUP_KEEP, borrar los más viejos
    existentes = sorted(BACKUP_DIR.glob(f"{BACKUP_PREFIX}*{BACKUP_SUFFIX}"))
    a_borrar = existentes[:-BACKUP_KEEP] if len(existentes) > BACKUP_KEEP else []
    for viejo in a_borrar:
        try:
            viejo.unlink()
            log.info("backup: rotado (borrado) %s", viejo.name)
        except OSError as exc:
            log.warning("backup: no se pudo borrar %s: %s", viejo.name, exc)

    return 0


def armar_scheduler() -> BlockingScheduler:
    sched = BlockingScheduler(timezone=TZ)
    # misfire de 1 h y una sola instancia: un cuelgue momentáneo no pierde el día ni superpone corridas
    sched.add_job(correr_sincronizacion, CronTrigger(hour=6, minute=30, timezone=TZ),
                  id="sincronizacion-diaria", coalesce=True, max_instances=1, misfire_grace_time=3600)
    sched.add_job(correr_backup, CronTrigger(hour=7, minute=0, timezone=TZ),
                  id="backup-diario", coalesce=True, max_instances=1, misfire_grace_time=3600)
    return sched


def main() -> None:
    log.info("corrida inicial al arrancar (idempotente; reemplaza al Persistent de systemd)")
    try:
        correr_sincronizacion()
    except Exception:
        log.exception("la corrida inicial falló; el cron diario sigue en pie")
    sched = armar_scheduler()
    log.info("worker en marcha; próxima corrida diaria 06:30 (%s)", TZ)
    sched.start()


if __name__ == "__main__":
    main()
