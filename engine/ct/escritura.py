"""Prorrateo de la liquidación contra los porcentuales de dominio de la escritura (art. 6°).

La transcripción del reglamento trae los porcentuales como texto corrido (`número N: X,XXXX%`)
y la Unidad Complementaria I aparte. La liquidación aplica en la clase A el porcentual de la
escritura TRUNCADO (no redondeado) a 2 decimales — de ahí la tolerancia de 0,01 por UF — y
materializa la Complementaria I en cocheras individuales, que se comparan como grupo con
tolerancia escalada. `parsear_porcentuales` nunca lanza: texto sin la tabla → `({}, None)`.
"""
from __future__ import annotations
import re
from typing import Optional

from .model import Liquidacion
from .rules import Hallazgo

TOL_UF = 0.01        # truncado a 2 decimales: la pérdida máxima por UF es < 0,01
TOL_SUMA = 0.0001    # la transcripción verificada suma exactamente 100,0000%

_RE_PAR = re.compile(r"número\s+(\d+)\s*:\s*(\d+,\d{4})\s*%")
_RE_COMP = re.compile(r"Complementaria\s+I\b")
# 1-2 enteros: un porcentual real es < 100, y así el "suma exactamente 100,0000%" que la
# transcripción menciona al lado de la Complementaria I no se confunde con su porcentual.
_RE_PCT = re.compile(r"(?<!\d)(\d{1,2},\d{4})\s*%")
VENTANA_COMP = 80    # caracteres después de la mención donde buscar el porcentual (misma línea)


def _num(s: str) -> float:
    return float(s.replace(",", "."))


def _pct(v: float) -> str:
    return f"{v:.4f}".replace(".", ",") + "%"


def parsear_porcentuales(texto_md: str) -> tuple[dict[int, float], Optional[float]]:
    """Pares UF→porcentual del art. 6° y el porcentual de la Complementaria I (o None)."""
    try:
        porcentuales = {int(n): _num(v) for n, v in _RE_PAR.findall(texto_md or "")}
        complementaria = None
        for m in _RE_COMP.finditer(texto_md or ""):
            # solo la misma línea: una mención al final de una línea no debe robarse el
            # porcentual de la tabla que arranca en la siguiente
            ventana = texto_md[m.end():m.end() + VENTANA_COMP].split("\n", 1)[0]
            mp = _RE_PCT.search(ventana)
            if mp:
                complementaria = _num(mp.group(1))
                break
        return porcentuales, complementaria
    except Exception:
        return {}, None


def evaluar_escritura(liq: Liquidacion, porcentuales: dict[int, float],
                      complementaria: Optional[float]) -> list[Hallazgo]:
    """Regla `prorrateo_escritura`. Solo corre con porcentuales parseados; refs = UFs."""
    if not porcentuales:
        return []
    out: list[Hallazgo] = []
    unidades = {u.uf: u for u in liq.unidades}

    # 1. clase A por UF contra el porcentual de dominio
    for uf in sorted(porcentuales):
        u = unidades.get(uf)
        if u is None:
            continue    # la junta el agregado de faltantes
        pa = u.pcts.get("A")
        if pa is None:
            continue
        esc = porcentuales[uf]
        if abs(pa - esc) > TOL_UF:
            out.append(Hallazgo(
                "prorrateo_escritura", "ALTO", "Prorrateo",
                f"La UF {uf} ({u.piso_depto}) paga {_pct(pa)} pero la escritura le asigna {_pct(esc)}",
                f"Clase A de la liquidación: {_pct(pa)}; porcentual de dominio del art. 6°: "
                f"{_pct(esc)}. La diferencia ({_pct(abs(pa - esc))}) supera la tolerancia por "
                f"truncado (0,01).",
                0, "Pedir la corrección del prorrateo de la unidad según el porcentual de la escritura.",
                [str(uf)], clave=f"escritura|{uf}"))

    # 2. UFs de la escritura que no figuran en la liquidación
    faltantes = sorted(uf for uf in porcentuales if uf not in unidades)
    if faltantes:
        out.append(Hallazgo(
            "prorrateo_escritura", "MEDIO", "Prorrateo",
            f"{len(faltantes)} UF de la escritura no figuran en el prorrateo de la liquidación",
            "UFs con porcentual en el art. 6° y sin fila este mes: "
            + ", ".join(str(u) for u in faltantes) + ".",
            0, "Pedir por qué esas unidades no aparecen en el prorrateo del mes.",
            [str(u) for u in faltantes], clave="escritura-faltantes"))

    # 3. unidades de la liquidación sin porcentual en la escritura (las cocheras van aparte)
    cocheras = [u for u in liq.unidades if u.tipo.strip().lower().startswith("cochera")]
    uf_cocheras = {u.uf for u in cocheras}
    sobrantes = sorted({u.uf for u in liq.unidades
                        if u.uf not in porcentuales and u.uf not in uf_cocheras})
    if sobrantes:
        out.append(Hallazgo(
            "prorrateo_escritura", "MEDIO", "Prorrateo",
            f"{len(sobrantes)} unidades de la liquidación no figuran en la escritura",
            "Unidades prorrateadas este mes sin porcentual en el art. 6° (y que no son cocheras): "
            + ", ".join(str(u) for u in sobrantes) + ".",
            0, "Pedir con qué respaldo se les asigna porcentual a esas unidades.",
            [str(u) for u in sobrantes], clave="escritura-sobrantes"))

    # 4. cocheras como grupo contra la Unidad Complementaria I
    if complementaria is not None and cocheras:
        suma = round(sum(u.pcts.get("A", 0.0) for u in cocheras), 4)
        tolerancia = TOL_UF * len(cocheras)
        if abs(suma - complementaria) > tolerancia + 1e-9:
            out.append(Hallazgo(
                "prorrateo_escritura", "MEDIO", "Prorrateo",
                f"Las cocheras cargan {_pct(suma)} pero la Complementaria I de la escritura es "
                f"{_pct(complementaria)}",
                f"Suma de la clase A de las {len(cocheras)} cocheras: {_pct(suma)}; porcentual de "
                f"la Unidad Complementaria I en el art. 6°: {_pct(complementaria)}. La diferencia "
                f"({_pct(abs(suma - complementaria))}) supera la tolerancia escalada "
                f"(0,01 × {len(cocheras)}).",
                0, "Pedir cómo se reparte el porcentual de la Complementaria I entre las cocheras.",
                [str(u.uf) for u in cocheras], clave="escritura-cocheras"))

    # 5. sanidad de la transcripción: protege contra ediciones rotas del md
    total = round(sum(porcentuales.values()) + (complementaria or 0.0), 4)
    if abs(total - 100.0) > TOL_SUMA:
        out.append(Hallazgo(
            "prorrateo_escritura", "MEDIO", "Prorrateo",
            "La transcripción de la escritura no suma 100%",
            f"Los {len(porcentuales)} porcentuales parseados más la Complementaria I "
            f"({_pct(complementaria) if complementaria is not None else 'no encontrada'}) "
            f"suman {_pct(total)}.",
            0, "Revisar la transcripción del art. 6° antes de confiar en esta comparación.",
            [], clave="escritura-suma"))
    return out
