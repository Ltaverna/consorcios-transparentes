"""Del PDF a la base: parseo, cuadre, reglas y sincronización. La regla de oro vive acá:
si la liquidación no cuadra queda en `no_cuadra` y no se inserta ni publica nada."""
import hashlib
import io
import logging
import pathlib
import re
import tempfile
import zipfile
from collections.abc import Iterable

from sqlalchemy.orm import Session

from ct.comprobantes import cargar_manifiesto_redconar, cruzar
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
    """Estable entre reprocesos: regla + clave declarada por la regla (combinada con las
    referencias si también las hay, para no confundir subcasos de una misma regla y el
    mismo slug pero sobre gastos distintos); si no hay clave, regla + referencias; y si
    tampoco hay refs, el título con las cifras borradas (para que una corrección de
    montos no cambie la clave)."""
    if h.clave and h.refs:
        base = f"{h.regla}|{h.clave}|" + "|".join(sorted(str(r) for r in h.refs))
    elif h.clave:
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


def limpiar_al_rechazar(db: Session, storage, liq_row: models.Liquidacion) -> None:
    """No_cuadra: no puede quedar nada publicable de un proceso anterior. Se borran los gastos
    y los informes de esta liquidación (archivo incluido), y sus hallazgos (los de esta
    liquidación, no los de comprobantes) se despublican sin tocar estado/respuesta_admin/
    historial: el auditor no pierde su trabajo, pero el hallazgo deja de estar visible
    hasta que la liquidación cuadre.

    El borrado de archivos se hace DESPUÉS de que el caller confirme la transacción (acá
    solo se borran las filas y se devuelven las claves): si el archivo no se pudiera borrar,
    la base ya quedó consistente."""
    db.query(models.Gasto).filter_by(liquidacion_id=liq_row.id).delete()
    informes = db.query(models.Informe).filter_by(liquidacion_id=liq_row.id).all()
    claves = [inf.archivo_key for inf in informes]
    for inf in informes:
        db.delete(inf)
    for h in db.query(models.Hallazgo).filter_by(liquidacion_id=liq_row.id, origen="liquidacion").all():
        h.publicado = False
    return claves


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
        if clave in vistos:      # colisión (misma regla y clave/refs/título): desambiguar
            i, base_clave = 2, clave
            while clave in vistos:
                clave = f"{base_clave[:490]}~{i}"
                i += 1
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
            claves = limpiar_al_rechazar(db, storage, liq_row)
            liq_row.estado = "no_cuadra"
            db.commit()
            for clave in claves:
                storage.borrar(clave)
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
        # Los datos cambiaron: cualquier informe ya generado para esta liquidación (publicada
        # o no; el endpoint de subida resetea el estado a "procesando" antes de llegar acá, así
        # que no sirve mirar el estado) queda inválido. El auditor revisa y vuelve a publicar;
        # acá no se auto-publica un informe nuevo.
        informes = db.query(models.Informe).filter_by(liquidacion_id=liq_row.id).all()
        claves = [inf.archivo_key for inf in informes]
        for inf in informes:
            db.delete(inf)
        liq_row.estado, liq_row.error = "procesada", ""
        db.commit()
        for clave in claves:
            storage.borrar(clave)
    except Exception as e:
        db.rollback()
        logger.exception("Falló la ingesta de la liquidación %s", liq_id)
        liq_row = db.get(models.Liquidacion, liq_id)
        liq_row.estado = "error"
        liq_row.error = (str(e) if isinstance(e, ValueError) else f"{type(e).__name__}: {e}")[:2000]
        db.commit()


def _sin_rutas_invalidas(nombres: Iterable[str]) -> bool:
    for n in nombres:
        p = pathlib.PurePosixPath(n)
        if p.is_absolute() or ".." in p.parts:
            return False
    return True


MAX_ARCHIVOS_ZIP = 1000
MAX_BYTES_ZIP_DESCOMPRIMIDO = 500 * 1024 * 1024


def cruzar_comprobantes(db: Session, liq_id: int, zip_bytes: bytes, storage) -> None:
    """Descomprime el ZIP del portal (carpeta que genera `ct descargar`, con su manifest.json),
    corre el cruce del motor contra la liquidación ya procesada y persiste documentos y
    hallazgos (origen "comprobantes"). Reemplaza los documentos de una subida anterior.

    Nada se toca en la base hasta validar el ZIP entero: manifiesto presente, con filas del
    período de esta liquidación, y con todos los archivos que cita realmente adentro. Así un
    ZIP equivocado (otro mes, o incompleto) nunca deja la liquidación sin evidencia."""
    liq_row = db.get(models.Liquidacion, liq_id)
    if liq_row is None:
        raise ValueError("No existe esa liquidación")
    with tempfile.TemporaryDirectory() as tmp:
        with zipfile.ZipFile(io.BytesIO(zip_bytes)) as z:
            infos = z.infolist()
            if not _sin_rutas_invalidas(i.filename for i in infos):
                raise ValueError("ZIP con rutas inválidas")
            if len(infos) > MAX_ARCHIVOS_ZIP:
                raise ValueError("El ZIP trae demasiados archivos")
            if sum(i.file_size for i in infos) > MAX_BYTES_ZIP_DESCOMPRIMIDO:
                raise ValueError("El ZIP descomprimido supera los 500 MB")
            z.extractall(tmp)
        manifiestos = list(pathlib.Path(tmp).rglob("manifest.json"))
        if not manifiestos:
            raise ValueError("El ZIP no trae manifest.json (usar la carpeta que genera ct descargar)")
        carpeta = manifiestos[0].parent
        items = cargar_manifiesto_redconar(str(manifiestos[0]), str(carpeta), mes=liq_row.periodo)
        if not items:
            raise ValueError(f"El ZIP no trae comprobantes del período {liq_row.periodo} (¿es de otro mes?)")
        rutas = [p for it in items for p in it.adjuntos]
        faltan = [pathlib.Path(r).name for r in rutas if not pathlib.Path(r).exists()]
        if faltan:
            raise ValueError("Archivos citados en el manifiesto que no están en el ZIP: " + ", ".join(faltan[:5]))

        liq = cargar_engine(storage, liq_row)
        docs, hallazgos = cruzar(liq, items)
        # `Documento.archivo` del motor es solo el basename (se calcula con os.path.basename);
        # los nombres que genera `ct descargar` ya son únicos dentro de un mismo mes, así que
        # alcanza con el basename para la clave de storage.
        anteriores = {d.archivo_key for d in
                     db.query(models.Documento).filter_by(liquidacion_id=liq_row.id).all()}
        db.query(models.Documento).filter_by(liquidacion_id=liq_row.id).delete()
        nuevas = set()
        for d, ruta in zip(docs, rutas, strict=True):
            origen_path = pathlib.Path(ruta)
            key = f"comprobantes/{liq_row.periodo}/{origen_path.name}"
            storage.guardar(key, origen_path.read_bytes())
            nuevas.add(key)
            db.add(models.Documento(liquidacion_id=liq_row.id, gasto_n=d.gasto_n, tipo=d.tipo,
                                    archivo_key=key, hash=d.hash, metadatos=d.to_dict()))
        upsert_hallazgos(db, liq_row, hallazgos, origen="comprobantes")
        db.commit()
    # Si esta subida reusa el mismo nombre de archivo que una anterior (resubida del mismo
    # manifiesto), la clave de storage es la misma y ya quedó sobreescrita con el contenido
    # nuevo: no hay que borrarla. Solo se limpian las claves que de verdad quedaron huérfanas.
    for clave in anteriores - nuevas:
        storage.borrar(clave)
