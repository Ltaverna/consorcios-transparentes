"""Reglas históricas contra la serie real (julio y agosto 2026) y variantes sintéticas.

La serie real disponible en fixtures tiene UN solo período previo (julio) para agosto:
`salto` y `concentracion` exigen ≥2 previos, así que sobre la serie real se verifica que NO
corren; para ejercitarlas se derivan períodos sintéticos copiando el parse real."""
import copy
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


def _gasto_con_factura(liq):
    return next(g for g in liq.gastos if _norm_nro(g.factura_nro))


def test_duplicado_por_numero_mismo_importe_es_critico():
    liq = _agosto()
    g = _gasto_con_factura(liq)
    prev = _julio()
    prev.gastos.append(copy.deepcopy(g))    # la misma factura ya figuraba el mes pasado
    hs = _hallazgos("historia_duplicado", liq, [prev], Config())
    h = next(x for x in hs if x.clave == f"dup-fact|{prev.periodo}|{_norm_nro(g.factura_nro)}")
    assert h.severidad == "CRÍTICO"
    assert str(g.n) in h.refs
    assert prev.periodo in h.titulo or prev.periodo in h.evidencia


def test_duplicado_por_numero_distinto_importe_es_alto():
    liq = _agosto()
    g = _gasto_con_factura(liq)
    prev = _julio()
    clon = copy.deepcopy(g)
    clon.importe = round(g.importe + 500, 2)
    prev.gastos.append(clon)
    hs = _hallazgos("historia_duplicado", liq, [prev], Config())
    h = next(x for x in hs if x.clave == f"dup-fact|{prev.periodo}|{_norm_nro(g.factura_nro)}")
    assert h.severidad == "ALTO"


def test_duplicado_por_hash_entre_meses():
    hs = _hallazgos("historia_duplicado", _agosto(), [_julio()], Config(),
                    docs_actual=[(12, "abc123def456", "factura.pdf")],
                    docs_previos={"2026-07": [(3, "abc123def456", "factura.pdf")]})
    dup = [h for h in hs if h.clave.startswith("dup-hash|")]
    assert len(dup) == 1
    assert dup[0].severidad == "ALTO"
    assert dup[0].clave == "dup-hash|2026-07|abc123def456"
    assert dup[0].refs == ["12"]


def test_sin_docs_el_chequeo_de_hash_no_corre():
    hs = _hallazgos("historia_duplicado", _agosto(), [_julio()], Config(),
                    docs_actual=[(12, "abc", "f.pdf")], docs_previos=None)
    assert [h for h in hs if h.clave.startswith("dup-hash|")] == []
