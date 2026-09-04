from app import models

from .test_liquidaciones_api import subir


def test_publicar_genera_informes_y_cambia_estado(db, auditor, tmp_path):
    liq_id = subir(auditor).json()["id"]
    for h in db.query(models.Hallazgo).limit(3):
        h.publicado = True
    db.commit()
    r = auditor.post(f"/liquidaciones/{liq_id}/publicar")
    assert r.status_code == 200
    liq = db.get(models.Liquidacion, liq_id)
    assert liq.estado == "publicada"
    informes = {i.tipo: i for i in db.query(models.Informe).filter_by(liquidacion_id=liq_id)}
    assert set(informes) == {"html", "xlsx"}
    assert (tmp_path / informes["html"].archivo_key).exists()
    html = (tmp_path / informes["html"].archivo_key).read_text()
    assert "Consorcio Transparente" in html


def test_no_publicable_si_no_esta_procesada(db, auditor):
    liq = models.Liquidacion(periodo="2026-01", archivo_key="x", estado="no_cuadra")
    db.add(liq)
    db.commit()
    assert auditor.post(f"/liquidaciones/{liq.id}/publicar").status_code == 409


def test_republicar_actualiza_sin_duplicar(db, auditor):
    liq_id = subir(auditor).json()["id"]
    auditor.post(f"/liquidaciones/{liq_id}/publicar")
    auditor.post(f"/liquidaciones/{liq_id}/publicar")
    assert db.query(models.Informe).filter_by(liquidacion_id=liq_id).count() == 2  # html y xlsx, una vez
