from app import admin, models


def test_ver_y_editar_umbrales(db, auditor):
    admin.init_consorcio(db, "Rivadavia 2069")
    r = auditor.put("/consorcio", json={"umbrales": {"efectivo_linea_alta": 500000}})
    assert r.status_code == 200
    assert auditor.get("/consorcio").json()["umbrales"]["efectivo_linea_alta"] == 500000


def test_umbral_desconocido_422(db, auditor):
    admin.init_consorcio(db, "Rivadavia 2069")
    r = auditor.put("/consorcio", json={"umbrales": {"umbral_inventado": 1}})
    assert r.status_code == 422


def test_umbral_con_tipo_invalido_da_422(db, auditor):
    admin.init_consorcio(db, "Rivadavia 2069")
    r = auditor.put("/consorcio", json={"umbrales": {"efectivo_mes_alto": "muchisimo"}})
    assert r.status_code == 422


def test_umbral_numerico_como_texto_se_coerciona(db, auditor):
    admin.init_consorcio(db, "Rivadavia 2069")
    r = auditor.put("/consorcio", json={"umbrales": {"efectivo_linea_alta": "500000"}})
    assert r.status_code == 200
    valor = auditor.get("/consorcio").json()["umbrales"]["efectivo_linea_alta"]
    assert valor == 500000 and isinstance(valor, (int, float))


def test_generar_codigo_por_endpoint(db, auditor):
    db.add(models.Unidad(uf=27, piso_depto="13-B"))
    db.commit()
    r = auditor.post("/unidades/27/codigo")
    assert r.status_code == 200 and len(r.json()["codigo"]) == 8
    assert auditor.get("/unidades").json()[0]["tiene_codigo"] is True
