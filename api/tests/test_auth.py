from app import admin, models, security


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


def test_rate_limit_por_ip_del_proxy(db, cliente, monkeypatch):
    from app.config import settings
    from app import security
    monkeypatch.setattr(settings, "confiar_proxy", True)
    security.limiter_login._hits.clear()
    for i in range(10):
        cliente.post("/auth/login", json={"email": "x@example.com", "clave": "mala-clave"},
                     headers={"CF-Connecting-IP": "200.1.1.1"})
    r = cliente.post("/auth/login", json={"email": "x@example.com", "clave": "mala-clave"},
                     headers={"CF-Connecting-IP": "200.1.1.1"})
    assert r.status_code == 429
    r2 = cliente.post("/auth/login", json={"email": "x@example.com", "clave": "mala-clave"},
                      headers={"CF-Connecting-IP": "200.2.2.2"})
    assert r2.status_code == 401  # otra IP real → otro bucket


def test_login_google_sin_configurar_da_404(db, cliente):
    r = cliente.post("/auth/login-google", json={"credential": "x"})
    assert r.status_code == 404


def test_login_google_sin_alta_da_403(db, cliente, monkeypatch):
    from app.config import settings
    monkeypatch.setattr(settings, "google_client_id", "cid-test")
    monkeypatch.setattr(security, "verificar_id_token_google", lambda c: "desconocido@gmail.com")
    r = cliente.post("/auth/login-google", json={"credential": "tok"})
    assert r.status_code == 403


def test_login_google_con_alta_entra(db, cliente, monkeypatch):
    from app.config import settings
    monkeypatch.setattr(settings, "google_client_id", "cid-test")
    monkeypatch.setattr(security, "verificar_id_token_google", lambda c: "consejo@example.com")
    admin.crear_usuario(db, "consejo@example.com", "Vecina", "consejo", "clave-de-test")
    r = cliente.post("/auth/login-google", json={"credential": "tok"})
    assert r.status_code == 200
    assert r.json() == {"rol": "consejo", "nombre": "Vecina"}
    assert security.COOKIE in r.cookies


def test_validar_mcp_token_vigente_revocado_e_inexistente(db, cliente):
    token = admin.crear_mcp_token(db, "lucas")
    r = cliente.post("/auth/mcp-token/validar", json={"token": token})
    assert r.status_code == 200
    assert r.json() == {"valido": True, "nombre": "lucas"}
    # Revocado e inexistente responden EXACTAMENTE igual: no se revela si el token existió
    admin.revocar_mcp_token(db, "lucas")
    r_revocado = cliente.post("/auth/mcp-token/validar", json={"token": token})
    r_inexistente = cliente.post("/auth/mcp-token/validar", json={"token": "no-existe"})
    assert r_revocado.status_code == r_inexistente.status_code == 200
    assert r_revocado.json() == r_inexistente.json() == {"valido": False, "nombre": None}


def test_validar_mcp_token_rate_limit(db, cliente):
    # limiter_mcp_token tiene techo de 60 (no 10 como limiter_login): cubre estampidas
    # de cache fría del contenedor MCP que comparte IP con todos los tokens de tabla.
    for _ in range(60):
        cliente.post("/auth/mcp-token/validar", json={"token": "cualquiera"})
    r = cliente.post("/auth/mcp-token/validar", json={"token": "cualquiera"})
    assert r.status_code == 429


def test_cookie_con_dominio_configurado(db, cliente, monkeypatch):
    from app.config import settings
    from app import admin
    monkeypatch.setattr(settings, "cookie_dominio", ".neuralcore.dev")
    admin.crear_usuario(db, "d@example.com", "D", "auditor", "clave-de-test")
    r = cliente.post("/auth/login", json={"email": "d@example.com", "clave": "clave-de-test"})
    assert "domain=.neuralcore.dev" in r.headers.get("set-cookie", "").lower()
