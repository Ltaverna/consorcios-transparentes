"""Prorrateo vs escritura: parser de la transcripción y regla `prorrateo_escritura`.

Los valores del snippet son inventados (los reales viven en la carpeta privada) pero el
formato es el real: pares `número N: X,XXXX%` en texto corrido y la Complementaria I con
la trampa del `100,0000%` cerca de la mención (como en la transcripción verdadera).
"""
from ct.escritura import evaluar_escritura, parsear_porcentuales
from ct.model import Liquidacion, Unidad

SNIPPET = """\
### Artículo 6°

Los porcentuales de dominio son: número 1: 30,0000%; número 2: 25,0000%;
número 3: 20,0000%; número 4: 15,0000%.

La suma de los porcentuales da 90,0000%, que más el 10,0000% de la
Unidad Complementaria I suma exactamente 100,0000%.

**b) Unidad Complementaria I:** 10,0000%. *(Verificado.)*
"""

ESC = {1: 30.0, 2: 25.0, 3: 20.0, 4: 15.0}


def _unidad(uf, pct_a, tipo="Departamento"):
    pcts = {} if pct_a is None else {"A": pct_a}
    return Unidad(uf=uf, piso_depto=f"P-{uf}", propietario="X", tipo=tipo,
                  saldo_ant=0, pagos=0, cred_deb=0, deuda=0, interes=0,
                  expensas={}, pcts=pcts, total_mes=0, redondeo=0, a_pagar=0)


def _liq(unidades):
    return Liquidacion(sistema="test", periodo="Agosto 2026", unidades=unidades)


def _por_clave(hs):
    return {h.clave: h for h in hs}


# ------------------------------------------------------------------ parser
def test_parsear_snippet_formato_real():
    porc, comp = parsear_porcentuales(SNIPPET)
    assert porc == ESC
    assert comp == 10.0    # no se confunde con el 100,0000% pegado a la primera mención


def test_parsear_texto_sin_tabla():
    assert parsear_porcentuales("un md cualquiera sin porcentuales") == ({}, None)
    assert parsear_porcentuales("") == ({}, None)


def test_parsear_nunca_lanza():
    assert parsear_porcentuales(None) == ({}, None)


def test_complementaria_no_toma_porcentuales_de_otra_linea():
    # En la transcripción real una mención de la Complementaria I termina la línea justo
    # antes de la tabla: el 2,8100% de la UF 1 (línea siguiente) no es la complementaria.
    texto = ("que más otro porcentual la Unidad Complementaria I completa.\n"
             "**a) Unidades funcionales:**\nnúmero 1: 2,8100%")
    assert parsear_porcentuales(texto) == ({1: 2.81}, None)


def test_complementaria_ausente_es_none():
    porc, comp = parsear_porcentuales("número 1: 30,0000% y nada más")
    assert porc == {1: 30.0} and comp is None


# ------------------------------------------------------------------ regla
def test_porcentuales_vacios_no_emite_nada():
    assert evaluar_escritura(_liq([_unidad(1, 30.0)]), {}, None) == []


def test_discrepancia_por_uf_dispara_alto():
    liq = _liq([_unidad(1, 29.5)] + [_unidad(u, ESC[u]) for u in (2, 3, 4)])
    hs = evaluar_escritura(liq, ESC, 10.0)
    h = _por_clave(hs)["escritura|1"]
    assert h.regla == "prorrateo_escritura" and h.severidad == "ALTO" and h.area == "Prorrateo"
    assert h.refs == ["1"] and h.monto == 0
    assert "UF 1" in h.titulo and "P-1" in h.titulo


def test_truncado_a_dos_decimales_no_dispara():
    esc = {2: 1.4488, 3: 98.5512}
    liq = _liq([_unidad(2, 1.44), _unidad(3, 98.55)])   # truncados, dif ≤ 0,01
    assert [h for h in evaluar_escritura(liq, esc, None) if h.clave.startswith("escritura|")] == []


def test_uf_sin_clase_a_se_saltea():
    liq = _liq([_unidad(1, None)] + [_unidad(u, ESC[u]) for u in (2, 3, 4)])
    assert "escritura|1" not in _por_clave(evaluar_escritura(liq, ESC, 10.0))


def test_faltantes_agrega_un_medio():
    liq = _liq([_unidad(1, 30.0), _unidad(2, 25.0)])    # faltan la 3 y la 4
    h = _por_clave(evaluar_escritura(liq, ESC, 10.0))["escritura-faltantes"]
    assert h.severidad == "MEDIO" and h.refs == ["3", "4"]
    assert "3" in h.evidencia and "4" in h.evidencia


def test_sobrantes_agrega_un_medio_y_excluye_cocheras():
    liq = _liq([_unidad(u, ESC[u]) for u in ESC]
               + [_unidad(99, 0.10), _unidad(201, 0.42, tipo="Cochera")])
    h = _por_clave(evaluar_escritura(liq, ESC, 10.0))["escritura-sobrantes"]
    assert h.severidad == "MEDIO" and h.refs == ["99"]      # la cochera no es sobrante


def test_cocheras_dentro_de_la_tolerancia_escalada():
    liq = _liq([_unidad(u, ESC[u]) for u in ESC]
               + [_unidad(201, 4.99, tipo="Cochera"), _unidad(202, 5.02, tipo="Cochera")])
    # suma 10,01 vs complementaria 10,0000: dif 0,01 ≤ 0,01 × 2
    assert "escritura-cocheras" not in _por_clave(evaluar_escritura(liq, ESC, 10.0))


def test_cocheras_fuera_de_la_tolerancia_escalada():
    liq = _liq([_unidad(u, ESC[u]) for u in ESC]
               + [_unidad(201, 4.99, tipo="Cochera"), _unidad(202, 5.04, tipo="Cochera")])
    # suma 10,03 vs 10,0000: dif 0,03 > 0,02
    h = _por_clave(evaluar_escritura(liq, ESC, 10.0))["escritura-cocheras"]
    assert h.regla == "prorrateo_escritura" and h.severidad == "MEDIO"
    assert sorted(h.refs) == ["201", "202"]
    assert "Complementaria" in h.titulo


def test_sin_complementaria_no_corre_el_chequeo_de_cocheras():
    liq = _liq([_unidad(201, 4.0, tipo="Cochera")])
    claves = _por_clave(evaluar_escritura(liq, ESC, None))
    assert "escritura-cocheras" not in claves


def test_suma_distinta_de_100_dispara():
    esc = {1: 30.0, 2: 25.0}      # 55 + 10 ≠ 100
    liq = _liq([_unidad(1, 30.0), _unidad(2, 25.0)])
    h = _por_clave(evaluar_escritura(liq, esc, 10.0))["escritura-suma"]
    assert h.severidad == "MEDIO" and h.refs == []
    assert "100" in h.titulo


def test_suma_100_no_dispara():
    liq = _liq([_unidad(u, ESC[u]) for u in ESC])
    assert "escritura-suma" not in _por_clave(evaluar_escritura(liq, ESC, 10.0))
