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
    """Índice compuesto (antes: solo pct_trazable*100). Mismo escenario de siempre: todos los
    gastos sin docs salvo el primero, que tiene factura y queda verificado. La cuenta a mano:
      documentacion = trazabilidad = importe_g0/total; conciliacion sale de los pagos del
      fixture (los débitos automáticos quedan respaldados aunque no haya docs);
      consistencia = 1/1 (un solo período, cuadra); explicaciones = 1.0 (cero hallazgos);
      penalización = 0 (cero CRÍTICOS abiertos).
      indice = round(0.30*v_doc*100 + 0.30*v_conc*100 + 0.20*v_traz*100 + 10.0 + 10.0)
    Con el fixture de agosto (total 29.876.923,16 · gasto 1 = 256.260,11 · débitos
    respaldados 5.667.925,62): round(0.3 + 5.7 + 0.2 + 10.0 + 10.0) = 26.
    """
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
    assert t["dinero_con_factura"] == gastos[0].importe
    assert t["gastos_por_estado"]["sin_informacion"]["cantidad"] == len(gastos) - 1
    assert m["periodos"][0]["periodo"] == "2026-08"
    # componentes: peso/valor/puntos verificados contra los dineros ya validados arriba
    c = t["componentes"]
    v_doc = t["dinero_con_factura"] / total
    v_conc = t["dinero_pago_respaldado"] / total
    v_traz = t["dinero_verificado"] / total
    assert c["documentacion"] == {"peso": 0.30, "valor": round(v_doc, 4),
                                  "puntos": round(0.30 * v_doc * 100, 1)}
    assert c["conciliacion"]["puntos"] == round(0.30 * v_conc * 100, 1)
    assert c["trazabilidad"]["puntos"] == round(0.20 * v_traz * 100, 1)
    assert c["consistencia"] == {"peso": 0.10, "valor": 1.0, "puntos": 10.0,
                                 "periodos_cuadran": 1, "periodos_totales": 1}
    assert c["explicaciones"] == {"peso": 0.10, "valor": 1.0, "puntos": 10.0}
    assert t["penalizacion"] == {"criticos_abiertos": 0, "por_critico": 2, "tope": 25, "puntos": 0}
    esperado = max(0, min(100, round(round(0.30 * v_doc * 100, 1) + round(0.30 * v_conc * 100, 1)
                                     + round(0.20 * v_traz * 100, 1) + 10.0 + 10.0)))
    assert m["indice"] == esperado
    # lo viejo sigue: pct_trazable no cambió de significado
    assert t["pct_trazable"] == round(v_traz, 4)


def test_penalizacion_por_criticos_con_tope(db, tmp_path):
    """15 CRÍTICOS abiertos → 15×2 = 30 puntos, pero el tope es 25; el índice nunca baja de 0."""
    st, liq = preparar(db, tmp_path)
    _limpiar_hallazgos(db, liq)
    gastos = db.query(models.Gasto).filter_by(liquidacion_id=liq.id).order_by(models.Gasto.n).all()
    assert len(gastos) >= 15
    for g in gastos[:15]:
        _hallazgo(db, liq, g.n, "CRÍTICO")
    m = analitica.metricas(db, solo_publicado=False)
    t = m["totales"]
    assert t["penalizacion"] == {"criticos_abiertos": 15, "por_critico": 2, "tope": 25, "puntos": 25}
    esperado = max(0, min(100, round(sum(c["puntos"] for c in t["componentes"].values()) - 25)))
    assert m["indice"] == esperado
    assert 0 <= m["indice"] <= 100
    # el período también arrastra su propia penalización
    assert m["periodos"][0]["penalizacion"]["puntos"] == 25


def test_explicaciones_sin_hallazgos_es_uno(db, tmp_path):
    """Sin ningún hallazgo (ni abierto ni resuelto): nada que explicar = todo explicado."""
    st, liq = preparar(db, tmp_path)
    _limpiar_hallazgos(db, liq)
    m = analitica.metricas(db, solo_publicado=False)
    assert m["totales"]["componentes"]["explicaciones"]["valor"] == 1.0
    assert m["periodos"][0]["componentes"]["explicaciones"]["valor"] == 1.0


def test_consistencia_cuenta_las_no_cuadra(db, tmp_path):
    """Una liquidación no_cuadra en el rango agranda el denominador de consistencia, pero no
    aporta gastos, hallazgos ni dinero a ninguna otra métrica."""
    st, liq = preparar(db, tmp_path)
    _limpiar_hallazgos(db, liq)
    gastos = db.query(models.Gasto).filter_by(liquidacion_id=liq.id).order_by(models.Gasto.n).all()
    total = round(sum(g.importe for g in gastos), 2)
    db.add(models.Liquidacion(periodo="2026-05", archivo_key="x", estado="no_cuadra"))
    db.commit()
    m = analitica.metricas(db, solo_publicado=False)
    c = m["totales"]["componentes"]["consistencia"]
    assert c["periodos_cuadran"] == 1 and c["periodos_totales"] == 2 and c["valor"] == 0.5
    assert m["totales"]["dinero_total"] == total          # la no_cuadra no suma nada más
    assert len(m["periodos"]) == 1                        # y no aparece como período
    assert m["periodos"][0]["componentes"]["consistencia"]["valor"] == 1.0  # el mes propio siempre 1/1


def test_propietario_no_ve_no_cuadra_ni_en_el_conteo(db, tmp_path):
    """La vista del propietario afirma solo sobre lo publicado: una no_cuadra sin publicar no
    se filtra ni siquiera como conteo en el denominador de consistencia."""
    st, liq = preparar(db, tmp_path)
    _limpiar_hallazgos(db, liq)
    db.add(models.Liquidacion(periodo="2026-05", archivo_key="x", estado="no_cuadra"))
    liq.estado = "publicada"
    db.commit()
    m = analitica.metricas(db, solo_publicado=True)
    c = m["totales"]["componentes"]["consistencia"]
    assert c["periodos_cuadran"] == 1 and c["periodos_totales"] == 1 and c["valor"] == 1.0


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


# ── Tests de endpoints ──────────────────────────────────────────────────────


def test_endpoint_indice_para_auditor(db, tmp_path, auditor):
    st, liq = preparar(db, tmp_path)
    r = auditor.get("/analitica/indice")
    assert r.status_code == 200
    d = r.json()
    assert "indice" in d and d["periodos"][0]["periodo"] == "2026-08"


def test_endpoint_gastos_filtra_por_estado(db, tmp_path, auditor):
    st, liq = preparar(db, tmp_path)
    r = auditor.get("/analitica/gastos", params={"periodo": "2026-08", "estado": "verificado"})
    assert r.status_code == 200
    assert all(g["estado"] == "verificado" for g in r.json()["gastos"])
    assert auditor.get("/analitica/gastos", params={"periodo": "2026-08", "estado": "zzz"}).status_code == 422
    assert auditor.get("/analitica/gastos", params={"periodo": "2020-01"}).status_code == 404


def test_endpoint_requiere_sesion(db, cliente):
    assert cliente.get("/analitica/indice").status_code in (401, 403)


def test_endpoint_propietario_ve_solo_publicado(db, tmp_path, cliente, auditor):
    """Propietario obtiene 200 en /analitica/indice, pero con la liquidación en estado
    'procesada' no ve ningún período. Al publicarla, el período aparece."""
    from app import admin
    st, liq = preparar(db, tmp_path)
    # la liquidación quedó en estado "procesada" → propietario no ve nada
    uf = db.query(models.Unidad).first().uf
    codigo = admin.generar_codigo(db, uf)
    r = cliente.post("/auth/login-unidad", json={"uf": uf, "codigo": codigo})
    assert r.status_code == 200
    # propietario recibe 200 pero periodos vacíos (solo ve "publicada")
    r = cliente.get("/analitica/indice")
    assert r.status_code == 200
    assert r.json()["periodos"] == []
    # publicar → el período ahora aparece
    liq.estado = "publicada"
    db.commit()
    r2 = cliente.get("/analitica/indice")
    assert r2.status_code == 200
    assert r2.json()["periodos"][0]["periodo"] == "2026-08"
