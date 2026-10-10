import pytest
from sqlalchemy.exc import IntegrityError

from app.models import AsambleaSesion, AsambleaClaim, AsambleaVoto


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
