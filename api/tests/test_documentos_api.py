from app import admin, models

from .test_liquidaciones_api import subir


def test_descargar_documento_con_rol(db, auditor, tmp_path):
    liq_id = subir(auditor).json()["id"]
    st_key = "comprobantes/2026-08/f.pdf"
    (tmp_path / "comprobantes/2026-08").mkdir(parents=True)
    (tmp_path / st_key).write_bytes(b"pdf")
    d = models.Documento(liquidacion_id=liq_id, tipo="factura", archivo_key=st_key)
    db.add(d)
    db.commit()
    r = auditor.get(f"/documentos/{d.id}/contenido")
    assert r.status_code == 200 and r.content == b"pdf"
    assert r.headers["x-content-type-options"] == "nosniff"
    assert "attachment" in r.headers["content-disposition"]


def test_propietario_no_ve_documentos(db, cliente, auditor, tmp_path):
    liq_id = subir(auditor).json()["id"]
    d = models.Documento(liquidacion_id=liq_id, tipo="factura", archivo_key="x.pdf")
    db.add(d)
    # el fixture de la liquidación ya trae la UF 1 entre sus unidades (sincronizar_unidades
    # la crea al procesar); no volver a insertarla o rompe la unique constraint.
    if not db.query(models.Unidad).filter_by(uf=1).first():
        db.add(models.Unidad(uf=1))
    db.commit()
    codigo = admin.generar_codigo(db, 1)
    cliente.post("/auth/login-unidad", json={"uf": 1, "codigo": codigo})
    assert cliente.get(f"/documentos/{d.id}/contenido").status_code == 403


def test_propietario_ve_informe_publicado(db, cliente, auditor):
    liq_id = subir(auditor).json()["id"]
    auditor.post(f"/liquidaciones/{liq_id}/publicar")
    uf = db.query(models.Unidad).first().uf
    codigo = admin.generar_codigo(db, uf)
    cliente.post("/auth/login-unidad", json={"uf": uf, "codigo": codigo})
    mi = cliente.get("/mi-unidad").json()
    assert mi["uf"] == uf and mi["periodo"] == "2026-08"
    r = cliente.get(f"/informes/2026-08/html")
    assert r.status_code == 200 and b"Consorcio" in r.content
    assert r.headers["x-content-type-options"] == "nosniff"
    assert "content-disposition" not in r.headers


def test_propietario_no_ve_informe_sin_publicar(db, cliente, auditor):
    subir(auditor)
    uf = db.query(models.Unidad).first().uf
    codigo = admin.generar_codigo(db, uf)
    cliente.post("/auth/login-unidad", json={"uf": uf, "codigo": codigo})
    assert cliente.get("/informes/2026-08/html").status_code == 404
    assert cliente.get("/mi-unidad").status_code == 404


def test_url_firmada_pide_descarga_para_documentos_pero_no_informes(db, auditor, monkeypatch):
    from .test_liquidaciones_api import subir
    llamadas = []

    class StorageEspia:
        def url_firmada(self, key, segundos=900, descarga=False):
            llamadas.append((key, descarga))
            return "https://r2.example/" + key

        def leer(self, key): return b""

        def guardar(self, key, data): pass

        def existe(self, key): return True

        def borrar(self, key): pass

    liq_id = subir(auditor).json()["id"]
    auditor.post(f"/liquidaciones/{liq_id}/publicar")
    d = models.Documento(liquidacion_id=liq_id, tipo="factura", archivo_key="comprobantes/2026-08/f.pdf")
    db.add(d)
    db.commit()
    from app.main import app
    espia = StorageEspia()
    original = app.state.storage
    app.state.storage = espia
    try:
        auditor.get(f"/documentos/{d.id}/contenido")
        auditor.get("/informes/2026-08/html")
    finally:
        app.state.storage = original
    assert (d.archivo_key, True) in llamadas          # documento → attachment
    assert any(k.startswith("informes/") and not desc for k, desc in llamadas)  # informe → inline
