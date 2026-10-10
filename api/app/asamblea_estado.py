"""Lógica de estado de asamblea en vivo (sin HTTP). Bloqueo por fila UNIQUE.

Corte duro/blando: claims y votos son filas (concurrencia segura); el resto (mociones,
agenda, oradores, etc.) vive en `AsambleaSesion.doc` con `version` (último-gana)."""
import copy
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified

from .models import AsambleaClaim, AsambleaSesion, AsambleaVoto

def sesion_activa(db: Session) -> AsambleaSesion:
    """La asamblea activa (una sola). Se crea vacía si no existe."""
    # Asamblea única por instalación: sin carrera real (un solo moderador la inicia).
    s = db.query(AsambleaSesion).order_by(AsambleaSesion.id.desc()).first()
    if s is None:
        s = AsambleaSesion(titulo="", doc={"mociones": []}, version=1)
        db.add(s)
        db.commit()
        db.refresh(s)
    return s


def set_doc(db: Session, s: AsambleaSesion, doc: dict) -> None:
    """Reemplaza el doc blando y sube la versión.
    Usa flag_modified para forzar el flush incluso cuando la mutación fue anidada
    (MutableDict solo trackea cambios de primer nivel; las mutaciones de sub-dicts
    pasan desapercibidas para la sesión)."""
    s.doc = copy.deepcopy(doc)
    flag_modified(s, "doc")
    s.version = (s.version or 0) + 1
    db.add(s)
    db.commit()


def _prop_por_uf(s: AsambleaSesion) -> dict:
    return {u["uf"]: u.get("prop", "") for u in (s.doc or {}).get("units", [])}


def ensamblar_estado(db: Session, s: AsambleaSesion) -> dict:
    """Arma la forma que el cliente ya entiende + `claims` y `abierta` por moción."""
    doc = dict(s.doc or {})
    claims = db.query(AsambleaClaim).filter_by(sesion_id=s.id).all()
    votos = db.query(AsambleaVoto).filter_by(sesion_id=s.id).all()
    presentes, poderes, claims_out = {}, {}, {}
    for c in claims:
        k = str(c.uf)
        # El cliente trata presencia y poder como excluyentes: titular → presentes, mandatario → poderes.
        if c.rol == "mandatario":
            poderes[k] = c.nombre or True
        elif c.presente:
            presentes[k] = True
        claims_out[k] = {"device": c.device_id, "rol": c.rol, "nombre": c.nombre}
    votos_por_mocion: dict[int, dict] = {}
    for v in votos:
        votos_por_mocion.setdefault(v.mocion_idx, {})[str(v.uf)] = v.opcion_idx
    mociones = []
    for i, m in enumerate(doc.get("mociones", [])):
        mociones.append({**m, "votos": votos_por_mocion.get(i, {})})
    return {
        "titulo": s.titulo,
        "version": s.version,
        "mociones": mociones,
        "activa": doc.get("activa", 0),
        "agenda": doc.get("agenda", {}),
        "palabra": doc.get("palabra", []),
        "respuestas": doc.get("respuestas", {}),
        "objeciones": doc.get("objeciones", {}),
        "cumplimiento": doc.get("cumplimiento", {}),
        "presentes": presentes,
        "poderes": poderes,
        "claims": claims_out,
    }


def _cuenta_propietarios(s: AsambleaSesion, representados: list[int]) -> int:
    """Propietarios distintos representados (condominio = 1)."""
    pmap = _prop_por_uf(s)
    return len({pmap.get(uf, f"uf{uf}") for uf in representados})


def reclamar(db: Session, s: AsambleaSesion, device: str, uf: int,
             representados: list[int], nombre: str) -> dict:
    """Fija el conjunto COMPLETO de claims de `device`: su unidad (titular) + las representadas
    (mandatario). Reemplaza cualquier claim previo de ese device (las unidades que ya no estén
    en el pedido se liberan, con sus votos). Todo-o-nada. Devuelve {ok:True} o
    {ok:False, conflicto:[uf]} (alguna la tiene otro device) / {ok:False, motivo:str} (tope art.25h)."""
    representados = [int(x) for x in (representados or []) if int(x) != int(uf)]
    if _cuenta_propietarios(s, representados) > 5:
        return {"ok": False, "motivo": "Un mandatario no puede representar a más de cinco propietarios (art. 25 h)."}
    objetivo = {int(uf): "titular"}
    for r in representados:
        objetivo.setdefault(r, "mandatario")
    tomadas = {c.uf: c.device_id for c in db.query(AsambleaClaim).filter_by(sesion_id=s.id).all()}
    conflicto = [u for u in objetivo if u in tomadas and tomadas[u] != device]
    if conflicto:
        return {"ok": False, "conflicto": conflicto}
    try:
        for c in db.query(AsambleaClaim).filter_by(sesion_id=s.id, device_id=device).all():
            if c.uf not in objetivo:
                db.query(AsambleaVoto).filter_by(sesion_id=s.id, uf=c.uf).delete()
                db.delete(c)
        for u, rol in objetivo.items():
            if tomadas.get(u) == device:
                continue
            db.add(AsambleaClaim(sesion_id=s.id, uf=u, device_id=device, rol=rol,
                                 presente=True, nombre=nombre))
        db.commit()
    except IntegrityError:
        db.rollback()
        return {"ok": False, "conflicto": list(objetivo)}
    return {"ok": True}


def liberar(db: Session, s: AsambleaSesion, uf: int, device: str | None) -> dict:
    """Suelta el claim de `uf`. Si `device` viene, solo si le pertenece (propietario);
    con device=None es override del moderador. Al liberar, borra los votos de esa uf."""
    q = db.query(AsambleaClaim).filter_by(sesion_id=s.id, uf=int(uf))
    if device is not None:
        q = q.filter_by(device_id=device)
    c = q.first()
    if not c:
        return {"ok": False}
    db.query(AsambleaVoto).filter_by(sesion_id=s.id, uf=int(uf)).delete()
    db.delete(c)
    db.commit()
    return {"ok": True}


def votar(db: Session, s: AsambleaSesion, device: str, mocion: int, uf: int, opcion: int | None,
          override: bool = False) -> dict:
    """Emite/cambia un voto. Sin override exige ventana abierta y que `device` sea dueño de `uf`.
    Con opcion=None borra el voto existente (toggle-off)."""
    mociones = (s.doc or {}).get("mociones", [])
    if mocion < 0 or mocion >= len(mociones):
        return {"ok": False, "motivo": "moción inexistente"}
    if not override:
        if not mociones[mocion].get("abierta"):
            return {"ok": False, "motivo": "La votación de esta moción no está abierta."}
        c = db.query(AsambleaClaim).filter_by(sesion_id=s.id, uf=int(uf)).first()
        if not c or c.device_id != device:
            return {"ok": False, "motivo": "Esa unidad no es tuya."}
    v = db.query(AsambleaVoto).filter_by(sesion_id=s.id, mocion_idx=int(mocion), uf=int(uf)).first()
    if opcion is None:
        if v:
            db.delete(v)
            db.commit()
        return {"ok": True}
    if v:
        v.opcion_idx = int(opcion)
        v.device_id = device
    else:
        db.add(AsambleaVoto(sesion_id=s.id, mocion_idx=int(mocion), uf=int(uf),
                            opcion_idx=int(opcion), device_id=device))
    db.commit()
    return {"ok": True}


def set_claim_mod(db: Session, s: AsambleaSesion, uf: int, presente: bool, rol: str, nombre: str) -> dict:
    """Override del moderador: fija/forza presencia o poder de una unidad (device='mod')."""
    c = db.query(AsambleaClaim).filter_by(sesion_id=s.id, uf=int(uf)).first()
    if c:
        c.device_id, c.rol, c.presente, c.nombre = "mod", rol, presente, nombre
    else:
        db.add(AsambleaClaim(sesion_id=s.id, uf=int(uf), device_id="mod", rol=rol,
                             presente=presente, nombre=nombre))
    db.commit()
    return {"ok": True}


def reset(db: Session, s: AsambleaSesion) -> dict:
    db.query(AsambleaVoto).filter_by(sesion_id=s.id).delete()
    db.query(AsambleaClaim).filter_by(sesion_id=s.id).delete()
    db.commit()
    return {"ok": True}
