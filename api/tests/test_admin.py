import pytest

from app import admin, models, security


def test_init_consorcio_es_idempotente(db):
    c1 = admin.init_consorcio(db, "Rivadavia 2069", direccion="Av. Rivadavia 2069, CABA")
    c2 = admin.init_consorcio(db, "Rivadavia 2069")
    assert c1.id == c2.id
    assert db.query(models.Consorcio).count() == 1


def test_crear_usuario_y_verificar(db):
    u = admin.crear_usuario(db, "lucas@example.com", "Lucas", "auditor", "clave-larga")
    assert u.rol == "auditor"
    assert security.verificar(u.clave_hash, "clave-larga")
    with pytest.raises(ValueError):
        admin.crear_usuario(db, "x@example.com", "X", "hacker", "123")  # rol inválido


def test_generar_codigo_de_unidad(db):
    db.add(models.Unidad(uf=27, piso_depto="13-B", propietario="Alguien"))
    db.commit()
    codigo = admin.generar_codigo(db, 27)
    unidad = db.query(models.Unidad).filter_by(uf=27).one()
    assert len(codigo) == 8
    assert security.verificar(unidad.codigo_hash, codigo)
    with pytest.raises(ValueError):
        admin.generar_codigo(db, 999)  # unidad inexistente
