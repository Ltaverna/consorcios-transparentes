import pytest
from fastapi import HTTPException

from app import security


def test_hash_y_verificacion():
    h = security.hashear("secreto")
    assert security.verificar(h, "secreto")
    assert not security.verificar(h, "otro")
    assert not security.verificar("basura-no-hash", "secreto")


def test_token_ida_y_vuelta():
    tok = security.crear_token("u:1", "auditor")
    datos = security.leer_token(tok)
    assert datos == {"sub": "u:1", "rol": "auditor"}


def test_token_invalido():
    with pytest.raises(HTTPException):
        security.leer_token("no.es.jwt")


def test_rate_limiter():
    rl = security.RateLimiter(maximo=3, ventana=60)
    assert all(rl.permitir("ip") for _ in range(3))
    assert not rl.permitir("ip")
    assert rl.permitir("otra-ip")


def test_rate_limiter_desaloja_claves_vencidas():
    rl = security.RateLimiter(maximo=2, ventana=0)  # todo vence al instante
    rl.permitir("ip-1")
    rl.permitir("ip-2")
    rl.permitir("ip-3")
    assert len(rl._hits) <= 1  # las claves vencidas no se acumulan


def test_ip_cliente_sin_proxy_usa_client_host():
    from unittest.mock import Mock
    req = Mock()
    req.client.host = "1.2.3.4"
    req.headers = {"cf-connecting-ip": "9.9.9.9"}
    assert security.ip_cliente(req) == "1.2.3.4"  # sin flag, ignora el header


def test_ip_cliente_con_proxy_usa_cf_connecting_ip(monkeypatch):
    from unittest.mock import Mock
    from app.config import settings
    monkeypatch.setattr(settings, "confiar_proxy", True)
    req = Mock()
    req.client.host = "10.0.0.1"
    req.headers = {"cf-connecting-ip": "181.30.1.2"}
    assert security.ip_cliente(req) == "181.30.1.2"
    req.headers = {}
    assert security.ip_cliente(req) == "10.0.0.1"  # con flag pero sin header, fallback
