from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy.orm import Session

from .. import models, security
from ..db import get_db
from ..storage import mime_por_clave

router = APIRouter(tags=["documentos"])


def _servir(request: Request, key: str, attachment: bool = True) -> Response:
    """`X-Content-Type-Options: nosniff` siempre: nada de lo que servimos acá lo tiene que
    interpretar el navegador como HTML/script por más que el contenido se preste. Como
    descarga (`Content-Disposition: attachment`) todo excepto los informes: un comprobante
    de un tercero no se abre inline en la pestaña del auditor; el informe publicado sí, para
    que el propietario lo pueda ver directamente."""
    headers = {"X-Content-Type-Options": "nosniff"}
    if attachment:
        headers["Content-Disposition"] = f"attachment; filename={key.rsplit('/', 1)[-1]}"
    url = request.app.state.storage.url_firmada(key, descarga=attachment)
    if url:
        headers["Location"] = url
        return Response(status_code=307, headers=headers)
    return Response(request.app.state.storage.leer(key), media_type=mime_por_clave(key), headers=headers)


def _gastos_citados(db: Session, liquidacion_id: int) -> set[str]:
    """Devuelve el set de refs (como strings) de todos los hallazgos publicados de
    origen="comprobantes" para una liquidación dada.

    Las refs son un namespace compartido entre orígenes: en hallazgos de origen
    "liquidacion" (p.ej. morosidad) las refs pueden ser UFs de deudores u otra cosa
    que casualmente coincida con un número de gasto. Solo los hallazgos de origen
    "comprobantes" garantizan que sus refs son números de gasto. Mismo criterio que
    en publicar.py (~línea 39)."""
    filas = (db.query(models.Hallazgo)
               .filter_by(liquidacion_id=liquidacion_id, publicado=True, origen="comprobantes")
               .all())
    return {r for h in filas for r in (h.refs or [])}


def _accesible_para_propietario(db: Session, d: models.Documento) -> bool:
    """Un propietario solo ve documentos citados por un hallazgo publicado de origen
    "comprobantes" (gasto_n en refs). Ver _gastos_citados para la justificación del
    filtro por origen."""
    if d.gasto_n is None:
        return False
    return str(d.gasto_n) in _gastos_citados(db, d.liquidacion_id)


@router.get("/documentos")
def listar(liquidacion_id: int, db: Session = Depends(get_db),
           s: dict = Depends(security.requiere("auditor", "consejo", "moderador", "propietario"))):
    filas = db.query(models.Documento).filter_by(liquidacion_id=liquidacion_id).all()
    if s["rol"] == "propietario":
        # Una sola query de hallazgos para toda la lista (evita N+1).
        permitidos = _gastos_citados(db, liquidacion_id)
        filas = [d for d in filas if d.gasto_n is not None and str(d.gasto_n) in permitidos]
    return [{"id": d.id, "gasto_n": d.gasto_n, "tipo": d.tipo, "hash": d.hash,
             "metadatos": d.metadatos} for d in filas]


@router.get("/documentos/{d_id}/contenido")
def contenido(d_id: int, request: Request, vista: bool = False, db: Session = Depends(get_db),
              s: dict = Depends(security.requiere("auditor", "consejo", "moderador", "propietario"))):
    d = db.get(models.Documento, d_id)
    if s["rol"] == "propietario":
        # El propietario recibe 403 tanto si el documento no existe como si no tiene acceso:
        # responder 404 le permitiría enumerar qué IDs existen en el sistema.
        if vista:
            raise HTTPException(403, "Solo el equipo puede ver documentos embebidos")
        if not d or not _accesible_para_propietario(db, d):
            raise HTTPException(403, "No autorizado para este documento")
    elif not d:
        raise HTTPException(404, "No existe ese documento")
    # vista=True: inline para el triage del equipo (el chequeo de arriba lo bloquea para
    # propietarios); sin el flag, descarga forzada como siempre. Igual que los informes,
    # inline = sin el header de attachment (nosniff se conserva en _servir).
    return _servir(request, d.archivo_key, attachment=not vista)


@router.get("/informes/{periodo}/{tipo}")
def informe(periodo: str, tipo: str, request: Request, db: Session = Depends(get_db),
            s: dict = Depends(security.sesion)):
    fila = (db.query(models.Informe).join(models.Liquidacion)
              .filter(models.Liquidacion.periodo == periodo,
                      models.Liquidacion.estado == "publicada",
                      models.Informe.tipo == tipo).first())
    if not fila:
        raise HTTPException(404, "No hay informe publicado para ese período")
    return _servir(request, fila.archivo_key, attachment=False)


@router.get("/mi-unidad")
def mi_unidad(db: Session = Depends(get_db), s: dict = Depends(security.requiere("propietario"))):
    uf = int(s["sub"][3:])
    liq = (db.query(models.Liquidacion).filter_by(estado="publicada")
             .order_by(models.Liquidacion.periodo.desc()).first())
    if not liq:
        raise HTTPException(404, "Todavía no hay ningún informe publicado")
    fila = next((u for u in (liq.datos or {}).get("unidades", []) if u["uf"] == uf), None)
    return {"uf": uf, "periodo": liq.periodo, "estado_cuenta": fila,
            "informes": [f"/informes/{liq.periodo}/html", f"/informes/{liq.periodo}/xlsx"]}
