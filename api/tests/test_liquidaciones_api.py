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


def test_subida_demasiado_grande_413(auditor):
    r = auditor.post("/liquidaciones", data={"periodo": "2026-08"},
                     files={"archivo": ("x.txt", b"x" * (30 * 1024 * 1024 + 1), "text/plain")})
    assert r.status_code == 413


def test_resubir_mientras_procesa_409(db, auditor):
    from app import models
    liq = models.Liquidacion(periodo="2026-06", archivo_key="liquidaciones/2026-06.txt", estado="procesando")
    db.add(liq)
    db.commit()
    r = auditor.post("/liquidaciones", data={"periodo": "2026-06"},
                     files={"archivo": ("x.txt", b"da igual", "text/plain")})
    assert r.status_code == 409


def test_cada_subida_usa_clave_de_storage_propia(db, auditor):
    from app import models
    subir(auditor)
    key1 = db.query(models.Liquidacion).filter_by(periodo="2026-08").one().archivo_key
    subir(auditor)
    db.expire_all()
    key2 = db.query(models.Liquidacion).filter_by(periodo="2026-08").one().archivo_key
    assert key1 != key2 and key2.startswith("liquidaciones/2026-08-")
