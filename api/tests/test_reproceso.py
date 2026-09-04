"""Reprocesar el mismo mes debe conservar el trabajo del auditor sobre los hallazgos."""
from app import ingesta, models

from .test_ingesta import preparar


def test_reprocesar_conserva_estado_y_publicacion(db, tmp_path):
    st, liq = preparar(db, tmp_path)
    ingesta.procesar(db, liq.id, st)
    h = db.query(models.Hallazgo).filter_by(liquidacion_id=liq.id).first()
    h.estado, h.publicado, h.respuesta_admin = "preguntado", True, "Dijeron que lo revisan"
    db.commit()
    clave, cantidad = h.clave, db.query(models.Hallazgo).count()

    liq.estado = "procesando"
    db.commit()
    ingesta.procesar(db, liq.id, st)

    h2 = db.query(models.Hallazgo).filter_by(liquidacion_id=liq.id, clave=clave).one()
    assert h2.estado == "preguntado" and h2.publicado
    assert h2.respuesta_admin == "Dijeron que lo revisan"
    assert db.query(models.Hallazgo).count() == cantidad  # sin duplicados


def test_reprocesar_no_borra_hallazgos_de_comprobantes(db, tmp_path):
    st, liq = preparar(db, tmp_path)
    ingesta.procesar(db, liq.id, st)
    db.add(models.Hallazgo(liquidacion_id=liq.id, clave="cruce|x", origen="comprobantes",
                           regla="cruce", severidad="CRÍTICO", area="Comprobantes",
                           titulo="Pago a un tercero", evidencia="e"))
    db.commit()
    liq.estado = "procesando"
    db.commit()
    ingesta.procesar(db, liq.id, st)
    assert db.query(models.Hallazgo).filter_by(origen="comprobantes").count() == 1
