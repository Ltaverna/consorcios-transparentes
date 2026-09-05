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


@router.get("/documentos")
def listar(liquidacion_id: int, db: Session = Depends(get_db),
           s: dict = Depends(security.requiere("auditor", "consejo", "moderador"))):
    filas = db.query(models.Documento).filter_by(liquidacion_id=liquidacion_id).all()
    return [{"id": d.id, "gasto_n": d.gasto_n, "tipo": d.tipo, "hash": d.hash,
             "metadatos": d.metadatos} for d in filas]


@router.get("/documentos/{d_id}/contenido")
def contenido(d_id: int, request: Request, db: Session = Depends(get_db),
              s: dict = Depends(security.requiere("auditor", "consejo", "moderador"))):
    d = db.get(models.Documento, d_id)
    if not d:
        raise HTTPException(404, "No existe ese documento")
    return _servir(request, d.archivo_key)


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
