from app import models


def test_hallazgo_unico_por_liquidacion_y_clave(db):
    liq = models.Liquidacion(periodo="2026-08", archivo_key="x.pdf")
    db.add(liq)
    db.flush()
    db.add(models.Hallazgo(liquidacion_id=liq.id, clave="efectivo|", regla="efectivo",
                           severidad="ALTO", area="Caja", titulo="t", evidencia="e"))
    db.commit()
    h = db.query(models.Hallazgo).one()
    assert h.estado == "pendiente" and h.publicado is False and h.origen == "liquidacion"


def test_consorcio_umbrales_json(db):
    c = models.Consorcio(nombre="Rivadavia 2069", umbrales={"efectivo_linea_alta": 500000})
    db.add(c)
    db.commit()
    assert db.query(models.Consorcio).one().umbrales["efectivo_linea_alta"] == 500000
