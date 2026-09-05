from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from .. import models, security
from ..db import get_db

router = APIRouter(prefix="/hallazgos", tags=["hallazgos"])
ESTADOS = ("pendiente", "preguntado", "respondido", "descartado", "cerrado")
ORDEN_SEV = {"CRÍTICO": 0, "ALTO": 1, "MEDIO": 2, "BAJO": 3}


class CambioEstado(BaseModel):
    estado: str
    nota: str = ""


class CambioPublicado(BaseModel):
    publicado: bool


class Respuesta(BaseModel):
    texto: str


def _usuario(db: Session, s: dict) -> models.Usuario | None:
    return db.get(models.Usuario, int(s["sub"][2:])) if s["sub"].startswith("u:") else None


def _resumen(h: models.Hallazgo) -> dict:
    return {"id": h.id, "liquidacion_id": h.liquidacion_id, "periodo": h.liquidacion.periodo,
            "regla": h.regla, "origen": h.origen, "severidad": h.severidad, "area": h.area,
            "titulo": h.titulo, "monto": h.monto, "estado": h.estado, "publicado": h.publicado}


@router.get("")
def listar(severidad: str | None = None, estado: str | None = None, regla: str | None = None,
           periodo: str | None = None, db: Session = Depends(get_db),
           s: dict = Depends(security.requiere("auditor", "consejo", "moderador", "propietario"))):
    q = db.query(models.Hallazgo).join(models.Liquidacion)
    if s["rol"] == "propietario":
        q = q.filter(models.Hallazgo.publicado == True)  # noqa: E712
    if severidad:
        q = q.filter(models.Hallazgo.severidad == severidad)
    if estado:
        q = q.filter(models.Hallazgo.estado == estado)
    if regla:
        q = q.filter(models.Hallazgo.regla == regla)
    if periodo:
        q = q.filter(models.Liquidacion.periodo == periodo)
    filas = sorted(q.all(), key=lambda h: (ORDEN_SEV.get(h.severidad, 9), -abs(h.monto)))
    return [_resumen(h) for h in filas]


@router.get("/{h_id}")
def detalle(h_id: int, db: Session = Depends(get_db),
            s: dict = Depends(security.requiere("auditor", "consejo", "moderador", "propietario"))):
    h = db.get(models.Hallazgo, h_id)
    # Para el propietario, un hallazgo sin publicar responde el MISMO 404 que uno
    # inexistente: no revelamos que existe algo en borrador.
    if not h or (s["rol"] == "propietario" and not h.publicado):
        raise HTTPException(404, "No existe ese hallazgo")
    base = {**_resumen(h), "evidencia": h.evidencia, "recomendacion": h.recomendacion,
            "refs": h.refs, "respuesta_admin": h.respuesta_admin}
    if s["rol"] == "propietario":
        return base  # sin historial interno de eventos (ni consulta de usuarios)
    eventos = sorted(h.eventos, key=lambda e: (e.ts, e.id), reverse=True)
    ids = {e.usuario_id for e in h.eventos if e.usuario_id}
    usuarios = {u.id: u.nombre for u in db.query(models.Usuario).filter(models.Usuario.id.in_(ids))} if ids else {}
    return {**base,
            "eventos": [{"de": e.de, "a": e.a, "nota": e.nota, "ts": e.ts.isoformat(),
                         "usuario": usuarios.get(e.usuario_id, "")} for e in eventos]}


@router.post("/{h_id}/estado")
def cambiar_estado(h_id: int, cambio: CambioEstado, db: Session = Depends(get_db),
                   s: dict = Depends(security.requiere("auditor"))):
    if cambio.estado not in ESTADOS:
        raise HTTPException(422, f"Estado inválido; válidos: {', '.join(ESTADOS)}")
    h = db.get(models.Hallazgo, h_id)
    if not h:
        raise HTTPException(404, "No existe ese hallazgo")
    u = _usuario(db, s)
    db.add(models.HallazgoEvento(hallazgo_id=h.id, usuario_id=u.id if u else None,
                                 de=h.estado, a=cambio.estado, nota=cambio.nota))
    h.estado = cambio.estado
    db.commit()
    return {"ok": True, "estado": h.estado}


@router.post("/{h_id}/publicar")
def publicar(h_id: int, cambio: CambioPublicado, db: Session = Depends(get_db),
             s: dict = Depends(security.requiere("auditor"))):
    h = db.get(models.Hallazgo, h_id)
    if not h:
        raise HTTPException(404, "No existe ese hallazgo")
    h.publicado = cambio.publicado
    db.commit()
    return {"ok": True, "publicado": h.publicado}


@router.post("/{h_id}/respuesta")
def registrar_respuesta(h_id: int, r: Respuesta, db: Session = Depends(get_db),
                        s: dict = Depends(security.requiere("auditor"))):
    h = db.get(models.Hallazgo, h_id)
    if not h:
        raise HTTPException(404, "No existe ese hallazgo")
    h.respuesta_admin = r.texto
    db.commit()
    return {"ok": True}
