import io
import json
import zipfile

from app import models

from .test_liquidaciones_api import subir


def zip_comprobantes(liq_datos):
    """Manifiesto con el formato de ct descargar: filas mes/n/fecha/proveedor/valor/archivo,
    con el archivo dentro de la carpeta del mes (así lo arma `portal.descargar_mes`)."""
    g = liq_datos["gastos"][0]
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr("2026-08 Agosto/gasto-001-factura.pdf", b"no es un pdf real")
        z.writestr("manifest.json", json.dumps([
            {"n": g["n"], "mes": "2026-08 Agosto", "fecha": "05-08-2026",
             "proveedor": g["proveedor"], "valor": str(g["importe"]), "factura": g.get("factura_nro"),
             "archivo": "gasto-001-factura.pdf"},
        ]))
    return buf.getvalue()


def test_subir_comprobantes_crea_documentos_y_hallazgos(db, auditor):
    liq_id = subir(auditor).json()["id"]
    datos = db.get(models.Liquidacion, liq_id).datos
    r = auditor.post(f"/liquidaciones/{liq_id}/comprobantes",
                     files={"archivo": ("agosto.zip", zip_comprobantes(datos), "application/zip")})
    assert r.status_code == 200
    assert db.query(models.Documento).filter_by(liquidacion_id=liq_id).count() >= 1
    cruce = db.query(models.Hallazgo).filter_by(liquidacion_id=liq_id, origen="comprobantes").all()
    assert len(cruce) > 0  # al menos los gastos sin comprobante


def test_resubir_no_duplica_documentos(db, auditor):
    liq_id = subir(auditor).json()["id"]
    datos = db.get(models.Liquidacion, liq_id).datos
    z = zip_comprobantes(datos)
    auditor.post(f"/liquidaciones/{liq_id}/comprobantes", files={"archivo": ("a.zip", z, "application/zip")})
    n1 = db.query(models.Documento).count()
    auditor.post(f"/liquidaciones/{liq_id}/comprobantes", files={"archivo": ("a.zip", z, "application/zip")})
    assert db.query(models.Documento).count() == n1


def test_zip_sin_manifiesto_da_error(db, auditor):
    liq_id = subir(auditor).json()["id"]
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr("suelto.txt", b"x")
    r = auditor.post(f"/liquidaciones/{liq_id}/comprobantes",
                     files={"archivo": ("malo.zip", buf.getvalue(), "application/zip")})
    assert r.status_code == 422
