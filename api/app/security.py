"""Hashes (argon2), JWT en cookie httpOnly, dependencias de rol y rate limit simple."""
import time
from datetime import datetime, timedelta, timezone

import jwt
from argon2 import PasswordHasher
from fastapi import Depends, HTTPException, Request

from .config import settings

COOKIE = "ct_sesion"
_ph = PasswordHasher()


def hashear(secreto: str) -> str:
    return _ph.hash(secreto)


def verificar(hash_: str, secreto: str) -> bool:
    try:
        return _ph.verify(hash_, secreto)
    except Exception:
        return False


def crear_token(sub: str, rol: str) -> str:
    exp = datetime.now(timezone.utc) + timedelta(hours=settings.jwt_horas)
    return jwt.encode({"sub": sub, "rol": rol, "exp": exp}, settings.jwt_secret, algorithm="HS256")


def leer_token(token: str) -> dict:
    try:
        d = jwt.decode(token, settings.jwt_secret, algorithms=["HS256"])
        return {"sub": d["sub"], "rol": d["rol"]}
    except Exception:
        raise HTTPException(401, "Sesión inválida o vencida")


def sesion(request: Request) -> dict:
    token = request.cookies.get(COOKIE)
    if not token:
        raise HTTPException(401, "Hay que iniciar sesión")
    return leer_token(token)


def requiere(*roles: str):
    def dep(s: dict = Depends(sesion)) -> dict:
        if s["rol"] not in roles:
            raise HTTPException(403, "No autorizado para esta acción")
        return s
    return dep


class RateLimiter:
    """Ventana deslizante en memoria. Alcanza para un proceso único (etapa 1)."""

    def __init__(self, maximo: int = 10, ventana: int = 300):
        self.maximo, self.ventana = maximo, ventana
        self._hits: dict[str, list[float]] = {}

    def permitir(self, clave: str) -> bool:
        ahora = time.monotonic()
        hits = [t for t in self._hits.get(clave, []) if ahora - t < self.ventana]
        if len(hits) >= self.maximo:
            self._hits[clave] = hits
            return False
        hits.append(ahora)
        self._hits[clave] = hits
        return True


limiter_login = RateLimiter()
