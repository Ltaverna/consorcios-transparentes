"""Lectura del QR de ARCA: decodificación pura del payload, lectura de imagen (skip sin
pyzbar), integración en interpretar (el QR es autoritativo) y cross-checks de cruzar."""
import base64
import json
import os
from datetime import date

import pytest

import ct.comprobantes as comprobantes
from ct.comprobantes import Documento, ItemManifiesto, cruzar, interpretar
from ct.model import Liquidacion
from ct.qr import decodificar_payload, leer_qr

FIX = os.path.join(os.path.dirname(__file__), "fixtures")

# Mismo JSON de ejemplo que el codificado en fixtures/qr_arca.png (datos de ejemplo, no privados).
PAYLOAD = {"ver": 1, "fecha": "2026-03-25", "cuit": 30708293632, "ptoVta": 5, "tipoCmp": 6,
           "nroCmp": 56068, "importe": 987969.0, "moneda": "PES", "ctz": 1,
           "tipoDocRec": 80, "nroDocRec": 30712345678, "tipoCodAut": "E", "codAut": 75123456789012}


def _url(payload, strip_padding=False, urlsafe=False):
    raw = json.dumps(payload).encode()
    b64 = (base64.urlsafe_b64encode(raw) if urlsafe else base64.b64encode(raw)).decode()
    if strip_padding:
        b64 = b64.rstrip("=")
    return "https://www.afip.gob.ar/fe/qr/?p=" + b64


# ------------------------------------------------------------------ decodificar_payload

def test_payload_arca_completo():
    q = decodificar_payload(_url(PAYLOAD))
    assert q == {"cuit_emisor": "30708293632", "tipo_cmp": 6, "pto_vta": 5, "nro_cmp": 56068,
                 "fecha": "2026-03-25", "importe": 987969.0, "moneda": "PES",
                 "cuit_receptor": "30712345678", "cae": "75123456789012"}


def test_padding_faltante_y_urlsafe():
    assert decodificar_payload(_url(PAYLOAD, strip_padding=True))["importe"] == 987969.0
    assert decodificar_payload(_url(PAYLOAD, urlsafe=True))["cuit_emisor"] == "30708293632"
    assert decodificar_payload(_url(PAYLOAD, urlsafe=True, strip_padding=True))["nro_cmp"] == 56068


def test_json_roto_devuelve_none():
    b64 = base64.b64encode(b'{"ver": 1, "cuit":').decode()
    assert decodificar_payload("https://www.afip.gob.ar/fe/qr/?p=" + b64) is None


def test_url_no_arca_devuelve_none():
    assert decodificar_payload("https://ejemplo.com/?p=eyJ2ZXIiOjF9") is None
    assert decodificar_payload("https://www.afip.gob.ar/fe/qr/") is None
    assert decodificar_payload("no es una url") is None


def test_host_spoofing_devuelve_none():
    # afip.gob.ar como subdominio de un host malicioso → None
    assert decodificar_payload(_url(PAYLOAD).replace("www.afip.gob.ar", "afip.gob.ar.evil.com")) is None
    # afip.gob.ar como credencial (userinfo) → None
    assert decodificar_payload(_url(PAYLOAD).replace("www.afip.gob.ar", "www.afip.gob.ar@evil.com")) is None
    # host legítimo con subdominio → decodifica
    assert decodificar_payload(_url(PAYLOAD))["nro_cmp"] == 56068


def test_tipo_doc_receptor_distinto_de_80_sin_cuit_receptor():
    p = dict(PAYLOAD, tipoDocRec=96, nroDocRec=12345678)   # DNI, no CUIT
    q = decodificar_payload(_url(p))
    assert q["cuit_receptor"] is None
    assert q["cuit_emisor"] == "30708293632"


def test_fecha_en_ambos_formatos():
    assert decodificar_payload(_url(dict(PAYLOAD, fecha="2026-03-25")))["fecha"] == "2026-03-25"
    assert decodificar_payload(_url(dict(PAYLOAD, fecha="20260325")))["fecha"] == "2026-03-25"


def test_campos_ausentes_quedan_en_none():
    q = decodificar_payload(_url({"ver": 1, "fecha": "2026-03-25"}))
    assert q["cuit_emisor"] is None and q["importe"] is None and q["cuit_receptor"] is None


# ------------------------------------------------------------------ lectura de imagen (skip sin pyzbar)

def test_leer_qr_de_imagen():
    pytest.importorskip("pyzbar")
    q = leer_qr(os.path.join(FIX, "qr_arca.png"))
    assert q is not None
    assert q["cuit_emisor"] == "30708293632"
    assert q["importe"] == 987969.0
    assert q["pto_vta"] == 5 and q["nro_cmp"] == 56068
    assert q["cuit_receptor"] == "30712345678"


def test_leer_qr_archivo_inexistente_devuelve_none():
    assert leer_qr("/no/existe.png") is None


# ------------------------------------------------------------------ interpretar con QR

FACTURA_TEXTO = """                 FACTURA B
 Comp. Nro: 0001-00000099
 Razón Social: PROVEEDOR EJEMPLO SA        CUIT: 30-71212174-9
 Fecha de Emisión: 01/03/2026
 CAE: 75123456789012
 Importe Total: $ 500.000,00
"""

QR_EJEMPLO = {"cuit_emisor": "30708293632", "tipo_cmp": 6, "pto_vta": 5, "nro_cmp": 56068,
              "fecha": "2026-03-25", "importe": 987969.0, "moneda": "PES",
              "cuit_receptor": "30712345678", "cae": "75123456789012"}


def test_interpretar_qr_pisa_los_datos_y_anota_divergencias(monkeypatch):
    monkeypatch.setattr(comprobantes, "leer_texto", lambda path: FACTURA_TEXTO)
    monkeypatch.setattr(comprobantes, "leer_qr", lambda path: dict(QR_EJEMPLO))
    doc = interpretar("fact.pdf", 10, "30-70709095-4")
    assert doc.tipo == "factura"
    assert doc.qr == QR_EJEMPLO
    # el QR es autoritativo
    assert doc.emisor_cuit == "30708293632"
    assert doc.importe == 987969.0
    assert doc.fecha == date(2026, 3, 25)
    assert doc.factura_nro == "0005-00056068"
    assert doc.receptor_cuit == "30712345678"
    # divergencias materiales anotadas (importe y CUIT del texto difieren)
    divs = [n for n in doc.notas if n.startswith("QR: el texto de la factura dice")]
    assert len(divs) == 2
    assert any("500.000" in n and "987.969" in n for n in divs)
    assert any("30712121749" in n and "30708293632" in n for n in divs)


def test_interpretar_qr_sin_divergencias_no_anota(monkeypatch):
    texto = FACTURA_TEXTO.replace("30-71212174-9", "30-70829363-2").replace("500.000,00", "987.969,00")
    monkeypatch.setattr(comprobantes, "leer_texto", lambda path: texto)
    monkeypatch.setattr(comprobantes, "leer_qr", lambda path: dict(QR_EJEMPLO))
    doc = interpretar("fact.pdf", 10, "30-70709095-4")
    assert doc.qr is not None
    assert not any(n.startswith("QR:") for n in doc.notas)


def test_interpretar_imagen_con_qr_pasa_a_factura(monkeypatch):
    monkeypatch.setattr(comprobantes, "leer_texto", lambda path: "")
    monkeypatch.setattr(comprobantes, "leer_qr", lambda path: dict(QR_EJEMPLO))
    doc = interpretar("foto.jpg", 10, "30-70709095-4")
    assert doc.tipo == "factura"
    assert doc.qr == QR_EJEMPLO
    assert doc.importe == 987969.0
    assert doc.factura_nro == "0005-00056068"
    assert any(n == "Clasificada por el QR de ARCA (sin texto extraíble)." for n in doc.notas)


def test_interpretar_sin_qr_no_cambia_nada(monkeypatch):
    monkeypatch.setattr(comprobantes, "leer_texto", lambda path: FACTURA_TEXTO)
    monkeypatch.setattr(comprobantes, "leer_qr", lambda path: None)
    doc = interpretar("fact.pdf", 10, "30-70709095-4")
    assert doc.qr is None
    assert doc.tipo == "factura"
    assert doc.importe == 500_000.0
    assert doc.emisor_cuit == "30712121749"
    assert doc.factura_nro == "0001-00000099"
    monkeypatch.setattr(comprobantes, "leer_texto", lambda path: "")
    doc = interpretar("foto.jpg", 10, "30-70709095-4")
    assert doc.tipo == "imagen" and doc.qr is None


def test_documento_qr_viaja_en_to_dict():
    d = Documento(archivo="a.pdf", gasto_n=1, qr=dict(QR_EJEMPLO))
    assert d.to_dict()["qr"]["cuit_emisor"] == "30708293632"


# ------------------------------------------------------------------ cross-checks en cruzar

from ct.model import Gasto  # noqa: E402


def _liq_qr(factura_nro=None):
    liq = Liquidacion(sistema="test", periodo="Marzo 2026", cuit_consorcio="30-70709095-4")
    g = Gasto(n=10, categoria="ABONOS Y SERVICIOS", proveedor="PROVEEDOR EJEMPLO SA",
              concepto="Servicio", columna="A", importe=987_969.0, factura_nro=factura_nro)
    liq.gastos = [g]
    return liq


def _cruzar_con_doc(monkeypatch, liq, doc):
    monkeypatch.setattr(comprobantes, "interpretar", lambda path, gasto_n, cuit: doc)
    item = ItemManifiesto(None, "PROVEEDOR EJEMPLO SA", 987_969.0, None, ["fact.pdf"])
    _, hs = cruzar(liq, [item])
    return hs


def _doc_qr(factura_nro="0005-00056068", notas=()):
    d = Documento(archivo="fact.pdf", gasto_n=10, tipo="factura", texto_len=500,
                  qr=dict(QR_EJEMPLO), factura_nro=factura_nro,
                  emisor_cuit="30708293632", receptor_cuit="30707090954",
                  importe=987_969.0, fecha=date(2026, 3, 25))
    d.notas = list(notas)
    return d


def test_cruzar_qr_texto_dispara_con_nota_de_divergencia(monkeypatch):
    doc = _doc_qr(notas=["QR: el texto de la factura dice importe $500.000,00 pero el QR de ARCA dice $987.969,00."])
    hs = _cruzar_con_doc(monkeypatch, _liq_qr(), doc)
    h = next(x for x in hs if x.clave == "qr-texto")
    assert h.severidad == "ALTO"
    assert "no coincide con su QR de ARCA" in h.titulo and "PROVEEDOR EJEMPLO SA" in h.titulo
    assert "500.000" in h.evidencia
    assert h.monto == 0 and h.refs == ["10"]


def test_cruzar_qr_numeracion_dispara_con_otra_factura(monkeypatch):
    hs = _cruzar_con_doc(monkeypatch, _liq_qr(factura_nro="0001-00000200"), _doc_qr())
    h = next(x for x in hs if x.clave == "qr-numeracion")
    assert h.severidad == "MEDIO"
    assert "no es la citada en la liquidación" in h.titulo
    assert "0001-00000200" in h.evidencia and "0005-00056068" in h.evidencia
    assert h.refs == ["10"]


def test_cruzar_qr_numeracion_no_dispara_si_coincide_normalizado(monkeypatch):
    # '5-56068' vs '0005-00056068': misma factura escrita distinto
    hs = _cruzar_con_doc(monkeypatch, _liq_qr(factura_nro="5-56068"), _doc_qr())
    assert not any(x.clave == "qr-numeracion" for x in hs)


def test_cruzar_qr_consistente_no_dispara(monkeypatch):
    hs = _cruzar_con_doc(monkeypatch, _liq_qr(factura_nro="0005-00056068"), _doc_qr())
    assert not any(x.clave in ("qr-texto", "qr-numeracion") for x in hs)


def test_cruzar_sin_nro_en_liquidacion_no_dispara_numeracion(monkeypatch):
    hs = _cruzar_con_doc(monkeypatch, _liq_qr(factura_nro=None), _doc_qr())
    assert not any(x.clave == "qr-numeracion" for x in hs)


# ---- bare-number: citación sin punto de venta no es divergencia ----

def _doc_qr_nro(pto_vta, nro_cmp):
    """Documento con QR cuyo nroCmp = nro_cmp (para tests de bare-number)."""
    qr = dict(QR_EJEMPLO, pto_vta=pto_vta, nro_cmp=nro_cmp)
    factura_nro = f"{pto_vta:04d}-{nro_cmp:08d}"
    d = Documento(archivo="fact.pdf", gasto_n=10, tipo="factura", texto_len=500,
                  qr=qr, factura_nro=factura_nro,
                  emisor_cuit="30708293632", receptor_cuit="30707090954",
                  importe=987_969.0, fecha=date(2026, 3, 25))
    d.notas = []
    return d


def test_cruzar_qr_numeracion_bare_igual_nro_no_dispara(monkeypatch):
    # liquidación cita "8675" (sin ptoVta); QR dice ptoVta=5, nroCmp=8675 → misma factura
    hs = _cruzar_con_doc(monkeypatch, _liq_qr(factura_nro="8675"), _doc_qr_nro(5, 8675))
    assert not any(x.clave == "qr-numeracion" for x in hs)


def test_cruzar_qr_numeracion_bare_ceros_no_dispara(monkeypatch):
    # "00007897" normalizado es "7897" (bare), QR nroCmp=7897 → misma factura
    hs = _cruzar_con_doc(monkeypatch, _liq_qr(factura_nro="00007897"), _doc_qr_nro(3, 7897))
    assert not any(x.clave == "qr-numeracion" for x in hs)


def test_cruzar_qr_numeracion_bare_nro_distinto_dispara(monkeypatch):
    # "9234" (bare) vs QR nroCmp=19234 → distinto comprobante → hallazgo
    hs = _cruzar_con_doc(monkeypatch, _liq_qr(factura_nro="9234"), _doc_qr_nro(5, 19234))
    assert any(x.clave == "qr-numeracion" for x in hs)


def test_cruzar_qr_numeracion_pto_vta_completo_no_dispara(monkeypatch):
    # "0501-76051312" completo: ptoVta=501, nroCmp=76051312 → coincide
    hs = _cruzar_con_doc(monkeypatch, _liq_qr(factura_nro="0501-76051312"), _doc_qr_nro(501, 76051312))
    assert not any(x.clave == "qr-numeracion" for x in hs)
