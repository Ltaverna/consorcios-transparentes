"""Lógica de sincronización con portal y API falsos (sin red)."""
import json

import pytest

from ct.sincronizar import Sincronizador, periodo_api, zip_determinista


class PortalFalso:
    def __init__(self, periodos, liquidaciones):
        self._periodos = periodos          # [("2026-8", "Agosto 2026"), ...]
        self._liq = liquidaciones          # {"2026-8": (b"%PDF-...", "2026-08-31-x.pdf")}
        self.descargas_mes = []
    def periodos(self):
        return self._periodos
    def liquidacion(self, periodo):
        return self._liq.get(periodo)
    def descargar_mes(self, periodo, carpeta, log=print):
        self.descargas_mes.append(periodo)
        return []


class ApiFalsa:
    def __init__(self):
        self.liqs = {}                     # periodo -> dict de la API
        self.subidas = []                  # (tipo, periodo)
        self.zips = []
    def login(self): pass
    def liquidaciones(self):
        return list(self.liqs.values())
    def subir_liquidacion(self, periodo, pdf_bytes, nombre):
        self.subidas.append(("liq", periodo))
        self.liqs[periodo] = {"id": len(self.liqs) + 1, "periodo": periodo, "estado": "procesada",
                              "cuadra": True, "error": ""}
        return self.liqs[periodo]
    def detalle(self, liq_id):
        return next(l for l in self.liqs.values() if l["id"] == liq_id) | {"checks_ok": 30, "checks_mal": 0}
    def subir_comprobantes(self, liq_id, zip_bytes):
        self.zips.append(liq_id)
        return {"ok": True, "documentos": 2, "hallazgos_cruce": 1}


def armar_carpetas(tmp_path, periodo_carpeta="2026-08 Agosto"):
    (tmp_path / "liquidaciones").mkdir()
    mes = tmp_path / "Comprobantes Rivadavia 2069" / periodo_carpeta
    mes.mkdir(parents=True)
    (mes / "01-1 doc.pdf").write_bytes(b"%PDF-doc")
    (tmp_path / "Comprobantes Rivadavia 2069" / "manifest.json").write_text("[]")
    return tmp_path


def test_mes_nuevo_baja_e_ingesta_todo(tmp_path):
    armar_carpetas(tmp_path)
    portal = PortalFalso([("2026-8", "Agosto 2026")], {"2026-8": (b"%PDF-agosto", "2026-08-31-liq.pdf")})
    api = ApiFalsa()
    s = Sincronizador(portal, api, str(tmp_path))
    rc = s.correr()
    assert rc == 0
    assert (tmp_path / "liquidaciones" / "2026-08-31-liq.pdf").read_bytes() == b"%PDF-agosto"
    assert portal.descargas_mes == ["2026-8"]
    assert ("liq", "2026-08") in api.subidas and api.zips  # subió PDF y ZIP
    estado = json.loads((tmp_path / "sincronizacion.json").read_text())
    assert estado["2026-08"]["liquidacion_subida"] and estado["2026-08"]["zip_hash"]


def test_sin_cambios_no_resube_nada(tmp_path):
    armar_carpetas(tmp_path)
    portal = PortalFalso([("2026-8", "Agosto 2026")], {"2026-8": (b"%PDF-agosto", "2026-08-31-liq.pdf")})
    api = ApiFalsa()
    s = Sincronizador(portal, api, str(tmp_path))
    assert s.correr() == 0
    subidas = list(api.subidas); zips = list(api.zips)
    assert s.correr() == 0                      # segunda corrida, nada cambió
    assert api.subidas == subidas and api.zips == zips


def test_comprobante_nuevo_resube_solo_el_zip(tmp_path):
    armar_carpetas(tmp_path)
    portal = PortalFalso([("2026-8", "Agosto 2026")], {"2026-8": (b"%PDF-agosto", "2026-08-31-liq.pdf")})
    api = ApiFalsa()
    s = Sincronizador(portal, api, str(tmp_path))
    s.correr()
    (tmp_path / "Comprobantes Rivadavia 2069" / "2026-08 Agosto" / "02-1 nuevo.pdf").write_bytes(b"%PDF-n")
    n_liq = len([x for x in api.subidas if x[0] == "liq"])
    s.correr()
    assert len([x for x in api.subidas if x[0] == "liq"]) == n_liq   # liquidación no se re-sube
    assert len(api.zips) == 2                                        # el ZIP sí


def test_no_cuadra_corta_con_error(tmp_path):
    armar_carpetas(tmp_path)
    portal = PortalFalso([("2026-8", "Agosto 2026")], {"2026-8": (b"%PDF-agosto", "2026-08-31-liq.pdf")})
    api = ApiFalsa()
    def subir_mal(periodo, pdf_bytes, nombre):
        api.subidas.append(("liq", periodo))
        api.liqs[periodo] = {"id": 1, "periodo": periodo, "estado": "no_cuadra", "cuadra": False,
                             "error": "no cuadra"}
        return api.liqs[periodo]
    api.subir_liquidacion = subir_mal
    s = Sincronizador(portal, api, str(tmp_path))
    assert s.correr() != 0
    assert not api.zips                                              # no siguió con comprobantes
    estado = json.loads((tmp_path / "sincronizacion.json").read_text())
    assert not estado.get("2026-08", {}).get("liquidacion_subida")   # queda pendiente para reintentar


def test_reconcilia_con_liquidaciones_ya_ingresadas_a_mano(tmp_path):
    armar_carpetas(tmp_path)
    (tmp_path / "liquidaciones" / "2026-08-31-liq.pdf").write_bytes(b"%PDF-agosto")
    portal = PortalFalso([("2026-8", "Agosto 2026")], {})
    api = ApiFalsa()
    api.liqs["2026-08"] = {"id": 7, "periodo": "2026-08", "estado": "publicada", "cuadra": True, "error": ""}
    s = Sincronizador(portal, api, str(tmp_path))
    assert s.correr() == 0
    assert not [x for x in api.subidas if x[0] == "liq"]             # no re-sube lo que la API ya tiene
    assert api.zips                                                  # pero el ZIP inicial sí (hash nuevo)


def test_periodo_api():
    assert periodo_api("2026-8") == "2026-08"
    assert periodo_api("2026-11") == "2026-11"


def test_zip_determinista(tmp_path):
    d = tmp_path / "m"; d.mkdir()
    (d / "b.pdf").write_bytes(b"B"); (d / "a.pdf").write_bytes(b"A")
    z1 = zip_determinista(str(d))
    z2 = zip_determinista(str(d))
    assert z1 == z2 and len(z1) > 0


def test_zip_con_prefijo_replica_el_layout_de_la_carpeta(tmp_path):
    import zipfile, io
    d = tmp_path / "2026-08 Agosto"; d.mkdir()
    (d / "01-1 doc.pdf").write_bytes(b"%PDF-doc")
    z = zip_determinista(str(d), extra={"manifest.json": b"[]"}, prefijo="2026-08 Agosto")
    nombres = zipfile.ZipFile(io.BytesIO(z)).namelist()
    assert "2026-08 Agosto/01-1 doc.pdf" in nombres and "manifest.json" in nombres
