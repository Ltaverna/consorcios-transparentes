import pytest
from datetime import timezone
from sqlalchemy.exc import IntegrityError

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


def test_clave_duplicada_por_liquidacion_falla(db):
    liq = models.Liquidacion(periodo="2026-08", archivo_key="x.pdf")
    db.add(liq)
    db.flush()
    db.add(models.Hallazgo(liquidacion_id=liq.id, clave="k", regla="r", severidad="ALTO", area="a", titulo="t"))
    db.commit()
    db.add(models.Hallazgo(liquidacion_id=liq.id, clave="k", regla="r", severidad="ALTO", area="a", titulo="t2"))
    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()


def test_mutacion_en_json_persiste(db):
    liq = models.Liquidacion(periodo="2026-08", archivo_key="x.pdf")
    db.add(liq)
    db.flush()
    h = models.Hallazgo(liquidacion_id=liq.id, clave="k", regla="r", severidad="ALTO", area="a", titulo="t")
    db.add(h)
    db.commit()
    h.refs.append("g:1")
    db.commit()
    db.expire_all()
    assert db.query(models.Hallazgo).one().refs == ["g:1"]


def test_fechas_vuelven_con_timezone(db):
    liq = models.Liquidacion(periodo="2026-08", archivo_key="x.pdf")
    db.add(liq)
    db.commit()
    db.expire_all()
    assert db.query(models.Liquidacion).one().creado.tzinfo is not None
