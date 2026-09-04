"""La ingesta usa los fixtures reales del motor (julio y agosto 2026, cuadran al 100 %)."""
from app import ingesta, models
from app.storage import LocalStorage

from .conftest import FIXTURES


def preparar(db, tmp_path, periodo="2026-08", fixture="redconar_202608.txt"):
    st = LocalStorage(str(tmp_path))
    key = f"liquidaciones/{periodo}.txt"
    st.guardar(key, (FIXTURES / fixture).read_bytes())
    liq = models.Liquidacion(periodo=periodo, archivo_key=key)
    db.add(liq)
    db.commit()
    return st, liq


def test_procesar_agosto_queda_procesada_con_gastos_y_hallazgos(db, tmp_path):
    st, liq = preparar(db, tmp_path)
    ingesta.procesar(db, liq.id, st)
    db.refresh(liq)
    assert liq.estado == "procesada" and liq.cuadra
    assert liq.sistema != "" and liq.datos["periodo"]
    assert db.query(models.Gasto).filter_by(liquidacion_id=liq.id).count() > 20
    assert db.query(models.Hallazgo).filter_by(liquidacion_id=liq.id).count() > 0
    assert db.query(models.Unidad).count() > 100  # las 116 unidades sincronizadas


def test_procesar_usa_el_mes_anterior_si_existe(db, tmp_path):
    st, liq_jul = preparar(db, tmp_path, "2026-07", "redconar_202607.txt")
    ingesta.procesar(db, liq_jul.id, st)
    st.guardar("liquidaciones/2026-08.txt", (FIXTURES / "redconar_202608.txt").read_bytes())
    liq_ago = models.Liquidacion(periodo="2026-08", archivo_key="liquidaciones/2026-08.txt")
    db.add(liq_ago)
    db.commit()
    ingesta.procesar(db, liq_ago.id, st)
    db.refresh(liq_ago)
    assert liq_ago.estado == "procesada"


def test_archivo_invalido_queda_en_error(db, tmp_path):
    st = LocalStorage(str(tmp_path))
    st.guardar("liquidaciones/2026-08.txt", b"esto no es una liquidacion")
    liq = models.Liquidacion(periodo="2026-08", archivo_key="liquidaciones/2026-08.txt")
    db.add(liq)
    db.commit()
    ingesta.procesar(db, liq.id, st)
    db.refresh(liq)
    assert liq.estado == "error" and liq.error


def test_periodo_equivocado_queda_en_error(db, tmp_path):
    st, liq = preparar(db, tmp_path, periodo="2026-05", fixture="redconar_202608.txt")
    ingesta.procesar(db, liq.id, st)
    db.refresh(liq)
    assert liq.estado == "error" and "2026-08" in liq.error


def test_no_cuadra_no_inserta_gastos(db, tmp_path, monkeypatch):
    from ct.model import Check, Liquidacion as LiqMotor
    falsa = LiqMotor(sistema="test", periodo="Agosto 2026")
    falsa.checks.append(Check("total", ok=False, esperado=1.0, obtenido=2.0))
    monkeypatch.setattr(ingesta, "parsear_bytes", lambda nombre, data: falsa)
    st, liq = preparar(db, tmp_path)
    ingesta.procesar(db, liq.id, st)
    db.refresh(liq)
    assert liq.estado == "no_cuadra" and not liq.cuadra
    assert db.query(models.Gasto).count() == 0
