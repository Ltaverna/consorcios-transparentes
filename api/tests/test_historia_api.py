"""Integración de las reglas históricas: recálculo idempotente, contención de fallas
y despublicación al rechazar. El cálculo en sí se prueba en el motor; acá se stubbea."""
from app import ingesta, models
from app.storage import LocalStorage
from ct.rules import Hallazgo as HallazgoMotor

from .conftest import FIXTURES


def preparar(db, tmp_path, periodo="2026-08", fixture="redconar_202608.txt"):
    st = LocalStorage(str(tmp_path))
    key = f"liquidaciones/{periodo}.txt"
    st.guardar(key, (FIXTURES / fixture).read_bytes())
    liq = models.Liquidacion(periodo=periodo, archivo_key=key)
    db.add(liq)
    db.commit()
    return st, liq


def _canned(*_args, **_kw):
    return [HallazgoMotor("historia_duplicado", "ALTO", "Respaldo documental",
                          "La factura X ya figuraba en julio", "evidencia", 0,
                          "Verificar", ["1"], clave="dup-fact|2026-07|3-1234")]


def test_procesar_genera_hallazgos_de_historia(db, tmp_path, monkeypatch):
    monkeypatch.setattr(ingesta, "evaluar_historia", _canned)
    st, liq = preparar(db, tmp_path)
    ingesta.procesar(db, liq.id, st)
    db.refresh(liq)
    assert liq.estado == "procesada"
    hs = db.query(models.Hallazgo).filter_by(liquidacion_id=liq.id, origen="historia").all()
    assert len(hs) == 1 and hs[0].regla == "historia_duplicado"


def test_recalcular_es_idempotente_y_conserva_la_clave(db, tmp_path, monkeypatch):
    monkeypatch.setattr(ingesta, "evaluar_historia", _canned)
    st, liq = preparar(db, tmp_path)
    ingesta.procesar(db, liq.id, st)
    fila = db.query(models.Hallazgo).filter_by(liquidacion_id=liq.id, origen="historia").one()
    ingesta.recalcular_historia(db, liq, st)
    db.commit()
    tras = db.query(models.Hallazgo).filter_by(liquidacion_id=liq.id, origen="historia").one()
    assert (tras.id, tras.clave) == (fila.id, fila.clave)


def test_falla_de_historia_no_rompe_la_ingesta(db, tmp_path, monkeypatch):
    def explota(*_a, **_k):
        raise RuntimeError("boom")
    monkeypatch.setattr(ingesta, "evaluar_historia", explota)
    st, liq = preparar(db, tmp_path)
    ingesta.procesar(db, liq.id, st)
    db.refresh(liq)
    assert liq.estado == "procesada"
    assert db.query(models.Hallazgo).filter_by(liquidacion_id=liq.id, origen="historia").count() == 0


def test_limpiar_al_rechazar_despublica_historia(db, tmp_path):
    st, liq = preparar(db, tmp_path)
    ingesta.procesar(db, liq.id, st)
    h = models.Hallazgo(liquidacion_id=liq.id, clave="dup-fact|x|1", origen="historia",
                        regla="historia_duplicado", severidad="ALTO", area="a",
                        titulo="t", evidencia="e", publicado=True)
    db.add(h)
    db.commit()
    ingesta.limpiar_al_rechazar(db, liq)
    db.commit()
    assert h.publicado is False


def test_serie_y_docs_llegan_al_motor(db, tmp_path, monkeypatch):
    """Con julio procesado con un documento, el recálculo de agosto recibe la serie con julio
    y sus comprobantes como previos."""
    recibido = {}

    def espia(liq, serie, cfg, docs_actual=None, docs_previos=None):
        recibido.update(serie=[l.periodo for l in serie], docs_previos=docs_previos)
        return []

    st, liq_jul = preparar(db, tmp_path, "2026-07", "redconar_202607.txt")
    ingesta.procesar(db, liq_jul.id, st)
    db.add(models.Documento(liquidacion_id=liq_jul.id, gasto_n=3, tipo="factura",
                            archivo_key="comprobantes/2026-07/f.pdf", hash="abc123", metadatos={}))
    db.commit()
    st.guardar("liquidaciones/2026-08.txt", (FIXTURES / "redconar_202608.txt").read_bytes())
    liq_ago = models.Liquidacion(periodo="2026-08", archivo_key="liquidaciones/2026-08.txt")
    db.add(liq_ago)
    db.commit()
    monkeypatch.setattr(ingesta, "evaluar_historia", espia)
    ingesta.procesar(db, liq_ago.id, st)
    assert recibido["serie"] and "julio" in recibido["serie"][0].lower()
    assert recibido["docs_previos"] == {"2026-07": [(3, "abc123", "f.pdf")]}
