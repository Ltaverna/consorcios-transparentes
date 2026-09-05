"""Reglas de referencias de mercado, calibradas contra la liquidación real de agosto 2026.

Números del fixture `redconar_202608.txt`: sueldos netos $3.198.809 (gastos 6 y 7; el patrón
excluye F.931, FATERYH/SERACARH/SUTERH y retenciones sobre factura), gastos de administración
$874.799 (gastos 34 y 35) y abono de matafuegos $99.750,74 (gasto 29, "SOLUCIONES EN
EXTINGUIDORES"; la póliza del seguro integral menciona matafuegos pero no cuenta como abono)."""
import pathlib

from ct.redconar import parse_text
from ct.rules import Config, evaluar

FIXTURES = pathlib.Path(__file__).resolve().parent / "fixtures"

NETO = 3_198_809.00
HONORARIOS = 874_799.00
MATAFUEGOS = 99_750.74


def _liq():
    return parse_text((FIXTURES / "redconar_202608.txt").read_text(encoding="utf-8"))


def _hallazgos(regla, liq, cfg):
    return [h for h in evaluar(liq, None, cfg) if h.regla == regla]


def test_sueldo_sobre_la_referencia_dispara():
    cfg = Config(sueldo_encargado_ref=NETO * 0.7, sueldo_tolerancia=0.10)
    hs = _hallazgos("sueldo_mercado", _liq(), cfg)
    assert len(hs) == 1
    h = hs[0]
    assert h.severidad == "ALTO"  # desvío de 42,9 %, más del doble de la tolerancia
    assert "sobre la referencia" in h.titulo
    assert sorted(h.refs) == ["6", "7"]


def test_sueldo_bajo_escala_es_alto():
    cfg = Config(sueldo_encargado_ref=NETO * 1.5)
    hs = _hallazgos("sueldo_mercado", _liq(), cfg)
    assert len(hs) == 1
    h = hs[0]
    assert h.severidad == "ALTO"
    assert "bajo la" in h.titulo
    assert "fuera de recibo" in h.recomendacion


def test_sueldo_dentro_de_banda_no_dispara():
    cfg = Config(sueldo_encargado_ref=NETO)
    assert _hallazgos("sueldo_mercado", _liq(), cfg) == []


def test_referencia_cero_apaga_las_reglas():
    liq = _liq()
    for regla in ("sueldo_mercado", "honorarios_mercado", "abonos_mercado"):
        assert _hallazgos(regla, liq, Config()) == []


def test_honorarios_sobre_referencia():
    liq = _liq()
    hs = _hallazgos("honorarios_mercado", liq, Config(honorarios_ref=HONORARIOS * 0.8))
    assert len(hs) == 1
    assert hs[0].severidad in ("MEDIO", "ALTO")
    assert sorted(hs[0].refs) == ["34", "35"]
    assert _hallazgos("honorarios_mercado", liq, Config(honorarios_ref=HONORARIOS * 2)) == []


def test_abono_sobre_tope():
    cfg = Config(abono_matafuegos_ref=MATAFUEGOS * 0.5)
    hs = _hallazgos("abonos_mercado", _liq(), cfg)
    assert len(hs) == 1
    h = hs[0]
    assert h.severidad == "MEDIO"
    assert "matafuegos" in h.titulo
    assert "matafuegos" in h.evidencia
    assert h.refs == ["29"]
    assert h.clave == "abono-caro:matafuegos"
