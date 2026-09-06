"""El worker agenda la sincronización diaria y la corre in-process."""
import subprocess

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


# ── Tests del backup diario ────────────────────────────────────────────────────


def test_backup_sin_postgres_se_saltea(monkeypatch):
    """Con CT_DATABASE_URL=sqlite:// (conftest lo pone) el backup retorna 0 sin llamar a subprocess."""
    # subprocess.run explota si se invoca — garantiza que no hay llamada real
    def subprocess_no_debe_llamarse(*args, **kwargs):
        raise AssertionError("subprocess.run no debería invocarse sin Postgres configurado")

    monkeypatch.setattr(subprocess, "run", subprocess_no_debe_llamarse)
    # CT_DATABASE_URL ya es "sqlite://" gracias al conftest
    rc = worker.correr_backup()
    assert rc == 0


def test_backup_rota_los_viejos(tmp_path, monkeypatch):
    """Con 15 backups previos crea el nuevo y deja exactamente 14 (borra el más viejo)."""
    import gzip

    # Redirigir la carpeta de backups al directorio temporal
    monkeypatch.setattr(worker, "BACKUP_DIR", tmp_path)

    # Crear 15 archivos falsos con fechas en el nombre (el más viejo primero)
    for i in range(15):
        fecha = f"2026-08-{i + 1:02d}"
        f = tmp_path / f"consorcio-{fecha}.sql.gz"
        with gzip.open(f, "wb") as gz:
            gz.write(b"-- dump falso")

    # Simular CT_DATABASE_URL de Postgres
    monkeypatch.setenv("CT_DATABASE_URL", "postgresql+psycopg://u:p@h:5432/db")

    # Monkeypatch de subprocess.run devolviendo un dump falso
    def fake_pg_dump(cmd, stdout, stderr, env):
        import types
        resultado = types.SimpleNamespace()
        resultado.returncode = 0
        resultado.stdout = b"-- dump"
        resultado.stderr = b""
        return resultado

    monkeypatch.setattr(subprocess, "run", fake_pg_dump)

    rc = worker.correr_backup()
    assert rc == 0

    archivos = sorted(tmp_path.glob("consorcio-*.sql.gz"))
    assert len(archivos) == 14  # 13 de los viejos + el nuevo de hoy
    # El más viejo (2026-08-01) debe haber sido borrado
    nombres = [f.name for f in archivos]
    assert "consorcio-2026-08-01.sql.gz" not in nombres


def test_scheduler_agenda_el_backup():
    """armar_scheduler() registra el job 'backup-diario' a las 07:00."""
    sched = worker.armar_scheduler()
    job = sched.get_job("backup-diario")
    assert job is not None
    campos = {f.name: str(f) for f in job.trigger.fields}
    assert campos["hour"] == "7" and campos["minute"] == "0"
    assert str(job.trigger.timezone) == "America/Argentina/Buenos_Aires"
