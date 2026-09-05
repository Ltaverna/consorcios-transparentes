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
