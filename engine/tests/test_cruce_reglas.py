"""Chequeos puros del cruce, con Gasto/Documento sintéticos (sin PDFs, nunca se saltean).
Números reales de agosto 2026: cuotas de Roth (FC de mayo por $7.950.000, cuota de agosto
declarada el 21-08 sin comprobante propio) y saldo de Saczewiczyk."""
from datetime import date

from ct.comprobantes import (Documento, chequear_importe_factura, chequear_pagos_declarados)
from ct.model import Gasto, Pago


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
