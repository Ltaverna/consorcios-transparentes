"""Estados por gasto e índice: clasificación con hallazgos/documentos sintéticos sobre el
fixture real de agosto, fórmula verificada a mano, y vista propietario sin lo no publicado."""
from app import analitica, ingesta, models
from app.storage import LocalStorage

from .conftest import FIXTURES


def preparar(db, tmp_path, periodo="2026-08", fixture="redconar_202608.txt"):
    st = LocalStorage(str(tmp_path))
    key = f"liquidaciones/{periodo}.txt"
    st.guardar(key, (FIXTURES / fixture).read_bytes())
    liq = models.Liquidacion(periodo=periodo, archivo_key=key)
    db.add(liq)
    db.commit()
    ingesta.procesar(db, liq.id, st)
    db.refresh(liq)
    return st, liq


def _limpiar_hallazgos(db, liq):
    """Los tests de clasificación fijan su propio escenario: se borran los hallazgos que la
    ingesta generó sobre el fixture real para que no interfieran."""
    db.query(models.Hallazgo).filter_by(liquidacion_id=liq.id).delete()
    db.commit()


def _hallazgo(db, liq, n, severidad, estado="pendiente", publicado=False, regla="prueba", clave=None):
    h = models.Hallazgo(liquidacion_id=liq.id, clave=clave or f"t|{regla}|{severidad}|{n}|{estado}",
                        origen="liquidacion", regla=regla, severidad=severidad,
                        titulo="t", refs=[str(n)], estado=estado, publicado=publicado)
    db.add(h)
    db.commit()
    return h


def _doc(db, liq, n, tipo="factura"):
    d = models.Documento(liquidacion_id=liq.id, gasto_n=n, tipo=tipo,
                        archivo_key=f"comprobantes/{liq.periodo}/g{n}-{tipo}.pdf", metadatos={})
    db.add(d)
    db.commit()
    return d


def test_clasificar_precedencia():
    assert analitica.clasificar(True, {"CRÍTICO", "MEDIO"}) == "inconsistencia"
    assert analitica.clasificar(True, {"ALTO"}) == "anomalia"
    assert analitica.clasificar(False, set()) == "sin_informacion"
    assert analitica.clasificar(False, {"CRÍTICO"}) == "inconsistencia"   # 1-2 le ganan a sin-docs
    assert analitica.clasificar(True, {"MEDIO"}) == "requiere_explicacion"
    assert analitica.clasificar(True, set()) == "verificado"


def test_estados_sobre_gastos_reales(db, tmp_path):
    st, liq = preparar(db, tmp_path)
    _limpiar_hallazgos(db, liq)
    gastos = db.query(models.Gasto).filter_by(liquidacion_id=liq.id).order_by(models.Gasto.n).all()
    a, b, c, d_, e = (g.n for g in gastos[:5])
    _doc(db, liq, a); _hallazgo(db, liq, a, "CRÍTICO")                    # inconsistencia
    _doc(db, liq, b); _hallazgo(db, liq, b, "ALTO")                       # anomalia
    _doc(db, liq, c); _hallazgo(db, liq, c, "MEDIO")                      # requiere_explicacion
    _doc(db, liq, d_); _hallazgo(db, liq, d_, "CRÍTICO", estado="cerrado")  # resuelto → verificado
    # e: sin docs y sin hallazgos → sin_informacion
    filas, hs, abiertos = analitica.evaluar_liquidacion(db, liq, solo_publicado=False)
    por_n = {g.n: est for g, est, _h, _d in filas}
    assert por_n[a] == "inconsistencia"
    assert por_n[b] == "anomalia"
    assert por_n[c] == "requiere_explicacion"
    assert por_n[d_] == "verificado"
    assert por_n[e] == "sin_informacion"


def test_respondido_sigue_abierto_y_morosidad_no_clasifica(db, tmp_path):
    st, liq = preparar(db, tmp_path)
    _limpiar_hallazgos(db, liq)
    gastos = db.query(models.Gasto).filter_by(liquidacion_id=liq.id).order_by(models.Gasto.n).all()
    a, b = gastos[0].n, gastos[1].n
    _doc(db, liq, a); _hallazgo(db, liq, a, "ALTO", estado="respondido")
    _doc(db, liq, b); _hallazgo(db, liq, b, "CRÍTICO", regla="morosidad")   # refs de UF: no aplica
    filas, _, _ = analitica.evaluar_liquidacion(db, liq, solo_publicado=False)
    por_n = {g.n: est for g, est, _h, _d in filas}
    assert por_n[a] == "anomalia"        # respondido cuenta como abierto
    assert por_n[b] == "verificado"      # morosidad no baja el estado del gasto


def test_indice_formula_a_mano(db, tmp_path):
    st, liq = preparar(db, tmp_path)
    _limpiar_hallazgos(db, liq)
    gastos = db.query(models.Gasto).filter_by(liquidacion_id=liq.id).order_by(models.Gasto.n).all()
    total = round(sum(g.importe for g in gastos), 2)
    # todos sin docs (sin_informacion) salvo el primero, verificado
    _doc(db, liq, gastos[0].n)
    m = analitica.metricas(db, solo_publicado=False)
    t = m["totales"]
    assert t["dinero_total"] == total
    assert t["dinero_verificado"] == gastos[0].importe
    assert m["indice"] == round(gastos[0].importe / total * 100)
    assert t["gastos_por_estado"]["sin_informacion"]["cantidad"] == len(gastos) - 1
    assert m["periodos"][0]["periodo"] == "2026-08"


def test_vista_propietario_solo_lo_publicado(db, tmp_path):
    st, liq = preparar(db, tmp_path)
    _limpiar_hallazgos(db, liq)
    gastos = db.query(models.Gasto).filter_by(liquidacion_id=liq.id).order_by(models.Gasto.n).all()
    a = gastos[0].n
    _doc(db, liq, a)
    _hallazgo(db, liq, a, "CRÍTICO", publicado=False)
    filas_int, _, _ = analitica.evaluar_liquidacion(db, liq, solo_publicado=False)
    assert {g.n: e for g, e, _h, _d in filas_int}[a] == "inconsistencia"
    # liquidación no publicada: el propietario no ve NADA del período
    m = analitica.metricas(db, solo_publicado=True)
    assert m["periodos"] == [] and m["indice"] == 0
    liq.estado = "publicada"
    db.commit()
    filas_prop, _, _ = analitica.evaluar_liquidacion(db, liq, solo_publicado=True)
    assert {g.n: e for g, e, _h, _d in filas_prop}[a] == "verificado"   # el no publicado no lo baja


def test_pago_respaldado(db, tmp_path):
    st, liq = preparar(db, tmp_path)
    _limpiar_hallazgos(db, liq)
    gastos = db.query(models.Gasto).filter_by(liquidacion_id=liq.id).order_by(models.Gasto.n).all()
    ef = next(g for g in gastos if g.pagos and any((p.get("forma") or "").lower().startswith("efectivo") for p in g.pagos))
    tr = next(g for g in gastos if g.pagos and all((p.get("forma") or "").lower().startswith("transf") for p in g.pagos))
    _doc(db, liq, tr.n, tipo="pago")
    m = analitica.metricas(db, solo_publicado=False)
    t = m["totales"]
    assert t["dinero_pago_respaldado"] >= tr.importe          # transferencia con doc cuenta
    # el efectivo jamás cuenta: sumarle un doc de pago no lo respalda
    _doc(db, liq, ef.n, tipo="pago")
    t2 = analitica.metricas(db, solo_publicado=False)["totales"]
    assert t2["dinero_pago_respaldado"] == t["dinero_pago_respaldado"]
