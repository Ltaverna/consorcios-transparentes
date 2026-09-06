import hashlib

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel
from sqlalchemy.orm import Session

from .. import models, security
from ..config import settings
from ..db import get_db

router = APIRouter(prefix="/auth", tags=["auth"])

_DUMMY_HASH = security.hashear("dummy-para-tiempos-constantes")


class LoginUsuario(BaseModel):
    email: str
    clave: str


class LoginUnidad(BaseModel):
    uf: int
    codigo: str


class LoginGoogle(BaseModel):
    credential: str


class TokenMcp(BaseModel):
    token: str


def _entrar(response: Response, sub: str, rol: str) -> None:
    response.set_cookie(security.COOKIE, security.crear_token(sub, rol), httponly=True,
                        samesite="lax", secure=settings.cookie_segura,
                        domain=settings.cookie_dominio or None,
                        max_age=settings.jwt_horas * 3600)


@router.post("/login")
def login(datos: LoginUsuario, request: Request, response: Response, db: Session = Depends(get_db)):
    if not security.limiter_login.permitir(f"{security.ip_cliente(request)}|{datos.email.lower()}"):
        raise HTTPException(429, "Demasiados intentos; probá de nuevo en unos minutos")
    u = db.query(models.Usuario).filter_by(email=datos.email.lower()).first()
    ok = security.verificar(u.clave_hash if u else _DUMMY_HASH, datos.clave)
    if not u or not ok:
        raise HTTPException(401, "Email o clave incorrectos")
    _entrar(response, f"u:{u.id}", u.rol)
    return {"rol": u.rol, "nombre": u.nombre}


@router.post("/login-unidad")
def login_unidad(datos: LoginUnidad, request: Request, response: Response, db: Session = Depends(get_db)):
    if not security.limiter_login.permitir(f"{security.ip_cliente(request)}|uf:{datos.uf}"):
        raise HTTPException(429, "Demasiados intentos; probá de nuevo en unos minutos")
    unidad = db.query(models.Unidad).filter_by(uf=datos.uf).first()
    hash_ = unidad.codigo_hash if unidad and unidad.codigo_hash else _DUMMY_HASH
    ok = security.verificar(hash_, datos.codigo)
    if not unidad or not unidad.codigo_hash or not ok:
        raise HTTPException(401, "Unidad o código incorrectos")
    _entrar(response, f"uf:{unidad.uf}", "propietario")
    return {"rol": "propietario", "uf": unidad.uf, "piso_depto": unidad.piso_depto}


@router.post("/login-google")
def login_google(datos: LoginGoogle, request: Request, response: Response, db: Session = Depends(get_db)):
    if not settings.google_client_id:
        raise HTTPException(404, "SSO de Google no configurado")
    # bucket único por IP (no por email como el login con clave): más estricto, alcanza para un equipo chico
    if not security.limiter_login.permitir(f"{security.ip_cliente(request)}|google"):
        raise HTTPException(429, "Demasiados intentos; probá de nuevo en unos minutos")
    email = security.verificar_id_token_google(datos.credential)
    u = db.query(models.Usuario).filter_by(email=email).first()
    if not u:
        raise HTTPException(403, "Esa cuenta no tiene acceso; pedile al auditor que te dé de alta")
    _entrar(response, f"u:{u.id}", u.rol)
    return {"rol": u.rol, "nombre": u.nombre}


@router.post("/mcp-token/validar")
def validar_mcp_token(datos: TokenMcp, request: Request, db: Session = Depends(get_db)):
    """Valida un token de acceso al MCP. Sin sesión: solo confirma un secreto que el
    llamador ya posee. Inexistente y revocado responden exactamente igual: no se
    revela si el token existió."""
    if not security.limiter_mcp_token.permitir(f"{security.ip_cliente(request)}|mcp-token"):
        raise HTTPException(429, "Demasiados intentos; probá de nuevo en unos minutos")
    hash_ = hashlib.sha256(datos.token.encode()).hexdigest()
    t = db.query(models.McpToken).filter_by(token_sha256=hash_, activo=True).first()
    if not t:
        return {"valido": False, "nombre": None}
    return {"valido": True, "nombre": t.nombre}


@router.post("/salir")
def salir(response: Response):
    response.delete_cookie(security.COOKIE, samesite="lax", secure=settings.cookie_segura,
                           domain=settings.cookie_dominio or None)
    return {"ok": True}


@router.get("/yo")
def yo(s: dict = Depends(security.sesion), db: Session = Depends(get_db)):
    out = {"rol": s["rol"]}
    if s["sub"].startswith("uf:"):
        out["uf"] = int(s["sub"][3:])
    elif s["sub"].startswith("u:"):
        u = db.query(models.Usuario).filter_by(id=int(s["sub"][2:])).first()
        out["nombre"] = u.nombre if u else ""
    return out
