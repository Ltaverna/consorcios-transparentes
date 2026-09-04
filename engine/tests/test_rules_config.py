from ct.rules import Config


def test_desde_dict_aplica_conocidos_e_ignora_extras():
    cfg = Config.desde_dict({"efectivo_linea_alta": 100.0, "inventado": 1})
    assert cfg.efectivo_linea_alta == 100.0
    assert cfg.dias_factura_pago_max == 60  # default intacto


def test_desde_dict_vacio_o_none_da_defaults():
    assert Config.desde_dict({}) == Config()
    assert Config.desde_dict(None) == Config()
