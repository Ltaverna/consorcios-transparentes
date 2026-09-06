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


def evaluar_historia(liq: Liquidacion, serie: list[Liquidacion], cfg: Optional[Config] = None,
                     docs_actual: Optional[list[Doc]] = None,
                     docs_previos: Optional[dict[str, list[Doc]]] = None) -> list[Hallazgo]:
    cfg = cfg or Config()
    out: list[Hallazgo] = []
    for _, fn in RULES_H:
        out.extend(fn(liq, serie, cfg, docs_actual, docs_previos))
    return out
