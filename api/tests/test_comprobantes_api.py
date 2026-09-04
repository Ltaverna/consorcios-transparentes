import io
import json
import zipfile

from app import admin, models
from app.config import settings

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


def test_resubir_con_otro_manifiesto_borra_el_archivo_huerfano(db, auditor, tmp_path):
    """Al resubir con un manifiesto distinto (otro nombre de archivo), el Documento viejo
    desaparece de la base y su archivo en storage no puede quedar huérfano."""
    liq_id = subir(auditor).json()["id"]
    datos = db.get(models.Liquidacion, liq_id).datos
    auditor.post(f"/liquidaciones/{liq_id}/comprobantes",
                files={"archivo": ("a.zip", zip_comprobantes(datos), "application/zip")})
    clave_vieja = db.query(models.Documento).filter_by(liquidacion_id=liq_id).first().archivo_key
    assert (tmp_path / clave_vieja).exists()

    g = datos["gastos"][0]
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr("2026-08 Agosto/otro-archivo.pdf", b"no es un pdf real")
        z.writestr("manifest.json", json.dumps([
            {"n": g["n"], "mes": "2026-08 Agosto", "fecha": "05-08-2026",
             "proveedor": g["proveedor"], "valor": str(g["importe"]), "factura": g.get("factura_nro"),
             "archivo": "otro-archivo.pdf"},
        ]))
    r = auditor.post(f"/liquidaciones/{liq_id}/comprobantes",
                     files={"archivo": ("b.zip", buf.getvalue(), "application/zip")})
    assert r.status_code == 200
    assert not (tmp_path / clave_vieja).exists()


def test_zip_sin_manifiesto_da_error(db, auditor):
    liq_id = subir(auditor).json()["id"]
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr("suelto.txt", b"x")
    r = auditor.post(f"/liquidaciones/{liq_id}/comprobantes",
                     files={"archivo": ("malo.zip", buf.getvalue(), "application/zip")})
    assert r.status_code == 422


def test_zip_de_otro_periodo_no_borra_la_evidencia_cargada(db, auditor):
    """Si el manifiesto no trae ninguna fila del período de esta liquidación (p. ej. se subió
    el ZIP de otro mes por error), no puede vaciar en silencio los documentos ya cargados."""
    liq_id = subir(auditor).json()["id"]
    datos = db.get(models.Liquidacion, liq_id).datos
    auditor.post(f"/liquidaciones/{liq_id}/comprobantes",
                files={"archivo": ("agosto.zip", zip_comprobantes(datos), "application/zip")})
    n_previo = db.query(models.Documento).filter_by(liquidacion_id=liq_id).count()
    assert n_previo >= 1

    g = datos["gastos"][0]
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr("2026-05 Mayo/gasto-001-factura.pdf", b"no es un pdf real")
        z.writestr("manifest.json", json.dumps([
            {"n": g["n"], "mes": "2026-05 Mayo", "fecha": "05-05-2026",
             "proveedor": g["proveedor"], "valor": str(g["importe"]), "factura": g.get("factura_nro"),
             "archivo": "gasto-001-factura.pdf"},
        ]))
    r = auditor.post(f"/liquidaciones/{liq_id}/comprobantes",
                     files={"archivo": ("mayo.zip", buf.getvalue(), "application/zip")})
    assert r.status_code == 422
    assert db.query(models.Documento).filter_by(liquidacion_id=liq_id).count() == n_previo


def test_zip_con_manifiesto_que_cita_archivo_ausente_da_error(db, auditor):
    liq_id = subir(auditor).json()["id"]
    datos = db.get(models.Liquidacion, liq_id).datos
    g = datos["gastos"][0]
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        # el manifiesto cita un archivo que no está en el ZIP
        z.writestr("manifest.json", json.dumps([
            {"n": g["n"], "mes": "2026-08 Agosto", "fecha": "05-08-2026",
             "proveedor": g["proveedor"], "valor": str(g["importe"]), "factura": g.get("factura_nro"),
             "archivo": "no-esta.pdf"},
        ]))
    r = auditor.post(f"/liquidaciones/{liq_id}/comprobantes",
                     files={"archivo": ("incompleto.zip", buf.getvalue(), "application/zip")})
    assert r.status_code == 422


def test_solo_auditor_sube_comprobantes(db, cliente, auditor):
    liq_id = subir(auditor).json()["id"]
    admin.crear_usuario(db, "c2@example.com", "C", "consejo", "clave-de-test")
    cliente.post("/auth/login", json={"email": "c2@example.com", "clave": "clave-de-test"})
    r = cliente.post(f"/liquidaciones/{liq_id}/comprobantes",
                     files={"archivo": ("x.zip", b"da igual", "application/zip")})
    assert r.status_code == 403


def test_comprobantes_demasiado_grande_413(db, auditor):
    liq_id = subir(auditor).json()["id"]
    tope = settings.max_zip_mb * 1024 * 1024
    r = auditor.post(f"/liquidaciones/{liq_id}/comprobantes",
                     files={"archivo": ("x.zip", b"x" * (tope + 1), "application/zip")})
    assert r.status_code == 413


def test_comprobantes_zip_slip_da_422(db, auditor):
    liq_id = subir(auditor).json()["id"]
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr("../fuera.txt", b"x")
        z.writestr("manifest.json", json.dumps([]))
    r = auditor.post(f"/liquidaciones/{liq_id}/comprobantes",
                     files={"archivo": ("slip.zip", buf.getvalue(), "application/zip")})
    assert r.status_code == 422


def test_flujo_completo_subir_comprobantes_publicar(db, auditor, tmp_path):
    liq_id = subir(auditor).json()["id"]
    datos = db.get(models.Liquidacion, liq_id).datos
    r = auditor.post(f"/liquidaciones/{liq_id}/comprobantes",
                     files={"archivo": ("agosto.zip", zip_comprobantes(datos), "application/zip")})
    assert r.status_code == 200
    r = auditor.post(f"/liquidaciones/{liq_id}/publicar")
    assert r.status_code == 200
    assert db.query(models.Informe).filter_by(liquidacion_id=liq_id).count() == 2
