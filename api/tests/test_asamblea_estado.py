import pytest
from sqlalchemy.exc import IntegrityError

from app.models import AsambleaSesion, AsambleaClaim, AsambleaVoto
from app import asamblea_estado as ae


def test_modelos_crean_filas(db):
    s = AsambleaSesion(titulo="Asamblea test", doc={"mociones": []}, version=1)
    db.add(s)
    db.flush()
    db.add(AsambleaClaim(sesion_id=s.id, uf=3, device_id="dev-1", rol="titular"))
    db.add(AsambleaVoto(sesion_id=s.id, mocion_idx=0, uf=3, opcion_idx=1, device_id="dev-1"))
    db.commit()
    assert db.query(AsambleaClaim).filter_by(sesion_id=s.id, uf=3).one().device_id == "dev-1"
    assert db.query(AsambleaVoto).filter_by(sesion_id=s.id, uf=3).one().opcion_idx == 1


def test_claim_uf_es_unico(db):
    s = AsambleaSesion(titulo="t", doc={}, version=1)
    db.add(s); db.flush()
    db.add(AsambleaClaim(sesion_id=s.id, uf=5, device_id="a", rol="titular")); db.commit()
    db.add(AsambleaClaim(sesion_id=s.id, uf=5, device_id="b", rol="titular"))
    with pytest.raises(IntegrityError):
        db.commit()


def test_voto_mocion_uf_es_unico(db):
    s = AsambleaSesion(titulo="t", doc={}, version=1)
    db.add(s); db.flush()
    db.add(AsambleaVoto(sesion_id=s.id, mocion_idx=0, uf=7, opcion_idx=1, device_id="a")); db.commit()
    db.add(AsambleaVoto(sesion_id=s.id, mocion_idx=0, uf=7, opcion_idx=0, device_id="b"))
    with pytest.raises(IntegrityError):
        db.commit()


def test_sesion_activa_es_singleton(db):
    s1 = ae.sesion_activa(db)
    s2 = ae.sesion_activa(db)
    assert s1.id == s2.id


def test_ensamblar_estado_forma_compatible(db):
    s = ae.sesion_activa(db)
    s.doc = {"mociones": [{"titulo": "M1", "opciones": ["A", "B"], "regla": "abs", "abierta": True}],
             "activa": 0, "agenda": {}, "palabra": [], "respuestas": {}, "objeciones": {}, "cumplimiento": {},
             "units": [{"uf": 3, "prop": "X"}, {"uf": 4, "prop": "X"}, {"uf": 5, "prop": "Y"}]}
    db.add(AsambleaClaim(sesion_id=s.id, uf=3, device_id="d", rol="titular", presente=True))
    db.add(AsambleaVoto(sesion_id=s.id, mocion_idx=0, uf=3, opcion_idx=1, device_id="d"))
    db.commit()
    est = ae.ensamblar_estado(db, s)
    assert est["presentes"] == {"3": True}
    assert est["mociones"][0]["votos"] == {"3": 1}
    assert est["mociones"][0]["abierta"] is True
    assert est["claims"]["3"]["rol"] == "titular"
    assert "version" in est


def test_reclamar_bloquea_y_rechaza_conflicto(db):
    s = ae.sesion_activa(db)
    s.doc = {"units": [{"uf": 3, "prop": "X"}]}
    db.commit()
    r = ae.reclamar(db, s, device="d1", uf=3, representados=[], nombre="Juan")
    assert r["ok"] is True
    r2 = ae.reclamar(db, s, device="d2", uf=3, representados=[], nombre="Otro")
    assert r2["ok"] is False and 3 in r2["conflicto"]


def test_reclamar_tope_cinco_propietarios(db):
    s = ae.sesion_activa(db)
    s.doc = {"units": [{"uf": i, "prop": f"P{i}"} for i in range(1, 8)]}
    db.commit()
    r = ae.reclamar(db, s, device="d", uf=1, representados=[2, 3, 4, 5, 6], nombre="M")
    assert r["ok"] is True
    r2 = ae.reclamar(db, s, device="d", uf=1, representados=[2, 3, 4, 5, 6, 7], nombre="M")
    assert r2["ok"] is False and r2.get("motivo")


def test_reclamar_condominio_cuenta_uno(db):
    s = ae.sesion_activa(db)
    s.doc = {"units": [{"uf": 1, "prop": "M"},
                       {"uf": 2, "prop": "A"}, {"uf": 3, "prop": "B"}, {"uf": 4, "prop": "C"},
                       {"uf": 5, "prop": "D"}, {"uf": 6, "prop": "Z"}, {"uf": 7, "prop": "Z"},
                       {"uf": 8, "prop": "Z"}]}
    db.commit()
    r = ae.reclamar(db, s, device="d", uf=1, representados=[2, 3, 4, 5, 6, 7, 8], nombre="M")
    assert r["ok"] is True


def test_votar_requiere_ventana_abierta_y_dueno(db):
    s = ae.sesion_activa(db)
    s.doc = {"mociones": [{"titulo": "M", "opciones": ["A", "B"], "regla": "abs", "abierta": False}],
             "units": [{"uf": 3, "prop": "X"}]}
    db.commit()
    ae.reclamar(db, s, device="d1", uf=3, representados=[], nombre="J")
    assert ae.votar(db, s, device="d1", mocion=0, uf=3, opcion=1)["ok"] is False  # cerrada
    s.doc["mociones"][0]["abierta"] = True
    ae.set_doc(db, s, s.doc)
    assert ae.votar(db, s, device="d1", mocion=0, uf=3, opcion=1)["ok"] is True   # ok
    assert ae.votar(db, s, device="dX", mocion=0, uf=3, opcion=0)["ok"] is False  # no dueño


def test_reclamar_reemplaza_conjunto_del_device(db):
    s = ae.sesion_activa(db)
    s.doc = {"units": [{"uf": i, "prop": f"P{i}"} for i in range(1, 11)]}
    db.commit()
    assert ae.reclamar(db, s, device="d", uf=1, representados=[2, 3, 4, 5], nombre="M")["ok"] is True
    # segunda llamada: libera 2-5, toma 6-9; no acumula ni excede el tope
    assert ae.reclamar(db, s, device="d", uf=1, representados=[6, 7, 8, 9], nombre="M")["ok"] is True
    ufs = {c.uf for c in db.query(AsambleaClaim).filter_by(sesion_id=s.id, device_id="d").all()}
    assert ufs == {1, 6, 7, 8, 9}
    # 6 propietarios distintos sigue rechazado
    assert ae.reclamar(db, s, device="d", uf=1, representados=[2, 3, 4, 5, 6, 7], nombre="M")["ok"] is False


def test_votar_null_borra_el_voto(db):
    s = ae.sesion_activa(db)
    s.doc = {"mociones": [{"titulo": "M", "opciones": ["A", "B"], "regla": "abs", "abierta": True}],
             "units": [{"uf": 3, "prop": "X"}]}
    db.commit()
    ae.reclamar(db, s, device="d1", uf=3, representados=[], nombre="J")
    assert ae.votar(db, s, device="d1", mocion=0, uf=3, opcion=1)["ok"] is True
    assert ae.ensamblar_estado(db, s)["mociones"][0]["votos"] == {"3": 1}
    assert ae.votar(db, s, device="d1", mocion=0, uf=3, opcion=None)["ok"] is True
    assert ae.ensamblar_estado(db, s)["mociones"][0]["votos"] == {}


def test_ensamblar_mandatario_va_a_poderes_no_presentes(db):
    s = ae.sesion_activa(db)
    s.doc = {"units": [{"uf": 1, "prop": "M"}, {"uf": 2, "prop": "A"}]}
    db.commit()
    # device d: uf1 titular (presente) + uf2 representada (mandatario)
    ae.reclamar(db, s, device="d", uf=1, representados=[2], nombre="Mandatario")
    est = ae.ensamblar_estado(db, s)
    assert est["presentes"] == {"1": True}            # solo el titular
    assert est["poderes"] == {"2": "Mandatario"}       # la representada va a poderes
    assert "2" not in est["presentes"]                 # no duplicada
