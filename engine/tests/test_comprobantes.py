"""Pruebas del cruce de comprobantes.

Las pruebas con documentos reales corren solo si existe la carpeta local del piloto (datos privados, fuera del repo).
"""
import os
from datetime import date

import pytest

from ct.comprobantes import cuit_valido, nombre_vinculado, cargar_manifiesto_redconar, cruzar
from ct.redconar import parse_text

FIX = os.path.join(os.path.dirname(__file__), "fixtures")
CARPETA = os.path.join(os.environ.get("CT_PRIVADO", os.path.expanduser("~/consorcio-transparente-privado")), "Comprobantes Rivadavia 2069")
MANIFEST = os.path.join(CARPETA, "manifest.json")


def test_cuit_valido():
    assert cuit_valido("33600391459")      # consorcio
    assert cuit_valido("27178395691")      # persona física
    assert cuit_valido("30712121749")
    assert not cuit_valido("23000000000")  # relleno de una factura de servicios
    assert not cuit_valido("33600391450")  # dígito verificador incorrecto


def test_nombre_vinculado_tolera_ortografia():
    nombres = {"Gonzales Ramon": "empleado", "ACOSTA ROSANA": "propietario de 13-B"}
    assert nombre_vinculado("RAMON GONZALEZ\nRIVADAVIA AV. 2069 1 D", nombres) == ("Gonzales Ramon", "empleado")
    assert nombre_vinculado("Razón social: Hermelinda Rosana Acosta", nombres)[1] == "propietario de 13-B"
    assert nombre_vinculado("CONSORCIO DE PROPIETARIOS AV RIVADAVIA 2067 69 71", nombres) is None


@pytest.mark.skipif(not (os.path.isdir(CARPETA) and os.path.exists(MANIFEST)), reason="documentos del piloto no disponibles")
def test_cruce_agosto_2026_detecta_los_casos_conocidos():
    liq = parse_text(open(os.path.join(FIX, "redconar_202608.txt"), encoding="utf-8").read())
    items = cargar_manifiesto_redconar(MANIFEST, CARPETA, mes="2026-08")
    docs, hs = cruzar(liq, items)
    assert len(docs) >= 80
    titulos = " | ".join(h.titulo for h in hs)
    assert "SACZEWICZYK" in titulos and "Acosta" in titulos           # pago a la propietaria
    assert "LEV RENTAL" in titulos                                     # factura a nombre de la propietaria
    assert "Gonzales Ramon (empleado)" in titulos                     # Flow a nombre del encargado
    assert "MATHIL" in titulos                                         # pagado a otra empresa
    assert "1.350.000" in titulos and "Devolución" in titulos          # error de pago y devolución
    assert any("anterior a la factura" in h.titulo for h in hs)        # Peñaloza
    # sin falsos positivos conocidos
    assert not any("EDESUR" in h.titulo and "tercero" in h.titulo for h in hs)
    assert not any("METROGAS" in h.titulo and "tercero" in h.titulo for h in hs)
    crit = [h for h in hs if h.severidad == "CRÍTICO"]
    assert 5 <= len(crit) <= 9


@pytest.mark.skipif(not (os.path.isdir(CARPETA) and os.path.exists(MANIFEST)), reason="documentos del piloto no disponibles")
def test_cruce_julio_2026_efectivo_y_terceros():
    liq = parse_text(open(os.path.join(FIX, "redconar_202607.txt"), encoding="utf-8").read())
    items = cargar_manifiesto_redconar(MANIFEST, CARPETA, mes="2026-07")
    docs, hs = cruzar(liq, items)
    t = " | ".join(h.titulo for h in hs)
    assert "C.S.I" in t and "efectivo" in t
    assert "LOPEZ RAMIREZ" in t
    assert not any("SOLVER" in h.titulo or "DESTAPACIONES" in h.titulo for h in hs if "tercero" in h.titulo or "emisor" in h.titulo)
