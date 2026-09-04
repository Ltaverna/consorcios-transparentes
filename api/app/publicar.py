"""Publicar = generar los informes del motor con los hallazgos aprobados y marcar la liquidación."""
import dataclasses
import pathlib
import tempfile
import uuid
from datetime import date

from sqlalchemy.orm import Session

from ct.comprobantes import Documento as DocumentoMotor
from ct.informe import informe_excel, informe_html
from ct.rules import Hallazgo as HallazgoMotor

from . import ingesta, models

_CAMPOS_DOCUMENTO = {f.name for f in dataclasses.fields(DocumentoMotor)}


def _hallazgos_motor(liq_row: models.Liquidacion) -> list[HallazgoMotor]:
    orden = {"CRÍTICO": 0, "ALTO": 1, "MEDIO": 2, "BAJO": 3}
    filas = sorted((h for h in liq_row.hallazgos if h.publicado),
                   key=lambda h: (orden.get(h.severidad, 9), -abs(h.monto)))
    return [HallazgoMotor(regla=h.regla, severidad=h.severidad, area=h.area, titulo=h.titulo,
                          evidencia=h.evidencia, monto=h.monto, recomendacion=h.recomendacion,
                          refs=list(h.refs)) for h in filas]


def _documentos_motor(db: Session, liq_row: models.Liquidacion) -> list[DocumentoMotor]:
    """Solo la evidencia (comprobantes) referenciada por hallazgos que el auditor efectivamente
    publicó: publicar hallazgos "no" no puede filtrar los documentos que los respaldan pero
    dejar la evidencia cruda disponible en el informe igual. La tabla de deudores del motor
    no pasa por acá: es parte de la liquidación mensual que los propietarios ya reciben, no
    evidencia del cruce de comprobantes.

    Las refs son un espacio de nombres compartido entre orígenes: en un hallazgo "comprobantes"
    (el que arma `cruzar`) siempre son números de gasto, pero en uno "liquidacion" pueden ser
    UFs de deudores (morosidad) u otra cosa que casualmente coincida con un n de gasto. Por eso
    solo se toman refs de hallazgos origen="comprobantes"."""
    ns = {int(r) for h in liq_row.hallazgos if h.publicado and h.origen == "comprobantes"
          for r in h.refs if str(r).isdigit()}
    docs = []
    for d in db.query(models.Documento).filter_by(liquidacion_id=liq_row.id):
        if d.gasto_n not in ns:
            continue
        md = {k: v for k, v in d.metadatos.items() if k in _CAMPOS_DOCUMENTO}
        if md.get("fecha"):
            md["fecha"] = date.fromisoformat(md["fecha"])
        docs.append(DocumentoMotor(**md))
    return docs


def publicar(db: Session, liq_id: int, storage) -> dict:
    liq_row = db.get(models.Liquidacion, liq_id)
    if not liq_row:
        raise ValueError("No existe esa liquidación")
    if liq_row.estado not in ("procesada", "publicada"):
        raise ValueError(f"No se puede publicar en estado {liq_row.estado}: primero tiene que cuadrar")
    if not liq_row.cuadra:
        raise ValueError("La liquidación no cuadra: no se puede publicar")
    archivo_key_inicial = liq_row.archivo_key
    consorcio = db.query(models.Consorcio).first()
    marca = consorcio.marca if consorcio else "Consorcio Transparente"
    liq = ingesta.cargar_engine(storage, liq_row)
    prev = ingesta.cargar_anterior(db, storage, liq_row.periodo)
    hs = _hallazgos_motor(liq_row)
    docs = _documentos_motor(db, liq_row)

    # Claves versionadas con un sello único por publicación: una resubida de comprobantes que
    # dispare una republicación mientras alguien está leyendo el informe anterior no le pisa el
    # archivo por debajo. El sello lleva un uuid además del timestamp porque `strftime` tiene
    # resolución de un segundo: dos publicaciones seguidas (republicar, o el test) caen fácil en
    # el mismo segundo, y una clave repetida + "borrar las claves viejas" borraría el archivo
    # recién escrito. Por las dudas, además, solo se borra lo que quedó huérfano de verdad
    # (mismo patrón que en `cruzar_comprobantes`): la intersección con las claves nuevas nunca
    # se toca.
    sello = f"{models.ahora().strftime('%Y%m%d%H%M%S')}-{uuid.uuid4().hex[:8]}"
    claves_viejas = {inf.archivo_key for inf in
                     db.query(models.Informe).filter_by(liquidacion_id=liq_row.id).all()}
    claves_nuevas = set()
    with tempfile.TemporaryDirectory() as tmp:
        rutas = {"html": pathlib.Path(tmp) / "informe.html", "xlsx": pathlib.Path(tmp) / "informe.xlsx"}
        informe_html(liq, hs, str(rutas["html"]), prev, docs, marca)
        informe_excel(liq, hs, str(rutas["xlsx"]), prev, docs, marca)
        for tipo, ruta in rutas.items():
            key = f"informes/{liq_row.periodo}-{sello}.{tipo}"
            storage.guardar(key, ruta.read_bytes())
            claves_nuevas.add(key)
            fila = db.query(models.Informe).filter_by(liquidacion_id=liq_row.id, tipo=tipo).first()
            if not fila:
                fila = models.Informe(liquidacion_id=liq_row.id, tipo=tipo, archivo_key=key)
                db.add(fila)
            fila.archivo_key, fila.marca, fila.publicado_en = key, marca, models.ahora()
    # La liquidación pudo cambiar mientras se generaban los informes (un reproceso concurrente
    # reemplaza el archivo y reinicia el estado): si eso pasó, no se confirma la publicación
    # sobre datos que ya no son los que se leyeron.
    db.refresh(liq_row)
    if liq_row.estado not in ("procesada", "publicada") or liq_row.archivo_key != archivo_key_inicial:
        db.rollback()
        # Los informes nuevos ya se escribieron en storage pero la fila que los referencia
        # nunca se confirmó: no pueden quedar huérfanos.
        for clave in claves_nuevas:
            storage.borrar(clave)
        raise ValueError("La liquidación cambió mientras se publicaba; revisala y volvé a publicar")
    liq_row.estado = "publicada"
    db.commit()
    for clave in claves_viejas - claves_nuevas:
        storage.borrar(clave)
    return {"hallazgos_publicados": len(hs)}
