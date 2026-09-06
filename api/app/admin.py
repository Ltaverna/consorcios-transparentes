"""Altas administrativas: consorcio, usuarios, códigos de acceso y tokens del MCP."""
import hashlib
import secrets

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from . import models, security

ROLES = ("auditor", "consejo", "moderador")
# Sin 0/O/1/I para poder dictarlo por teléfono
ALFABETO = "23456789abcdefghjkmnpqrstuvwxyz"


def init_consorcio(db: Session, nombre: str, **campos) -> models.Consorcio:
    c = db.query(models.Consorcio).first()
    if not c:
        c = models.Consorcio(nombre=nombre, **campos)
        db.add(c)
        db.commit()
    return c


def crear_usuario(db: Session, email: str, nombre: str, rol: str, clave: str) -> models.Usuario:
    if len(clave) < 8:
        raise ValueError("La clave debe tener al menos 8 caracteres")
    if rol not in ROLES:
        raise ValueError(f"Rol inválido: {rol}. Válidos: {', '.join(ROLES)}")
    u = models.Usuario(email=email.lower(), nombre=nombre, rol=rol, clave_hash=security.hashear(clave))
    db.add(u)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise ValueError(f"Ya existe un usuario con el email {email}")
    return u


def generar_codigo(db: Session, uf: int) -> str:
    unidad = db.query(models.Unidad).filter_by(uf=uf).first()
    if not unidad:
        raise ValueError(f"No existe la unidad UF {uf}")
    codigo = "".join(secrets.choice(ALFABETO) for _ in range(8))
    unidad.codigo_hash = security.hashear(codigo)
    db.commit()
    return codigo  # se muestra una sola vez; solo queda el hash


def crear_mcp_token(db: Session, nombre: str) -> str:
    """Genera el token de acceso al MCP para `nombre` y guarda solo el hash."""
    token = secrets.token_urlsafe(24)
    db.add(models.McpToken(nombre=nombre,
                           token_sha256=hashlib.sha256(token.encode()).hexdigest()))
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise ValueError(f"Ya existe un token MCP con el nombre {nombre}")
    return token  # se muestra una sola vez; solo queda el hash


def revocar_mcp_token(db: Session, nombre: str) -> None:
    t = db.query(models.McpToken).filter_by(nombre=nombre).first()
    if not t:
        raise ValueError(f"No existe un token MCP con el nombre {nombre}")
    t.activo = False
    db.commit()


def listar_mcp_tokens(db: Session) -> list[models.McpToken]:
    return db.query(models.McpToken).order_by(models.McpToken.nombre).all()
