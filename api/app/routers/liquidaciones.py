import re
import uuid
import zipfile

from fastapi import (APIRouter, BackgroundTasks, Depends, HTTPException,
                     Request, UploadFile, Form)
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from .. import ingesta, models, security
from .. import publicar as publicacion
from ..db import SessionLocal, get_db

router = APIRouter(prefix="/liquidaciones", tags=["liquidaciones"])
PERIODO = re.compile(r"^\d{4}-(0[1-9]|1[0-2])$")


def _procesar_en_background(liq_id: int, storage) -> None:
    db = SessionLocal()
    try:
        ingesta.procesar(db, liq_id, storage)
    finally:
        db.close()


@router.post("")
def subir(request: Request, tareas: BackgroundTasks, archivo: UploadFile,
          periodo: str = Form(...), db: Session = Depends(get_db),
          s: dict = Depends(security.requiere("auditor"))):
    if not PERIODO.match(periodo):
        raise HTTPException(422, "El período debe ser AAAA-MM, por ejemplo 2026-08")
    data = archivo.file.read(30 * 1024 * 1024 + 1)
    if len(data) > 30 * 1024 * 1024:
        raise HTTPException(413, "El archivo supera los 30 MB")
    storage = request.app.state.storage
    liq = db.query(models.Liquidacion).filter_by(periodo=periodo).first()
    if liq and liq.estado == "procesando":
        raise HTTPException(409, "Esa liquidación ya se está procesando; esperá a que termine")
    sufijo = ".pdf" if (archivo.filename or "").lower().endswith(".pdf") else ".txt"
    # Clave única por subida: dos subidas concurrentes del mismo período nunca pisan
    # el mismo archivo, aunque una de las dos termine perdiendo la carrera del período.
    key = f"liquidaciones/{periodo}-{uuid.uuid4().hex[:8]}{sufijo}"
    storage.guardar(key, data)
    key_anterior = liq.archivo_key if liq else None
    if not liq:
        liq = models.Liquidacion(periodo=periodo, archivo_key=key)
        db.add(liq)
        try:
            db.commit()
        except IntegrityError:
            db.rollback()
            storage.borrar(key)  # perdimos la carrera del período: no dejamos el archivo huérfano
            liq = db.query(models.Liquidacion).filter_by(periodo=periodo).first()
            if liq.estado == "procesando":
                raise HTTPException(409, "Esa liquidación ya se está procesando; esperá a que termine")
            key_anterior = liq.archivo_key
    liq.archivo_key, liq.estado, liq.error = key, "procesando", ""
    db.commit()
    if key_anterior and key_anterior != key:
        storage.borrar(key_anterior)  # limpieza best-effort del archivo reemplazado
    tareas.add_task(_procesar_en_background, liq.id, storage)
    return {"id": liq.id, "periodo": periodo, "estado": "procesando"}


@router.get("")
def listar(db: Session = Depends(get_db), s: dict = Depends(security.sesion)):
    filas = db.query(models.Liquidacion).order_by(models.Liquidacion.periodo.desc()).all()
    return [{"id": l.id, "periodo": l.periodo, "estado": l.estado, "cuadra": l.cuadra,
             "sistema": l.sistema, "error": l.error} for l in filas]


@router.get("/{liq_id}")
def detalle(liq_id: int, db: Session = Depends(get_db),
            s: dict = Depends(security.requiere("auditor", "consejo", "moderador"))):
    liq = db.get(models.Liquidacion, liq_id)
    if not liq:
        raise HTTPException(404, "No existe esa liquidación")
    checks = (liq.datos or {}).get("checks", [])
    return {
        "id": liq.id, "periodo": liq.periodo, "estado": liq.estado, "cuadra": liq.cuadra,
        "sistema": liq.sistema, "error": liq.error,
        "checks_ok": sum(1 for c in checks if c["ok"]),
        "checks_mal": sum(1 for c in checks if not c["ok"]),
        "checks": [c for c in checks if not c["ok"]],
        "totales_categoria": (liq.datos or {}).get("totales_categoria", {}),
        "gastos": [{"n": g.n, "categoria": g.categoria, "proveedor": g.proveedor,
                    "concepto": g.concepto, "columna": g.columna, "importe": g.importe,
                    "factura_nro": g.factura_nro, "pagos": g.pagos} for g in liq.gastos],
    }


@router.post("/{liq_id}/comprobantes")
def subir_comprobantes(liq_id: int, request: Request, archivo: UploadFile,
                       db: Session = Depends(get_db),
                       s: dict = Depends(security.requiere("auditor"))):
    liq = db.get(models.Liquidacion, liq_id)
    if not liq:
        raise HTTPException(404, "No existe esa liquidación")
    if liq.estado not in ("procesada", "publicada"):
        raise HTTPException(409, f"La liquidación está en estado {liq.estado}; procesarla primero")
    data = archivo.file.read(100 * 1024 * 1024 + 1)
    if len(data) > 100 * 1024 * 1024:
        raise HTTPException(413, "El ZIP supera los 100 MB")
    try:
        # sincrónico: son segundos, y así el error llega directo al auditor
        ingesta.cruzar_comprobantes(db, liq.id, data, request.app.state.storage)
    except ValueError as e:
        raise HTTPException(422, str(e))
    except zipfile.BadZipFile:
        raise HTTPException(422, "El archivo no es un ZIP válido")
    docs = db.query(models.Documento).filter_by(liquidacion_id=liq.id).count()
    cruce = db.query(models.Hallazgo).filter_by(liquidacion_id=liq.id, origen="comprobantes").count()
    return {"ok": True, "documentos": docs, "hallazgos_cruce": cruce}


@router.post("/{liq_id}/publicar")
def publicar_liquidacion(liq_id: int, request: Request, db: Session = Depends(get_db),
                         s: dict = Depends(security.requiere("auditor"))):
    liq = db.get(models.Liquidacion, liq_id)
    if not liq:
        raise HTTPException(404, "No existe esa liquidación")
    try:
        out = publicacion.publicar(db, liq.id, request.app.state.storage)
    except ValueError as e:
        raise HTTPException(409, str(e))
    return {"ok": True, **out}
