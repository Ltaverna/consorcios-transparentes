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
