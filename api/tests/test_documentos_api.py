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


def propietario_con_documentos(db, cliente, auditor, tmp_path):
    """Liquidación con dos comprobantes (gastos 2 y 3) y un hallazgo publicado que
    solo cita el gasto 2; deja al cliente logueado como propietario. Devuelve
    (liq_id, doc_ok_id, doc_no_id)."""
    liq_id = subir(auditor).json()["id"]
    (tmp_path / "comprobantes/2026-08").mkdir(parents=True)
    docs = []
    for n in (2, 3):
        key = f"comprobantes/2026-08/g{n}.pdf"
        (tmp_path / key).write_bytes(b"pdf")
        docs.append(models.Documento(liquidacion_id=liq_id, gasto_n=n, tipo="factura", archivo_key=key))
    db.add_all(docs)
    db.add(models.Hallazgo(liquidacion_id=liq_id, clave="cruce|pub", origen="comprobantes",
                           regla="cruce", severidad="ALTO", titulo="Publicado",
                           refs=["2"], publicado=True))
    db.commit()
    uf = db.query(models.Unidad).first().uf
    codigo = admin.generar_codigo(db, uf)
    r = cliente.post("/auth/login-unidad", json={"uf": uf, "codigo": codigo})
    assert r.status_code == 200
    return liq_id, docs[0].id, docs[1].id


def test_propietario_descarga_documento_de_hallazgo_publicado(db, cliente, auditor, tmp_path):
    _, doc_ok_id, doc_no_id = propietario_con_documentos(db, cliente, auditor, tmp_path)
    r = cliente.get(f"/documentos/{doc_ok_id}/contenido", follow_redirects=False)
    assert r.status_code in (200, 307)
    assert cliente.get(f"/documentos/{doc_no_id}/contenido").status_code == 403
    # vista=1 sobre doc accesible → permitido e inline (sin attachment)
    r_vista = cliente.get(f"/documentos/{doc_ok_id}/contenido?vista=1", follow_redirects=False)
    assert r_vista.status_code in (200, 307)
    assert "attachment" not in r_vista.headers.get("content-disposition", "")
    # vista=1 sobre doc NO accesible → 403 igual que sin vista
    assert cliente.get(f"/documentos/{doc_no_id}/contenido?vista=1").status_code == 403


def test_propietario_lista_documentos_de_publicados(db, cliente, auditor, tmp_path):
    liq_id, doc_ok_id, _ = propietario_con_documentos(db, cliente, auditor, tmp_path)
    r = cliente.get(f"/documentos?liquidacion_id={liq_id}")
    assert r.status_code == 200
    assert {d["id"] for d in r.json()} == {doc_ok_id}


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


def test_refs_de_morosidad_no_habilitan_documentos(db, cliente, auditor, tmp_path):
    """PoC del reviewer: un hallazgo publicado de origen "liquidacion" (morosidad) con
    refs=["2"] (UFs deudoras) NO debe habilitar el acceso al documento con gasto_n=2.
    El propietario debe recibir 403 tanto en contenido como en el listado; un ID
    inexistente también devuelve 403 (sin enumerar qué IDs existen)."""
    liq_id = subir(auditor).json()["id"]
    (tmp_path / "comprobantes/2026-08").mkdir(parents=True)
    key = "comprobantes/2026-08/gasto2.pdf"
    (tmp_path / key).write_bytes(b"pdf")
    doc = models.Documento(liquidacion_id=liq_id, gasto_n=2, tipo="factura", archivo_key=key)
    db.add(doc)
    # Hallazgo de morosidad: origen="liquidacion", refs=["2"] son UFs deudoras, no gastos.
    db.add(models.Hallazgo(liquidacion_id=liq_id, clave="morosidad|pub", origen="liquidacion",
                           regla="morosidad", severidad="ALTO", titulo="Morosidad",
                           refs=["2"], publicado=True))
    db.commit()
    uf = db.query(models.Unidad).first().uf
    codigo = admin.generar_codigo(db, uf)
    r = cliente.post("/auth/login-unidad", json={"uf": uf, "codigo": codigo})
    assert r.status_code == 200

    # El propietario NO puede bajar el comprobante (refs de morosidad ≠ refs de comprobantes).
    assert cliente.get(f"/documentos/{doc.id}/contenido").status_code == 403
    # El propietario NO lo ve en el listado.
    r = cliente.get(f"/documentos?liquidacion_id={liq_id}")
    assert r.status_code == 200
    assert all(d["id"] != doc.id for d in r.json())
    # Un ID inexistente también devuelve 403 (no enumera qué IDs existen).
    assert cliente.get("/documentos/99999/contenido").status_code == 403


def test_contenido_con_vista_sirve_inline(db, auditor):
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
    d = models.Documento(liquidacion_id=liq_id, tipo="factura", archivo_key="comprobantes/2026-08/f.pdf")
    db.add(d)
    db.commit()
    from app.main import app
    espia = StorageEspia()
    original = app.state.storage
    app.state.storage = espia
    try:
        r_vista = auditor.get(f"/documentos/{d.id}/contenido?vista=1", follow_redirects=False)
        r_descarga = auditor.get(f"/documentos/{d.id}/contenido", follow_redirects=False)
    finally:
        app.state.storage = original
    assert (d.archivo_key, False) in llamadas   # vista=1 → URL firmada inline
    assert (d.archivo_key, True) in llamadas    # sin vista → attachment
    assert r_vista.status_code == 307
    assert "attachment" not in r_vista.headers.get("content-disposition", "")
    assert r_vista.headers.get("x-content-type-options") == "nosniff"
    assert "attachment" in r_descarga.headers.get("content-disposition", "")
