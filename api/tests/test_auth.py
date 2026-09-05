from app import admin, models


def test_login_y_yo(auditor):
    r = auditor.get("/auth/yo")
    assert r.status_code == 200
    assert r.json()["rol"] == "auditor"
    assert r.json()["nombre"] == "Auditor"


def test_login_clave_incorrecta(db, cliente):
    admin.crear_usuario(db, "a@example.com", "A", "auditor", "correcta-larga")
    r = cliente.post("/auth/login", json={"email": "a@example.com", "clave": "incorrecta"})
    assert r.status_code == 401


def test_sin_sesion_401(cliente):
    assert cliente.get("/auth/yo").status_code == 401


def test_login_unidad(db, cliente):
    db.add(models.Unidad(uf=27, piso_depto="13-B"))
    db.commit()
    codigo = admin.generar_codigo(db, 27)
    r = cliente.post("/auth/login-unidad", json={"uf": 27, "codigo": codigo})
    assert r.status_code == 200
    yo = cliente.get("/auth/yo").json()
    assert yo["rol"] == "propietario" and yo["uf"] == 27


def test_login_unidad_codigo_malo(db, cliente):
    db.add(models.Unidad(uf=27))
    db.commit()
    admin.generar_codigo(db, 27)
    assert cliente.post("/auth/login-unidad", json={"uf": 27, "codigo": "malo1234"}).status_code == 401


def test_salir(auditor):
    auditor.post("/auth/salir")
    assert auditor.get("/auth/yo").status_code == 401


def test_login_rate_limit_429(db, cliente):
    admin.crear_usuario(db, "r@example.com", "R", "auditor", "clave-larga-1")
    for _ in range(10):
        cliente.post("/auth/login", json={"email": "r@example.com", "clave": "mala"})
    r = cliente.post("/auth/login", json={"email": "r@example.com", "clave": "clave-larga-1"})
    assert r.status_code == 429


def test_cookie_con_dominio_configurado(db, cliente, monkeypatch):
    from app.config import settings
    from app import admin
    monkeypatch.setattr(settings, "cookie_dominio", ".neuralcore.dev")
    admin.crear_usuario(db, "d@example.com", "D", "auditor", "clave-de-test")
    r = cliente.post("/auth/login", json={"email": "d@example.com", "clave": "clave-de-test"})
    assert "domain=.neuralcore.dev" in r.headers.get("set-cookie", "").lower()
