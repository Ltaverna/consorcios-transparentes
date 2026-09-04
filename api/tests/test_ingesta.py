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


def test_documento_sin_checks_queda_en_error(db, tmp_path, monkeypatch):
    """cuadra es `all(c.ok for c in checks)`: con 0 checks da True vacuamente. Un documento
    que no produjo ninguna verificación no puede tratarse como si cuadrara."""
    from ct.model import Liquidacion as LiqMotor
    vacia = LiqMotor(sistema="test", periodo="Agosto 2026")  # sin checks
    monkeypatch.setattr(ingesta, "parsear_bytes", lambda nombre, data: vacia)
    st, liq = preparar(db, tmp_path)
    assert vacia.cuadra is True and not vacia.checks
    ingesta.procesar(db, liq.id, st)
    db.refresh(liq)
    assert liq.estado == "error" and liq.error


def test_periodo_iso():
    assert ingesta.periodo_iso("Agosto 2026") == "2026-08"
    assert ingesta.periodo_iso("agosto, 2026") == "2026-08"
    assert ingesta.periodo_iso("sin fecha") is None


def test_periodo_anterior():
    assert ingesta.periodo_anterior("2026-01") == "2025-12"
    assert ingesta.periodo_anterior("2026-08") == "2026-07"


def test_sincronizar_no_pisa_datos_mas_recientes_al_procesar_un_mes_viejo(db, tmp_path):
    """Ingestar un mes viejo (fuera de orden) no debe revertir nombres de propietario
    que ya reflejan información más reciente."""
    st, liq_ago = preparar(db, tmp_path, "2026-08", "redconar_202608.txt")
    ingesta.procesar(db, liq_ago.id, st)
    unidad = db.query(models.Unidad).first()
    uf, unidad.propietario = unidad.uf, "X-MANUAL"
    db.commit()

    st.guardar("liquidaciones/2026-07.txt", (FIXTURES / "redconar_202607.txt").read_bytes())
    liq_jul = models.Liquidacion(periodo="2026-07", archivo_key="liquidaciones/2026-07.txt")
    db.add(liq_jul)
    db.commit()
    ingesta.procesar(db, liq_jul.id, st)
    db.refresh(liq_jul)

    assert liq_jul.estado == "procesada"
    assert db.query(models.Unidad).filter_by(uf=uf).one().propietario == "X-MANUAL"


def test_upsert_hallazgos_desambigua_colisiones_sin_romper_unicidad(db):
    """Tres hallazgos sintéticos con la misma regla y los mismos refs (misma clave natural
    de base) deben quedar como tres filas con claves distintas y deterministas, sin pisarse
    entre sí ni romper la restricción de unicidad."""
    from ct.rules import Hallazgo as HallazgoMotor
    liq = models.Liquidacion(periodo="2026-08", archivo_key="x.txt")
    db.add(liq)
    db.commit()
    hs = [HallazgoMotor("regla_x", "ALTO", "Área", "Título", "evidencia", refs=["1", "2"]) for _ in range(3)]
    ingesta.upsert_hallazgos(db, liq, hs, origen="liquidacion")
    db.commit()
    filas = db.query(models.Hallazgo).filter_by(liquidacion_id=liq.id).all()
    assert len(filas) == 3
    assert len({f.clave for f in filas}) == 3


def test_upsert_hallazgos_desambigua_clave_de_exactamente_500_caracteres(db):
    """Regresión: si la clave de base mide exactamente 500 caracteres, la vieja
    desambiguación (agregar '~' y truncar a 500) devolvía la MISMA cadena (el '~' quedaba
    afuera del corte) y el bucle no terminaba nunca. La desambiguación por contador debe
    terminar y producir tres claves distintas."""
    from ct.rules import Hallazgo as HallazgoMotor
    liq = models.Liquidacion(periodo="2026-08", archivo_key="x.txt")
    db.add(liq)
    db.commit()
    regla = "r"
    clave_larga = "x" * (500 - len(regla) - 1)  # "regla|clave" da exactamente 500 caracteres
    assert len(f"{regla}|{clave_larga}") == 500
    hs = [HallazgoMotor(regla, "ALTO", "Área", "Título", "evidencia", clave=clave_larga) for _ in range(3)]
    ingesta.upsert_hallazgos(db, liq, hs, origen="liquidacion")
    db.commit()
    filas = db.query(models.Hallazgo).filter_by(liquidacion_id=liq.id).all()
    assert len(filas) == 3
    assert len({f.clave for f in filas}) == 3
