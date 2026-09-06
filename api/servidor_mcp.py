"""Servidor MCP read-only del consorcio: expone las consultas como tools para
Claude Code, claude.ai y ChatGPT (Streamable HTTP + segmento secreto en el path)."""
import functools
import json
import os
import urllib.error
import urllib.parse
import urllib.request
from http.cookiejar import CookieJar

from mcp.server.mcpserver import MCPServer

mcp = MCPServer("consorcio-transparente")

_WEB = os.environ.get("CT_WEB_URL", "https://panel-consorcio.neuralcore.dev")


class ClienteApi:
    """Cliente mínimo de la API del panel con la sesión del bot (cookie)."""

    def __init__(self):
        self.base = os.environ.get("CT_API_URL", "https://api-consorcio.neuralcore.dev")
        jar = CookieJar()
        self.opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))
        # el Browser Integrity Check de Cloudflare banea el UA default de Python (error 1010)
        self.opener.addheaders = [("User-Agent", "ConsorcioTransparente/1.0")]
        body = json.dumps({"email": os.environ["CT_API_BOT_EMAIL"],
                           "clave": os.environ["CT_API_BOT_CLAVE"]}).encode()
        req = urllib.request.Request(self.base + "/auth/login", data=body,
                                     headers={"Content-Type": "application/json"})
        with self.opener.open(req, timeout=30) as r:
            r.read()

    def get(self, path, params=None):
        limpio = {k: v for k, v in (params or {}).items() if v not in (None, "", 0)}
        url = self.base + path + ("?" + urllib.parse.urlencode(limpio) if limpio else "")
        with self.opener.open(url, timeout=60) as r:
            return json.loads(r.read())

    def get_texto(self, path):
        """Como get() pero devuelve el string crudo en lugar de parsear JSON."""
        url = self.base + path
        with self.opener.open(url, timeout=60) as r:
            return r.read().decode("utf-8")


_sesion = None
_reglamento_cache = None  # str con el markdown completo; se llena en la primera llamada


def _cliente():
    global _sesion
    if _sesion is None:
        _sesion = ClienteApi()
    return _sesion


def _plata(v):
    return "$" + f"{v:,.0f}".replace(",", ".")


def _con_api(fn):
    """Errores de red → mensaje legible, jamás un stack trace. Ante un 401
    (cookie del bot vencida) resetea la sesión y reintenta una vez."""

    @functools.wraps(fn)
    def envuelta(*args, **kwargs):
        global _sesion
        try:
            try:
                return fn(*args, **kwargs)
            except urllib.error.HTTPError as e:
                if e.code != 401:
                    raise
                _sesion = None
                return fn(*args, **kwargs)
        except urllib.error.HTTPError as e:
            return f"la API del consorcio no respondió: HTTP {e.code}"
        except urllib.error.URLError as e:
            return f"la API del consorcio no respondió: {getattr(e, 'reason', e)}"

    return envuelta


@_con_api
def consultar_gastos(proveedor: str = "", categoria: str = "", q: str = "",
                     periodo_desde: str = "", periodo_hasta: str = "",
                     importe_min: float = 0.0) -> str:
    """Busca gastos de las liquidaciones por proveedor, categoría, texto del
    concepto, rango de períodos (AAAA-MM) y/o importe mínimo."""
    d = _cliente().get("/consulta/gastos", {
        "proveedor": proveedor, "categoria": categoria, "q": q,
        "periodo_desde": periodo_desde, "periodo_hasta": periodo_hasta,
        "importe_min": importe_min,
    })
    lineas = [f"{d['cantidad']} gasto(s), total {_plata(d['total'])}:"]
    lineas += [f"{f['periodo']} · {f['proveedor']} · {f['concepto'][:80]} · {_plata(f['importe'])}"
               for f in d["filas"]]
    return "\n".join(lineas)


@_con_api
def agregados(por: str, periodo_desde: str = "", periodo_hasta: str = "") -> str:
    """Totales agrupados por 'proveedor', 'categoria' o 'periodo', con variación
    del último período contra el anterior cuando hay datos."""
    d = _cliente().get("/consulta/agregados", {
        "por": por, "periodo_desde": periodo_desde, "periodo_hasta": periodo_hasta,
    })
    lineas = []
    for g in d["grupos"]:
        var = "s/d" if g.get("variacion") is None else f"{g['variacion']:+.0%}"
        lineas.append(f"{g['clave']}: {_plata(g['total'])} ({g['cantidad']} gastos, variación {var})")
    return "\n".join(lineas) or "Sin gastos en ese rango."


@_con_api
def listar_hallazgos(severidad: str = "", estado: str = "", regla: str = "",
                     periodo: str = "") -> str:
    """Lista los hallazgos de la auditoría, filtrables por severidad, estado,
    regla y período (AAAA-MM)."""
    filas = _cliente().get("/hallazgos", {
        "severidad": severidad, "estado": estado, "regla": regla, "periodo": periodo,
    })
    lineas = [f"#{h['id']} [{h['severidad']}] {h['periodo']} · {h['titulo']} ({h['estado']})"
              for h in filas]
    return "\n".join(lineas) or "Sin hallazgos con esos filtros."


@_con_api
def detalle_hallazgo(id: int) -> str:
    """Detalle completo de un hallazgo: evidencia, qué pedir y respuesta de la
    administración si la hay."""
    h = _cliente().get(f"/hallazgos/{id}")
    partes = [f"#{h['id']} [{h['severidad']}] {h['periodo']} · {h['titulo']} ({h['estado']})",
              f"Evidencia: {h['evidencia']}",
              f"Qué pedir: {h['recomendacion']}"]
    if h.get("respuesta_admin"):
        partes.append(f"Respuesta de la administración: {h['respuesta_admin']}")
    return "\n".join(partes)


@_con_api
def estado_liquidaciones() -> str:
    """Estado de las liquidaciones cargadas: período, estado de publicación y si
    los totales cuadran al centavo."""
    filas = _cliente().get("/liquidaciones")
    lineas = []
    for l in filas:
        linea = f"{l['periodo']}: {l['estado']}, {'cuadra' if l['cuadra'] else 'NO cuadra'}"
        if l.get("error"):
            linea += f" — error: {l['error']}"
        lineas.append(linea)
    return "\n".join(lineas) or "No hay liquidaciones cargadas."


def _parsear_reglamento(markdown: str) -> list[tuple[int, str, str]]:
    """Devuelve lista de (índice, título, cuerpo) para cada sección ## o ###."""
    secciones = []
    titulo_actual = None
    cuerpo_lineas: list[str] = []
    for linea in markdown.splitlines():
        if linea.startswith("## ") or linea.startswith("### "):
            if titulo_actual is not None:
                secciones.append((len(secciones), titulo_actual, "\n".join(cuerpo_lineas).strip()))
            titulo_actual = linea
            cuerpo_lineas = []
        else:
            cuerpo_lineas.append(linea)
    if titulo_actual is not None:
        secciones.append((len(secciones), titulo_actual, "\n".join(cuerpo_lineas).strip()))
    return secciones


def _secciones_reglamento() -> list[tuple[int, str, str]]:
    """Baja y cachea la transcripción del reglamento; devuelve las secciones parseadas."""
    global _reglamento_cache
    if _reglamento_cache is None:
        _reglamento_cache = _cliente().get_texto("/consorcio/reglamento/transcripcion")
    return _parsear_reglamento(_reglamento_cache)


@_con_api
def reglamento(busqueda: str = "") -> str:
    """Consulta el reglamento del consorcio. Sin argumento devuelve el índice de
    secciones; con texto devuelve las secciones completas donde aparece (en título
    o cuerpo, case-insensitive)."""
    secciones = _secciones_reglamento()
    if not busqueda:
        lineas = [f"{i}. {titulo}" for i, titulo, _ in secciones]
        lineas.append("\nPedí reglamento(busqueda=...) con palabras del tema para ver el texto completo.")
        return "\n".join(lineas)

    termino = busqueda.lower()
    encontradas = [(i, titulo, cuerpo) for i, titulo, cuerpo in secciones
                   if termino in titulo.lower() or termino in cuerpo.lower()]
    if not encontradas:
        return f"ninguna sección menciona '{busqueda}'; probá con el índice (reglamento())."

    _LIMITE = 15000
    partes = []
    total = 0
    for i, titulo, cuerpo in encontradas:
        bloque = f"{titulo}\n{cuerpo}"
        if total + len(bloque) > _LIMITE:
            partes.append(f"\n[respuesta cortada por tamaño — hay {len(encontradas) - len(partes)} sección(es) más]")
            break
        partes.append(bloque)
        total += len(bloque)
    return "\n\n".join(partes)


@_con_api
def search(query: str) -> dict:
    """Busca gastos y hallazgos por texto (compatibilidad con el modo
    investigación de ChatGPT)."""
    c = _cliente()
    results, vistos = [], set()
    for params in ({"q": query}, {"proveedor": query}):
        for f in c.get("/consulta/gastos", params)["filas"][:10]:
            gid = f"gasto:{f['periodo']}:{f['n']}"
            if gid in vistos:
                continue
            vistos.add(gid)
            results.append({"id": gid,
                            "title": f"{f['proveedor']} · {f['concepto'][:80]} · {_plata(f['importe'])} ({f['periodo']})",
                            "url": f"{_WEB}/panel/analisis"})
    for h in c.get("/hallazgos"):
        if query.lower() in h["titulo"].lower():
            results.append({"id": f"hallazgo:{h['id']}",
                            "title": f"[{h['severidad']}] {h['titulo']} ({h['periodo']})",
                            "url": f"{_WEB}/panel/hallazgos/{h['id']}"})
    # Buscar en los títulos de secciones del reglamento (usa cache si ya está cargado)
    if _reglamento_cache is not None:
        secciones = _parsear_reglamento(_reglamento_cache)
        for i, titulo, _ in secciones:
            if query.lower() in titulo.lower():
                results.append({"id": f"reglamento:{i}",
                                "title": f"Reglamento: {titulo}",
                                "url": f"{_WEB}/reglamento"})
    return {"results": results[:10]}


_ID_INVALIDO = {"id": "", "title": "id inválido",
                "text": "El id no corresponde a un recurso conocido.", "url": "", "metadata": {}}


@_con_api
def fetch(id: str) -> dict:
    """Trae el documento completo de un resultado de search por su id
    (gasto:<periodo>:<n> o hallazgo:<id>)."""
    import re
    c = _cliente()
    if id.startswith("gasto:"):
        partes = id.split(":", 2)
        if len(partes) != 3:
            return {**_ID_INVALIDO, "id": id}
        _, per, n = partes
        # Validar que los componentes no permitan traversal
        if not n.isdigit() or not re.match(r"^\d{4}-\d{2}$", per):
            return {**_ID_INVALIDO, "id": id}
        d = c.get("/consulta/gastos", {"periodo_desde": per, "periodo_hasta": per})
        for f in d["filas"]:
            if str(f["n"]) == n:
                texto = (f"Gasto {f['n']} del período {f['periodo']}\n"
                         f"Proveedor: {f['proveedor']}\nCategoría: {f['categoria']}\n"
                         f"Concepto: {f['concepto']}\nImporte: {_plata(f['importe'])}\n"
                         f"Factura: {f.get('factura_nro') or 's/d'}\n"
                         f"Pagos: {json.dumps(f.get('pagos') or [], ensure_ascii=False)}")
                return {"id": id, "title": f"{f['proveedor']} · {f['concepto'][:80]}",
                        "text": texto, "url": f"{_WEB}/panel/analisis", "metadata": f}
        raise ValueError(f"no existe el gasto {id}")
    if id.startswith("hallazgo:"):
        parte = id.split(":", 1)[1]
        # Validar que la parte sea solo dígitos para evitar traversal a otros endpoints
        if not parte.isdigit():
            return {**_ID_INVALIDO, "id": id}
        h = c.get(f"/hallazgos/{parte}")
        texto = (f"Hallazgo #{h['id']} [{h['severidad']}] {h['periodo']} — {h['titulo']}\n"
                 f"Estado: {h['estado']}\nEvidencia: {h['evidencia']}\n"
                 f"Qué pedir: {h['recomendacion']}")
        if h.get("respuesta_admin"):
            texto += f"\nRespuesta de la administración: {h['respuesta_admin']}"
        return {"id": id, "title": h["titulo"], "text": texto,
                "url": f"{_WEB}/panel/hallazgos/{h['id']}", "metadata": h}
    if id.startswith("reglamento:"):
        parte = id.split(":", 1)[1]
        if not parte.isdigit():
            return {**_ID_INVALIDO, "id": id}
        secciones = _secciones_reglamento()
        idx = int(parte)
        if idx >= len(secciones):
            return {**_ID_INVALIDO, "id": id}
        _, titulo, cuerpo = secciones[idx]
        texto = f"{titulo}\n{cuerpo}"
        return {"id": id, "title": titulo, "text": texto,
                "url": f"{_WEB}/reglamento", "metadata": {}}
    raise ValueError(f"id no reconocido: {id}")


for fn in (consultar_gastos, agregados, listar_hallazgos, detalle_hallazgo, estado_liquidaciones, reglamento):
    mcp.tool()(fn)
# search/fetch devuelven dict pero sin output estructurado: ante un error de red
# el wrapper devuelve un string legible, y ChatGPT espera el JSON como texto.
for fn in (search, fetch):
    mcp.tool(structured_output=False)(fn)


def app_con_token():
    """La app MCP servida solo bajo /mcp/<token>; cualquier otro path → 404 pelado.

    En mcp 2.x `streamable_http_app()` ya devuelve la Starlette con el lifespan
    del session manager, así que en vez de montarla bajo un padre (que no
    propaga lifespans) se le pide directamente el path con el token. La
    protección anti DNS-rebinding se apaga: detrás de cloudflared el Host es el
    hostname público y el secreto es el token del path."""
    from mcp.server.transport_security import TransportSecuritySettings

    token = os.environ["CT_MCP_TOKEN"]
    return mcp.streamable_http_app(
        streamable_http_path=f"/mcp/{token}",
        stateless_http=True,
        transport_security=TransportSecuritySettings(enable_dns_rebinding_protection=False),
    )


if __name__ == "__main__":
    import uvicorn
    # access_log=False: el path incluye el token; no debe aparecer en docker logs
    uvicorn.run(app_con_token(), host="0.0.0.0", port=8765, access_log=False)
