"""Del PDF a la base: parseo, cuadre, reglas y sincronización. La regla de oro vive acá:
si la liquidación no cuadra queda en `no_cuadra` y no se inserta ni publica nada."""
import tempfile

from sqlalchemy.orm import Session

from ct.model import Liquidacion as LiqMotor
from ct.redconar import parse_pdf, parse_text
from ct.rules import Config, Hallazgo as HallazgoMotor, evaluar

from . import models

MESES = {"enero": 1, "febrero": 2, "marzo": 3, "abril": 4, "mayo": 5, "junio": 6,
         "julio": 7, "agosto": 8, "septiembre": 9, "octubre": 10, "noviembre": 11, "diciembre": 12}


def periodo_iso(texto: str) -> str | None:
    """'Agosto 2026' -> '2026-08'. None si no se reconoce."""
    partes = texto.lower().split()
    mes = next((MESES[p] for p in partes if p in MESES), None)
    anio = next((p for p in partes if p.isdigit() and len(p) == 4), None)
    return f"{anio}-{mes:02d}" if mes and anio else None


def periodo_anterior(periodo: str) -> str:
    anio, mes = int(periodo[:4]), int(periodo[5:7])
    return f"{anio - 1}-12" if mes == 1 else f"{anio}-{mes - 1:02d}"


def parsear_bytes(nombre: str, data: bytes) -> LiqMotor:
    if nombre.lower().endswith(".pdf"):
        with tempfile.NamedTemporaryFile(suffix=".pdf") as f:
            f.write(data)
            f.flush()
            return parse_pdf(f.name)
    return parse_text(data.decode("utf-8"))


def clave_natural(h: HallazgoMotor) -> str:
    """Estable entre reprocesos: regla + referencias; si no hay refs, regla + título."""
    if h.refs:
        return f"{h.regla}|" + "|".join(sorted(str(r) for r in h.refs))
    return f"{h.regla}|{h.titulo}"[:500]


def config_consorcio(db: Session) -> Config:
    c = db.query(models.Consorcio).first()
    return Config.desde_dict(c.umbrales if c else None)


def cargar_engine(storage, liq_row: models.Liquidacion) -> LiqMotor:
    return parsear_bytes(liq_row.archivo_key, storage.leer(liq_row.archivo_key))


def cargar_anterior(db: Session, storage, periodo: str) -> LiqMotor | None:
    prev = (db.query(models.Liquidacion)
              .filter(models.Liquidacion.periodo == periodo_anterior(periodo),
                      models.Liquidacion.estado.in_(("procesada", "publicada"))).first())
    return cargar_engine(storage, prev) if prev else None


def guardar_gastos(db: Session, liq_row: models.Liquidacion, liq: LiqMotor) -> None:
    db.query(models.Gasto).filter_by(liquidacion_id=liq_row.id).delete()
    for g in liq.gastos:
        db.add(models.Gasto(
            liquidacion_id=liq_row.id, n=g.n, categoria=g.categoria, proveedor=g.proveedor,
            concepto=g.concepto, columna=g.columna, importe=g.importe,
            factura_fecha=g.factura_fecha, factura_nro=g.factura_nro, factura_importe=g.factura_importe,
            pagos=[{"fecha": p.fecha.isoformat() if p.fecha else None,
                    "importe": p.importe, "caja": p.caja, "forma": p.forma} for p in g.pagos]))


def sincronizar_unidades(db: Session, liq: LiqMotor) -> None:
    existentes = {u.uf: u for u in db.query(models.Unidad).all()}
    for u in liq.unidades:
        row = existentes.get(u.uf)
        if not row:
            row = models.Unidad(uf=u.uf)
            db.add(row)
        row.piso_depto, row.tipo, row.propietario = u.piso_depto, u.tipo, u.propietario
        row.porcentuales = u.pcts  # el codigo_hash nunca se toca acá


def upsert_hallazgos(db: Session, liq_row: models.Liquidacion,
                     hallazgos: list[HallazgoMotor], origen: str) -> None:
    """Reprocesar actualiza la descripción pero jamás pisa estado/publicado/respuesta.
    Los hallazgos que desaparecen se borran solo si siguen `pendiente` y sin publicar."""
    existentes = {h.clave: h for h in db.query(models.Hallazgo)
                  .filter_by(liquidacion_id=liq_row.id, origen=origen).all()}
    vistos = set()
    for h in hallazgos:
        clave = clave_natural(h)
        if clave in vistos:      # dos hallazgos de la misma regla y refs: distingue por título
            clave = f"{clave}|{h.titulo}"[:500]
        vistos.add(clave)
        row = existentes.get(clave)
        if not row:
            row = models.Hallazgo(liquidacion_id=liq_row.id, clave=clave, origen=origen, regla=h.regla,
                                  severidad=h.severidad, area=h.area, titulo=h.titulo, evidencia=h.evidencia)
            db.add(row)
        row.severidad, row.area, row.titulo = h.severidad, h.area, h.titulo
        row.evidencia, row.monto, row.recomendacion = h.evidencia, h.monto, h.recomendacion
        row.refs = [str(r) for r in h.refs]
    for clave, row in existentes.items():
        if clave not in vistos and row.estado == "pendiente" and not row.publicado:
            db.delete(row)


def procesar(db: Session, liq_id: int, storage) -> None:
    liq_row = db.get(models.Liquidacion, liq_id)
    try:
        liq = parsear_bytes(liq_row.archivo_key, storage.leer(liq_row.archivo_key))
        detectado = periodo_iso(liq.periodo)
        if not detectado:
            raise ValueError("No se reconoce el documento como una liquidación (no se detectó el período)")
        if detectado != liq_row.periodo:
            raise ValueError(f"El documento es de {detectado}, no de {liq_row.periodo}")
        liq_row.datos, liq_row.sistema, liq_row.cuadra = liq.to_dict(), liq.sistema, liq.cuadra
        if not liq.cuadra:
            liq_row.estado = "no_cuadra"
            db.commit()
            return
        hs = evaluar(liq, cargar_anterior(db, storage, liq_row.periodo), config_consorcio(db))
        guardar_gastos(db, liq_row, liq)
        sincronizar_unidades(db, liq)
        upsert_hallazgos(db, liq_row, hs, origen="liquidacion")
        liq_row.estado, liq_row.error = "procesada", ""
        db.commit()
    except Exception as e:
        db.rollback()
        liq_row = db.get(models.Liquidacion, liq_id)
        liq_row.estado, liq_row.error = "error", str(e)
        db.commit()
