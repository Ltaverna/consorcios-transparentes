"""Búsqueda semántica: columna embedding (TypeDecorator dual), población en la
ingesta de comprobantes y endpoint /consulta/semantica. El cliente real de
embeddings nunca se llama acá: sin key queda deshabilitado (conftest) y los
tests que necesitan vectores lo stubean."""
import io
import json
import zipfile

from app import admin, models
from app.config import settings
from app.texto import fragmento_relevante

from .test_documentos_api import pdf_minimo
from .test_liquidaciones_api import subir


def zip_con_pdf_real(liq_datos):
    """Como zip_comprobantes de test_comprobantes_api pero con un PDF de verdad
    (pdf_minimo), para que extraer_texto tenga algo que embeber."""
    g = liq_datos["gastos"][0]
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr("2026-08 Agosto/gasto-001-factura.pdf",
                   pdf_minimo("FACTURA B 0001-00001111 IMPERMEABILIZACION DE TERRAZA"))
        z.writestr("manifest.json", json.dumps([
            {"n": g["n"], "mes": "2026-08 Agosto", "fecha": "05-08-2026",
             "proveedor": g["proveedor"], "valor": str(g["importe"]),
             "factura": g.get("factura_nro"), "archivo": "gasto-001-factura.pdf"},
        ]))
    return buf.getvalue()


def _habilitar(monkeypatch, vectores_por_llamada):
    """Activa la key (para que la ingesta/el endpoint no se salteen el paso) y stubea
    el cliente para que devuelva vectores fijos sin tocar la red."""
    monkeypatch.setattr(settings, "embeddings_api_key", "clave-de-test")

    llamadas = []

    def stub(textos):
        llamadas.append(list(textos))
        return vectores_por_llamada(textos)

    monkeypatch.setattr("app.embeddings.embeber", stub)
    return llamadas


def test_typedecorator_guarda_y_lee_lista_de_floats_en_sqlite(db):
    liq = models.Liquidacion(periodo="2026-08", archivo_key="x.pdf")
    db.add(liq)
    db.flush()
    db.add(models.Documento(liquidacion_id=liq.id, tipo="factura", archivo_key="k.pdf",
                            embedding=[0.25, -1.5, 3.0]))
    db.commit()
    db.expire_all()
    row = db.query(models.Documento).one()
    assert row.embedding == [0.25, -1.5, 3.0]


def test_ingesta_puebla_embeddings(db, auditor, monkeypatch):
    llamadas = _habilitar(monkeypatch, lambda textos: [[1.0, 0.0, 0.0] for _ in textos])
    liq_id = subir(auditor).json()["id"]
    datos = db.get(models.Liquidacion, liq_id).datos
    r = auditor.post(f"/liquidaciones/{liq_id}/comprobantes",
                     files={"archivo": ("agosto.zip", zip_con_pdf_real(datos), "application/zip")})
    assert r.status_code == 200
    docs = db.query(models.Documento).filter_by(liquidacion_id=liq_id).all()
    assert len(docs) >= 1
    assert all(d.embedding == [1.0, 0.0, 0.0] for d in docs)
    # se embebió el texto extraído del PDF, en batch
    assert len(llamadas) == 1 and "IMPERMEABILIZACION" in llamadas[0][0]


def _tres_documentos(db):
    """Liquidación sintética con 3 documentos de embeddings conocidos y uno sin embedding
    (no extraíble: no debe aparecer nunca en los resultados)."""
    liq = models.Liquidacion(periodo="2026-08", archivo_key="x.txt",
                             estado="procesada", cuadra=True)
    db.add(liq)
    db.flush()
    docs = [
        models.Documento(liquidacion_id=liq.id, gasto_n=1, tipo="factura",
                         archivo_key="comprobantes/2026-08/a.pdf", embedding=[1.0, 0.0, 0.0]),
        models.Documento(liquidacion_id=liq.id, gasto_n=2, tipo="pago",
                         archivo_key="comprobantes/2026-08/b.pdf", embedding=[0.9, 0.9, 0.0]),
        models.Documento(liquidacion_id=liq.id, gasto_n=3, tipo="factura",
                         archivo_key="comprobantes/2026-08/c.pdf", embedding=[0.0, 1.0, 0.0]),
        models.Documento(liquidacion_id=liq.id, gasto_n=4, tipo="imagen",
                         archivo_key="comprobantes/2026-08/d.png", embedding=None),
    ]
    db.add_all(docs)
    db.commit()
    return docs


def test_semantica_rankea_por_coseno(db, auditor, monkeypatch):
    docs = _tres_documentos(db)
    _habilitar(monkeypatch, lambda textos: [[1.0, 0.0, 0.0]])

    r = auditor.get("/consulta/semantica?q=impermeabilizacion")
    assert r.status_code == 200
    res = r.json()["resultados"]
    # el documento sin embedding queda afuera; el resto ordenado por similitud
    assert [f["documento_id"] for f in res] == [docs[0].id, docs[1].id, docs[2].id]
    assert abs(res[0]["similitud"] - 1.0) < 1e-6
    assert abs(res[1]["similitud"] - 0.7071068) < 1e-6  # cos([1,0,0], [0.9,0.9,0]) = 1/√2
    assert abs(res[2]["similitud"] - 0.0) < 1e-6
    assert {"documento_id", "gasto_n", "periodo", "tipo", "similitud", "fragmento"} <= set(res[0])
    assert res[0]["gasto_n"] == 1 and res[0]["periodo"] == "2026-08" and res[0]["tipo"] == "factura"

    # k limita el top
    res2 = auditor.get("/consulta/semantica?q=impermeabilizacion&k=2").json()["resultados"]
    assert [f["documento_id"] for f in res2] == [docs[0].id, docs[1].id]


def test_sin_key_semantica_503_y_la_ingesta_persiste_igual(db, auditor):
    # conftest deja CT_EMBEDDINGS_API_KEY vacía: semántica no configurada
    assert auditor.get("/consulta/semantica?q=x").status_code == 503

    # la ingesta de comprobantes ni se entera: documentos persistidos con embedding NULL
    liq_id = subir(auditor).json()["id"]
    datos = db.get(models.Liquidacion, liq_id).datos
    r = auditor.post(f"/liquidaciones/{liq_id}/comprobantes",
                     files={"archivo": ("agosto.zip", zip_con_pdf_real(datos), "application/zip")})
    assert r.status_code == 200
    docs = db.query(models.Documento).filter_by(liquidacion_id=liq_id).all()
    assert len(docs) >= 1
    assert all(d.embedding is None for d in docs)


# Shape sintético calibrado con las facturas reales de la carpeta privada (monotributo
# emitidas por el sitio de ARCA): encabezado boilerplate, tabla "Producto / Servicio"
# con el ítem, y bloque de totales.
FACTURA_AFIP_SINTETICA = """\
                                                     ORIGINAL

     PLOMERIA SINTETICA S.R.L.                            C          FACTURA
                                                       COD. 011
                                                                     Punto de Venta: 00003    Comp. Nro: 00000268
Razón Social: PLOMERIA SINTETICA S.R.L.                              Fecha de Emisión: 29/07/2026
Domicilio Comercial: Calle Falsa 123 - Ciudad de Buenos Aires        CUIT: 20111111112
Condición frente al IVA: Responsable Monotributo                     Ingresos Brutos: EXENTO
Período Facturado Desde: 29/07/2026     Hasta: 29/07/2026            Fecha de Vto. para el pago: 29/07/2026
CUIT: 33600391459           Apellido y Nombre / Razón Social: CONSORCIO DE PROPIETARIOS AV RIVADAVIA 2067 69 71
Condición frente al IVA:  Consumidor Final          Domicilio: Rivadavia Av. 2069
Condición de venta:  Contado

Código    Producto / Servicio            Cantidad     U. Medida    Precio Unit.    % Bonif    Imp. Bonif.    Subtotal

1        REPARACIÓN DE BOMBA DE AGUA          1,00      unidades      135000,00      0,00           0,00     135000,00


                                                                                       Subtotal: $     135000,00
                                                                      Importe Otros Tributos: $              0,00
                                                                                Importe Total: $       135000,00
"""


def test_fragmento_relevante_arranca_en_el_item_de_la_factura_afip():
    frag = fragmento_relevante(FACTURA_AFIP_SINTETICA)
    assert "REPARACIÓN DE BOMBA DE AGUA" in frag
    # nada del boilerplate del encabezado ni de los totales
    assert "ORIGINAL" not in frag
    assert "Punto de Venta" not in frag
    assert "Importe Total" not in frag
    assert len(frag) <= 300


def test_fragmento_relevante_sin_marcadores_saltea_boilerplate():
    texto = ("CUIT: 30-11111111-1\n"
             "Fecha de emisión: 01/08/2026\n"
             "Trabajos de pintura en palier del 3er piso\n"
             "Mano de obra y materiales\n")
    frag = fragmento_relevante(texto)
    assert frag.startswith("Trabajos de pintura")
    assert "Mano de obra y materiales" in frag
    assert "CUIT" not in frag


def test_fragmento_relevante_texto_corto_plano_va_tal_cual():
    assert fragmento_relevante("Pago de plomeria urgente") == "Pago de plomeria urgente"
    assert fragmento_relevante("") == ""


def test_fragmento_relevante_nunca_vacio_aunque_todo_sea_boilerplate():
    frag = fragmento_relevante("FACTURA\nCUIT: 20111111112\nPunto de Venta: 00003\n")
    assert frag  # último recurso: primeros n caracteres, como antes
    assert "FACTURA" in frag


def test_fragmento_relevante_respeta_n():
    assert len(fragmento_relevante(FACTURA_AFIP_SINTETICA, n=40)) <= 40


def test_semantica_usa_fragmento_relevante(db, auditor, monkeypatch):
    _tres_documentos(db)
    _habilitar(monkeypatch, lambda textos: [[1.0, 0.0, 0.0]])
    monkeypatch.setattr("app.routers.consulta.extraer_texto",
                        lambda storage, d: FACTURA_AFIP_SINTETICA)
    res = auditor.get("/consulta/semantica?q=bomba de agua").json()["resultados"]
    assert "REPARACIÓN DE BOMBA DE AGUA" in res[0]["fragmento"]
    assert "ORIGINAL" not in res[0]["fragmento"]


def test_semantica_es_solo_del_equipo(db, auditor, cliente):
    subir(auditor)
    uf = db.query(models.Unidad).first().uf
    codigo = admin.generar_codigo(db, uf)
    assert cliente.post("/auth/login-unidad", json={"uf": uf, "codigo": codigo}).status_code == 200
    assert cliente.get("/consulta/semantica?q=x").status_code == 403
