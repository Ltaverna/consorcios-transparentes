"""Chequeos puros del cruce, con Gasto/Documento sintéticos (sin PDFs, nunca se saltean).
Números reales de agosto 2026: cuotas de Roth (FC de mayo por $7.950.000, cuota de agosto
declarada el 21-08 sin comprobante propio) y saldo de Saczewiczyk."""
from datetime import date

import ct.comprobantes as comprobantes
from ct.comprobantes import (Documento, chequear_importe_factura, chequear_pagos_declarados,
                             cruzar, interpretar, nombre_vinculado, ItemManifiesto, _match_gasto)
from ct.model import Gasto, Liquidacion, Pago, Unidad


def _gasto(n=25, proveedor="MARIO LEONARDO ROTH", importe=2_650_000.0, pagos=(),
           concepto="Cambio de serpentina", **kw):
    g = Gasto(n=n, categoria="ABONOS Y SERVICIOS", proveedor=proveedor,
              concepto=concepto, columna="A", importe=importe, **kw)
    g.pagos = list(pagos)
    return g


def _pago_doc(fecha, importe, archivo="transf.pdf"):
    d = Documento(archivo=archivo, gasto_n=25, tipo="pago")
    d.fecha, d.importe = fecha, importe
    return d


def test_pago_declarado_sin_comprobante_dispara():
    # Roth agosto: declara transferencia 21-08; los adjuntos son del 29-05 y 13-07
    g = _gasto(pagos=[Pago(date(2026, 8, 21), 2_650_000.0, "BANCO", "Transferencia")])
    docs = [_pago_doc(date(2026, 5, 29), 2_650_000.0), _pago_doc(date(2026, 7, 13), 2_650_000.0)]
    hs = chequear_pagos_declarados(g, docs)
    assert len(hs) == 1
    h = hs[0]
    assert h.severidad == "ALTO"
    assert h.clave == "pago-sin-comp|2026-08-21"
    assert "2026-05-29" in h.evidencia and "2026-07-13" in h.evidencia


def test_pago_declarado_con_comprobante_no_dispara():
    # Roth julio: declara 13-07 y la transferencia del 13-07 está adjunta
    g = _gasto(n=27, pagos=[Pago(date(2026, 7, 13), 2_650_000.0, "BANCO", "Transferencia")])
    docs = [_pago_doc(date(2026, 5, 29), 2_650_000.0), _pago_doc(date(2026, 7, 13), 2_650_000.0)]
    assert chequear_pagos_declarados(g, docs) == []


def test_transferencia_combinada_por_mas_importe_no_dispara():
    # una sola transferencia paga varios gastos: el doc trae el total, misma fecha
    g = _gasto(importe=100_000.0, pagos=[Pago(date(2026, 8, 10), 100_000.0, "BANCO", "Transferencia")])
    assert chequear_pagos_declarados(g, [_pago_doc(date(2026, 8, 10), 350_000.0)]) == []


def test_efectivo_y_debito_no_se_evaluan():
    g = _gasto(pagos=[Pago(date(2026, 8, 21), 500_000.0, "CAJA", "Efectivo"),
                      Pago(date(2026, 8, 21), 500_000.0, "BANCO", "Débito automático")])
    assert chequear_pagos_declarados(g, [_pago_doc(date(2026, 1, 1), 1.0)]) == []


def test_sin_ningun_comprobante_no_dispara():
    # eso ya lo cubre la regla existente de respaldo documental
    g = _gasto(pagos=[Pago(date(2026, 8, 21), 2_650_000.0, "BANCO", "Transferencia")])
    assert chequear_pagos_declarados(g, []) == []


def test_tolerancia_de_fecha_tres_dias():
    g = _gasto(pagos=[Pago(date(2026, 8, 21), 2_650_000.0, "BANCO", "Transferencia")])
    assert chequear_pagos_declarados(g, [_pago_doc(date(2026, 8, 18), 2_650_000.0)]) == []
    assert len(chequear_pagos_declarados(g, [_pago_doc(date(2026, 8, 17), 2_650_000.0)])) == 1


def test_pago_con_comprobante_de_la_fecha_pero_importe_insuficiente():
    # sueldos de agosto: el doc es del mismo día pero por menos plata
    g = _gasto(importe=1_424_799.0,
               pagos=[Pago(date(2026, 8, 4), 1_424_799.0, "BANCO", "Transferencia")])
    hs = chequear_pagos_declarados(g, [_pago_doc(date(2026, 8, 4), 1_324_798.66)])
    assert len(hs) == 1
    assert "no cubren el pago declarado" in hs[0].evidencia
    assert "otras fechas" not in hs[0].evidencia


def _factura_doc(importe, archivo="fact.pdf"):
    d = Documento(archivo=archivo, gasto_n=25, tipo="factura")
    d.importe = importe
    return d


def test_facturas_roth_cierran_por_la_suma():
    # tres facturas (2,9M + 4,9M + 0,15M = 7,95M) contra un gasto de 2,65M con facturado 7,95M
    g = _gasto(importe=2_650_000.0, factura_importe=7_950_000.0)
    facts = [_factura_doc(2_900_000.0), _factura_doc(4_900_000.0), _factura_doc(150_000.0)]
    assert chequear_importe_factura(g, facts, total_proveedor_mes=2_740_000.0) == []


def test_factura_que_no_cierra_dispara():
    g = _gasto(importe=300_000.0, factura_importe=None)
    hs = chequear_importe_factura(g, [_factura_doc(500_000.0)], total_proveedor_mes=300_000.0)
    assert len(hs) == 1
    assert hs[0].severidad == "MEDIO"
    assert hs[0].clave == "imp-fact"


def test_factura_igual_al_gasto_no_dispara():
    g = _gasto(importe=300_000.0)
    assert chequear_importe_factura(g, [_factura_doc(300_000.0)], 300_000.0) == []


def test_factura_igual_al_total_del_proveedor_no_dispara():
    g = _gasto(importe=300_000.0)
    assert chequear_importe_factura(g, [_factura_doc(750_000.0)], total_proveedor_mes=750_000.0) == []


def test_factura_sin_importe_legible_no_cuenta():
    g = _gasto(importe=300_000.0)
    assert chequear_importe_factura(g, [_factura_doc(None)], 300_000.0) == []


def test_factura_declarada_en_el_concepto_no_dispara():
    # caso real CSI: el concepto declara el bruto y las retenciones; la factura trae el bruto
    g = _gasto(importe=2_891_220.01, proveedor="COOPERATIVA DE TRABAJO CSI LIMITADA",
               concepto="SERVICIO DE SEGURIDAD FACTURA Nº 4925 POR UN TOTAL DE $3.166.031,55 "
                        "A ESTA SUMA SE DESCUENTAN RETENCIONES, SIRE IVA $274.811,54. "
                        "SE PAGA A LA EMPRESA UN TOTAL DE $2.891.220,01")
    assert chequear_importe_factura(g, [_factura_doc(3_166_031.55)], 2_891_220.01) == []


def test_monto_en_formato_anglo_tambien_cuenta():
    g = _gasto(importe=200_000.0, concepto="SEGUN PRESUPUESTO POR 255,132.48")
    assert chequear_importe_factura(g, [_factura_doc(255_132.48)], 200_000.0) == []


# ------------------------------------------------------------------ _match_gasto (Task 4)

def _liq_con(*gastos):
    liq = Liquidacion(sistema="test", periodo="Agosto 2026")
    liq.gastos = list(gastos)
    return liq


def test_match_unico_por_importe_es_certero():
    liq = _liq_con(_gasto(n=1, importe=100.0))
    g, certero = _match_gasto(ItemManifiesto(None, "X", 100.0, None, []), liq)
    assert g.n == 1 and certero


def test_match_empatado_desempata_por_factura():
    liq = _liq_con(_gasto(n=1, importe=100.0, factura_nro="0001-11"),
                   _gasto(n=2, importe=100.0, factura_nro="0001-22"))
    g, certero = _match_gasto(ItemManifiesto(None, "X", 100.0, "0001-22", []), liq)
    assert g.n == 2 and certero


def test_match_empatado_desempata_por_fecha():
    g1 = _gasto(n=1, importe=100.0, pagos=[Pago(date(2026, 8, 1), 100.0, "BANCO", "Transferencia")])
    g2 = _gasto(n=2, importe=100.0, pagos=[Pago(date(2026, 8, 9), 100.0, "BANCO", "Transferencia")])
    g, certero = _match_gasto(ItemManifiesto(date(2026, 8, 9), "X", 100.0, None, []), _liq_con(g1, g2))
    assert g.n == 2 and certero


def test_match_irresoluble_devuelve_primero_sin_certeza():
    liq = _liq_con(_gasto(n=1, importe=100.0), _gasto(n=2, importe=100.0))
    g, certero = _match_gasto(ItemManifiesto(None, "X", 100.0, None, []), liq)
    assert g.n == 1 and not certero


def test_match_sin_candidatos():
    g, certero = _match_gasto(ItemManifiesto(None, "X", 999.0, None, []), _liq_con(_gasto(n=1, importe=100.0)))
    assert g is None and certero


# ------------------------------------------------------------------ casos reales de falsos positivos, 06-09-2026

PAGO_EDESUR = """Comprobante de transferencia
Detalle de la operación
Fecha 10/03/2026
Importe $ 1.234.567,89
Leyendas adicionales
EDESUR
008005215300
589244000759530437
"""

FACTURA_TECNO_SIM = """                 FACTURA B
 Nro: 0003-00012345
                      Dirección: 3480 Av. F Fernandez de la Cruz          CUIT: 30-70829363-2
                                                                          IIBB: 30-70829363-2
 Cliente:       CONSORCIO DE PROPIETARIOS AV RIVADAVIA
                2067 69 71
 Email:         luisa_escuredo@yahoo.com.ar
 Condición:     CONSUMIDOR FINAL
 CAE: 75123456789012
 Importe Total: $ 27.500,00
"""


def test_referencia_de_pago_no_es_cuit(monkeypatch):
    # Edesur adjunta el pago con una referencia de 12 dígitos bajo 'Leyendas adicionales':
    # una ventana de 11 dígitos de esa referencia NO es un CUIT del destinatario.
    monkeypatch.setattr(comprobantes, "leer_texto", lambda path: PAGO_EDESUR)
    doc = interpretar("pago_edesur.pdf", 10, "30-70709095-4")
    assert doc.tipo == "pago"
    assert doc.destinatario_cuit is None


def test_cuit_duplicado_no_es_receptor(monkeypatch):
    # Tecno Sim imprime el CUIT del emisor dos veces (CUIT + IIBB): el duplicado
    # no debe interpretarse como CUIT del receptor.
    monkeypatch.setattr(comprobantes, "leer_texto", lambda path: FACTURA_TECNO_SIM)
    doc = interpretar("factura_tecnosim.pdf", 10, "30-70709095-4")
    assert doc.tipo == "factura"
    assert doc.emisor_cuit == "30708293632"
    assert doc.receptor_cuit != doc.emisor_cuit
    assert doc.receptor_cuit is None


def _liq_cruce(gasto):
    liq = Liquidacion(sistema="test", periodo="Marzo 2026", cuit_consorcio="30-70709095-4")
    liq.gastos = [gasto]
    liq.unidades = [Unidad(13, "UC-13", "ESCUREDO LUISA", "V", 0, 0, 0, 0, 0, {}, {}, 0, 0, 0)]
    return liq


def _cruzar_con_factura(monkeypatch, receptor, texto):
    g = _gasto(n=10, proveedor="TECNO SIM SA", importe=27_500.0)
    liq = _liq_cruce(g)

    def fake_interpretar(path, gasto_n, cuit_consorcio):
        d = Documento(archivo=path, gasto_n=gasto_n, tipo="factura", texto_len=len(texto))
        d.emisor_cuit = "30708293632"
        d.receptor = receptor
        d.notas.append("__texto__:" + texto)
        return d

    monkeypatch.setattr(comprobantes, "interpretar", fake_interpretar)
    item = ItemManifiesto(None, "TECNO SIM SA", 27_500.0, None, ["fact.pdf"])
    _, hs = cruzar(liq, [item])
    return hs


def test_email_de_contacto_no_vincula_al_propietario(monkeypatch):
    # el mail de contacto luisa_escuredo@... no convierte a la propietaria en titular
    # de la factura cuando el cliente es el propio consorcio
    hs = _cruzar_con_factura(monkeypatch, "CONSORCIO DE PROPIETARIOS AV RIVADAVIA", FACTURA_TECNO_SIM)
    assert not any(h.area == "Gasto ajeno al consorcio" for h in hs)


def test_email_sin_receptor_legible_tampoco_vincula(monkeypatch):
    # aun sin receptor parseado, un email es dato de contacto, no titularidad
    hs = _cruzar_con_factura(monkeypatch, None, "Email: luisa_escuredo@yahoo.com.ar\nCAE: 75123456789012\n")
    assert not any(h.area == "Gasto ajeno al consorcio" for h in hs)


def test_nombre_fuera_de_email_sigue_vinculando(monkeypatch):
    # regresión: si el nombre figura como titular (no dentro de un email), la regla sigue
    assert nombre_vinculado("Titular: Escuredo Luisa", {"Escuredo Luisa": "propietario de UC-13"})
    hs = _cruzar_con_factura(monkeypatch, None, "FACTURA\nTitular: Escuredo Luisa\nCAE: 75123456789012\n")
    assert any(h.area == "Gasto ajeno al consorcio" and "Escuredo" in h.titulo for h in hs)
