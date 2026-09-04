from app import models

from .test_liquidaciones_api import subir

ESTADOS = ("pendiente", "preguntado", "respondido", "descartado", "cerrado")


def con_datos(auditor):
    subir(auditor)
    return auditor


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
