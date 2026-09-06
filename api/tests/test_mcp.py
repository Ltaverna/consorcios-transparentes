"""Tools del MCP contra un cliente de API falso (sin red)."""
import os

import servidor_mcp

_REGLAMENTO_SINTETICO = """\
## Generalidades
Normas generales del consorcio.

## Uso de partes comunes
Solo residentes pueden usar el SUM.

### Asambleas
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
