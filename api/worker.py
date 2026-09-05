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
