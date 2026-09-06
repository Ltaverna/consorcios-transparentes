"""Reglas históricas: la liquidación actual contra la serie de meses previos.

`evaluar_historia` devuelve hallazgos que SIEMPRE involucran a `liq` (el mes actual): un
duplicado julio↔agosto cuelga de agosto y no se re-emite al procesar septiembre. `serie` va
ordenada por período ascendente y puede ser vacía. Sin dependencias de base de datos: los
comprobantes llegan como tuplas `(gasto_n, hash, archivo)` — `docs_actual` es la lista del mes
y `docs_previos` un dict por período; si faltan, el chequeo por hash simplemente no corre.
"""
from __future__ import annotations
import re
from statistics import median
from typing import Callable, Optional

from .model import Liquidacion
from .rules import Config, Hallazgo, fmt, pct

Doc = tuple[Optional[int], str, str]    # (gasto_n, hash, archivo)
RuleH = Callable[..., list[Hallazgo]]
RULES_H: list[tuple[str, RuleH]] = []


def rule_h(name: str):
    def deco(fn: RuleH) -> RuleH:
        RULES_H.append((name, fn))
        return fn
    return deco


def _norm(s: str) -> str:
    return re.sub(r"[^a-z0-9]", "", (s or "").lower())


_RE_EXCLUIDA = re.compile(r"\bSUELDOS?\b|\bCARGAS?\b")


def _excluida(categoria: str) -> bool:
    """Sueldos y cargas sociales quedan afuera de salto/concentración: el SAC de junio y
    diciembre y los aportes distorsionan, y ya los cubren sueldo_mercado y costos."""
    return bool(_RE_EXCLUIDA.search(categoria.upper()))


def _norm_nro(nro: Optional[str]) -> Optional[str]:
    """'0003-00001234' -> '3-1234'. None si el número junto no llega a 100 (relleno)."""
    partes = re.findall(r"\d+", nro or "")
    if not partes:
        return None
    if int("".join(str(int(p)) for p in partes)) < 100:
        return None
    return "-".join(str(int(p)) for p in partes)


# ------------------------------------------------------------- duplicados entre meses
@rule_h("historia_duplicado")
def r_duplicado(liq, serie, cfg, docs_actual, docs_previos):
    out: list[Hallazgo] = []
    previos: dict[tuple[str, str], list] = {}
    for pl in serie:
        for g in pl.gastos:
            nro = _norm_nro(g.factura_nro)
            if nro and _norm(g.proveedor):
                previos.setdefault((_norm(g.proveedor), nro), []).append((pl.periodo, g))
    for g in liq.gastos:
        nro = _norm_nro(g.factura_nro)
        for periodo_prev, gp in (previos.get((_norm(g.proveedor), nro), []) if nro and _norm(g.proveedor) else []):
            mismo = abs(g.importe - gp.importe) <= 1
            cuotas = bool(g.factura_importe) and g.importe + gp.importe <= g.factura_importe + 1
            if cuotas:
                out.append(Hallazgo(
                    "historia_duplicado", "MEDIO", "Respaldo documental",
                    f"Posible pago en cuotas de la factura {g.factura_nro} de {g.proveedor}",
                    f"{periodo_prev}: gasto {gp.n} por {fmt(gp.importe)}; este mes: gasto {g.n} por "
                    f"{fmt(g.importe)}. La suma ({fmt(g.importe + gp.importe)}) no supera el total "
                    f"facturado ({fmt(g.factura_importe)}).",
                    0, "Pedir el comprobante de cada cuota y el detalle del plan de pagos.",
                    [str(g.n)], clave=f"dup-fact|{periodo_prev}|{nro}"))
                continue
            out.append(Hallazgo(
                "historia_duplicado", "CRÍTICO" if mismo else "ALTO", "Respaldo documental",
                f"La factura {g.factura_nro} de {g.proveedor} ya figuraba en la liquidación de {periodo_prev}"
                + (" por el mismo importe" if mismo else ""),
                f"{periodo_prev}: gasto {gp.n} por {fmt(gp.importe)}; este mes: gasto {g.n} por {fmt(g.importe)}.",
                g.importe if mismo else 0,
                "Verificar que la misma factura no se haya pagado dos veces." if mismo
                else "Pedir la factura de este mes: el número repetido puede ser un error de carga.",
                [str(g.n)], clave=f"dup-fact|{periodo_prev}|{nro}"))
    if docs_actual and docs_previos:
        hprev: dict[str, tuple[str, Optional[int]]] = {}
        for periodo in sorted(docs_previos):
            for gn, h, _archivo in docs_previos[periodo]:
                if h and h not in hprev:
                    hprev[h] = (periodo, gn)
        vistos: set[tuple[str, Optional[int]]] = set()
        for gn, h, archivo in docs_actual:
            if not h or h not in hprev:
                continue
            periodo_prev, gn_prev = hprev[h]
            clave = f"dup-hash|{periodo_prev}|{h}"
            if (clave, gn) in vistos:
                continue
            vistos.add((clave, gn))
            out.append(Hallazgo(
                "historia_duplicado", "ALTO", "Respaldo documental",
                f"El comprobante {archivo} ya respaldaba un gasto de {periodo_prev}",
                f"El mismo archivo está adjunto al gasto {gn_prev if gn_prev is not None else '?'} de "
                f"{periodo_prev} y al gasto {gn if gn is not None else '?'} de este mes.",
                0, "Verificar que un mismo comprobante no respalde dos pagos distintos.",
                [str(gn)] if gn is not None else [], clave=clave))
    return out


# ------------------------------------------------------------- salto vs. la propia serie
def _sumas(l: Liquidacion) -> dict[tuple[str, str], float]:
    out: dict[tuple[str, str], float] = {}
    for g in l.gastos:
        if _excluida(g.categoria):
            continue
        k = (_norm(g.proveedor), _norm(g.categoria))
        out[k] = round(out.get(k, 0.0) + g.importe, 2)
    return out


@rule_h("historia_salto")
def r_salto(liq, serie, cfg, *_):
    if len(serie) < 2:
        return []
    mensuales = [(pl.periodo, _sumas(pl)) for pl in serie]
    apariciones: dict[tuple[str, str], int] = {}
    for _p, m in mensuales:
        for k in m:
            apariciones[k] = apariciones.get(k, 0) + 1
    act, ult = _sumas(liq), mensuales[-1][1]
    variaciones = {k: act[k] / ult[k] - 1
                   for k, veces in apariciones.items()
                   if veces >= 2 and k in act and ult.get(k, 0) > 0}
    if len(variaciones) < 3:    # sin masa de recurrentes la mediana no dice nada
        return []
    med = median(variaciones.values())
    out: list[Hallazgo] = []
    for k, v in sorted(variaciones.items()):
        exceso = v - med
        if exceso <= cfg.salto_puntos_medio or act[k] <= cfg.salto_importe_min:
            continue
        gs = [g for g in liq.gastos if (_norm(g.proveedor), _norm(g.categoria)) == k]
        historia = " → ".join(f"{p}: {fmt(m[k])}" for p, m in mensuales if k in m)
        out.append(Hallazgo(
            "historia_salto", "ALTO" if exceso > cfg.salto_puntos_alto else "MEDIO",
            "Evolución de costos",
            f"{gs[0].proveedor}: subió {pct(v)} en el mes cuando la mediana de los gastos "
            f"recurrentes fue {pct(med)}",
            f"Serie: {historia} → este mes: {fmt(act[k])}. Exceso de {pct(exceso)} sobre la "
            f"mediana de {len(variaciones)} gastos recurrentes.",
            round(act[k] - ult[k] * (1 + med), 2),
            "Pedir qué justifica el aumento (presupuesto, acuerdo o factura nueva).",
            [str(g.n) for g in gs], clave=f"salto|{k[0]}|{k[1]}"))
    return out


# paso mínimo de 0,5 pp por mes: el ruido de redondeo no es "crecimiento"
PASO_CRECIENTE = 0.005

# ------------------------------------------------------------- concentración de proveedores
def _shares(l: Liquidacion) -> dict[str, float]:
    gastos = [g for g in l.gastos if not _excluida(g.categoria)]
    total = sum(g.importe for g in gastos)
    if total <= 0:
        return {}
    by: dict[str, float] = {}
    for g in gastos:
        by[_norm(g.proveedor)] = by.get(_norm(g.proveedor), 0.0) + g.importe
    return {k: v / total for k, v in by.items()}


@rule_h("historia_concentracion")
def r_concentracion(liq, serie, cfg, *_):
    if len(serie) < 2:
        return []
    s_act, s_prev1, s_prev2 = _shares(liq), _shares(serie[-1]), _shares(serie[-2])
    out: list[Hallazgo] = []
    for k, sh in sorted(s_act.items()):
        alto = sh > cfg.concentracion_proveedor
        creciente = s_prev2.get(k, 0.0) + PASO_CRECIENTE <= s_prev1.get(k, 0.0) <= sh - PASO_CRECIENTE
        if not alto and not (creciente and sh > 0.15):
            continue
        gs = [g for g in liq.gastos if not _excluida(g.categoria) and _norm(g.proveedor) == k]
        titulo = (f"{gs[0].proveedor} concentra {pct(sh)} del gasto del mes (sin sueldos)" if alto
                  else f"{gs[0].proveedor} concentra una parte creciente del gasto: {pct(sh)} este mes")
        out.append(Hallazgo(
            "historia_concentracion", "MEDIO", "Proveedores", titulo,
            f"Share sobre el gasto sin sueldos: {serie[-2].periodo}: {pct(s_prev2.get(k, 0.0))} → "
            f"{serie[-1].periodo}: {pct(s_prev1.get(k, 0.0))} → este mes: {pct(sh)}. "
            f"Umbral: {pct(cfg.concentracion_proveedor)}.",
            round(sum(g.importe for g in gs), 2),
            "Pedir presupuestos alternativos o el detalle de la contratación.",
            [str(g.n) for g in gs], clave=f"concentracion|{k}"))
    return out


def evaluar_historia(liq: Liquidacion, serie: list[Liquidacion], cfg: Optional[Config] = None,
                     docs_actual: Optional[list[Doc]] = None,
                     docs_previos: Optional[dict[str, list[Doc]]] = None) -> list[Hallazgo]:
    cfg = cfg or Config()
    out: list[Hallazgo] = []
    for _, fn in RULES_H:
        out.extend(fn(liq, serie, cfg, docs_actual, docs_previos))
    return out
