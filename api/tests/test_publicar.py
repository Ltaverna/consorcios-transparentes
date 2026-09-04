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


def test_no_publicable_si_no_cuadra(db, auditor):
    """Aunque el estado sea 'procesada' (p. ej. quedó así de un dato viejo), si cuadra=False
    no se publica: la regla de oro no se salta nunca."""
    liq_id = subir(auditor).json()["id"]
    liq = db.get(models.Liquidacion, liq_id)
    liq.cuadra = False
    db.commit()
    assert auditor.post(f"/liquidaciones/{liq_id}/publicar").status_code == 409


def test_republicar_actualiza_sin_duplicar(db, auditor):
    liq_id = subir(auditor).json()["id"]
    auditor.post(f"/liquidaciones/{liq_id}/publicar")
    auditor.post(f"/liquidaciones/{liq_id}/publicar")
    assert db.query(models.Informe).filter_by(liquidacion_id=liq_id).count() == 2  # html y xlsx, una vez


def test_solo_se_publica_evidencia_de_hallazgos_publicados(db, auditor, tmp_path):
    """Decisión de producto: el informe publicado solo muestra los documentos (comprobantes)
    referenciados por hallazgos que el auditor efectivamente publicó. La tabla de deudores
    no entra en esta regla: es parte de la liquidación que los propietarios ya reciben todos
    los meses, no evidencia sensible del cruce de comprobantes."""
    liq_id = subir(auditor).json()["id"]
    # sin hallazgos publicados (los que trajo el procesamiento quedan en pendiente/no publicado)
    db.add(models.Documento(liquidacion_id=liq_id, gasto_n=None, tipo="factura",
                            archivo_key="comprobantes/2026-08/x.pdf",
                            metadatos={"archivo": "x.pdf", "gasto_n": None, "receptor": "TERCERO-NO-PUBLICADO"}))
    db.commit()
    r = auditor.post(f"/liquidaciones/{liq_id}/publicar")
    assert r.status_code == 200
    informe = db.query(models.Informe).filter_by(liquidacion_id=liq_id, tipo="html").one()
    html = (tmp_path / informe.archivo_key).read_text()
    assert "TERCERO-NO-PUBLICADO" not in html


def test_publicar_incluye_evidencia_de_hallazgos_publicados(db, auditor, tmp_path):
    liq_id = subir(auditor).json()["id"]
    h_pub = models.Hallazgo(liquidacion_id=liq_id, clave="cruce|pub", origen="comprobantes", regla="cruce",
                            severidad="ALTO", area="Comprobantes", titulo="Hallazgo publicado",
                            evidencia="e", publicado=True, refs=["3"])
    h_no_pub = models.Hallazgo(liquidacion_id=liq_id, clave="cruce|nopub", origen="comprobantes", regla="cruce",
                               severidad="ALTO", area="Comprobantes", titulo="Hallazgo NO publicado",
                               evidencia="e", publicado=False, refs=["9"])
    db.add_all([h_pub, h_no_pub])
    db.add(models.Documento(liquidacion_id=liq_id, gasto_n=3, tipo="factura",
                            archivo_key="comprobantes/2026-08/pub.pdf",
                            metadatos={"archivo": "pub.pdf", "gasto_n": 3, "receptor": "GASTO-PUBLICADO"}))
    db.add(models.Documento(liquidacion_id=liq_id, gasto_n=9, tipo="factura",
                            archivo_key="comprobantes/2026-08/nopub.pdf",
                            metadatos={"archivo": "nopub.pdf", "gasto_n": 9, "receptor": "GASTO-NO-PUBLICADO"}))
    db.commit()
    r = auditor.post(f"/liquidaciones/{liq_id}/publicar")
    assert r.status_code == 200
    informe = db.query(models.Informe).filter_by(liquidacion_id=liq_id, tipo="html").one()
    html = (tmp_path / informe.archivo_key).read_text()
    assert "Hallazgo publicado" in html
    assert "Hallazgo NO publicado" not in html
    assert "GASTO-PUBLICADO" in html
    assert "GASTO-NO-PUBLICADO" not in html
