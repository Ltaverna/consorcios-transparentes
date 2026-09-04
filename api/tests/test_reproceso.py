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


def test_reprocesar_a_no_cuadra_limpia_gastos_informes_y_despublica(db, tmp_path, monkeypatch):
    """Si un reproceso cae en no_cuadra, no puede quedar nada publicable de la vez anterior:
    se borran gastos e informes, y los hallazgos de esta liquidación se despublican (sin
    tocar su estado ni la respuesta de la administración: el auditor no pierde su trabajo)."""
    st, liq = preparar(db, tmp_path)
    ingesta.procesar(db, liq.id, st)
    assert db.query(models.Gasto).filter_by(liquidacion_id=liq.id).count() > 0

    h = db.query(models.Hallazgo).filter_by(liquidacion_id=liq.id).first()
    h.estado, h.publicado, h.respuesta_admin = "preguntado", True, "Dijeron que lo revisan"
    db.add(models.Informe(liquidacion_id=liq.id, tipo="html", archivo_key="informes/x.html"))
    db.commit()
    h_id = h.id

    from ct.model import Check, Liquidacion as LiqMotor
    falsa = LiqMotor(sistema="test", periodo="Agosto 2026")
    falsa.checks.append(Check("total", ok=False, esperado=1.0, obtenido=2.0))
    monkeypatch.setattr(ingesta, "parsear_bytes", lambda nombre, data: falsa)

    liq.estado = "procesando"
    db.commit()
    ingesta.procesar(db, liq.id, st)
    db.refresh(liq)

    assert liq.estado == "no_cuadra" and not liq.cuadra
    assert db.query(models.Gasto).filter_by(liquidacion_id=liq.id).count() == 0
    assert db.query(models.Informe).filter_by(liquidacion_id=liq.id).count() == 0
    h2 = db.get(models.Hallazgo, h_id)
    assert h2.publicado is False
    assert h2.estado == "preguntado"                        # estado: no se toca
    assert h2.respuesta_admin == "Dijeron que lo revisan"    # respuesta: no se toca


def test_hallazgo_con_respuesta_o_historial_no_se_borra_al_desaparecer(db, tmp_path, monkeypatch):
    """Un hallazgo pendiente y sin publicar que ya tiene respuesta del administrador o
    eventos en su historial no debe borrarse aunque la regla deje de dispararlo."""
    st, liq = preparar(db, tmp_path)
    ingesta.procesar(db, liq.id, st)
    hallazgos = db.query(models.Hallazgo).filter_by(liquidacion_id=liq.id).all()
    assert len(hallazgos) >= 2
    con_respuesta, con_historial = hallazgos[0], hallazgos[1]
    con_respuesta.respuesta_admin = "Ya lo corregimos"
    db.add(models.HallazgoEvento(hallazgo_id=con_historial.id, de="pendiente", a="pendiente", nota="revisado"))
    db.commit()
    id_respuesta, id_historial = con_respuesta.id, con_historial.id

    monkeypatch.setattr(ingesta, "evaluar", lambda liq, prev, cfg: [])
    liq.estado = "procesando"
    db.commit()
    ingesta.procesar(db, liq.id, st)

    assert db.get(models.Hallazgo, id_respuesta) is not None
    assert db.get(models.Hallazgo, id_historial) is not None


def test_reprocesar_publicada_retira_los_informes(db, tmp_path):
    """Reprocesar una liquidación publicada retracta la publicación: los datos cambiaron,
    así que el informe viejo ya no es válido. El auditor tiene que revisar y republicar."""
    st, liq = preparar(db, tmp_path)
    ingesta.procesar(db, liq.id, st)
    db.add(models.Informe(liquidacion_id=liq.id, tipo="html", archivo_key="informes/x.html"))
    db.add(models.Informe(liquidacion_id=liq.id, tipo="xlsx", archivo_key="informes/x.xlsx"))
    liq.estado = "publicada"
    db.commit()

    ingesta.procesar(db, liq.id, st)
    db.refresh(liq)

    assert liq.estado == "procesada"
    assert db.query(models.Informe).filter_by(liquidacion_id=liq.id).count() == 0


def test_resubir_por_el_endpoint_retira_informes(db, auditor, tmp_path):
    from .test_liquidaciones_api import subir
    liq_id = subir(auditor).json()["id"]
    liq = db.get(models.Liquidacion, liq_id)
    liq.estado = "publicada"
    db.add(models.Informe(liquidacion_id=liq_id, tipo="html", archivo_key="informes/2026-08.html"))
    db.commit()
    r = subir(auditor)  # re-subida real por HTTP (estado publicada, no procesando → permitida)
    assert r.status_code == 200
    assert db.query(models.Informe).filter_by(liquidacion_id=liq_id).count() == 0


def test_clave_natural_es_estable_ante_cambios_de_cifras_en_el_titulo():
    """La clave no puede depender de las cifras del título: una corrección de montos no
    debe hacer que el hallazgo se vea como uno nuevo."""
    from ct.rules import Hallazgo as HallazgoMotor

    a = HallazgoMotor("efectivo", "CRÍTICO", "Área", "El 10,0 % de las disponibilidades está en efectivo", "ev")
    b = HallazgoMotor("efectivo", "CRÍTICO", "Área", "El 55,3 % de las disponibilidades está en efectivo", "ev")
    assert ingesta.clave_natural(a) == ingesta.clave_natural(b)

    c = HallazgoMotor("morosidad", "ALTO", "Área", "Deuda concentrada: UC-1 debe $100", "ev", clave="concentracion")
    d = HallazgoMotor("morosidad", "ALTO", "Área", "Deuda concentrada: UC-9 debe $999.999", "ev", clave="concentracion")
    assert ingesta.clave_natural(c) == ingesta.clave_natural(d)


def test_clave_natural_combina_clave_y_refs_para_no_confundir_subcasos():
    """Dos hallazgos de la misma regla y el mismo slug de clave, pero sobre gastos distintos
    (refs distintos), no pueden colapsar en la misma identidad."""
    from ct.rules import Hallazgo as HallazgoMotor

    a = HallazgoMotor("efectivo", "ALTO", "Área", "Pago en efectivo de $1 a Proveedor A", "ev",
                      refs=["1"], clave="efectivo-linea")
    b = HallazgoMotor("efectivo", "ALTO", "Área", "Pago en efectivo de $2 a Proveedor B", "ev",
                      refs=["2"], clave="efectivo-linea")
    assert ingesta.clave_natural(a) != ingesta.clave_natural(b)


def test_clave_natural_de_un_agregado_no_depende_de_los_refs():
    """Hallazgos "agregados" (una sola fila que resume varios gastos, como obras en unidades
    privadas) llevan más de una ref: a diferencia del caso por-gasto (una única ref), acá las
    refs no distinguen subcasos, son solo el detalle de cuáles gastos entraron en la suma. Si
    una liquidación corregida agrega o saca un gasto del agregado, la clave no puede cambiar:
    el auditor perdería el estado/respuesta que ya había puesto en ese hallazgo."""
    from ct.rules import Hallazgo as HallazgoMotor

    a = HallazgoMotor("obras", "ALTO", "Área", "Obras en unidades privadas: $100.000", "ev",
                      refs=["1", "2", "3"], clave="obras-unidades")
    b = HallazgoMotor("obras", "ALTO", "Área", "Obras en unidades privadas: $120.000", "ev",
                      refs=["1", "2", "3", "4"], clave="obras-unidades")
    assert ingesta.clave_natural(a) == ingesta.clave_natural(b)
