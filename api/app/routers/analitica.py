from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .. import analitica, models, security
from ..db import get_db

router = APIRouter(prefix="/analitica", tags=["analitica"])
ROLES = ("auditor", "consejo", "moderador", "propietario")


@router.get("/indice")
def indice(desde: str = "", hasta: str = "", db: Session = Depends(get_db),
           s: dict = Depends(security.requiere(*ROLES))):
    return analitica.metricas(db, desde, hasta, solo_publicado=s["rol"] == "propietario")


@router.get("/gastos")
def gastos(periodo: str, estado: str = "", db: Session = Depends(get_db),
           s: dict = Depends(security.requiere(*ROLES))):
    if estado and estado not in analitica.ESTADOS_GASTO:
        raise HTTPException(422, "Estado inválido; válidos: " + ", ".join(analitica.ESTADOS_GASTO))
    solo_pub = s["rol"] == "propietario"
    estados_liq = ("publicada",) if solo_pub else ("procesada", "publicada")
    liq = (db.query(models.Liquidacion).filter_by(periodo=periodo)
             .filter(models.Liquidacion.estado.in_(estados_liq)).first())
    if not liq:
        raise HTTPException(404, "No hay liquidación de ese período")
    filas, _hs, _abiertos = analitica.evaluar_liquidacion(db, liq, solo_pub)
    out = []
    for g, est, halls, dd in filas:
        if estado and est != estado:
            continue
        out.append({"n": g.n, "proveedor": g.proveedor, "categoria": g.categoria,
                    "concepto": g.concepto[:160], "importe": g.importe, "estado": est,
                    "hallazgos": [{"id": h.id, "severidad": h.severidad, "estado": h.estado,
                                   "titulo": h.titulo} for h in halls],
                    "documentos": [{"id": d.id, "tipo": d.tipo,
                                    "archivo": d.archivo_key.rsplit("/", 1)[-1]} for d in dd]})
    return {"periodo": periodo, "gastos": out}
