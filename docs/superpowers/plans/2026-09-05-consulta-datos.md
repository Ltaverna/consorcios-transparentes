# Consulta de datos (MCP + vista analítica) — Plan de implementación

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** los datos estructurados del consorcio se consultan con filtros/agregados desde el panel (`/panel/analisis`) y en lenguaje natural vía un servidor MCP accesible desde Claude Code, claude.ai y ChatGPT.

**Architecture:** dos endpoints read-only nuevos en la API (`/consulta/gastos`, `/consulta/agregados`) son la base compartida; el panel les pone UI; un contenedor `mcp` nuevo (misma imagen de la API, entrypoint propio con el SDK oficial de MCP en Streamable HTTP) los envuelve como tools, protegido por un segmento secreto en el path y publicado por el tunnel como `mcp-consorcio.neuralcore.dev`.

**Tech Stack:** lo existente + `mcp>=1.2` (SDK oficial, en deps de la API — comparte imagen).

**Spec:** `docs/superpowers/specs/2026-09-05-consulta-datos-design.md`.

**Contexto de la máquina:** suites hoy: engine 53 · api 111 · web 40 (Node 22.11 → `NODE_OPTIONS='--experimental-require-module' npm test`). Rama: `consulta-datos` desde `main`. Commits en español + trailer. Producción corre entera en compose (api, db, worker, tunnel); NADA se levanta ni deploya hasta la Task 4 con confirmación del usuario. El `.env` raíz tiene las credenciales del bot (`CT_API_BOT_EMAIL`/`CT_API_BOT_CLAVE`).

---

### Task 1: API — endpoints `/consulta`

**Files:**
- Create: `api/app/routers/consulta.py`
- Modify: `api/app/main.py` (registrar el router)
- Test: `api/tests/test_consulta_api.py` (nuevo)

- [ ] **Step 1: Tests que fallan.** Crear `api/tests/test_consulta_api.py`. Armado de datos: reusar `subir(auditor)` de `test_liquidaciones_api` sube UNA liquidación real procesada (fixture de agosto con 43 gastos — mirá qué períodos/gastos deja); para probar agregados multi-período, crear una segunda `models.Liquidacion` por modelo con 2-3 `models.Gasto` sintéticos (mirá los campos reales en `api/app/models.py`). Casos:

```python
def test_consulta_gastos_filtra_y_totaliza(db, auditor):
    # con la liquidación real subida: filtrar por proveedor parcial case-insensitive
    r = auditor.get("/consulta/gastos?proveedor=saczewiczyk")
    assert r.status_code == 200
    data = r.json()
    assert data["cantidad"] >= 1
    assert abs(data["total"] - sum(f["importe"] for f in data["filas"])) < 0.01
    assert all("SACZEWICZYK" in f["proveedor"].upper() for f in data["filas"])
    # rango de períodos + importe_min combinados
    r2 = auditor.get("/consulta/gastos?periodo_desde=2026-08&periodo_hasta=2026-08&importe_min=1000000")
    assert all(f["importe"] >= 1000000 and f["periodo"] == "2026-08" for f in r2.json()["filas"])


def test_consulta_gastos_busca_en_concepto(db, auditor):
    r = auditor.get("/consulta/gastos?q=sueldo")
    assert r.json()["cantidad"] >= 1
    assert all("SUELDO" in f["concepto"].upper() for f in r.json()["filas"])


def test_consulta_agregados_por_proveedor_y_periodo(db, auditor):
    # (con la segunda liquidación sintética creada para tener 2 períodos)
    r = auditor.get("/consulta/agregados?por=proveedor")
    grupos = r.json()["grupos"]
    assert grupos == sorted(grupos, key=lambda g: -g["total"])
    assert {"clave", "total", "cantidad", "variacion"} <= set(grupos[0].keys())
    p = auditor.get("/consulta/agregados?por=periodo").json()["grupos"]
    assert len(p) >= 2
    # `variacion`: total del grupo vs el mismo grupo en el período anterior al rango — con un
    # solo período en el rango y datos del anterior presentes, no debe ser None para claves repetidas
    assert auditor.get("/consulta/agregados?por=cualquiera").status_code == 422


def test_consulta_es_solo_del_equipo(db, auditor, ...):
    # propietario (patrón login-unidad de los tests vecinos) → 403 en ambos
    assert propietario.get("/consulta/gastos").status_code == 403
    assert propietario.get("/consulta/agregados?por=proveedor").status_code == 403
```

- [ ] **Step 2:** correr → FAIL (router inexistente).

- [ ] **Step 3: Implementar** `api/app/routers/consulta.py`:

```python
"""Consultas read-only sobre gastos: la base de la vista analítica y del MCP."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .. import models, security
from ..db import get_db

router = APIRouter(prefix="/consulta", tags=["consulta"])

_EQUIPO = security.requiere("auditor", "consejo", "moderador")


def _query_gastos(db, proveedor=None, categoria=None, q=None,
                  periodo_desde=None, periodo_hasta=None, importe_min=None):
    filas = db.query(models.Gasto, models.Liquidacion.periodo).join(models.Liquidacion)
    if periodo_desde:
        filas = filas.filter(models.Liquidacion.periodo >= periodo_desde)
    if periodo_hasta:
        filas = filas.filter(models.Liquidacion.periodo <= periodo_hasta)
    if proveedor:
        filas = filas.filter(models.Gasto.proveedor.ilike(f"%{proveedor}%"))
    if categoria:
        filas = filas.filter(models.Gasto.categoria.ilike(f"%{categoria}%"))
    if q:
        filas = filas.filter(models.Gasto.concepto.ilike(f"%{q}%"))
    if importe_min is not None:
        filas = filas.filter(models.Gasto.importe >= importe_min)
    return filas.all()


@router.get("/gastos")
def gastos(proveedor: str | None = None, categoria: str | None = None, q: str | None = None,
           periodo_desde: str | None = None, periodo_hasta: str | None = None,
           importe_min: float | None = None,
           db: Session = Depends(get_db), s: dict = Depends(_EQUIPO)):
    pares = _query_gastos(db, proveedor, categoria, q, periodo_desde, periodo_hasta, importe_min)
    filas = sorted(({"periodo": per, "n": g.n, "proveedor": g.proveedor, "categoria": g.categoria,
                     "concepto": g.concepto, "importe": g.importe, "factura_nro": g.factura_nro,
                     "pagos": g.pagos} for g, per in pares), key=lambda f: -f["importe"])
    return {"filas": filas, "total": sum(f["importe"] for f in filas), "cantidad": len(filas)}


@router.get("/agregados")
def agregados(por: str, periodo_desde: str | None = None, periodo_hasta: str | None = None,
              db: Session = Depends(get_db), s: dict = Depends(_EQUIPO)):
    if por not in ("proveedor", "categoria", "periodo"):
        raise HTTPException(422, "por debe ser proveedor, categoria o periodo")
    pares = _query_gastos(db, periodo_desde=periodo_desde, periodo_hasta=periodo_hasta)
    def clave(g, per):
        return per if por == "periodo" else getattr(g, por)
    grupos: dict[str, dict] = {}
    for g, per in pares:
        k = clave(g, per)
        it = grupos.setdefault(k, {"clave": k, "total": 0.0, "cantidad": 0})
        it["total"] += g.importe
        it["cantidad"] += 1
    # variación: mismo grupo en el período inmediato anterior al rango consultado
    periodos = sorted({per for _, per in pares})
    anterior = None
    if periodos:
        previa = (db.query(models.Liquidacion.periodo)
                    .filter(models.Liquidacion.periodo < periodos[0])
                    .order_by(models.Liquidacion.periodo.desc()).first())
        if previa and por != "periodo":
            pares_ant = _query_gastos(db, periodo_desde=previa[0], periodo_hasta=previa[0])
            anterior = {}
            for g, per in pares_ant:
                anterior[clave(g, per)] = anterior.get(clave(g, per), 0.0) + g.importe
    out = []
    for it in grupos.values():
        base = (anterior or {}).get(it["clave"])
        it["variacion"] = (it["total"] / base - 1) if base else None
        out.append(it)
    return {"grupos": sorted(out, key=lambda i: -i["total"])}
```

En `api/app/main.py`: importar y `app.include_router(consulta.router)` junto a los demás.

- [ ] **Step 4:** suite api completa → 115 passed (111 + 4).

- [ ] **Step 5: Commit.**

```bash
git add api/app/routers/consulta.py api/app/main.py api/tests/test_consulta_api.py
git commit -m "API: consultas de gastos con filtros y agregados (base del análisis y el MCP)"
```

### Task 2: Web — página `/panel/analisis`

**Files:**
- Create: `web/app/panel/analisis/page.tsx`
- Modify: `web/lib/api.ts`, `web/components/sidebar.tsx`
- Test: `web/tests/analisis.test.tsx` (nuevo)

- [ ] **Step 1: Tests que fallan.** `web/tests/analisis.test.tsx` (patrón MSW de los vecinos):

```tsx
import { render, screen } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { servidor, API } from "./msw";
import PaginaAnalisis from "@/app/panel/analisis/page";

const GRUPOS = { grupos: [
  { clave: "SACZEWICZYK MARIA EUGENIA", total: 5252000, cantidad: 3, variacion: 0.28 },
  { clave: "EDESUR S A", total: 1721032, cantidad: 3, variacion: -0.06 },
] };
const CATS = { grupos: [{ clave: "SUELDOS", total: 7000000, cantidad: 10, variacion: null }] };

test("renderiza el ranking de proveedores con variación", async () => {
  servidor.use(
    http.get(`${API}/consulta/agregados`, ({ request }) => {
      const por = new URL(request.url).searchParams.get("por");
      return HttpResponse.json(por === "proveedor" ? GRUPOS : CATS);
    }),
  );
  render(<PaginaAnalisis />);
  expect(await screen.findByText(/SACZEWICZYK/)).toBeInTheDocument();
  expect(screen.getByText(/\+28/)).toBeInTheDocument();   // variación formateada
  expect(screen.getByText(/SUELDOS/)).toBeInTheDocument();
});

test("el buscador de gastos consulta y muestra resultados", async () => {
  servidor.use(
    http.get(`${API}/consulta/agregados`, () => HttpResponse.json({ grupos: [] })),
    http.get(`${API}/consulta/gastos`, () => HttpResponse.json({
      filas: [{ periodo: "2026-08", n: 32, proveedor: "SACZEWICZYK MARIA EUGENIA",
                categoria: "MANTENIMIENTO", concepto: "Impermeabilización", importe: 2552000,
                factura_nro: "N° 7", pagos: [] }],
      total: 2552000, cantidad: 1,
    })),
  );
  render(<PaginaAnalisis />);
  const { fireEvent } = await import("@testing-library/react");
  fireEvent.change(await screen.findByLabelText(/Proveedor/), { target: { value: "sacze" } });
  fireEvent.click(screen.getByRole("button", { name: /Buscar/ }));
  expect(await screen.findByText(/Impermeabilización/)).toBeInTheDocument();
  expect(screen.getByText(/2.552.000/)).toBeInTheDocument();
});
```

- [ ] **Step 2:** correr → FAIL.

- [ ] **Step 3: Implementar.**
- `web/lib/api.ts`: tipos `GastoConsulta`/`GrupoAgregado` + en `api`: `consultarGastos(filtros)` (query string de los definidos) y `agregados(por, filtros?)`.
- `web/app/panel/analisis/page.tsx` (client, patrón de carga de `consorcio/page.tsx`): al montar trae agregados por proveedor y por categoría; dos Cards de ranking (tabla clave/total/variación — formatear con `moneda` y % con signo); Card "Buscar gastos" con inputs (Proveedor, Texto, Importe mínimo, Desde, Hasta — labels con `htmlFor`) y botón Buscar → tabla de resultados con total. Sin acciones de escritura.
- `web/components/sidebar.tsx`: ítem "Análisis" → `/panel/analisis` (ícono lucide `ChartColumn` o similar existente en el set).

- [ ] **Step 4:** `NODE_OPTIONS='--experimental-require-module' npm test` → 42 passed. `npm run build` → OK.

- [ ] **Step 5: Commit.**

```bash
git add web/app/panel/analisis web/lib/api.ts web/components/sidebar.tsx web/tests/analisis.test.tsx
git commit -m "Web: vista analítica con ranking de proveedores y buscador de gastos"
```

### Task 3: Servidor MCP + compose

**Files:**
- Create: `api/servidor_mcp.py`
- Modify: `api/pyproject.toml` (dep `mcp>=1.2`), `docker-compose.yml` (servicio `mcp`), `deploy/cloudflared/config.yml.example` (ingress), `api/.env.example` (nota del token)
- Test: `api/tests/test_mcp.py` (nuevo)

- [ ] **Step 1:** `"mcp>=1.2"` a dependencies de `api/pyproject.toml`; `cd api && .venv/bin/pip install -e '.[dev]'`. LEER la doc del SDK instalado (`.venv/lib/python*/site-packages/mcp/` o su README) para el shape exacto de `FastMCP` + streamable HTTP; el esqueleto de abajo es la intención — ajustá al API real del SDK y reportá si difiere.

- [ ] **Step 2: Tests que fallan.** `api/tests/test_mcp.py` — el server es un cliente HTTP de la API + tools; se testea la lógica de las tools con un cliente stub inyectado, no el transporte:

```python
"""Tools del MCP contra un cliente de API falso (sin red)."""
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
```

(Si registrás las tools con decoradores del SDK que envuelven la función, exponé también las funciones puras con esos nombres a nivel módulo para que el test las llame directo — p.ej. definí la función y después `mcp.tool()(consultar_gastos)`.)

- [ ] **Step 3:** correr → FAIL.

- [ ] **Step 4: Implementar** `api/servidor_mcp.py`. Esqueleto (ajustar al SDK real):

```python
"""Servidor MCP read-only del consorcio: expone las consultas como tools para
Claude Code, claude.ai y ChatGPT (Streamable HTTP + segmento secreto en el path)."""
import json
import os
import urllib.parse
import urllib.request
from http.cookiejar import CookieJar

from mcp.server.fastmcp import FastMCP

mcp = FastMCP("consorcio-transparente")


class ClienteApi:
    """Cliente mínimo de la API del panel con la sesión del bot (cookie)."""

    def __init__(self):
        self.base = os.environ.get("CT_API_URL", "https://api-consorcio.neuralcore.dev")
        jar = CookieJar()
        self.opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))
        body = json.dumps({"email": os.environ["CT_API_BOT_EMAIL"],
                           "clave": os.environ["CT_API_BOT_CLAVE"]}).encode()
        req = urllib.request.Request(self.base + "/auth/login", data=body,
                                     headers={"Content-Type": "application/json"})
        with self.opener.open(req, timeout=30) as r:
            r.read()

    def get(self, path, params=None):
        url = self.base + path + ("?" + urllib.parse.urlencode({k: v for k, v in (params or {}).items() if v is not None}) if params else "")
        with self.opener.open(url, timeout=60) as r:
            return json.loads(r.read())


_sesion = None


def _cliente():
    global _sesion
    if _sesion is None:
        _sesion = ClienteApi()
    return _sesion


def _plata(v):  # 2552000.0 -> "$2.552.000"
    return "$" + f"{v:,.0f}".replace(",", ".")


def consultar_gastos(proveedor: str = "", categoria: str = "", q: str = "",
                     periodo_desde: str = "", periodo_hasta: str = "", importe_min: float = 0) -> str:
    """Busca gastos de las liquidaciones con filtros combinables y devuelve filas + total."""
    d = _cliente().get("/consulta/gastos", {"proveedor": proveedor or None, "categoria": categoria or None,
                                            "q": q or None, "periodo_desde": periodo_desde or None,
                                            "periodo_hasta": periodo_hasta or None,
                                            "importe_min": importe_min or None})
    lineas = [f"{f['periodo']} · {f['proveedor']} · {f['concepto'][:80]} · {_plata(f['importe'])}"
              for f in d["filas"]]
    return f"{d['cantidad']} gasto(s), total {_plata(d['total'])}:\n" + "\n".join(lineas)
```

Más: `agregados(por, ...)` (tabla texto clave/total/variación), `listar_hallazgos(...)`/`detalle_hallazgo(id)` (texto legible con evidencia y qué pedir), `estado_liquidaciones()`, y los wrappers ChatGPT. **Degradación (spec §4)**: cada tool envuelve su cuerpo en try/except de errores de red/HTTP y devuelve un string claro ("la API del consorcio no respondió: <motivo breve>") — nunca un traceback; además, si el login del bot falla al primer uso, `_cliente` reintenta una vez (resetea `_sesion`) por si la sesión venció:

```python
def search(query: str) -> dict:
    """Compatibilidad ChatGPT: busca en gastos y hallazgos; devuelve results con id/title/url."""
    resultados = []
    d = _cliente().get("/consulta/gastos", {"q": query})
    for f in d["filas"][:10]:
        resultados.append({"id": f"gasto:{f['periodo']}:{f['n']}",
                           "title": f"{f['proveedor']} — {_plata(f['importe'])} ({f['periodo']})",
                           "url": f"https://panel-consorcio.neuralcore.dev/panel/liquidaciones"})
    hs = _cliente().get("/hallazgos", {})
    for h in hs:
        if query.lower() in h["titulo"].lower():
            resultados.append({"id": f"hallazgo:{h['id']}", "title": h["titulo"],
                               "url": f"https://panel-consorcio.neuralcore.dev/panel/hallazgos/{h['id']}"})
    return {"results": resultados}


def fetch(id: str) -> dict:
    """Compatibilidad ChatGPT: devuelve el detalle del recurso por id compuesto."""
    tipo, *resto = id.split(":")
    if tipo == "hallazgo":
        h = _cliente().get(f"/hallazgos/{resto[0]}")
        texto = f"{h['titulo']}\nEvidencia: {h['evidencia']}\nQué pedir: {h['recomendacion']}"
        return {"id": id, "title": h["titulo"], "text": texto, "url": "", "metadata": {"severidad": h["severidad"]}}
    per, n = resto
    d = _cliente().get("/consulta/gastos", {"periodo_desde": per, "periodo_hasta": per})
    f = next(x for x in d["filas"] if x["n"] == int(n))
    return {"id": id, "title": f["proveedor"], "text": json.dumps(f, ensure_ascii=False), "url": "", "metadata": {}}


for fn in (consultar_gastos, agregados, listar_hallazgos, detalle_hallazgo, estado_liquidaciones, search, fetch):
    mcp.tool()(fn)
```

Montaje con el token (al final del archivo; ajustar al API del SDK para obtener la app ASGI):

```python
def app_con_token():
    """La app MCP montada bajo /mcp/<token>/; cualquier otro path → 404 pelado."""
    from starlette.applications import Starlette
    from starlette.routing import Mount
    token = os.environ["CT_MCP_TOKEN"]
    return Starlette(routes=[Mount(f"/mcp/{token}", app=mcp.streamable_http_app())])


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app_con_token(), host="0.0.0.0", port=8765)
```

- [ ] **Step 5:** `docker-compose.yml`, servicio nuevo (estilo del worker):

```yaml
  mcp:
    build:
      context: .
      dockerfile: api/Dockerfile
    command: python servidor_mcp.py
    env_file:
      - .env          # CT_API_BOT_*, CT_MCP_TOKEN
    restart: unless-stopped
```

(Sin puerto publicado: solo lo alcanza el tunnel por la red interna.) En `deploy/cloudflared/config.yml.example`, agregar ANTES del catch-all:

```yaml
  - hostname: mcp-consorcio.neuralcore.dev
    service: http://mcp:8765
```

En `api/.env.example`: `# CT_MCP_TOKEN va en el .env RAÍZ (segmento secreto de la URL del MCP; generar con secrets.token_urlsafe(24))`.

- [ ] **Step 6:** suite api completa → 117 passed (115 + 2). `CT_PRIVADO_HOST=/tmp docker compose config >/dev/null && echo OK`. NO levantar nada.

- [ ] **Step 7: Commit.**

```bash
git add api/servidor_mcp.py api/pyproject.toml api/tests/test_mcp.py docker-compose.yml deploy/cloudflared/config.yml.example api/.env.example
git commit -m "MCP: servidor de consultas del consorcio (Streamable HTTP con token en el path)"
```

### Task 4: Cierre — merge, deploy y alta en los clientes (CON confirmación del usuario)

- [ ] **Step 1:** Suites: engine 53 · api 117 · web 42 · build OK. Revisión final de la rama + merge a `main`.
- [ ] **Step 2:** `docs/ESTADO.md` (consulta de datos implementada, URL del MCP sin el token) y `docs/DEPLOY.md` sección nueva "10. MCP de consultas" (token al `.env` raíz, ingress en `cloudflared/config.yml` REAL de la máquina — el example ya lo trae —, `docker compose up -d mcp`, DNS route una única vez, alta en los clientes). Commit.
- [ ] **Step 3: Producción (CON confirmación):** push → generar `CT_MCP_TOKEN` y agregarlo al `.env` raíz → agregar el ingress de `mcp-consorcio` al `cloudflared/config.yml` real (con sudo por el ownership 65532) → `cloudflared tunnel route dns consorcio mcp-consorcio.neuralcore.dev` (el binario del host sigue instalado y el cert está en `~/.cloudflared`) → `docker compose build && docker compose up -d api mcp && docker compose restart tunnel` → deploy del front (`npm run deploy:cf`).
- [ ] **Step 4: Smoke:** handshake MCP real con curl (POST initialize al endpoint con token → respuesta JSON-RPC; sin token → 404), `tools/list` devuelve las 7 tools, y una llamada real a `consultar_gastos` vía `tools/call` devolviendo datos de agosto. La página `/panel/analisis` carga con datos reales. Al usuario: pasarle la URL exacta (con token) para que la registre en claude.ai (Conectores) y ChatGPT (Conectores/modo desarrollador), y que pruebe una consulta.
