"""Estados por gasto e índice de transparencia compuesto. Todo derivado (documentos +
hallazgos + triage); nada se almacena y ninguna cifra la genera una IA. Fórmulas y precedencia:
docs/superpowers/specs/2026-09-06-indice-transparencia-design.md (estados) y
docs/superpowers/specs/2026-09-06-indice-compuesto-design.md (índice)."""
from sqlalchemy.orm import Session

from . import models

ABIERTOS = ("pendiente", "preguntado", "respondido")
RESUELTOS = ("descartado", "cerrado")
ESTADOS_GASTO = ("verificado", "requiere_explicacion", "anomalia", "inconsistencia", "sin_informacion")
SEVERIDADES = ("CRÍTICO", "ALTO", "MEDIO", "BAJO")
# los refs de morosidad son UFs, no números de gasto: esa regla no clasifica gastos
REGLAS_REFS_UF = {"morosidad"}

# Índice compuesto: pesos definidos por el dueño (la spec es normativa, no estos comentarios).
# documentacion = dinero_con_factura/total · conciliacion = dinero_pago_respaldado/total
# trazabilidad = dinero_verificado/total (el índice viejo, ahora componente)
# consistencia = períodos que cuadran / períodos con liquidación (incluye las no_cuadra)
# explicaciones = resueltos/(abiertos+resueltos); 1.0 si no hay ningún hallazgo
PESOS = {"documentacion": 0.30, "conciliacion": 0.30, "trazabilidad": 0.20,
         "consistencia": 0.10, "explicaciones": 0.10}
PENALIZACION_POR_CRITICO = 2      # puntos que resta cada hallazgo CRÍTICO abierto
PENALIZACION_TOPE = 25            # tope de la penalización total


def clasificar(tiene_docs: bool, severidades_abiertas: set[str]) -> str:
    if "CRÍTICO" in severidades_abiertas:
        return "inconsistencia"
    if "ALTO" in severidades_abiertas:
        return "anomalia"
    if not tiene_docs:
        return "sin_informacion"
    if severidades_abiertas:
        return "requiere_explicacion"
    return "verificado"


def evaluar_liquidacion(db: Session, liq: models.Liquidacion, solo_publicado: bool):
    """[(gasto, estado, hallazgos_abiertos_que_lo_refieren, documentos)], hallazgos, abiertos."""
    gastos = (db.query(models.Gasto).filter_by(liquidacion_id=liq.id)
                .order_by(models.Gasto.n).all())
    docs = db.query(models.Documento).filter_by(liquidacion_id=liq.id).all()
    hs = db.query(models.Hallazgo).filter_by(liquidacion_id=liq.id).all()
    if solo_publicado:
        hs = [h for h in hs if h.publicado]
    abiertos = [h for h in hs if h.estado in ABIERTOS]
    docs_por_n: dict[int, list] = {}
    for d in docs:
        if d.gasto_n is not None:
            docs_por_n.setdefault(d.gasto_n, []).append(d)
    sev_por_n: dict[int, set[str]] = {}
    hall_por_n: dict[int, list] = {}
    for h in abiertos:
        if h.regla in REGLAS_REFS_UF:
            continue
        for r in (h.refs or []):
            if isinstance(r, str) and r.isdigit():
                n = int(r)
                sev_por_n.setdefault(n, set()).add(h.severidad)
                hall_por_n.setdefault(n, []).append(h)
    filas = []
    for g in gastos:
        dd = docs_por_n.get(g.n, [])
        filas.append((g, clasificar(bool(dd), sev_por_n.get(g.n, set())),
                      hall_por_n.get(g.n, []), dd))
    return filas, hs, abiertos


def _stats_vacias() -> dict:
    return {"dinero_total": 0.0, "dinero_verificado": 0.0, "dinero_con_factura": 0.0,
            "dinero_pago_respaldado": 0.0,
            "gastos_por_estado": {e: {"cantidad": 0, "importe": 0.0} for e in ESTADOS_GASTO},
            "hallazgos_abiertos": {s: 0 for s in SEVERIDADES}, "hallazgos_resueltos": 0}


def _pago_respaldado(g: models.Gasto, tiene_doc_pago: bool, sin_comp_abierto: bool) -> bool:
    """Efectivo jamás respaldado; débito automático siempre (resumen bancario); transferencias
    exigen doc de pago adjunto y ningún hallazgo abierto de pago sin comprobante."""
    pagos = g.pagos or []
    if not pagos:
        return False
    formas = [(p.get("forma") or "").lower() for p in pagos]
    cajas = [(p.get("caja") or "").upper() for p in pagos]
    if any(f.startswith("efectivo") for f in formas) or "CAJA" in cajas:
        return False
    if all(f.startswith(("débito", "debito")) for f in formas):
        return True
    return tiene_doc_pago and not sin_comp_abierto


def _cerrar(s: dict, periodos_cuadran: int = 1, periodos_totales: int = 1) -> dict:
    """Redondeos + porcentajes + índice compuesto del bloque de stats. Un período propio
    siempre es 1/1 en consistencia (si está en `periodos[]` es porque cuadra); los totales
    del rango reciben el conteo real, incluidas las `no_cuadra`."""
    for k in ("dinero_total", "dinero_verificado", "dinero_con_factura", "dinero_pago_respaldado"):
        s[k] = round(s[k], 2)
    for v in s["gastos_por_estado"].values():
        v["importe"] = round(v["importe"], 2)
    total = s["dinero_total"]
    s["pct_trazable"] = round(s["dinero_verificado"] / total, 4) if total else 0.0
    s["pct_con_factura"] = round(s["dinero_con_factura"] / total, 4) if total else 0.0
    s["pct_pago_respaldado"] = round(s["dinero_pago_respaldado"] / total, 4) if total else 0.0
    abiertos = sum(s["hallazgos_abiertos"].values())
    resueltos = s["hallazgos_resueltos"]
    valores = {
        "documentacion": s["dinero_con_factura"] / total if total else 0.0,
        "conciliacion": s["dinero_pago_respaldado"] / total if total else 0.0,
        "trazabilidad": s["dinero_verificado"] / total if total else 0.0,
        "consistencia": periodos_cuadran / periodos_totales if periodos_totales else 0.0,
        # nada que explicar = todo explicado; pero sin ninguna liquidación en el rango
        # no hay nada que afirmar: 0.0 (así el rango vacío da índice 0, no 10)
        "explicaciones": (resueltos / (abiertos + resueltos)) if (abiertos + resueltos)
                         else (1.0 if periodos_totales else 0.0),
    }
    comp = {k: {"peso": PESOS[k], "valor": round(v, 4), "puntos": round(PESOS[k] * v * 100, 1)}
            for k, v in valores.items()}
    comp["consistencia"]["periodos_cuadran"] = periodos_cuadran
    comp["consistencia"]["periodos_totales"] = periodos_totales
    criticos = s["hallazgos_abiertos"]["CRÍTICO"]
    pen = min(PENALIZACION_TOPE, PENALIZACION_POR_CRITICO * criticos)
    s["componentes"] = comp
    s["penalizacion"] = {"criticos_abiertos": criticos, "por_critico": PENALIZACION_POR_CRITICO,
                         "tope": PENALIZACION_TOPE, "puntos": pen}
    s["indice"] = max(0, min(100, round(sum(c["puntos"] for c in comp.values()) - pen)))
    return s


def metricas(db: Session, desde: str = "", hasta: str = "", solo_publicado: bool = False) -> dict:
    estados_liq = ("publicada",) if solo_publicado else ("procesada", "publicada")
    q = db.query(models.Liquidacion).filter(models.Liquidacion.estado.in_(estados_liq))
    if desde:
        q = q.filter(models.Liquidacion.periodo >= desde)
    if hasta:
        q = q.filter(models.Liquidacion.periodo <= hasta)
    liqs = q.order_by(models.Liquidacion.periodo).all()
    if solo_publicado:
        # la vista del propietario afirma solo sobre lo publicado: una no_cuadra sin
        # publicar no se filtra ni siquiera como conteo
        periodos_totales = len(liqs)
    else:
        # consistencia: el denominador suma las no_cuadra del rango (solo el conteo,
        # jamás sus datos); error/procesando no cuentan, son operativos
        qn = db.query(models.Liquidacion).filter(models.Liquidacion.estado == "no_cuadra")
        if desde:
            qn = qn.filter(models.Liquidacion.periodo >= desde)
        if hasta:
            qn = qn.filter(models.Liquidacion.periodo <= hasta)
        periodos_totales = len(liqs) + qn.count()
    agg, periodos = _stats_vacias(), []
    for liq in liqs:
        filas, hs, abiertos = evaluar_liquidacion(db, liq, solo_publicado)
        s = _stats_vacias()
        for g, estado, halls, dd in filas:
            for destino in (s, agg):
                destino["dinero_total"] += g.importe
                destino["gastos_por_estado"][estado]["cantidad"] += 1
                destino["gastos_por_estado"][estado]["importe"] += g.importe
            if estado == "verificado":
                s["dinero_verificado"] += g.importe
                agg["dinero_verificado"] += g.importe
            if any(d.tipo == "factura" for d in dd):
                s["dinero_con_factura"] += g.importe
                agg["dinero_con_factura"] += g.importe
            sin_comp = any("pago-sin-comp" in (h.clave or "") for h in halls)
            if _pago_respaldado(g, any(d.tipo == "pago" for d in dd), sin_comp):
                s["dinero_pago_respaldado"] += g.importe
                agg["dinero_pago_respaldado"] += g.importe
        for h in abiertos:
            if h.severidad in s["hallazgos_abiertos"]:
                s["hallazgos_abiertos"][h.severidad] += 1
                agg["hallazgos_abiertos"][h.severidad] += 1
        resueltos = sum(1 for h in hs if h.estado in RESUELTOS)
        s["hallazgos_resueltos"] += resueltos
        agg["hallazgos_resueltos"] += resueltos
        s["periodo"] = liq.periodo
        periodos.append(_cerrar(s))
    tot = _cerrar(agg, periodos_cuadran=len(liqs), periodos_totales=periodos_totales)
    return {"indice": tot["indice"],
            "rango": {"desde": liqs[0].periodo if liqs else "", "hasta": liqs[-1].periodo if liqs else ""},
            "totales": tot, "periodos": periodos}
