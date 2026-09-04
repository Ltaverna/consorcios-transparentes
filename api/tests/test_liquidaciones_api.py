from .conftest import FIXTURES


def subir(cliente, periodo="2026-08", fixture="redconar_202608.txt"):
    return cliente.post("/liquidaciones",
                        data={"periodo": periodo},
                        files={"archivo": (fixture, (FIXTURES / fixture).read_bytes(), "text/plain")})


def test_subir_procesa_en_background(auditor):
    r = subir(auditor)
    assert r.status_code == 200
    # TestClient ejecuta las BackgroundTasks antes de devolver el control
    det = auditor.get(f"/liquidaciones/{r.json()['id']}").json()
    assert det["estado"] == "procesada" and det["cuadra"]
    assert det["checks_ok"] > 20 and det["checks_mal"] == 0
    assert len(det["gastos"]) > 20


def test_resubir_mismo_periodo_reusa_la_fila(auditor):
    id1 = subir(auditor).json()["id"]
    id2 = subir(auditor).json()["id"]
    assert id1 == id2
    lista = auditor.get("/liquidaciones").json()
    assert len(lista) == 1 and lista[0]["periodo"] == "2026-08"


def test_periodo_invalido_422(auditor):
    assert subir(auditor, periodo="agosto").status_code == 422


def test_solo_auditor_sube(db, cliente):
    from app import admin
    admin.crear_usuario(db, "c@example.com", "C", "consejo", "clave-de-test")
    cliente.post("/auth/login", json={"email": "c@example.com", "clave": "clave-de-test"})
    assert subir(cliente).status_code == 403


def test_listar_requiere_sesion(cliente):
    assert cliente.get("/liquidaciones").status_code == 401
