"""Tools del MCP contra un cliente de API falso (sin red)."""
import os

import servidor_mcp

_REGLAMENTO_SINTETICO = """\
## Generalidades
Normas generales del consorcio.

## Uso de partes comunes
Solo residentes pueden usar el SUM.

### Asambleas y representación
Cada propietario puede llevar hasta dos poderes.
"""


class ClienteFalso:
    def get(self, path, params=None):
        if path == "/consulta/gastos":
            return {"filas": [{"periodo": "2026-08", "n": 32, "proveedor": "SACZEWICZYK",
                               "categoria": "MANTENIMIENTO", "concepto": "Impermeabilización",
                               "importe": 2552000.0, "factura_nro": "7", "pagos": []}],
                    "total": 2552000.0, "cantidad": 1}
        if path == "/consulta/agregados":
            return {"grupos": [{"clave": "SACZEWICZYK", "total": 2552000.0, "cantidad": 1, "variacion": None}]}
        if path == "/consulta/comprobantes":
            return {"resultados": [{"documento_id": 7, "gasto_n": 32, "periodo": "2026-08",
                                    "tipo": "factura",
                                    "fragmento": "...texto IMPERMEABILIZACION SACZEWICZYK factura..."}]}
        if path == "/consulta/deudores":
            return {"periodo": "2026-08",
                    "deudores": [{"uf": 4, "piso_depto": "2A", "propietario": "DEL VALLE",
                                  "deuda": 150000.0, "meses_equivalentes": 1.5},
                                 {"uf": 9, "piso_depto": "4C", "propietario": "RODRIGUEZ",
                                  "deuda": 50000.0, "meses_equivalentes": 0.5}],
                    "total": 200000.0}
        if path == "/hallazgos":
            return [{"id": 61, "periodo": "2026-08", "severidad": "CRÍTICO", "titulo": "Pago a tercero",
                     "estado": "pendiente", "publicado": True, "regla": "comprobantes",
                     "liquidacion_id": 2, "origen": "comprobantes", "area": "Comprobantes", "monto": 2552000.0}]
        if path.startswith("/hallazgos/"):
            return {"id": 61, "titulo": "Pago a tercero", "evidencia": "CUIT distinto", "recomendacion": "Pedir",
                    "severidad": "CRÍTICO", "periodo": "2026-08", "estado": "pendiente", "publicado": True,
                    "regla": "comprobantes", "liquidacion_id": 2, "origen": "comprobantes", "area": "x",
                    "monto": 2552000.0, "refs": ["32"], "respuesta_admin": "", "eventos": []}
        if path == "/liquidaciones":
            return [{"id": 2, "periodo": "2026-08", "estado": "publicada", "cuadra": True, "sistema": "redconar", "error": ""}]
        if path == "/liquidaciones/2":
            return {"id": 2, "periodo": "2026-08", "estado": "publicada", "cuadra": True,
                    "sistema": "redconar", "error": "",
                    "checks_ok": 5, "checks_mal": 1,
                    "checks": [{"nombre": "cuadre_caja", "ok": False,
                                "detalle": "diferencia de $100"}],
                    "totales_categoria": {"MANTENIMIENTO": 2552000.0, "ADMINISTRACIÓN": 180000.0},
                    "gastos": []}
        if path == "/documentos/7/texto":
            return {"texto": "IMPERMEABILIZACION SACZEWICZYK CUIT 30-99887766-1", "extraible": True}
        if path == "/documentos/99/texto":
            return {"texto": "", "extraible": False}
        raise AssertionError(f"path inesperado: {path}")

    def get_texto(self, path):
        if path == "/consorcio/reglamento/transcripcion":
            return _REGLAMENTO_SINTETICO
        raise AssertionError(f"path inesperado: {path}")


def test_consultar_gastos_formatea_el_resultado(monkeypatch):
    monkeypatch.setattr(servidor_mcp, "_cliente", lambda: ClienteFalso())
    out = servidor_mcp.consultar_gastos(proveedor="sacze")
    assert "SACZEWICZYK" in out and "2.552.000" in out and "1 gasto" in out


def test_search_y_fetch_compatibles_chatgpt(monkeypatch):
    monkeypatch.setattr(servidor_mcp, "_cliente", lambda: ClienteFalso())
    res = servidor_mcp.search(query="sacze")
    assert res["results"] and {"id", "title", "url"} <= set(res["results"][0].keys())
    doc = servidor_mcp.fetch(id=res["results"][0]["id"])
    assert doc["id"] == res["results"][0]["id"] and doc["text"]


def test_reglamento_sin_busqueda_devuelve_indice(monkeypatch):
    monkeypatch.setattr(servidor_mcp, "_cliente", lambda: ClienteFalso())
    monkeypatch.setattr(servidor_mcp, "_reglamento_cache", None)
    out = servidor_mcp.reglamento()
    # Debe listar los 3 títulos en el índice
    assert "Generalidades" in out
    assert "Uso de partes comunes" in out
    assert "Asambleas" in out
    # Debe incluir instrucción para buscar
    assert "reglamento(busqueda=" in out


def test_reglamento_con_busqueda_devuelve_seccion_correcta(monkeypatch):
    monkeypatch.setattr(servidor_mcp, "_cliente", lambda: ClienteFalso())
    monkeypatch.setattr(servidor_mcp, "_reglamento_cache", None)
    out = servidor_mcp.reglamento(busqueda="poderes")
    # La sección Asambleas contiene "poderes" en el cuerpo → debe aparecer
    assert "Asambleas" in out
    assert "poderes" in out.lower()
    # Las otras secciones no la mencionan → no deben aparecer
    assert "Generalidades" not in out
    assert "Uso de partes comunes" not in out


def test_search_incluye_reglamento_y_fetch_lo_resuelve(monkeypatch):
    monkeypatch.setattr(servidor_mcp, "_cliente", lambda: ClienteFalso())
    monkeypatch.setattr(servidor_mcp, "_reglamento_cache", None)
    # Precalentar el cache para que search pueda consultar los títulos
    servidor_mcp.reglamento()  # carga el cache
    res = servidor_mcp.search(query="asambleas")
    ids = [r["id"] for r in res["results"]]
    reglamento_ids = [i for i in ids if i.startswith("reglamento:")]
    assert reglamento_ids, f"no hay resultado reglamento: en {ids}"
    # fetch del id reglamento devuelve el texto de la sección
    doc = servidor_mcp.fetch(id=reglamento_ids[0])
    assert doc["text"] and "Asambleas" in doc["text"]


def test_search_frio_incluye_reglamento_sin_precalentar(monkeypatch):
    """Un search en frío (cache = None) debe incluir resultados reglamento: sin
    haber llamado a reglamento() antes — el propio search lo baja y cachea."""
    monkeypatch.setattr(servidor_mcp, "_cliente", lambda: ClienteFalso())
    monkeypatch.setattr(servidor_mcp, "_reglamento_cache", None)
    # NO se llama a reglamento() antes — cache permanece None hasta que search lo cargue
    res = servidor_mcp.search(query="asambleas")
    ids = [r["id"] for r in res["results"]]
    reglamento_ids = [i for i in ids if i.startswith("reglamento:")]
    assert reglamento_ids, f"search frío no incluyó reglamento — ids: {ids}"


def test_leer_comprobante(monkeypatch):
    """leer_comprobante devuelve el texto cuando el PDF es extraíble, y un aviso claro cuando no."""
    monkeypatch.setattr(servidor_mcp, "_cliente", lambda: ClienteFalso())

    # Caso extraíble: el texto aparece en la salida
    out = servidor_mcp.leer_comprobante(documento_id=7)
    assert "IMPERMEABILIZACION" in out
    assert "SACZEWICZYK" in out

    # Caso no extraíble: aviso sin stack trace
    out_no = servidor_mcp.leer_comprobante(documento_id=99)
    assert "no extraíble" in out_no.lower() or "sin texto" in out_no.lower() or "escaneo" in out_no.lower()
    assert "panel" in out_no.lower() or "contenido" in out_no.lower()


def test_buscar_en_comprobantes(monkeypatch):
    """buscar_en_comprobantes incluye fragmento, documento_id y el período en la salida."""
    monkeypatch.setattr(servidor_mcp, "_cliente", lambda: ClienteFalso())

    out = servidor_mcp.buscar_en_comprobantes(texto="impermeabilizacion")
    # El fragmento del cliente falso aparece en la salida
    assert "IMPERMEABILIZACION" in out
    # El documento_id y el gasto están referenciados
    assert "7" in out          # documento_id
    assert "32" in out         # gasto_n
    assert "2026-08" in out    # periodo


def test_deudores_y_resumen(monkeypatch):
    """deudores formatea la tabla; resumen_mensual compone todas las secciones y degrada
    correctamente cuando una fuente falla."""
    monkeypatch.setattr(servidor_mcp, "_cliente", lambda: ClienteFalso())

    # --- deudores ---
    out = servidor_mcp.deudores()
    assert "DEL VALLE" in out
    assert "150.000" in out    # deuda formateada
    assert "2026-08" in out    # periodo

    # --- resumen_mensual: caso nominal ---
    out_r = servidor_mcp.resumen_mensual()
    # cuadre
    assert "cuadra" in out_r.lower() or "cuadre" in out_r.lower()
    # top gastos
    assert "SACZEWICZYK" in out_r
    # hallazgos
    assert "Pago a tercero" in out_r
    # deudores (resumen muestra total, no individual por nombre)
    assert "200.000" in out_r  # total deudores
    assert "2 unidad" in out_r  # cantidad de deudores

    # --- resumen_mensual: degradación por sección ---
    # Fabricamos un cliente que rompe /hallazgos para verificar que el resumen sale igual
    class ClienteConHallazgosRotos(ClienteFalso):
        def get(self, path, params=None):
            if path == "/hallazgos":
                raise Exception("servicio caído")
            return super().get(path, params)

    monkeypatch.setattr(servidor_mcp, "_cliente", lambda: ClienteConHallazgosRotos())
    out_degradado = servidor_mcp.resumen_mensual()
    # El resumen sigue saliendo con las otras secciones
    assert "SACZEWICZYK" in out_degradado      # top gastos OK
    assert "200.000" in out_degradado          # total deudores OK
    # La sección de hallazgos está marcada como no disponible
    assert "no disponible" in out_degradado.lower()


def test_detalle_liquidacion(monkeypatch):
    """detalle_liquidacion muestra estado, cuadre, checks fallidos y totales por categoría."""
    monkeypatch.setattr(servidor_mcp, "_cliente", lambda: ClienteFalso())

    out = servidor_mcp.detalle_liquidacion(periodo="2026-08")
    assert "2026-08" in out
    assert "publicada" in out
    assert "cuadra" in out.lower()
    # Checks fallidos
    assert "cuadre_caja" in out
    assert "$100" in out or "100" in out
    # Totales por categoría
    assert "MANTENIMIENTO" in out
    assert "2.552.000" in out


def test_reglamento_busqueda_insensible_a_acentos(monkeypatch):
    """reglamento(busqueda='representacion') (sin acento) debe encontrar la sección
    '### Asambleas y representación' (con acento en el título del reglamento sintético)."""
    monkeypatch.setattr(servidor_mcp, "_cliente", lambda: ClienteFalso())
    monkeypatch.setattr(servidor_mcp, "_reglamento_cache", None)

    # búsqueda SIN acento, título CON acento
    out = servidor_mcp.reglamento(busqueda="representacion")
    assert "Asambleas y representación" in out
    assert "poderes" in out.lower()
    # las secciones sin "representación" no deben aparecer
    assert "Generalidades" not in out
    assert "Uso de partes comunes" not in out

    # búsqueda CON acento también funciona
    monkeypatch.setattr(servidor_mcp, "_reglamento_cache", None)
    out2 = servidor_mcp.reglamento(busqueda="representación")
    assert "Asambleas y representación" in out2


def test_gating_del_token(monkeypatch):
    """El token en el path es la única puerta de entrada.

    - Cualquier path sin el token → 404.
    - POST al path correcto (aunque el body no sea initialize válido) → no 404
      (el transporte MCP contestará 4xx propio, pero no 404).
    """
    from starlette.testclient import TestClient

    monkeypatch.setenv("CT_MCP_TOKEN", "test-tok")
    app = servidor_mcp.app_con_token()
    client = TestClient(app, raise_server_exceptions=False)

    # Paths sin el token deben dar 404
    assert client.get("/mcp/otro").status_code == 404
    assert client.get("/").status_code == 404

    # El path correcto no da 404 (el MCP rechazará el body, pero la ruta existe)
    r = client.post("/mcp/test-tok", json={})
    assert r.status_code != 404
