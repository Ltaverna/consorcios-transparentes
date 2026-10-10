import os

from fastapi import APIRouter, Body, Depends, File, Header, HTTPException, UploadFile
from sqlalchemy.orm import Session

from .. import asamblea_estado as ae
from .. import convocatoria
from ..config import settings
from ..db import get_db

router = APIRouter(tags=["asamblea"])
MAX_MB = 15
EXT_OK = {".pdf", ".doc", ".docx"}


@router.post("/asamblea/convocatoria")
def convocatoria_a_mociones(archivo: UploadFile = File(...),
                            x_asamblea_token: str | None = Header(default=None)):
    if not settings.asamblea_token or x_asamblea_token != settings.asamblea_token:
        raise HTTPException(401, "Token inválido")
    ext = os.path.splitext(archivo.filename or "")[1].lower()
    if ext not in EXT_OK:
        raise HTTPException(400, "Formato no soportado; subí PDF, DOC o DOCX")
    data = archivo.file.read(MAX_MB * 1024 * 1024 + 1)
    if len(data) > MAX_MB * 1024 * 1024:
        raise HTTPException(413, f"El archivo supera los {MAX_MB} MB")
    try:
        return convocatoria.proponer_mociones(data, archivo.filename)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(502, f"No se pudo procesar la convocatoria: {e}")


def _auth(x_asamblea_token: str | None):
    if not settings.asamblea_token or x_asamblea_token != settings.asamblea_token:
        raise HTTPException(401, "Token inválido")


@router.get("/asamblea/estado")
def estado(desde: int | None = None, x_asamblea_token: str | None = Header(default=None),
           db: Session = Depends(get_db)):
    _auth(x_asamblea_token)
    s = ae.sesion_activa(db)
    if desde is not None and s.version <= desde:
        return {"sin_cambios": True, "version": s.version}
    return ae.ensamblar_estado(db, s)


@router.post("/asamblea/claim")
def claim(payload: dict = Body(...), x_asamblea_token: str | None = Header(default=None),
          db: Session = Depends(get_db)):
    _auth(x_asamblea_token)
    s = ae.sesion_activa(db)
    r = ae.reclamar(db, s, device=payload["device"], uf=int(payload["uf"]),
                    representados=payload.get("representados", []), nombre=payload.get("nombre", ""))
    if not r["ok"] and "conflicto" in r:
        raise HTTPException(409, detail=r)
    if not r["ok"]:
        raise HTTPException(400, detail=r)
    return r


@router.post("/asamblea/release")
def release(payload: dict = Body(...), x_asamblea_token: str | None = Header(default=None),
            db: Session = Depends(get_db)):
    _auth(x_asamblea_token)
    s = ae.sesion_activa(db)
    return ae.liberar(db, s, uf=int(payload["uf"]), device=payload["device"])


@router.post("/asamblea/voto")
def voto(payload: dict = Body(...), x_asamblea_token: str | None = Header(default=None),
         db: Session = Depends(get_db)):
    _auth(x_asamblea_token)
    s = ae.sesion_activa(db)
    r = ae.votar(db, s, device=payload["device"], mocion=int(payload["mocion"]),
                 uf=int(payload["uf"]), opcion=int(payload["opcion"]))
    if not r["ok"]:
        raise HTTPException(403, detail=r)
    return r


def _auth_mod(x_asamblea_token, x_asamblea_mod):
    _auth(x_asamblea_token)
    if not settings.asamblea_mod_token or x_asamblea_mod != settings.asamblea_mod_token:
        raise HTTPException(401, "Secreto de moderador inválido")


@router.post("/asamblea/mod/doc")
def mod_doc(payload: dict = Body(...), x_asamblea_token: str | None = Header(default=None),
            x_asamblea_mod: str | None = Header(default=None), db: Session = Depends(get_db)):
    _auth_mod(x_asamblea_token, x_asamblea_mod)
    s = ae.sesion_activa(db)
    ae.set_doc(db, s, payload["doc"])
    return {"ok": True, "version": s.version}


@router.post("/asamblea/mod/ventana")
def mod_ventana(payload: dict = Body(...), x_asamblea_token: str | None = Header(default=None),
                x_asamblea_mod: str | None = Header(default=None), db: Session = Depends(get_db)):
    _auth_mod(x_asamblea_token, x_asamblea_mod)
    s = ae.sesion_activa(db)
    doc = dict(s.doc or {})
    mociones = doc.get("mociones", [])
    i = int(payload["mocion"])
    if 0 <= i < len(mociones):
        mociones[i] = {**mociones[i], "abierta": bool(payload["abierta"])}
        doc["mociones"] = mociones
        ae.set_doc(db, s, doc)
    return {"ok": True}


@router.post("/asamblea/mod/claim")
def mod_claim(payload: dict = Body(...), x_asamblea_token: str | None = Header(default=None),
              x_asamblea_mod: str | None = Header(default=None), db: Session = Depends(get_db)):
    _auth_mod(x_asamblea_token, x_asamblea_mod)
    s = ae.sesion_activa(db)
    return ae.set_claim_mod(db, s, uf=int(payload["uf"]), presente=bool(payload.get("presente", True)),
                            rol=payload.get("rol", "titular"), nombre=payload.get("nombre", ""))


@router.post("/asamblea/mod/voto")
def mod_voto(payload: dict = Body(...), x_asamblea_token: str | None = Header(default=None),
             x_asamblea_mod: str | None = Header(default=None), db: Session = Depends(get_db)):
    _auth_mod(x_asamblea_token, x_asamblea_mod)
    s = ae.sesion_activa(db)
    return ae.votar(db, s, device="mod", mocion=int(payload["mocion"]), uf=int(payload["uf"]),
                    opcion=int(payload["opcion"]), override=True)


@router.post("/asamblea/mod/release")
def mod_release(payload: dict = Body(...), x_asamblea_token: str | None = Header(default=None),
                x_asamblea_mod: str | None = Header(default=None), db: Session = Depends(get_db)):
    _auth_mod(x_asamblea_token, x_asamblea_mod)
    s = ae.sesion_activa(db)
    return ae.liberar(db, s, uf=int(payload["uf"]), device=None)


@router.post("/asamblea/mod/reset")
def mod_reset(payload: dict = Body(default={}), x_asamblea_token: str | None = Header(default=None),
              x_asamblea_mod: str | None = Header(default=None), db: Session = Depends(get_db)):
    _auth_mod(x_asamblea_token, x_asamblea_mod)
    s = ae.sesion_activa(db)
    return ae.reset(db, s)
