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
    g.factura_importe = g.importe   # el gasto real es en cuotas (FC $9M); acá probamos el caso no-cuota
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
    g.factura_importe = g.importe   # el gasto real es en cuotas (FC $9M); acá probamos el caso no-cuota
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


def test_duplicado_exige_mismo_proveedor():
    liq = _agosto()
    g = _gasto_con_factura(liq)
    prev = _julio()
    clon = copy.deepcopy(g)
    clon.proveedor = "OTRO PROVEEDOR SRL"
    prev.gastos.append(clon)
    assert [h for h in _hallazgos("historia_duplicado", liq, [prev], Config())
            if h.clave == f"dup-fact|{prev.periodo}|{_norm_nro(g.factura_nro)}"] == []


def test_duplicado_borde_de_un_peso():
    liq = _agosto()
    g = _gasto_con_factura(liq)
    g.factura_importe = g.importe   # el gasto real es en cuotas (FC $9M); acá probamos el caso no-cuota
    prev = _julio()
    exacto = copy.deepcopy(g)
    exacto.importe = round(g.importe + 1.00, 2)   # ±$1: sigue siendo CRÍTICO
    prev.gastos.append(exacto)
    hs = _hallazgos("historia_duplicado", liq, [prev], Config())
    clave = f"dup-fact|{prev.periodo}|{_norm_nro(g.factura_nro)}"
    assert [h.severidad for h in hs if h.clave == clave] == ["CRÍTICO"]


def test_duplicado_por_hash_dos_gastos_actuales_reportan_ambos():
    hs = _hallazgos("historia_duplicado", _agosto(), [_julio()], Config(),
                    docs_actual=[(12, "abc123def456", "f.pdf"), (15, "abc123def456", "f.pdf")],
                    docs_previos={"2026-07": [(3, "abc123def456", "f.pdf")]})
    dup = [h for h in hs if h.clave.startswith("dup-hash|")]
    assert sorted(h.refs[0] for h in dup) == ["12", "15"]


# ======================================================= historia_salto

def _serie_sintetica():
    """Tres meses derivados del parse real de agosto: la serie sube pareja ~10 % por mes
    (inflación), así la mediana de variaciones queda ~0,10 y solo un salto real la excede."""
    base = _agosto()
    prev2 = copy.deepcopy(base)
    prev2.periodo = "Junio 2026"
    for g in prev2.gastos:
        g.importe = round(g.importe / 1.21, 2)
    prev1 = copy.deepcopy(base)
    prev1.periodo = "Julio 2026"
    for g in prev1.gastos:
        g.importe = round(g.importe / 1.10, 2)
    return [prev2, prev1], base


def _clave_objetivo(liq):
    g = max((x for x in liq.gastos if not _excluida(x.categoria) and x.importe > 60_000),
            key=lambda x: x.importe)
    return _norm(g.proveedor), _norm(g.categoria), g


def test_salto_y_concentracion_exigen_dos_previos():
    liq, serie = _agosto(), [_julio()]
    assert _hallazgos("historia_salto", liq, serie, Config()) == []
    assert _hallazgos("historia_concentracion", liq, serie, Config()) == []


def test_salto_contra_la_propia_serie_es_alto():
    serie, liq = _serie_sintetica()
    prov, cat, obj = _clave_objetivo(liq)
    for g in liq.gastos:
        if _norm(g.proveedor) == prov and _norm(g.categoria) == cat:
            g.importe = round(g.importe * 2.2, 2)    # salta al doble; el resto sube ~10 %
    hs = _hallazgos("historia_salto", liq, serie, Config())
    assert len(hs) == 1
    h = hs[0]
    assert h.severidad == "ALTO"
    assert h.clave == f"salto|{prov}|{cat}"
    assert str(obj.n) in h.refs


def test_salto_moderado_es_medio():
    serie, liq = _serie_sintetica()
    prov, cat, _ = _clave_objetivo(liq)
    for g in liq.gastos:
        if _norm(g.proveedor) == prov and _norm(g.categoria) == cat:
            g.importe = round(g.importe * 1.45, 2)   # ~+59 % vs mediana ~10 %: exceso ~0,49
    hs = _hallazgos("historia_salto", liq, serie, Config())
    assert [h.severidad for h in hs] == ["MEDIO"]


def test_salto_respeta_importe_minimo():
    serie, liq = _serie_sintetica()
    prov, cat, _ = _clave_objetivo(liq)
    for g in liq.gastos:
        if _norm(g.proveedor) == prov and _norm(g.categoria) == cat:
            g.importe = round(g.importe * 2.2, 2)
    assert _hallazgos("historia_salto", liq, serie, Config(salto_importe_min=10**9)) == []


def test_salto_excluye_sueldos():
    serie, liq = _serie_sintetica()
    sueldos = [g for g in liq.gastos if _excluida(g.categoria)]
    assert sueldos, "el fixture real tiene sueldos"
    for g in sueldos:
        g.importe = round(g.importe * 3, 2)
    assert _hallazgos("historia_salto", liq, serie, Config()) == []


# ======================================================= historia_concentracion

def _boost_hasta_share(liq, prov_norm, objetivo):
    """Escala los gastos del proveedor para que su share (sin sueldos) quede en `objetivo`."""
    mios = [g for g in liq.gastos if not _excluida(g.categoria) and _norm(g.proveedor) == prov_norm]
    resto = sum(g.importe for g in liq.gastos
                if not _excluida(g.categoria) and _norm(g.proveedor) != prov_norm)
    factor = (objetivo / (1 - objetivo) * resto) / sum(g.importe for g in mios)
    for g in mios:
        g.importe = round(g.importe * factor, 2)


def test_concentracion_por_encima_del_umbral():
    serie, liq = _serie_sintetica()
    prov, _, obj = _clave_objetivo(liq)
    _boost_hasta_share(liq, prov, 0.30)
    hs = _hallazgos("historia_concentracion", liq, serie, Config())
    h = next(x for x in hs if x.clave == f"concentracion|{prov}")
    assert h.severidad == "MEDIO"
    assert str(obj.n) in h.refs


def test_concentracion_creciente_sin_superar_umbral():
    serie, liq = _serie_sintetica()
    prov, _, _ = _clave_objetivo(liq)
    _boost_hasta_share(serie[0], prov, 0.10)
    _boost_hasta_share(serie[1], prov, 0.14)
    _boost_hasta_share(liq, prov, 0.18)
    hs = _hallazgos("historia_concentracion", liq, serie, Config())
    h = next(x for x in hs if x.clave == f"concentracion|{prov}")
    assert h.severidad == "MEDIO"
    assert "creciente" in h.titulo


def test_concentracion_estable_y_baja_no_dispara():
    serie, liq = _serie_sintetica()
    prov, _, _ = _clave_objetivo(liq)
    for l in (serie[0], serie[1], liq):
        _boost_hasta_share(l, prov, 0.12)
    assert [h for h in _hallazgos("historia_concentracion", liq, serie, Config())
            if h.clave == f"concentracion|{prov}"] == []


def test_concentracion_estable_con_ruido_no_es_creciente():
    serie, liq = _serie_sintetica()
    prov, _, _ = _clave_objetivo(liq)
    _boost_hasta_share(serie[0], prov, 0.179)
    _boost_hasta_share(serie[1], prov, 0.180)   # sube 0,1 pp: ruido, no crecimiento
    _boost_hasta_share(liq, prov, 0.181)
    assert [h for h in _hallazgos("historia_concentracion", liq, serie, Config())
            if h.clave == f"concentracion|{prov}"] == []


# Números reales de agosto 2026 (verificados contra la base el 06-09-2026)
ROTH_CUOTA = 2_650_000.0
ROTH_FACTURADO = 7_950_000.0        # FC 4182 + 4183 + 4191 (mayo 2026)
SACZ_JULIO, SACZ_AGOSTO, SACZ_FACTURADO = 2_000_000.0, 2_552_000.0, 4_552_000.0


def _duplicado_con(liq_importe, prev_importe, factura_importe):
    liq = _agosto()
    g = _gasto_con_factura(liq)
    g.importe, g.factura_importe = liq_importe, factura_importe
    prev = _julio()
    clon = copy.deepcopy(g)
    clon.importe = prev_importe
    prev.gastos.append(clon)
    hs = _hallazgos("historia_duplicado", liq, [prev], Config())
    return next(x for x in hs if x.clave == f"dup-fact|{prev.periodo}|{_norm_nro(g.factura_nro)}")


def test_duplicado_en_cuotas_mismo_importe_es_medio():
    h = _duplicado_con(ROTH_CUOTA, ROTH_CUOTA, ROTH_FACTURADO)
    assert h.severidad == "MEDIO"
    assert "cuotas" in h.titulo


def test_duplicado_en_cuotas_distinto_importe_es_medio():
    h = _duplicado_con(SACZ_AGOSTO, SACZ_JULIO, SACZ_FACTURADO)
    assert h.severidad == "MEDIO"
    assert "cuotas" in h.titulo


def test_duplicado_suma_mayor_al_facturado_sigue_critico():
    h = _duplicado_con(2_650_000.0, 2_650_000.0, 4_000_000.0)   # 5,3M pagados de 4M facturados
    assert h.severidad == "CRÍTICO"


def test_duplicado_sin_factura_importe_mantiene_severidad():
    h = _duplicado_con(1_000_000.0, 1_000_000.0, None)
    assert h.severidad == "CRÍTICO"
