"""Tools del MCP contra un cliente de API falso (sin red)."""
import os

import servidor_mcp


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
