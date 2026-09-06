"""Reglas históricas contra la serie real (julio y agosto 2026) y variantes sintéticas.

La serie real disponible en fixtures tiene UN solo período previo (julio) para agosto:
`salto` y `concentracion` exigen ≥2 previos, así que sobre la serie real se verifica que NO
corren; para ejercitarlas se derivan períodos sintéticos copiando el parse real."""
import pathlib

from ct.historia import _excluida, _norm, _norm_nro, evaluar_historia
from ct.redconar import parse_text
from ct.rules import Config

FIXTURES = pathlib.Path(__file__).resolve().parent / "fixtures"


def _parse(nombre):
    return parse_text((FIXTURES / nombre).read_text(encoding="utf-8"))


def _julio():
    return _parse("redconar_202607.txt")


def _agosto():
    return _parse("redconar_202608.txt")


def _hallazgos(regla, *args, **kw):
    return [h for h in evaluar_historia(*args, **kw) if h.regla == regla]


def test_norm_nro():
    assert _norm_nro("0003-00001234") == "3-1234"
    assert _norm_nro("0001-00000002") is None   # menos de 3 dígitos significativos: relleno
    assert _norm_nro("0000-00000000") is None
    assert _norm_nro("s/n") is None
    assert _norm_nro(None) is None
    assert _norm_nro("0010-00000001") == "10-1"  # 101 junto: pasa el umbral


def test_excluida():
    assert _excluida("SUELDOS Y CARGAS SOCIALES")
    assert _excluida("Cargas sociales")
    assert not _excluida("ABONOS DE MANTENIMIENTO")
    assert not _excluida("DESCARGA DE AGUA")
    assert not _excluida("GASTOS DEL ENCARGADO")


def test_serie_vacia_no_emite_nada():
    assert evaluar_historia(_agosto(), [], Config()) == []
