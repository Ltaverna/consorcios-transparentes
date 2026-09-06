"""Certificador = ejecutor, contra los fixtures reales: Roth certifica los equipos térmicos
(gasto 26 en julio, 24 en agosto) y además ejecuta reparaciones (27 en julio, 25 en agosto)."""
import pathlib

from ct.redconar import parse_text
from ct.rules import Config, evaluar

FIXTURES = pathlib.Path(__file__).resolve().parent / "fixtures"


def _hallazgos(fixture):
    liq = parse_text((FIXTURES / fixture).read_text(encoding="utf-8"))
    return liq, [h for h in evaluar(liq, None, Config()) if h.regla == "certificador"]


def test_roth_certifica_y_ejecuta_en_julio():
    liq, hs = _hallazgos("redconar_202607.txt")
    h = next(x for x in hs if "ROTH" in x.titulo.upper())
    assert h.severidad == "MEDIO"
    assert {"26", "27"} <= set(h.refs)
    assert h.clave.startswith("cert-ejecutor|")


def test_roth_certifica_y_ejecuta_en_agosto():
    liq, hs = _hallazgos("redconar_202608.txt")
    h = next(x for x in hs if "ROTH" in x.titulo.upper())
    assert {"24", "25"} <= set(h.refs)


def test_sin_certificacion_no_dispara():
    liq, hs = _hallazgos("redconar_202607.txt")
    for g in liq.gastos:
        g.concepto = g.concepto.replace("CERTIFICACION", "REVISION")
    hs2 = [h for h in evaluar(liq, None, Config()) if h.regla == "certificador"]
    assert [h for h in hs2 if "ROTH" in h.titulo.upper()] == []
