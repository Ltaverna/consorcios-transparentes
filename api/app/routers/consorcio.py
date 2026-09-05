from dataclasses import fields

from fastapi import APIRouter, Depends, File, HTTPException, Request, Response, UploadFile
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ct.rules import Config

from .. import admin, models, security
from ..db import get_db
from .documentos import _servir

router = APIRouter(tags=["consorcio"])
UMBRALES_VALIDOS = {f.name for f in fields(Config)}
# `Config` usa `from __future__ import annotations`, así que `f.type` es el string de la
# anotación ("float"/"int"), no el tipo en sí; todos los umbrales son uno de esos dos.
_TIPOS = {"float": float, "int": int}
UMBRALES_TIPO = {f.name: _TIPOS.get(f.type, float) for f in fields(Config)}

RUTA_REGLAMENTO = {"pdf": "consorcio/reglamento.pdf", "transcripcion": "consorcio/reglamento.md"}
MAX_REGLAMENTO_MB = 20


@router.get("/consorcio/reglamento")
def estado_reglamento(request: Request, s: dict = Depends(security.sesion)):
    st = request.app.state.storage
    return {tipo: st.existe(key) for tipo, key in RUTA_REGLAMENTO.items()}


@router.post("/consorcio/reglamento")
def subir_reglamento(request: Request, pdf: UploadFile | None = File(None),
                     transcripcion: UploadFile | None = File(None),
                     s: dict = Depends(security.requiere("auditor"))):
    if not pdf and not transcripcion:
        raise HTTPException(422, "Subí el PDF, la transcripción o ambos")
    st = request.app.state.storage
    tope = MAX_REGLAMENTO_MB * 1024 * 1024
    for archivo, tipo in ((pdf, "pdf"), (transcripcion, "transcripcion")):
        if not archivo:
            continue
        data = archivo.file.read(tope + 1)
        if len(data) > tope:
            raise HTTPException(413, f"El archivo supera los {MAX_REGLAMENTO_MB} MB")
        st.guardar(RUTA_REGLAMENTO[tipo], data)
    return {"ok": True, **{t: st.existe(k) for t, k in RUTA_REGLAMENTO.items()}}


@router.get("/consorcio/reglamento/{tipo}")
def ver_reglamento(tipo: str, request: Request, s: dict = Depends(security.sesion)):
    key = RUTA_REGLAMENTO.get(tipo)
    if not key:
        raise HTTPException(404, "No existe ese tipo de documento")
    st = request.app.state.storage
    if not st.existe(key):
        raise HTTPException(404, "El reglamento todavía no está cargado")
    if tipo == "pdf":
        return _servir(request, key)  # descarga forzada, local o R2
    # La transcripción se sirve directa (sin redirect a R2): el front la lee con fetch y es chica.
    return Response(st.leer(key), media_type="text/markdown; charset=utf-8",
                    headers={"X-Content-Type-Options": "nosniff"})


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
        umbrales, invalidos = {}, []
        for clave, valor in cambio.umbrales.items():
            tipo = UMBRALES_TIPO[clave]
            if valor is None or isinstance(valor, bool):
                invalidos.append(clave)
                continue
            try:
                umbrales[clave] = tipo(valor)
            except (TypeError, ValueError):
                invalidos.append(clave)
        if invalidos:
            raise HTTPException(422, f"Umbrales con un valor no numérico: {', '.join(sorted(invalidos))}")
        c.umbrales = umbrales
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
