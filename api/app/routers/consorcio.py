from dataclasses import fields

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ct.rules import Config

from .. import admin, models, security
from ..db import get_db

router = APIRouter(tags=["consorcio"])
UMBRALES_VALIDOS = {f.name for f in fields(Config)}


class CambioConsorcio(BaseModel):
    nombre: str | None = None
    direccion: str | None = None
    cuit: str | None = None
    admin_nombre: str | None = None
    admin_cuit: str | None = None
    marca: str | None = None
    umbrales: dict | None = None


@router.get("/consorcio")
def ver(db: Session = Depends(get_db),
        s: dict = Depends(security.requiere("auditor", "consejo", "moderador"))):
    c = db.query(models.Consorcio).first()
    if not c:
        raise HTTPException(404, "Inicializar el consorcio primero (cli.py init)")
    return {"nombre": c.nombre, "direccion": c.direccion, "cuit": c.cuit,
            "admin_nombre": c.admin_nombre, "admin_cuit": c.admin_cuit,
            "marca": c.marca, "umbrales": c.umbrales,
            "umbrales_default": {f.name: getattr(Config(), f.name) for f in fields(Config)}}


@router.put("/consorcio")
def editar(cambio: CambioConsorcio, db: Session = Depends(get_db),
           s: dict = Depends(security.requiere("auditor"))):
    c = db.query(models.Consorcio).first()
    if not c:
        raise HTTPException(404, "Inicializar el consorcio primero (cli.py init)")
    if cambio.umbrales is not None:
        raros = set(cambio.umbrales) - UMBRALES_VALIDOS
        if raros:
            raise HTTPException(422, f"Umbrales desconocidos: {', '.join(sorted(raros))}")
        c.umbrales = cambio.umbrales
    for campo in ("nombre", "direccion", "cuit", "admin_nombre", "admin_cuit", "marca"):
        valor = getattr(cambio, campo)
        if valor is not None:
            setattr(c, campo, valor)
    db.commit()
    return {"ok": True}


@router.get("/unidades")
def unidades(db: Session = Depends(get_db),
             s: dict = Depends(security.requiere("auditor", "consejo"))):
    return [{"uf": u.uf, "piso_depto": u.piso_depto, "tipo": u.tipo,
             "propietario": u.propietario, "tiene_codigo": u.codigo_hash is not None}
            for u in db.query(models.Unidad).order_by(models.Unidad.uf)]


@router.post("/unidades/{uf}/codigo")
def codigo(uf: int, db: Session = Depends(get_db),
           s: dict = Depends(security.requiere("auditor"))):
    try:
        return {"uf": uf, "codigo": admin.generar_codigo(db, uf)}
    except ValueError as e:
        raise HTTPException(404, str(e))
