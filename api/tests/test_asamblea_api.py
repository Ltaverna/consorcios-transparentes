import pytest

from app import asamblea_estado as ae
from app.config import settings


@pytest.fixture(autouse=True)
def tokens(monkeypatch):
    monkeypatch.setattr(settings, "asamblea_token", "secreto")
    monkeypatch.setattr(settings, "asamblea_mod_token", "modsecreto")


H = {"X-Asamblea-Token": "secreto"}


def _seed(db):
    s = ae.sesion_activa(db)
    ae.set_doc(db, s, {
        "mociones": [{"titulo": "M1", "opciones": ["A favor", "En contra"], "regla": "abs", "abierta": False}],
        "activa": 0, "units": [{"uf": 3, "prop": "X"}, {"uf": 4, "prop": "Y"}]})
    return s


def _abrir(db):
    s = ae.sesion_activa(db)
    doc = dict(s.doc)
    doc["mociones"][0]["abierta"] = True
    ae.set_doc(db, s, doc)


def test_estado_requiere_token(cliente):
    assert cliente.get("/asamblea/estado").status_code == 401


def test_estado_devuelve_forma(cliente, db):
    _seed(db)
    est = cliente.get("/asamblea/estado", headers=H).json()
    assert est["mociones"][0]["titulo"] == "M1"
    assert est["claims"] == {}


def test_claim_y_conflicto(cliente, db):
    _seed(db)
    r = cliente.post("/asamblea/claim", json={"device": "d1", "uf": 3, "nombre": "Juan"}, headers=H)
    assert r.status_code == 200 and r.json()["ok"] is True
    r2 = cliente.post("/asamblea/claim", json={"device": "d2", "uf": 3}, headers=H)
    assert r2.status_code == 409 and 3 in r2.json()["detail"]["conflicto"]


def test_voto_cerrada_luego_abierta(cliente, db):
    _seed(db)
    cliente.post("/asamblea/claim", json={"device": "d1", "uf": 3}, headers=H)
    assert cliente.post("/asamblea/voto", json={"device": "d1", "mocion": 0, "uf": 3, "opcion": 0},
                        headers=H).status_code == 403
    _abrir(db)
    assert cliente.post("/asamblea/voto", json={"device": "d1", "mocion": 0, "uf": 3, "opcion": 0},
                        headers=H).status_code == 200
    est = cliente.get("/asamblea/estado", headers=H).json()
    assert est["mociones"][0]["votos"] == {"3": 0}


def test_voto_no_dueno_prohibido(cliente, db):
    _seed(db)
    cliente.post("/asamblea/claim", json={"device": "d1", "uf": 3}, headers=H)
    _abrir(db)
    assert cliente.post("/asamblea/voto", json={"device": "dX", "mocion": 0, "uf": 3, "opcion": 0},
                        headers=H).status_code == 403


def test_release_permite_reclaim(cliente, db):
    _seed(db)
    cliente.post("/asamblea/claim", json={"device": "d1", "uf": 3}, headers=H)
    assert cliente.post("/asamblea/release", json={"device": "d1", "uf": 3}, headers=H).status_code == 200
    assert cliente.post("/asamblea/claim", json={"device": "d2", "uf": 3}, headers=H).json()["ok"] is True
