"""Del PDF a la base: parseo, cuadre, reglas y sincronización. La regla de oro vive acá:
si la liquidación no cuadra queda en `no_cuadra` y no se inserta ni publica nada."""
import hashlib
import logging
import re
import tempfile

from sqlalchemy.orm import Session

from ct.model import Liquidacion as LiqMotor
from ct.redconar import parse_pdf, parse_text
from ct.rules import Config, Hallazgo as HallazgoMotor, evaluar

from . import models

logger = logging.getLogger(__name__)

MESES = {"enero": 1, "febrero": 2, "marzo": 3, "abril": 4, "mayo": 5, "junio": 6,
         "julio": 7, "agosto": 8, "septiembre": 9, "octubre": 10, "noviembre": 11, "diciembre": 12}


def periodo_iso(texto: str) -> str | None:
    """'Agosto 2026' -> '2026-08'. None si no se reconoce."""
    partes = re.split(r"\W+", texto.lower())
    mes = next((MESES[p] for p in partes if p in MESES), None)
    anio = next((p for p in partes if p.isdigit() and len(p) == 4), None)
    return f"{anio}-{mes:02d}" if mes is not None and anio else None


def periodo_anterior(periodo: str) -> str:
    anio, mes = int(periodo[:4]), int(periodo[5:7])
    return f"{anio - 1}-12" if mes == 1 else f"{anio}-{mes - 1:02d}"


def parsear_bytes(nombre: str, data: bytes) -> LiqMotor:
    if nombre.lower().endswith(".pdf"):
        with tempfile.NamedTemporaryFile(suffix=".pdf") as f:
            f.write(data)
            f.flush()
            return parse_pdf(f.name)
    try:
        texto = data.decode("utf-8")
    except UnicodeDecodeError:
        raise ValueError("El archivo no es un texto de liquidación válido ni un PDF")
    return parse_text(texto)


def clave_natural(h: HallazgoMotor) -> str:
    """Estable entre reprocesos: regla + clave declarada por la regla, si no hay clave
    entonces regla + referencias (gastos o unidades), y si tampoco hay refs, el título
    con las cifras borradas (para que una corrección de montos no cambie la clave)."""
    if h.clave:
        base = f"{h.regla}|{h.clave}"
    elif h.refs:
        base = f"{h.regla}|" + "|".join(sorted(str(r) for r in h.refs))
    else:
        base = f"{h.regla}|" + re.sub(r"[\d.,%$]+", "#", h.titulo)
    if len(base) > 500:  # refs enormes (p. ej. todas las unidades deudoras): colapsar en un hash
        base = f"{h.regla}|" + hashlib.sha1(base.encode()).hexdigest()
    return base


def config_consorcio(db: Session) -> Config:
    c = db.query(models.Consorcio).first()
    return Config.desde_dict(c.umbrales if c else None)


def cargar_engine(storage, liq_row: models.Liquidacion) -> LiqMotor:
    return parsear_bytes(liq_row.archivo_key, storage.leer(liq_row.archivo_key))


def cargar_anterior(db: Session, storage, periodo: str) -> LiqMotor | None:
    prev = (db.query(models.Liquidacion)
              .filter(models.Liquidacion.periodo == periodo_anterior(periodo),
                      models.Liquidacion.estado.in_(("procesada", "publicada"))).first())
    if not prev:
        return None
    try:
        return cargar_engine(storage, prev)
    except Exception:
        # Sin comparación contra el mes anterior las reglas que la usan simplemente no corren;
        # no vale la pena tirar abajo el procesamiento de este mes por eso.
        logger.warning("No se pudo cargar la liquidación anterior (%s) para comparar", prev.periodo, exc_info=True)
        return None


def guardar_gastos(db: Session, liq_row: models.Liquidacion, liq: LiqMotor) -> None:
    db.query(models.Gasto).filter_by(liquidacion_id=liq_row.id).delete()
    for g in liq.gastos:
        db.add(models.Gasto(
            liquidacion_id=liq_row.id, n=g.n, categoria=g.categoria, proveedor=g.proveedor,
            concepto=g.concepto, columna=g.columna, importe=g.importe,
            factura_fecha=g.factura_fecha, factura_nro=g.factura_nro, factura_importe=g.factura_importe,
            pagos=[{"fecha": p.fecha.isoformat() if p.fecha else None,
                    "importe": p.importe, "caja": p.caja, "forma": p.forma} for p in g.pagos]))


def limpiar_al_rechazar(db: Session, liq_row: models.Liquidacion) -> None:
    """No_cuadra: no puede quedar nada publicable de un proceso anterior. Se borran los gastos
    y los informes de esta liquidación, y sus hallazgos (los de esta liquidación, no los de
    comprobantes) se despublican sin tocar estado/respuesta_admin/historial: el auditor no
    pierde su trabajo, pero el hallazgo deja de estar visible hasta que la liquidación cuadre."""
    db.query(models.Gasto).filter_by(liquidacion_id=liq_row.id).delete()
    db.query(models.Informe).filter_by(liquidacion_id=liq_row.id).delete()
    for h in db.query(models.Hallazgo).filter_by(liquidacion_id=liq_row.id, origen="liquidacion").all():
        h.publicado = False


def sincronizar_unidades(db: Session, liq: LiqMotor) -> None:
    existentes = {u.uf: u for u in db.query(models.Unidad).all()}
    for u in liq.unidades:
        row = existentes.get(u.uf)
        if not row:
            row = models.Unidad(uf=u.uf)
            db.add(row)
            existentes[u.uf] = row  # una UF duplicada en el mismo parseo no debe insertarse dos veces
        row.piso_depto, row.tipo, row.propietario = u.piso_depto, u.tipo, u.propietario
        row.porcentuales = u.pcts  # el codigo_hash nunca se toca acá


def upsert_hallazgos(db: Session, liq_row: models.Liquidacion,
                     hallazgos: list[HallazgoMotor], origen: str) -> None:
    """Reprocesar actualiza la descripción pero jamás pisa estado/publicado/respuesta.
    Los hallazgos que desaparecen se borran solo si siguen `pendiente`, sin publicar y sin
    respuesta ni historial (si el auditor ya interactuó con él, se conserva igual)."""
    existentes = {h.clave: h for h in db.query(models.Hallazgo)
                  .filter_by(liquidacion_id=liq_row.id, origen=origen).all()}
    vistos = set()
    for h in hallazgos:
        clave = clave_natural(h)
        while clave in vistos:      # colisión (misma regla y clave/refs/título): desambiguar
            clave = (clave + "~")[:500]
        vistos.add(clave)
        row = existentes.get(clave)
        if not row:
            row = models.Hallazgo(liquidacion_id=liq_row.id, clave=clave, origen=origen, regla=h.regla)
            db.add(row)
        row.severidad, row.area, row.titulo = h.severidad, h.area, h.titulo
        row.evidencia, row.monto, row.recomendacion = h.evidencia, h.monto, h.recomendacion
        row.refs = [str(r) for r in h.refs]
    for clave, row in existentes.items():
        if (clave not in vistos and row.estado == "pendiente" and not row.publicado
                and not row.respuesta_admin and not row.eventos):
            db.delete(row)


def procesar(db: Session, liq_id: int, storage) -> None:
    liq_row = db.get(models.Liquidacion, liq_id)
    if liq_row is None:
        logger.warning("Se pidió procesar la liquidación %s pero no existe", liq_id)
        return
    estaba_publicada = liq_row.estado == "publicada"
    try:
        liq = parsear_bytes(liq_row.archivo_key, storage.leer(liq_row.archivo_key))
        detectado = periodo_iso(liq.periodo)
        if not detectado:
            raise ValueError("No se reconoce el documento como una liquidación (no se detectó el período)")
        if detectado != liq_row.periodo:
            raise ValueError(f"El documento es de {detectado}, no de {liq_row.periodo}")
        if not liq.checks:
            raise ValueError("El documento no produjo ninguna verificación de cuadre; no se reconoce el formato")
        # `datos` guarda el parseo completo tal cual se recibió, cuadre o no: si no cuadra,
        # queda el parseo del documento RECHAZADO (no el del último válido), porque hace
        # falta para mostrarle al auditor qué verificaciones fallaron.
        liq_row.datos, liq_row.sistema, liq_row.cuadra = liq.to_dict(), liq.sistema, liq.cuadra
        if not liq.cuadra:
            limpiar_al_rechazar(db, liq_row)
            liq_row.estado = "no_cuadra"
            db.commit()
            return
        hs = evaluar(liq, cargar_anterior(db, storage, liq_row.periodo), config_consorcio(db))
        guardar_gastos(db, liq_row, liq)
        mas_reciente = (db.query(models.Liquidacion.periodo)
                          .filter(models.Liquidacion.estado.in_(("procesada", "publicada")),
                                  models.Liquidacion.id != liq_row.id)
                          .order_by(models.Liquidacion.periodo.desc()).first())
        if not mas_reciente or liq_row.periodo >= mas_reciente[0]:
            sincronizar_unidades(db, liq)
        upsert_hallazgos(db, liq_row, hs, origen="liquidacion")
        if estaba_publicada:
            # Los datos cambiaron: el informe publicado ya no es válido. El auditor vuelve a
            # publicar después de revisar; no se auto-publica un informe nuevo acá.
            db.query(models.Informe).filter_by(liquidacion_id=liq_row.id).delete()
        liq_row.estado, liq_row.error = "procesada", ""
        db.commit()
    except Exception as e:
        db.rollback()
        logger.exception("Falló la ingesta de la liquidación %s", liq_id)
        liq_row = db.get(models.Liquidacion, liq_id)
        liq_row.estado = "error"
        liq_row.error = str(e) if isinstance(e, ValueError) else f"{type(e).__name__}: {e}"[:2000]
        db.commit()
