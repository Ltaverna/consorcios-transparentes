"""Altas administrativas: consorcio, usuarios y códigos de acceso por unidad."""
import secrets

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
    if rol not in ROLES:
        raise ValueError(f"Rol inválido: {rol}. Válidos: {', '.join(ROLES)}")
    u = models.Usuario(email=email.lower(), nombre=nombre, rol=rol, clave_hash=security.hashear(clave))
    db.add(u)
    db.commit()
    return u


def generar_codigo(db: Session, uf: int) -> str:
    unidad = db.query(models.Unidad).filter_by(uf=uf).first()
    if not unidad:
        raise ValueError(f"No existe la unidad UF {uf}")
    codigo = "".join(secrets.choice(ALFABETO) for _ in range(8))
    unidad.codigo_hash = security.hashear(codigo)
    db.commit()
    return codigo  # se muestra una sola vez; solo queda el hash
