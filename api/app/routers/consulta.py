"""Consultas read-only sobre gastos, comprobantes y deudores: la base de la vista
analítica y del MCP."""
import unicodedata

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from .. import models, security
from ..db import get_db
from .documentos import extraer_texto

router = APIRouter(prefix="/consulta", tags=["consulta"])


def _plegar(s: str) -> str:
    """Minúsculas sin acentos, 1:1 por carácter (los índices del original se preservan)."""
    return "".join(unicodedata.normalize("NFD", c)[0].lower() for c in s)

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


@router.get("/comprobantes")
def comprobantes(q: str, request: Request, periodo: str | None = None,
                 db: Session = Depends(get_db), s: dict = Depends(_EQUIPO)):
    """Busca `q` (case-insensitive) en el texto extraído de los comprobantes del período
    (o de todos). La primera pasada extrae y cachea (cache por hash en documentos.py);
    las siguientes son en memoria."""
    filas = db.query(models.Documento, models.Liquidacion.periodo).join(models.Liquidacion)
    if periodo:
        filas = filas.filter(models.Liquidacion.periodo == periodo)
    aguja = _plegar(q)
    resultados = []
    for d, per in filas.all():
        texto = extraer_texto(request.app.state.storage, d)
        pos = _plegar(texto).find(aguja)
        if pos < 0:
            continue
        resultados.append({"documento_id": d.id, "gasto_n": d.gasto_n, "periodo": per,
                           "tipo": d.tipo,
                           "fragmento": texto[max(0, pos - 200):pos + len(q) + 200]})
    return {"resultados": resultados}


@router.get("/deudores")
def deudores(periodo: str | None = None, db: Session = Depends(get_db),
             s: dict = Depends(_EQUIPO)):
    """Unidades con deuda de la liquidación del período (default: la última procesada o
    publicada), del `datos` guardado en la ingesta. `meses_equivalentes` = deuda / expensa
    mensual de esa unidad (None si la unidad no tiene expensa ese mes)."""
    filas = (db.query(models.Liquidacion)
               .filter(models.Liquidacion.estado.in_(("procesada", "publicada"))))
    liq = (filas.filter_by(periodo=periodo).first() if periodo
           else filas.order_by(models.Liquidacion.periodo.desc()).first())
    if not liq:
        raise HTTPException(404, "No hay liquidación procesada para ese período")
    ds = []
    for u in (liq.datos or {}).get("unidades", []):
        if u["deuda"] > 0:
            ds.append({"uf": u["uf"], "piso_depto": u["piso_depto"],
                       "propietario": u["propietario"], "deuda": u["deuda"],
                       "meses_equivalentes": (round(u["deuda"] / u["total_mes"], 2)
                                              if u["total_mes"] else None)})
    ds.sort(key=lambda d: -d["deuda"])
    return {"periodo": liq.periodo, "deudores": ds,
            "total": round(sum(d["deuda"] for d in ds), 2)}


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

    # variación: "¿qué subió?" — dos semánticas según cuántos períodos haya en el rango.
    #
    # Rango con 2+ períodos (o sin rango = todos los períodos):
    #   variacion del grupo = total del grupo en el ÚLTIMO período del rango
    #                         vs el período inmediato ANTERIOR a ese (que está dentro del rango).
    #   Así la vista analítica sin rango siempre muestra variación real entre los dos últimos
    #   períodos disponibles.
    #   OJO: `total` y `cantidad` del grupo siguen siendo del rango completo; solo la
    #   variación usa "último vs penúltimo" del rango.
    #
    # Rango con 1 solo período:
    #   variacion = vs el período inmediato anterior al rango (fuera del rango),
    #   comportamiento original útil para comparar un mes concreto con el mes previo.
    #
    # `por=periodo` nunca tiene variación (la clave ya es el período).
    periodos = sorted({per for _, per in pares})
    # anterior: totales por clave del período base de comparación (penúltimo o externo)
    # numerador: totales por clave del período más reciente (None = usar total del grupo completo)
    anterior: dict[str, float] | None = None
    numerador: dict[str, float] | None = None

    if periodos and por != "periodo":
        if len(periodos) >= 2:
            # Semántica intra-rango: penúltimo período del rango como base, último como numerador.
            ultimo = periodos[-1]
            penultimo = periodos[-2]
            pares_base = _query_gastos(db, periodo_desde=penultimo, periodo_hasta=penultimo)
            anterior = {}
            for g, per in pares_base:
                k = clave(g, per)
                anterior[k] = anterior.get(k, 0.0) + g.importe
            # El numerador es solo el último período del rango; `total` del grupo abarca todo el rango.
            numerador = {}
            for g, per in pares:
                if per == ultimo:
                    k = clave(g, per)
                    numerador[k] = numerador.get(k, 0.0) + g.importe
        else:
            # Semántica fuera-de-rango: período anterior externo al rango como base.
            previa = (db.query(models.Liquidacion.periodo)
                        .filter(models.Liquidacion.periodo < periodos[0])
                        .order_by(models.Liquidacion.periodo.desc()).first())
            if previa:
                pares_base = _query_gastos(db, periodo_desde=previa[0], periodo_hasta=previa[0])
                anterior = {}
                for g, per in pares_base:
                    k = clave(g, per)
                    anterior[k] = anterior.get(k, 0.0) + g.importe
            # Con un solo período en el rango, el numerador es el total del grupo.
            numerador = None

    out = []
    for it in grupos.values():
        base = (anterior or {}).get(it["clave"]) if anterior is not None else None
        if base:
            num = (numerador or {}).get(it["clave"], it["total"]) if numerador is not None else it["total"]
            it["variacion"] = (num / base - 1)
        else:
            it["variacion"] = None
        out.append(it)
    return {"grupos": sorted(out, key=lambda i: -i["total"])}
