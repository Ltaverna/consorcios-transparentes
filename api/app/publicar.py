"""Publicar = generar los informes del motor con los hallazgos aprobados y marcar la liquidación."""
import pathlib
import tempfile
from datetime import date

from sqlalchemy.orm import Session

from ct.comprobantes import Documento as DocumentoMotor
from ct.informe import informe_excel, informe_html
from ct.rules import Hallazgo as HallazgoMotor

from . import ingesta, models


def _hallazgos_motor(liq_row: models.Liquidacion) -> list[HallazgoMotor]:
    orden = {"CRÍTICO": 0, "ALTO": 1, "MEDIO": 2, "BAJO": 3}
    filas = sorted((h for h in liq_row.hallazgos if h.publicado),
                   key=lambda h: (orden.get(h.severidad, 9), -abs(h.monto)))
    return [HallazgoMotor(regla=h.regla, severidad=h.severidad, area=h.area, titulo=h.titulo,
                          evidencia=h.evidencia, monto=h.monto, recomendacion=h.recomendacion,
                          refs=list(h.refs)) for h in filas]


def _documentos_motor(db: Session, liq_row: models.Liquidacion) -> list[DocumentoMotor]:
    docs = []
    for d in db.query(models.Documento).filter_by(liquidacion_id=liq_row.id):
        md = dict(d.metadatos)
        if md.get("fecha"):
            md["fecha"] = date.fromisoformat(md["fecha"])
        docs.append(DocumentoMotor(**md))
    return docs


def publicar(db: Session, liq_id: int, storage) -> dict:
    liq_row = db.get(models.Liquidacion, liq_id)
    if liq_row.estado not in ("procesada", "publicada"):
        raise ValueError(f"No se puede publicar en estado {liq_row.estado}: primero tiene que cuadrar")
    consorcio = db.query(models.Consorcio).first()
    marca = consorcio.marca if consorcio else "Consorcio Transparente"
    liq = ingesta.cargar_engine(storage, liq_row)
    prev = ingesta.cargar_anterior(db, storage, liq_row.periodo)
    hs = _hallazgos_motor(liq_row)
    docs = _documentos_motor(db, liq_row)

    with tempfile.TemporaryDirectory() as tmp:
        rutas = {"html": pathlib.Path(tmp) / "informe.html", "xlsx": pathlib.Path(tmp) / "informe.xlsx"}
        informe_html(liq, hs, str(rutas["html"]), prev, docs, marca)
        informe_excel(liq, hs, str(rutas["xlsx"]), prev, docs, marca)
        for tipo, ruta in rutas.items():
            key = f"informes/{liq_row.periodo}.{tipo}"
            storage.guardar(key, ruta.read_bytes())
            fila = db.query(models.Informe).filter_by(liquidacion_id=liq_row.id, tipo=tipo).first()
            if not fila:
                fila = models.Informe(liquidacion_id=liq_row.id, tipo=tipo, archivo_key=key)
                db.add(fila)
            fila.archivo_key, fila.marca, fila.publicado_en = key, marca, models.ahora()
    liq_row.estado = "publicada"
    db.commit()
    return {"hallazgos_publicados": len(hs)}
