"""Consultas read-only sobre gastos: la base de la vista analítica y del MCP."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .. import models, security
from ..db import get_db

router = APIRouter(prefix="/consulta", tags=["consulta"])

_EQUIPO = security.requiere("auditor", "consejo", "moderador")


def _query_gastos(db, proveedor=None, categoria=None, q=None,
                  periodo_desde=None, periodo_hasta=None, importe_min=None):
    filas = db.query(models.Gasto, models.Liquidacion.periodo).join(models.Liquidacion)
    if periodo_desde:
        filas = filas.filter(models.Liquidacion.periodo >= periodo_desde)
    if periodo_hasta:
        filas = filas.filter(models.Liquidacion.periodo <= periodo_hasta)
    if proveedor:
        filas = filas.filter(models.Gasto.proveedor.ilike(f"%{proveedor}%"))
    if categoria:
        filas = filas.filter(models.Gasto.categoria.ilike(f"%{categoria}%"))
    if q:
        filas = filas.filter(models.Gasto.concepto.ilike(f"%{q}%"))
    if importe_min is not None:
        filas = filas.filter(models.Gasto.importe >= importe_min)
    return filas.all()


@router.get("/gastos")
def gastos(proveedor: str | None = None, categoria: str | None = None, q: str | None = None,
           periodo_desde: str | None = None, periodo_hasta: str | None = None,
           importe_min: float | None = None,
           db: Session = Depends(get_db), s: dict = Depends(_EQUIPO)):
    pares = _query_gastos(db, proveedor, categoria, q, periodo_desde, periodo_hasta, importe_min)
    filas = sorted(
        ({"periodo": per, "n": g.n, "proveedor": g.proveedor, "categoria": g.categoria,
          "concepto": g.concepto, "importe": g.importe, "factura_nro": g.factura_nro,
          "pagos": g.pagos}
         for g, per in pares),
        key=lambda f: -f["importe"],
    )
    return {"filas": filas, "total": sum(f["importe"] for f in filas), "cantidad": len(filas)}


@router.get("/agregados")
def agregados(por: str, periodo_desde: str | None = None, periodo_hasta: str | None = None,
              db: Session = Depends(get_db), s: dict = Depends(_EQUIPO)):
    if por not in ("proveedor", "categoria", "periodo"):
        raise HTTPException(422, "por debe ser proveedor, categoria o periodo")
    pares = _query_gastos(db, periodo_desde=periodo_desde, periodo_hasta=periodo_hasta)

    def clave(g, per):
        return per if por == "periodo" else getattr(g, por)

    grupos: dict[str, dict] = {}
    for g, per in pares:
        k = clave(g, per)
        it = grupos.setdefault(k, {"clave": k, "total": 0.0, "cantidad": 0})
        it["total"] += g.importe
        it["cantidad"] += 1

    # variación: mismo grupo en el período inmediato anterior al rango consultado
    periodos = sorted({per for _, per in pares})
    anterior = None
    if periodos and por != "periodo":
        previa = (db.query(models.Liquidacion.periodo)
                    .filter(models.Liquidacion.periodo < periodos[0])
                    .order_by(models.Liquidacion.periodo.desc()).first())
        if previa:
            pares_ant = _query_gastos(db, periodo_desde=previa[0], periodo_hasta=previa[0])
            anterior = {}
            for g, per in pares_ant:
                k = clave(g, per)
                anterior[k] = anterior.get(k, 0.0) + g.importe

    out = []
    for it in grupos.values():
        base = (anterior or {}).get(it["clave"])
        it["variacion"] = (it["total"] / base - 1) if base else None
        out.append(it)
    return {"grupos": sorted(out, key=lambda i: -i["total"])}
