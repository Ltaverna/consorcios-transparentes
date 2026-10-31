"""Pruebas de regresión del parser sobre liquidaciones reales (texto extraído con pdftotext -layout)."""
import glob
import os

import pytest

from ct.redconar import parse_text
from ct.rules import Config, evaluar

FIX = os.path.join(os.path.dirname(__file__), "fixtures")
FILES = sorted(glob.glob(os.path.join(FIX, "redconar_*.txt")))
MODERN = [f for f in FILES if not f.endswith("redconar_202407.txt")]


def load(name):
    return parse_text(open(os.path.join(FIX, name), encoding="utf-8").read())


@pytest.mark.parametrize("path", FILES, ids=[os.path.basename(f) for f in FILES])
def test_gastos_cuadran(path):
    liq = parse_text(open(path, encoding="utf-8").read())
    assert liq.gastos, "sin líneas de gasto"
    fails = [c for c in liq.checks if not c.ok and ("Rubro" in c.nombre or "total de gastos" in c.nombre or "Columna" in c.nombre or "suma de rubros" in c.nombre)]
    assert not fails, fails
    # cada gasto tiene proveedor, categoría, importe y al menos un pago con fecha
    for g in liq.gastos:
        assert g.proveedor and g.categoria and g.importe != 0
        assert g.pagos and g.pagos[0].fecha, f"gasto {g.n} {g.proveedor} sin pago"


@pytest.mark.parametrize("path", FILES, ids=[os.path.basename(f) for f in FILES])
def test_estado_financiero_cuadra(path):
    liq = parse_text(open(path, encoding="utf-8").read())
    fails = [c for c in liq.checks if not c.ok and ("Estado financiero" in c.nombre or "Cuenta" in c.nombre or "disponibilidades" in c.nombre)]
    assert not fails, fails
    assert liq.estado.saldo_cierre != 0


@pytest.mark.parametrize("path", MODERN, ids=[os.path.basename(f) for f in MODERN])
def test_unidades_cuadran(path):
    liq = parse_text(open(path, encoding="utf-8").read())
    assert len(liq.unidades) == 116
    assert liq.cuadra, [c for c in liq.checks if not c.ok]
    assert not [a for a in liq.avisos if "no suman" in a or "no cierra" in a or "no se pudo" in a]
    total_pct = sum(u.pcts.get("A", 0) for u in liq.unidades)
    assert 99.5 < total_pct < 100.5


def test_agosto_2026_valores_conocidos():
    liq = load("redconar_202608.txt")
    assert liq.periodo == "Agosto 2026"
    assert liq.total_gastos == 29876923.16
    assert liq.totales_columna == {"A": 18690264.72, "B": 587416.67, "D": 10599241.77}
    assert liq.estado.saldo_cierre == 1941386.31
    assert [c.saldo_cierre for c in liq.cuentas] == [626104.26, 1315282.05]
    assert liq.total_deudores == 4027770.23 and len(liq.deudores) == 9
    uc1 = next(u for u in liq.unidades if u.uf == 201)
    assert uc1.deuda == 1425249.01 and uc1.interes == 102971.68 and uc1.pagos == 0
    acosta = next(u for u in liq.unidades if u.uf == 86)
    assert acosta.deuda == -421815.14
    pen = next(g for g in liq.gastos if g.proveedor.startswith("PEÑALOZA"))
    assert pen.columna == "D" and pen.factura_nro == "00003-00000202" and pen.importe == 4333333.33
    ef = [g for g in liq.gastos if g.en_efectivo]
    assert len(ef) == 1 and ef[0].importe == 70000.0
    assert len(liq.evolucion) == 6 and liq.evolucion[-1].mes == "Agosto 2026"


def test_julio_2026_cuatro_clases_y_efectivo():
    liq = load("redconar_202607.txt")
    assert set(k for k in liq.prorrateo_total if not k.startswith("_")) == {"A", "B", "C", "D"}
    assert round(sum(g.importe for g in liq.gastos if g.en_efectivo), 2) == 6730602.30


def test_reglas_agosto_2026():
    liq = load("redconar_202608.txt"); prev = load("redconar_202607.txt")
    hs = evaluar(liq, prev, Config())
    reglas = {h.regla for h in hs}
    assert {"efectivo", "liquidez", "obras_unidades", "prorrateo", "morosidad", "fechas", "proveedor_nuevo", "legales", "clasificacion", "costos"} <= reglas
    assert not any(h.regla == "cuadre" for h in hs)
    crit = [h for h in hs if h.severidad == "CRÍTICO"]
    assert len(crit) >= 3


def test_octubre_2026_cinco_clases_y_dos_vencimientos():
    """Octubre 2026 estrenó el prorrateo de 5 clases (A..E, con C y E de la obra de
    calefacción) y las columnas 1°/2° Vto en lugar de A Pagar. Además pdftotext
    deja el importe de 'Ingresos por pago de intereses' en un renglón propio."""
    liq = load("redconar_202610.txt")
    assert liq.periodo == "Octubre 2026"
    assert liq.total_gastos == 32244604.05
    assert liq.prorrateo_total["A"] == 20512710.00
    assert liq.prorrateo_total["B"] == 602051.73
    assert liq.prorrateo_total["C"] == -617400.42
    assert liq.prorrateo_total["D"] == 3826145.83
    assert liq.prorrateo_total["E"] == 617784.99
    assert liq.prorrateo_total["_a_pagar"] == 30525972.91   # 1° vencimiento, no el 2°
    assert liq.estado.ing_intereses == 355729.98            # importe en renglón aparte
    assert liq.estado.saldo_cierre == 1848488.69
    assert liq.total_deudores == 5087166.33   # sección Deudores (incluye intereses)
    assert liq.prorrateo_total["_deuda"] == 4855447.95


def test_noviembre_2025_gastos_de_liquidaciones_anteriores():
    """Noviembre 2025 pagó $149.000 devengados de la liquidación anterior (sección
    'PAGO DE GASTOS DE LIQUIDACIONES ANTERIORES'): los egresos del estado financiero
    son gastos del mes + ese pago, y el check debe contemplarlo."""
    liq = load("redconar_202511.txt")
    assert liq.periodo == "Noviembre 2025"
    assert liq.total_gastos == 18382925.52
    assert liq.estado.egresos == 18531925.52
    assert liq.estado.egresos_anteriores == 149000.00


def test_diciembre_2025_columna_por_alineacion():
    """El gasto de $300 de MAXICOPY queda visualmente corrido hacia la letra B,
    pero la liquidación lo cuenta en A: la columna se decide por el cluster de
    bordes derechos de los importes, no por la letra más cercana."""
    liq = load("redconar_202512.txt")
    assert liq.periodo == "Diciembre 2025"
    g = [x for x in liq.gastos if "MAXICOPY" in x.proveedor and x.importe == 300.00]
    assert len(g) == 1 and g[0].columna == "A"
    assert liq.totales_columna == {"A": 23209531.56, "B": 517139.29, "D": 143987.61}
