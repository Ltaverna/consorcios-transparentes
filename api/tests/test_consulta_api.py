"""Tests para /consulta — filtros de gastos y agregados."""
from app import models

from .test_liquidaciones_api import subir


def _segunda_liquidacion(db):
    """Liquidación sintética para 2026-07 con 3 gastos, para testear multi-período."""
    liq = models.Liquidacion(periodo="2026-07", archivo_key="liquidaciones/2026-07.txt",
                             estado="procesada", cuadra=True)
    db.add(liq)
    db.flush()
    db.add_all([
        models.Gasto(liquidacion_id=liq.id, n=1, categoria="LIMPIEZA",
                     proveedor="EMPRESA LIMPIEZA SRL", concepto="Servicio mensual julio",
                     importe=500000.0, pagos=[]),
        models.Gasto(liquidacion_id=liq.id, n=2, categoria="MANTENIMIENTOS EN UNIDADES",
                     proveedor="SACZEWICZYK MARIA EUGENIA", concepto="Trabajo en julio",
                     importe=800000.0, pagos=[]),
        models.Gasto(liquidacion_id=liq.id, n=3, categoria="SUELDOS Y CARGAS SOCIALES",
                     proveedor="Consorcio RIVADAVIA 2069", concepto="Sueldo julio",
                     importe=1200000.0, pagos=[]),
    ])
    db.commit()
    return liq


def test_consulta_gastos_filtra_y_totaliza(db, auditor):
    subir(auditor)  # período 2026-08, 43 gastos reales

    # filtro por proveedor: SACZEWICZYK tiene 2 gastos en el fixture (n=9 y n=10)
    r = auditor.get("/consulta/gastos?proveedor=saczewiczyk")
    assert r.status_code == 200
    data = r.json()
    assert data["cantidad"] >= 1
    assert abs(data["total"] - sum(f["importe"] for f in data["filas"])) < 0.01
    assert all("SACZEWICZYK" in f["proveedor"].upper() for f in data["filas"])

    # filtro por período y importe mínimo: en 2026-08 hay 9 gastos con importe >= 1.000.000
    r2 = auditor.get("/consulta/gastos?periodo_desde=2026-08&periodo_hasta=2026-08&importe_min=1000000")
    assert r2.status_code == 200
    filas2 = r2.json()["filas"]
    assert len(filas2) >= 1
    assert all(f["importe"] >= 1000000 and f["periodo"] == "2026-08" for f in filas2)


def test_consulta_gastos_busca_en_concepto(db, auditor):
    subir(auditor)

    # "sueldo" aparece en concepto de 4 gastos del fixture
    r = auditor.get("/consulta/gastos?q=sueldo")
    assert r.status_code == 200
    data = r.json()
    assert data["cantidad"] >= 1
    assert all("SUELDO" in f["concepto"].upper() for f in data["filas"])


def test_consulta_agregados_por_proveedor_y_periodo(db, auditor):
    subir(auditor)              # 2026-08
    _segunda_liquidacion(db)    # 2026-07

    # agregados por proveedor: ordenados de mayor a menor total
    r = auditor.get("/consulta/agregados?por=proveedor")
    assert r.status_code == 200
    grupos = r.json()["grupos"]
    assert len(grupos) >= 1
    assert grupos == sorted(grupos, key=lambda g: -g["total"])
    assert {"clave", "total", "cantidad", "variacion"} <= set(grupos[0].keys())

    # agregados por período: deben aparecer los 2 períodos
    p = auditor.get("/consulta/agregados?por=periodo").json()["grupos"]
    assert len(p) >= 2

    # valor inválido en `por` → 422
    assert auditor.get("/consulta/agregados?por=cualquiera").status_code == 422


def test_consulta_agregados_variacion_intra_rango(db, auditor):
    """Sin rango (2+ períodos) la variación compara último vs penúltimo dentro del rango.

    Datos conocidos:
      2026-07 (sintético): SACZEWICZYK MARIA EUGENIA → 800 000,00
      2026-08 (fixture):   SACZEWICZYK MARIA EUGENIA → 2 552 000,00 + 700 000,00 = 3 252 000,00
      variacion esperada = 3 252 000 / 800 000 − 1 = 3,065
    """
    subir(auditor)           # 2026-08
    _segunda_liquidacion(db) # 2026-07

    r = auditor.get("/consulta/agregados?por=proveedor")
    assert r.status_code == 200
    grupos = r.json()["grupos"]

    # Buscar el grupo de SACZEWICZYK (presente en ambos períodos)
    sazcz = next(
        (g for g in grupos if "SACZEWICZYK" in g["clave"].upper()),
        None,
    )
    assert sazcz is not None, "SACZEWICZYK debe aparecer en los agregados"

    # variacion no debe ser None porque hay 2 períodos en el rango
    assert sazcz["variacion"] is not None, "variacion debe ser no-None con 2+ períodos"

    # valor exacto: (3_252_000 / 800_000) - 1 = 3.065
    importe_ago = 2_552_000.0 + 700_000.0   # del fixture 2026-08
    importe_jul = 800_000.0                  # de _segunda_liquidacion (2026-07 = penúltimo período)
    esperado = importe_ago / importe_jul - 1
    assert abs(sazcz["variacion"] - esperado) < 1e-6, (
        f"variacion={sazcz['variacion']!r} ≠ esperado={esperado!r}"
    )


def test_consulta_es_solo_del_equipo(db, auditor, cliente):
    """Un propietario recibe 403 en /consulta/gastos y /consulta/agregados."""
    subir(auditor)

    # Loguear como propietario (patrón de test_documentos_api)
    uf = db.query(models.Unidad).first().uf
    from app import admin
    codigo = admin.generar_codigo(db, uf)
    r = cliente.post("/auth/login-unidad", json={"uf": uf, "codigo": codigo})
    assert r.status_code == 200

    assert cliente.get("/consulta/gastos").status_code == 403
    assert cliente.get("/consulta/agregados?por=proveedor").status_code == 403
