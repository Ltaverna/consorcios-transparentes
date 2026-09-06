"""Chequeos puros del cruce, con Gasto/Documento sintéticos (sin PDFs, nunca se saltean).
Números reales de agosto 2026: cuotas de Roth (FC de mayo por $7.950.000, cuota de agosto
declarada el 21-08 sin comprobante propio) y saldo de Saczewiczyk."""
from datetime import date

from ct.comprobantes import (Documento, chequear_pagos_declarados)
from ct.model import Gasto, Pago


def _gasto(n=25, proveedor="MARIO LEONARDO ROTH", importe=2_650_000.0, pagos=(), **kw):
    g = Gasto(n=n, categoria="ABONOS Y SERVICIOS", proveedor=proveedor,
              concepto="Cambio de serpentina", columna="A", importe=importe, **kw)
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
