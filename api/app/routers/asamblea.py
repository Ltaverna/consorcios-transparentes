import os

from fastapi import APIRouter, File, Header, HTTPException, UploadFile

from .. import convocatoria
from ..config import settings

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
