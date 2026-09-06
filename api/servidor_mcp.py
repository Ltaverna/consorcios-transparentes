"""Servidor MCP read-only del consorcio: expone las consultas como tools para
Claude Code, claude.ai y ChatGPT (Streamable HTTP + segmento secreto en el path)."""
import asyncio
import functools
import json
import os
import secrets
import time
import unicodedata
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


def _plegar(s: str) -> str:
    """Minúsculas sin acentos, 1:1 por carácter (los índices del original se preservan)."""
    return "".join(unicodedata.normalize("NFD", c)[0].lower() for c in s)


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
            try:
                detail = json.loads(e.read().decode()).get("detail", "")
            except Exception:
                detail = ""
            sufijo = f" — {detail}" if detail else ""
            return f"la API del consorcio no respondió: HTTP {e.code}{sufijo}"
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

    termino = _plegar(busqueda)
    encontradas = [(i, titulo, cuerpo) for i, titulo, cuerpo in secciones
                   if termino in _plegar(titulo) or termino in _plegar(cuerpo)]
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
    # Buscar en los títulos de secciones del reglamento (baja y cachea si aún no está cargado)
    try:
        secciones = _secciones_reglamento()
        for i, titulo, _ in secciones:
            if query.lower() in titulo.lower():
                results.append({"id": f"reglamento:{i}",
                                "title": f"Reglamento: {titulo}",
                                "url": f"{_WEB}/reglamento"})
    except Exception:
        pass  # falla del reglamento nunca tumba los resultados de gastos/hallazgos
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


@_con_api
def leer_comprobante(documento_id: int) -> str:
    """Devuelve el texto extraído del comprobante (PDF digital). Para escaneos o imágenes
    sin capa de texto indica que el documento no es extraíble y sugiere bajarlo del panel."""
    d = _cliente().get(f"/documentos/{documento_id}/texto")
    if not d["extraible"]:
        return (f"Documento {documento_id}: sin texto extraíble (escaneo o imagen). "
                f"Descargalo desde el panel con /documentos/{documento_id}/contenido.")
    return d["texto"]


@_con_api
def buscar_en_comprobantes(texto: str, periodo: str = "") -> str:
    """Busca `texto` (case-insensitive) en el contenido de todos los comprobantes del período
    (o de todos los períodos si no se especifica). Devuelve un fragmento de ±200 caracteres
    alrededor de cada coincidencia, con el documento y el gasto al que pertenece."""
    params = {"q": texto}
    if periodo:
        params["periodo"] = periodo
    d = _cliente().get("/consulta/comprobantes", params)
    resultados = d.get("resultados", [])
    if not resultados:
        return f"Ningún comprobante contiene '{texto}'."
    lineas = [f"{len(resultados)} coincidencia(s):"]
    for r in resultados:
        lineas.append(
            f"  Doc {r['documento_id']} · gasto {r['gasto_n']} · {r['periodo']} · {r['tipo']}\n"
            f"  …{r['fragmento']}…"
        )
    return "\n".join(lineas)


@_con_api
def deudores(periodo: str = "") -> str:
    """Lista las unidades funcionales con deuda del período indicado (default: el último con
    liquidación procesada), ordenadas de mayor a menor deuda."""
    params = {}
    if periodo:
        params["periodo"] = periodo
    d = _cliente().get("/consulta/deudores", params)
    lineas = [f"Deudores al {d['periodo']} — total {_plata(d['total'])}:"]
    for u in d["deudores"]:
        meses = f"{u['meses_equivalentes']:.1f} mes(es)" if u["meses_equivalentes"] is not None else "s/d meses"
        lineas.append(
            f"  UF {u['uf']} ({u['piso_depto']}) {u['propietario']}: "
            f"{_plata(u['deuda'])} — {meses}"
        )
    return "\n".join(lineas) or "Sin deudores en ese período."


@_con_api
def detalle_liquidacion(periodo: str) -> str:
    """Estado, cuadre y checks de una liquidación: busca el id a partir del período y trae el
    detalle completo (checks fallidos, totales por categoría)."""
    liqs = _cliente().get("/liquidaciones")
    fila = next((l for l in liqs if l["periodo"] == periodo), None)
    if not fila:
        return f"No hay liquidación cargada para el período {periodo}."
    liq = _cliente().get(f"/liquidaciones/{fila['id']}")
    lineas = [
        f"Liquidación {liq['periodo']} — {liq['estado']}",
        f"Cuadre: {'cuadra' if liq['cuadra'] else 'NO cuadra'}",
        f"Checks: {liq['checks_ok']} OK, {liq['checks_mal']} fallido(s)",
    ]
    for c in liq.get("checks", []):
        lineas.append(f"  ✗ {c['nombre']}: {c['detalle']}")
    if liq.get("totales_categoria"):
        lineas.append("Totales por categoría:")
        for cat, total in sorted(liq["totales_categoria"].items(), key=lambda x: -x[1]):
            lineas.append(f"  {cat}: {_plata(total)}")
    return "\n".join(lineas)


@_con_api
def buscar_semantico(texto: str) -> str:
    """Busca comprobantes por similitud semántica: devuelve el top-5 más relevante
    al `texto` de consulta libre, con similitud (porcentaje), documento, gasto,
    período, tipo y un fragmento del contenido. Requiere CT_EMBEDDINGS_API_KEY
    configurada en la API; sin ella devuelve un aviso claro."""
    d = _cliente().get("/consulta/semantica", {"q": texto, "k": 5})
    resultados = d.get("resultados", [])
    if not resultados:
        return "Sin resultados semánticos para esa consulta."
    lineas = [f"{len(resultados)} resultado(s) semántico(s):"]
    for r in resultados:
        similitud = f"{r['similitud'] * 100:.1f}%"
        fragmento = r.get("fragmento", "")[:150].replace("\n", " ").strip()
        lineas.append(
            f"  [{similitud}] Doc {r['documento_id']} · gasto {r['gasto_n']} · "
            f"{r['periodo']} · {r['tipo']}\n"
            f"  {fragmento}"
        )
    return "\n".join(lineas)


def resumen_mensual(periodo: str = "") -> str:
    """Resumen ejecutivo del mes: cuadre de la liquidación, top 10 gastos, hallazgos,
    variaciones fuertes y total de deudores. Cada sección degrada individualmente si
    la fuente falla — el resumen siempre sale aunque haya errores parciales."""
    # Determinar el período: el más reciente si no se especifica.
    if not periodo:
        try:
            liqs = _cliente().get("/liquidaciones")
            periodo = liqs[0]["periodo"] if liqs else ""
        except Exception:
            periodo = ""
    if not periodo:
        return "No hay liquidaciones cargadas para resumir."

    partes = [f"=== Resumen mensual {periodo} ===\n"]

    # Sección 1: cuadre y estado de la liquidación
    try:
        partes.append(detalle_liquidacion(periodo=periodo))
    except Exception:
        partes.append("Estado/cuadre: no disponible")
    partes.append("")

    # Sección 2: top 10 gastos del período
    try:
        d = _cliente().get("/consulta/gastos", {"periodo_desde": periodo, "periodo_hasta": periodo})
        filas = d["filas"][:10]
        partes.append(f"Top gastos de {periodo} ({d['cantidad']} total, {_plata(d['total'])}):")
        for f in filas:
            partes.append(f"  {f['proveedor']} · {f['concepto'][:60]} · {_plata(f['importe'])}")
    except Exception:
        partes.append("Top gastos: no disponible")
    partes.append("")

    # Sección 3: hallazgos del período
    try:
        hs = _cliente().get("/hallazgos", {"periodo": periodo})
        if hs:
            partes.append(f"Hallazgos de {periodo}:")
            for h in hs:
                partes.append(f"  #{h['id']} [{h['severidad']}] {h['titulo']} ({h['estado']})")
        else:
            partes.append(f"Sin hallazgos en {periodo}.")
    except Exception:
        partes.append("Hallazgos: no disponible")
    partes.append("")

    # Sección 4: proveedores con variación fuerte (|variación| > 20%)
    try:
        ag = _cliente().get("/consulta/agregados", {"por": "proveedor",
                                                    "periodo_desde": periodo,
                                                    "periodo_hasta": periodo})
        fuertes = [g for g in ag["grupos"] if g.get("variacion") is not None and abs(g["variacion"]) > 0.2]
        if fuertes:
            partes.append("Variaciones fuertes por proveedor:")
            for g in fuertes:
                partes.append(f"  {g['clave']}: {g['variacion']:+.0%} ({_plata(g['total'])})")
        else:
            partes.append("Sin variaciones fuertes de proveedores.")
    except Exception:
        partes.append("Variaciones de proveedores: no disponible")
    partes.append("")

    # Sección 5: total de deudores
    try:
        dds = _cliente().get("/consulta/deudores", {"periodo": periodo})
        partes.append(
            f"Deudores: {len(dds['deudores'])} unidad(es), total {_plata(dds['total'])}"
        )
    except Exception:
        partes.append("Deudores: no disponible")

    return "\n".join(partes)


for fn in (consultar_gastos, agregados, listar_hallazgos, detalle_hallazgo, estado_liquidaciones, reglamento,
           leer_comprobante, buscar_en_comprobantes, buscar_semantico, deudores, detalle_liquidacion, resumen_mensual):
    mcp.tool()(fn)
# search/fetch devuelven dict pero sin output estructurado: ante un error de red
# el wrapper devuelve un string legible, y ChatGPT espera el JSON como texto.
for fn in (search, fetch):
    mcp.tool(structured_output=False)(fn)


# --- Tokens por persona: wrapper ASGI que valida /mcp/{token} antes del app MCP ---

_MOUNT_INTERNO = "/mcp/sesion"  # path fijo del app MCP; solo alcanzable vía el wrapper
_TTL_CACHE = 60.0  # segundos: revocar un token tarda ≤1 minuto en hacer efecto


def _validar_contra_api(token: str) -> tuple[bool, str | None]:
    """Consulta POST /auth/mcp-token/validar de la API, SIN sesión de bot (el endpoint
    solo confirma un secreto que el llamador ya posee). Cualquier falla → inválido
    (el token maestro del env sigue entrando aunque la API esté caída)."""
    base = os.environ.get("CT_API_URL", "https://api-consorcio.neuralcore.dev")
    body = json.dumps({"token": token}).encode()
    req = urllib.request.Request(base + "/auth/mcp-token/validar", data=body,
                                 headers={"Content-Type": "application/json",
                                          "User-Agent": "ConsorcioTransparente/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            d = json.loads(r.read())
        return bool(d.get("valido")), d.get("nombre")
    except Exception:
        return False, None


def _validar_token(token: str) -> tuple[bool, str | None]:
    """1º el token maestro del env (comparación constante); 2º los de la tabla vía API."""
    maestro = os.environ.get("CT_MCP_TOKEN", "")
    if maestro and secrets.compare_digest(token, maestro):
        return True, None  # el maestro no tiene nombre (y no se loguea)
    return _validar_contra_api(token)


class WrapperTokens:
    """ASGI que valida el token del path (/mcp/{token}) antes de delegar al app MCP
    montado en _MOUNT_INTERNO.

    - lifespan → directo al app interno (el session manager del transporte lo necesita).
    - http → extrae el token, lo valida con cache en memoria TTL 60 s (positivo y
      negativo) y reescribe el path al mount interno. Inválido o path ajeno → 404
      pelado sin cuerpo, como el mount fijo de antes.
    - el streamable http no usa websockets: ese scope se cierra sin delegar."""

    def __init__(self, app_interno, validar=None, reloj=None):
        self.app_interno = app_interno
        self._validar = validar or _validar_token
        self._reloj = reloj or time.monotonic
        self._cache: dict[str, tuple[float, bool]] = {}  # token → (ts, válido)

    async def _token_valido(self, token: str) -> bool:
        ahora = self._reloj()
        # Desaloja entradas vencidas: un atacante rotando tokens no infla el dict.
        for k, (ts, _) in list(self._cache.items()):
            if ahora - ts >= _TTL_CACHE:
                del self._cache[k]
        entrada = self._cache.get(token)
        if entrada is not None:
            return entrada[1]
        # En un thread: la validación contra la API es urllib bloqueante (timeout 10 s)
        # y no debe frenar el event loop. La cache se muta acá, en el loop.
        valido, nombre = await asyncio.to_thread(self._validar, token)
        self._cache[token] = (ahora, valido)
        if valido and nombre:
            # Una vez por entrada de cache (no por request); jamás el secreto.
            print(f"MCP: acceso validado de '{nombre}'", flush=True)
        return valido

    @staticmethod
    def _partir(path: str) -> tuple[str, str]:
        """'/mcp/abc/xyz' → ('abc', '/xyz'); path ajeno → ('', '')."""
        if not path.startswith("/mcp/"):
            return "", ""
        token, sep, cola = path[len("/mcp/"):].partition("/")
        return token, (sep + cola if sep else "")

    async def __call__(self, scope, receive, send):
        if scope["type"] == "lifespan":
            await self.app_interno(scope, receive, send)
            return
        if scope["type"] != "http":
            if scope["type"] == "websocket":
                await send({"type": "websocket.close"})
            return
        token, cola = self._partir(scope["path"])
        if token and await self._token_valido(token):
            path = _MOUNT_INTERNO + cola
            await self.app_interno(dict(scope, path=path, raw_path=path.encode()),
                                   receive, send)
            return
        await send({"type": "http.response.start", "status": 404,
                    "headers": [(b"content-length", b"0")]})
        await send({"type": "http.response.body", "body": b""})


def app_con_token():
    """La app MCP servida bajo /mcp/<token> con token por persona; cualquier otro
    path → 404 pelado.

    En mcp 2.x `streamable_http_app()` ya devuelve la Starlette con el lifespan
    del session manager, así que se monta en el path interno fijo y el wrapper
    reescribe el path tras validar (delegándole también el lifespan). La
    protección anti DNS-rebinding se apaga: detrás de cloudflared el Host es el
    hostname público y el secreto es el token del path."""
    from mcp.server.transport_security import TransportSecuritySettings

    interno = mcp.streamable_http_app(
        streamable_http_path=_MOUNT_INTERNO,
        stateless_http=True,
        transport_security=TransportSecuritySettings(enable_dns_rebinding_protection=False),
    )
    return WrapperTokens(interno)


if __name__ == "__main__":
    import uvicorn
    # access_log=False: el path incluye el token; no debe aparecer en docker logs
    uvicorn.run(app_con_token(), host="0.0.0.0", port=8765, access_log=False)
