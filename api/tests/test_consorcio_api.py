import io

from app import admin, models


def test_reglamento_subir_requiere_auditor_y_sirve_a_cualquier_sesion(db, auditor, cliente):
    r = auditor.post("/consorcio/reglamento",
                     files={"pdf": ("reglamento.pdf", io.BytesIO(b"%PDF-reglamento"), "application/pdf"),
                            "transcripcion": ("reglamento.md", io.BytesIO("# Reglamento\ntexto".encode()), "text/markdown")})
    assert r.status_code == 200 and r.json() == {"ok": True, "pdf": True, "transcripcion": True}
    est = auditor.get("/consorcio/reglamento")
    assert est.json() == {"pdf": True, "transcripcion": True}
    pdf = auditor.get("/consorcio/reglamento/pdf")
    assert pdf.status_code == 200
    assert "attachment" in pdf.headers.get("content-disposition", "")
    md = auditor.get("/consorcio/reglamento/transcripcion")
    assert md.status_code == 200 and "Reglamento" in md.text
    assert md.headers["content-type"].startswith("text/markdown")


def test_reglamento_sin_subir_da_404_y_estado_false(db, auditor):
    assert auditor.get("/consorcio/reglamento").json() == {"pdf": False, "transcripcion": False}
    assert auditor.get("/consorcio/reglamento/pdf").status_code == 404
    assert auditor.get("/consorcio/reglamento/transcripcion").status_code == 404


def test_reglamento_subir_sin_archivos_o_sin_rol_falla(db, auditor, cliente):
    # Sin archivos (auditor autenticado): 422
    assert auditor.post("/consorcio/reglamento").status_code == 422
    # Sin sesión: cliente ya tiene la cookie de auditor (es el mismo objeto); hacemos logout
    # para probar el caso sin autenticación.
    auditor.post("/auth/salir")
    assert cliente.post("/consorcio/reglamento").status_code in (401, 403)


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
