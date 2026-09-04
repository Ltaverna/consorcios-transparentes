import pathlib

import pytest
from fastapi.testclient import TestClient

from app import admin, security
from app.db import Base, SessionLocal, engine, get_db
from app.storage import LocalStorage

FIXTURES = pathlib.Path(__file__).resolve().parents[2] / "engine" / "tests" / "fixtures"


@pytest.fixture()
def db():
    Base.metadata.create_all(engine)
    s = SessionLocal()
    yield s
    s.close()
    Base.metadata.drop_all(engine)


@pytest.fixture()
def cliente(db, tmp_path):
    from app.main import app
    app.dependency_overrides[get_db] = lambda: db
    app.state.storage = LocalStorage(str(tmp_path))
    with TestClient(app) as c:
        security.limiter_login._hits.clear()
        yield c
    app.dependency_overrides.clear()


@pytest.fixture()
def auditor(db, cliente):
    admin.crear_usuario(db, "auditor@example.com", "Auditor", "auditor", "clave-de-test")
    r = cliente.post("/auth/login", json={"email": "auditor@example.com", "clave": "clave-de-test"})
    assert r.status_code == 200
    return cliente  # el cliente conserva la cookie
