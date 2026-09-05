from app import admin, models

from .test_liquidaciones_api import subir

ESTADOS = ("pendiente", "preguntado", "respondido", "descartado", "cerrado")


def con_datos(auditor):
    subir(auditor)
    return auditor


def propietario_con_hallazgos(db, cliente, auditor):
    """Sube una liquidación, agrega un hallazgo publicado y otro sin publicar,
    y deja al cliente logueado como propietario de una unidad. Devuelve los ids."""
    liq_id = subir(auditor).json()["id"]
    h_pub = models.Hallazgo(liquidacion_id=liq_id, clave="cruce|pub", origen="comprobantes",
                            regla="cruce", severidad="ALTO", area="Mantenimiento",
                            titulo="Publicado", evidencia="ev", recomendacion="rec",
                            refs=["2"], publicado=True)
    h_no_pub = models.Hallazgo(liquidacion_id=liq_id, clave="cruce|nopub", origen="comprobantes",
                               regla="cruce", severidad="ALTO", area="Mantenimiento",
                               titulo="No publicado", refs=["3"])
    db.add_all([h_pub, h_no_pub])
    db.commit()
    uf = db.query(models.Unidad).first().uf
    codigo = admin.generar_codigo(db, uf)
    r = cliente.post("/auth/login-unidad", json={"uf": uf, "codigo": codigo})
    assert r.status_code == 200
    return h_pub.id, h_no_pub.id


def test_propietario_lista_solo_hallazgos_publicados(db, cliente, auditor):
    propietario_con_hallazgos(db, cliente, auditor)
    r = cliente.get("/hallazgos")
    assert r.status_code == 200
    assert len(r.json()) == 1 and all(h["publicado"] for h in r.json())


def test_propietario_detalle_sin_eventos_y_404_para_no_publicado(db, cliente, auditor):
    id_publicado, id_no_publicado = propietario_con_hallazgos(db, cliente, auditor)
    r = cliente.get(f"/hallazgos/{id_publicado}")
    assert r.status_code == 200
    assert "eventos" not in r.json()
    assert "evidencia" in r.json() and "recomendacion" in r.json()
    assert cliente.get(f"/hallazgos/{id_no_publicado}").status_code == 404


def test_listar_y_filtrar(db, auditor):
    con_datos(auditor)
    todos = auditor.get("/hallazgos").json()
    assert len(todos) > 0 and {"id", "regla", "severidad", "estado", "titulo"} <= set(todos[0])
    criticos = auditor.get("/hallazgos", params={"severidad": "CRÍTICO"}).json()
    assert all(h["severidad"] == "CRÍTICO" for h in criticos)


def test_cambiar_estado_crea_evento(db, auditor):
    con_datos(auditor)
    h = auditor.get("/hallazgos").json()[0]
    r = auditor.post(f"/hallazgos/{h['id']}/estado",
                     json={"estado": "preguntado", "nota": "Se preguntó en la asamblea"})
    assert r.status_code == 200
    det = auditor.get(f"/hallazgos/{h['id']}").json()
    assert det["estado"] == "preguntado"
    assert det["eventos"][0]["a"] == "preguntado"
    assert det["eventos"][0]["nota"] == "Se preguntó en la asamblea"
    assert det["eventos"][0]["usuario"] == "Auditor"


def test_estado_invalido_422(auditor):
    con_datos(auditor)
    h = auditor.get("/hallazgos").json()[0]
    assert auditor.post(f"/hallazgos/{h['id']}/estado", json={"estado": "inventado"}).status_code == 422


def test_publicar_y_respuesta(auditor):
    con_datos(auditor)
    h = auditor.get("/hallazgos").json()[0]
    auditor.post(f"/hallazgos/{h['id']}/publicar", json={"publicado": True})
    auditor.post(f"/hallazgos/{h['id']}/respuesta", json={"texto": "La administración respondió X"})
    det = auditor.get(f"/hallazgos/{h['id']}").json()
    assert det["publicado"] and det["respuesta_admin"] == "La administración respondió X"


def test_consejo_lee_pero_no_cambia(db, auditor):
    from app import admin
    con_datos(auditor)
    h = auditor.get("/hallazgos").json()[0]
    admin.crear_usuario(db, "c@example.com", "C", "consejo", "clave-de-test")
    auditor.post("/auth/login", json={"email": "c@example.com", "clave": "clave-de-test"})
    assert auditor.get("/hallazgos").status_code == 200
    assert auditor.post(f"/hallazgos/{h['id']}/estado", json={"estado": "cerrado"}).status_code == 403
