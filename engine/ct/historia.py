"""Reglas históricas: la liquidación actual contra la serie de meses previos.

`evaluar_historia` devuelve hallazgos que SIEMPRE involucran a `liq` (el mes actual): un
duplicado julio↔agosto cuelga de agosto y no se re-emite al procesar septiembre. `serie` va
ordenada por período ascendente y puede ser vacía. Sin dependencias de base de datos: los
comprobantes llegan como tuplas `(gasto_n, hash, archivo)` — `docs_actual` es la lista del mes
y `docs_previos` un dict por período; si faltan, el chequeo por hash simplemente no corre.
"""
from __future__ import annotations
import re
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
            if nro:
                previos.setdefault((_norm(g.proveedor), nro), []).append((pl.periodo, g))
    for g in liq.gastos:
        nro = _norm_nro(g.factura_nro)
        for periodo_prev, gp in (previos.get((_norm(g.proveedor), nro), []) if nro else []):
            mismo = abs(g.importe - gp.importe) <= 1
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
        vistos: set[str] = set()
        for gn, h, archivo in docs_actual:
            if not h or h not in hprev:
                continue
            periodo_prev, gn_prev = hprev[h]
            clave = f"dup-hash|{periodo_prev}|{h}"
            if clave in vistos:
                continue
            vistos.add(clave)
            out.append(Hallazgo(
                "historia_duplicado", "ALTO", "Respaldo documental",
                f"El comprobante {archivo} ya respaldaba un gasto de {periodo_prev}",
                f"El mismo archivo está adjunto al gasto {gn_prev if gn_prev is not None else '?'} de "
                f"{periodo_prev} y al gasto {gn if gn is not None else '?'} de este mes.",
                0, "Verificar que un mismo comprobante no respalde dos pagos distintos.",
                [str(gn)] if gn is not None else [], clave=clave))
    return out


def evaluar_historia(liq: Liquidacion, serie: list[Liquidacion], cfg: Optional[Config] = None,
                     docs_actual: Optional[list[Doc]] = None,
                     docs_previos: Optional[dict[str, list[Doc]]] = None) -> list[Hallazgo]:
    cfg = cfg or Config()
    out: list[Hallazgo] = []
    for _, fn in RULES_H:
        out.extend(fn(liq, serie, cfg, docs_actual, docs_previos))
    return out
