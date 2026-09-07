"""Tools del MCP contra un cliente de API falso (sin red)."""
import io
import json
import os
import urllib.error

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
        if path == "/consulta/semantica":
            return {"resultados": [{"documento_id": 7, "gasto_n": 32, "periodo": "2026-08",
                                    "tipo": "factura", "similitud": 0.92,
                                    "fragmento": "IMPERMEABILIZACION TERRAZA SACZEWICZYK CUIT 30-99887766-1"}]}
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
    # Un token desconocido no debe irse a la red a consultar la API real
    monkeypatch.setattr(servidor_mcp, "_validar_contra_api", lambda t: (False, None))
    app = servidor_mcp.app_con_token()
    client = TestClient(app, raise_server_exceptions=False)

    # Paths sin el token deben dar 404
    assert client.get("/mcp/otro").status_code == 404
    assert client.get("/").status_code == 404

    # El path correcto no da 404 (el MCP rechazará el body, pero la ruta existe)
    r = client.post("/mcp/test-tok", json={})
    assert r.status_code != 404


# --- Wrapper ASGI de tokens por persona: app interno fake + validador stub ---

async def _app_interno_falso(scope, receive, send):
    """ASGI mínimo: responde 200 con el path que le llegó (para verificar la reescritura)."""
    if scope["type"] == "lifespan":
        while True:
            msg = await receive()
            if msg["type"] == "lifespan.startup":
                await send({"type": "lifespan.startup.complete"})
            elif msg["type"] == "lifespan.shutdown":
                await send({"type": "lifespan.shutdown.complete"})
                return
    await send({"type": "http.response.start", "status": 200,
                "headers": [(b"content-type", b"text/plain")]})
    await send({"type": "http.response.body", "body": ("ok:" + scope["path"]).encode()})


def test_wrapper_acepta_el_token_del_env(monkeypatch):
    """CT_MCP_TOKEN valida primero (comparación constante) sin tocar la API."""
    from starlette.testclient import TestClient

    monkeypatch.setenv("CT_MCP_TOKEN", "tok-env")

    def sin_api(_):
        raise AssertionError("el token del env no debe consultar la API")

    monkeypatch.setattr(servidor_mcp, "_validar_contra_api", sin_api)
    with TestClient(servidor_mcp.WrapperTokens(_app_interno_falso)) as client:
        r = client.post("/mcp/tok-env", json={})
    assert r.status_code == 200
    assert r.text == "ok:/mcp/sesion"  # path reescrito al mount interno


def test_wrapper_acepta_token_de_tabla_y_404_con_invalido():
    from starlette.testclient import TestClient

    def validar(token):
        return (True, "lucas") if token == "tok-tabla" else (False, None)

    client = TestClient(servidor_mcp.WrapperTokens(_app_interno_falso, validar=validar))
    assert client.post("/mcp/tok-tabla", json={}).status_code == 200
    r = client.post("/mcp/otro", json={})
    assert r.status_code == 404 and r.content == b""  # 404 pelado, sin cuerpo
    assert client.get("/").status_code == 404
    # El mount interno no es alcanzable directo: "sesion" se valida como token y falla
    assert client.get("/mcp/sesion").status_code == 404


def test_wrapper_cachea_con_ttl_positivo_y_negativo():
    """Dentro del TTL no revalida (ni positivos ni negativos); expirado, revalida."""
    from starlette.testclient import TestClient

    llamadas = []

    def validar(token):
        llamadas.append(token)
        return (True, "lucas") if token == "bueno" else (False, None)

    reloj = {"t": 1000.0}
    wrapper = servidor_mcp.WrapperTokens(_app_interno_falso, validar=validar,
                                         reloj=lambda: reloj["t"])
    client = TestClient(wrapper)

    client.post("/mcp/bueno", json={})
    client.post("/mcp/bueno", json={})
    assert llamadas == ["bueno"]  # el segundo salió de la cache

    assert client.post("/mcp/malo", json={}).status_code == 404
    assert client.post("/mcp/malo", json={}).status_code == 404
    assert llamadas == ["bueno", "malo"]  # el negativo también se cachea

    reloj["t"] += 61  # pasa el TTL de 60 s
    client.post("/mcp/bueno", json={})
    assert llamadas == ["bueno", "malo", "bueno"]  # expirado → revalida


def test_wrapper_loguea_el_nombre_una_vez_por_entrada_de_cache(capsys):
    from starlette.testclient import TestClient

    client = TestClient(servidor_mcp.WrapperTokens(_app_interno_falso,
                                                   validar=lambda t: (True, "amigo-juan")))
    client.post("/mcp/tok", json={})
    client.post("/mcp/tok", json={})
    out = capsys.readouterr().out
    assert out.count("amigo-juan") == 1  # una vez por entrada de cache, no por request
    assert "tok" not in out.replace("amigo-juan", "")  # jamás el token


def test_buscar_semantico_formatea_resultado(monkeypatch):
    """buscar_semantico llama /consulta/semantica y formatea similitud, doc, gasto, período,
    tipo y fragmento recortado a ~150 caracteres."""
    monkeypatch.setattr(servidor_mcp, "_cliente", lambda: ClienteFalso())

    out = servidor_mcp.buscar_semantico(texto="impermeabilizacion terraza")
    # Similitud en porcentaje
    assert "92.0%" in out
    # Identificadores del resultado
    assert "7" in out          # documento_id
    assert "32" in out         # gasto_n
    assert "2026-08" in out    # periodo
    assert "factura" in out    # tipo
    # Fragmento del texto
    assert "IMPERMEABILIZACION" in out


def test_buscar_semantico_sin_key_devuelve_mensaje_claro(monkeypatch):
    """Cuando la API responde 503 (búsqueda semántica no configurada), el mensaje que
    llega al usuario incluye el detail del cuerpo HTTP y es inteligible."""
    cuerpo = json.dumps({"detail": "búsqueda semántica no configurada"}).encode()
    error_503 = urllib.error.HTTPError(
        url="http://x/consulta/semantica", code=503,
        msg="Service Unavailable", hdrs=None, fp=io.BytesIO(cuerpo)
    )

    class ClienteConSemantic503(ClienteFalso):
        def get(self, path, params=None):
            if path == "/consulta/semantica":
                raise error_503
            return super().get(path, params)

    monkeypatch.setattr(servidor_mcp, "_cliente", lambda: ClienteConSemantic503())
    monkeypatch.setattr(servidor_mcp, "_sesion", None)

    out = servidor_mcp.buscar_semantico(texto="impermeabilizacion")
    assert "503" in out
    assert "búsqueda semántica no configurada" in out


# --- Tests de cache resiliente a errores de red (stale-while-error) ---

def test_wrapper_error_de_red_usa_stale_positivo():
    """Con un validador que lanza _ErrorRed, un token previamente válido (entrada vencida)
    sigue pasando gracias al stale-while-error; un token nunca visto → rechazado."""
    from starlette.testclient import TestClient

    llamadas = []

    def validar_con_error(token):
        llamadas.append(token)
        raise servidor_mcp._ErrorRed("timeout simulado")

    # Primero un validador normal para poblar la cache con una entrada positiva.
    def validar_ok(token):
        return (True, "lucas") if token == "bueno" else (False, None)

    reloj = {"t": 1000.0}
    wrapper = servidor_mcp.WrapperTokens(_app_interno_falso, validar=validar_ok,
                                         reloj=lambda: reloj["t"])
    client = TestClient(wrapper)

    # Primera llamada: pobla la cache con entrada positiva.
    assert client.post("/mcp/bueno", json={}).status_code == 200

    # Avanzar el reloj para que la entrada quede vencida.
    reloj["t"] += 61

    # Cambiar al validador que lanza error de red.
    wrapper._validar = validar_con_error

    # El token "bueno" tiene entrada positiva vencida → stale-while-error: debe pasar.
    assert client.post("/mcp/bueno", json={}).status_code == 200
    assert llamadas == ["bueno"]  # se intentó preguntar (una vez, no 0)

    # Un token nunca visto con error de red → rechazado, SIN entrada negativa cacheada.
    assert client.post("/mcp/nuevo", json={}).status_code == 404
    assert "nuevo" in llamadas  # se intentó preguntar

    # El siguiente intento de "nuevo" vuelve a preguntar (no hay cache negativa).
    llamadas.clear()
    assert client.post("/mcp/nuevo", json={}).status_code == 404
    assert llamadas == ["nuevo"]  # reintentó → no había cache negativa


def test_wrapper_error_de_red_no_escribe_cache_negativa():
    """Con error de red, un token nunca visto no queda en la cache negativa: el siguiente
    intento vuelve a consultar el validador (conteo de llamadas lo confirma)."""
    from starlette.testclient import TestClient

    llamadas = []

    def validar_con_error(token):
        llamadas.append(token)
        raise servidor_mcp._ErrorRed("red caída")

    wrapper = servidor_mcp.WrapperTokens(_app_interno_falso, validar=validar_con_error)
    client = TestClient(wrapper)

    # Primer intento → error de red, rechazado, sin cache negativa.
    assert client.post("/mcp/fantasma", json={}).status_code == 404
    assert llamadas == ["fantasma"]

    # Segundo intento → vuelve a preguntar al validador (no hay cache negativa).
    assert client.post("/mcp/fantasma", json={}).status_code == 404
    assert llamadas == ["fantasma", "fantasma"]  # dos llamadas al validador


_INDICE_FALSO = {
    "indice": 20,
    "rango": {"desde": "2026-07", "hasta": "2026-08"},
    "totales": {
        "dinero_total": 1000.0,
        "dinero_verificado": 620.0,
        "dinero_con_factura": 810.0,
        "dinero_pago_respaldado": 700.0,
        "pct_trazable": 0.62,
        "pct_con_factura": 0.81,
        "pct_pago_respaldado": 0.7,
        "indice": 20,
        "gastos_por_estado": {
            "verificado": {"cantidad": 10, "importe": 620.0},
            "requiere_explicacion": {"cantidad": 3, "importe": 100.0},
            "anomalia": {"cantidad": 2, "importe": 150.0},
            "inconsistencia": {"cantidad": 1, "importe": 80.0},
            "sin_informacion": {"cantidad": 1, "importe": 50.0},
        },
        "hallazgos_abiertos": {"CRÍTICO": 1, "ALTO": 2, "MEDIO": 3, "BAJO": 0},
        "hallazgos_resueltos": 4,
        "componentes": {
            "documentacion":  {"peso": 0.30, "valor": 0.64, "puntos": 19.2},
            "conciliacion":   {"peso": 0.30, "valor": 0.54, "puntos": 16.2},
            "trazabilidad":   {"peso": 0.20, "valor": 0.10, "puntos": 2.0},
            "consistencia":   {"peso": 0.10, "valor": 0.80, "puntos": 8.0,
                               "periodos_cuadran": 8, "periodos_totales": 10},
            "explicaciones":  {"peso": 0.10, "valor": 0.0,  "puntos": 0.0},
        },
        "penalizacion": {"criticos_abiertos": 36, "por_critico": 2, "tope": 25, "puntos": 25},
    },
    "periodos": [{"periodo": "2026-08", "indice": 20}],
}

_GASTOS_FALSOS = {
    "periodo": "2026-08",
    "gastos": [
        {
            "n": 25,
            "proveedor": "MARIO LEONARDO ROTH",
            "categoria": "ABONOS",
            "concepto": "Serpentina",
            "importe": 2650000.0,
            "estado": "anomalia",
            "hallazgos": [{"id": 7, "severidad": "ALTO", "estado": "pendiente",
                           "titulo": "transferencia sin respaldo"}],
            "documentos": [{"id": 1, "tipo": "factura", "archivo": "fc.pdf"}],
        }
    ],
}


class ClienteFalsoConAnalitica(ClienteFalso):
    def get(self, path, params=None):
        if path == "/analitica/indice":
            return _INDICE_FALSO
        if path == "/analitica/gastos":
            return _GASTOS_FALSOS
        return super().get(path, params)


def test_indice_transparencia_contiene_indice_y_titulo(monkeypatch):
    """indice_transparencia devuelve texto con 'ÍNDICE DE TRANSPARENCIA' y el número."""
    monkeypatch.setattr(servidor_mcp, "_cliente", lambda: ClienteFalsoConAnalitica())
    out = servidor_mcp.indice_transparencia()
    assert "ÍNDICE DE TRANSPARENCIA" in out
    assert "20" in out


def test_indice_transparencia_incluye_componentes_y_penalizacion(monkeypatch):
    """indice_transparencia incluye la tabla de componentes y la cuenta de penalización."""
    monkeypatch.setattr(servidor_mcp, "_cliente", lambda: ClienteFalsoConAnalitica())
    out = servidor_mcp.indice_transparencia()

    # Tabla de componentes: debe haber una línea con "documentacion" y "peso"
    assert "documentacion" in out
    assert "peso" in out
    # Valores del fixture: 64% × peso 30% = 19,2 puntos
    assert "64%" in out
    assert "30%" in out
    assert "19,2" in out

    # Consistencia incluye el desglose de períodos
    assert "consistencia" in out
    assert "8 de 10" in out

    # Penalización con tope: 36 abiertos × 2 = 72 → tope 25
    assert "36" in out
    assert "tope 25" in out
    assert "25 puntos" in out


def test_indice_transparencia_penalizacion_sin_tope(monkeypatch):
    """Cuando la penalización no llega al tope, no muestra la flecha al tope."""
    import copy
    indice_bajo = copy.deepcopy(_INDICE_FALSO)
    indice_bajo["totales"]["penalizacion"] = {
        "criticos_abiertos": 4, "por_critico": 2, "tope": 25, "puntos": 8
    }

    class ClienteConPenalizacionBaja(ClienteFalsoConAnalitica):
        def get(self, path, params=None):
            if path == "/analitica/indice":
                return indice_bajo
            return super().get(path, params)

    monkeypatch.setattr(servidor_mcp, "_cliente", lambda: ClienteConPenalizacionBaja())
    out = servidor_mcp.indice_transparencia()
    # Debe mostrar la aritmética sin la flecha al tope
    assert "4" in out
    assert "se restan 8 puntos" in out
    # No debe mencionar "tope 25" (no se alcanzó el tope)
    assert "tope 25" not in out


def test_indice_transparencia_penalizacion_cero(monkeypatch):
    """Cuando no hay críticos abiertos, muestra 'sin penalización'."""
    import copy
    indice_sin_pen = copy.deepcopy(_INDICE_FALSO)
    indice_sin_pen["totales"]["penalizacion"] = {
        "criticos_abiertos": 0, "por_critico": 2, "tope": 25, "puntos": 0
    }

    class ClienteSinCriticos(ClienteFalsoConAnalitica):
        def get(self, path, params=None):
            if path == "/analitica/indice":
                return indice_sin_pen
            return super().get(path, params)

    monkeypatch.setattr(servidor_mcp, "_cliente", lambda: ClienteSinCriticos())
    out = servidor_mcp.indice_transparencia()
    assert "sin penalización" in out


def test_estado_gastos_lista_con_estado_uppercase(monkeypatch):
    """estado_gastos lista gastos con su estado en mayúsculas."""
    monkeypatch.setattr(servidor_mcp, "_cliente", lambda: ClienteFalsoConAnalitica())
    out = servidor_mcp.estado_gastos(periodo="2026-08")
    assert "ROTH" in out
    assert "ANOMALIA" in out
