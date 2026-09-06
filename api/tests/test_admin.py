import hashlib

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


def test_crear_usuario_email_duplicado(db):
    admin.crear_usuario(db, "a@example.com", "A", "auditor", "clave-larga")
    with pytest.raises(ValueError):
        admin.crear_usuario(db, "A@example.com", "Otro", "consejo", "clave-larga")


def test_crear_usuario_clave_corta(db):
    with pytest.raises(ValueError):
        admin.crear_usuario(db, "b@example.com", "B", "auditor", "corta")


def test_codigo_dentro_del_alfabeto(db):
    db.add(models.Unidad(uf=1))
    db.commit()
    assert set(admin.generar_codigo(db, 1)) <= set(admin.ALFABETO)


def test_mcp_token_crear_revocar_listar(db):
    token = admin.crear_mcp_token(db, "lucas")
    assert len(token) >= 32  # token_urlsafe(24)
    fila = db.query(models.McpToken).filter_by(nombre="lucas").one()
    assert fila.activo
    # En la base queda solo el hash, nunca el token en claro
    assert fila.token_sha256 == hashlib.sha256(token.encode()).hexdigest()
    with pytest.raises(ValueError):
        admin.crear_mcp_token(db, "lucas")  # nombre duplicado
    admin.crear_mcp_token(db, "amigo-juan")
    admin.revocar_mcp_token(db, "lucas")
    filas = admin.listar_mcp_tokens(db)
    assert [(f.nombre, f.activo) for f in filas] == [("amigo-juan", True), ("lucas", False)]
    with pytest.raises(ValueError):
        admin.revocar_mcp_token(db, "nadie")


def test_cli_mcp_token_smoke(db, monkeypatch, capsys):
    """Los subcomandos mcp-token del CLI contra la base de tests (StaticPool compartido)."""
    import cli

    monkeypatch.setattr("sys.argv", ["ct-api", "mcp-token", "crear", "lucas"])
    assert cli.main() == 0
    out = capsys.readouterr().out
    assert "https://mcp-consorcio.neuralcore.dev/mcp/" in out
    assert "no se vuelve a mostrar" in out

    monkeypatch.setattr("sys.argv", ["ct-api", "mcp-token", "listar"])
    assert cli.main() == 0
    out = capsys.readouterr().out
    assert "lucas" in out and "activo" in out
    hash_ = db.query(models.McpToken).filter_by(nombre="lucas").one().token_sha256
    assert hash_ not in out  # listar jamás muestra hashes

    monkeypatch.setattr("sys.argv", ["ct-api", "mcp-token", "revocar", "lucas"])
    assert cli.main() == 0
    monkeypatch.setattr("sys.argv", ["ct-api", "mcp-token", "listar"])
    assert cli.main() == 0
    assert "revocado" in capsys.readouterr().out

    monkeypatch.setattr("sys.argv", ["ct-api", "mcp-token", "revocar", "nadie"])
    assert cli.main() == 1  # inexistente: error legible, no traceback
