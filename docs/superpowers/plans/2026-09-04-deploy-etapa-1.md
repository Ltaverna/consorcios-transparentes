# Plan 3: Deploy de la etapa 1 (Fase A código + Fase B operación)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans para la Fase A. La Fase B es un checklist operativo que se ejecuta EN LA MÁQUINA FINAL con el usuario presente (logins de Neon/Cloudflare) — inline, no con subagentes. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** API en producción detrás de cloudflared (`api-consorcio.neuralcore.dev`) y panel en Cloudflare Workers (`panel-consorcio.neuralcore.dev`), con Neon + R2 y los datos reales de Rivadavia 2069.

**Architecture:** Fase A deja el código listo (IP real tras proxy, descarga forzada en R2, proxy.ts, Alembic baseline, adapter OpenNext). Fase B es el runbook de `docs/DEPLOY.md` ampliado, ejecutado en la máquina final. El estado vive en Neon/R2: migrar la máquina del tunnel después es mover contenedor + tunnel.

**Tech Stack:** lo ya existente + `alembic`, `@opennextjs/cloudflare`, `wrangler`, `cloudflared`.

**PARA UNA SESIÓN NUEVA DE CLAUDE CODE (máquina final):** antes de tocar nada: leé `CLAUDE.md`, `docs/ESTADO.md`, `docs/DEPLOY.md` y el spec `docs/superpowers/specs/2026-09-04-deploy-etapa-1-design.md`. Prerrequisitos de la máquina: git, Docker con daemon andando, Node/npm, `cloudflared`, Python 3.12+. Creá los venvs (`python3 -m venv engine/.venv && engine/.venv/bin/pip install -e 'engine[dev,excel]'`; ídem `api/.venv` con `-e engine -e 'api[dev]'`) y verificá las 3 suites ANTES de empezar (engine 29 passed 2 skipped · api 89 passed · `cd web && npm install && npm test` 29 passed). Verificá que llegaron los datos privados a `~/consorcio-transparente-privado/`. Trabajá en una rama `deploy-etapa-1`. Commits en español con el trailer de atribución de TU sesión.

---

## FASE A — Código pre-deploy

### Task A1: IP real detrás del proxy (`CT_CONFIAR_PROXY`)

**Files:**
- Modify: `api/app/config.py`, `api/app/security.py`, `api/app/routers/auth.py`, `api/.env.example`
- Test: `api/tests/test_security.py`, `api/tests/test_auth.py`

- [ ] **Step 1: Tests que fallan.** En `api/tests/test_security.py`:

```python
def test_ip_cliente_sin_proxy_usa_client_host():
    from unittest.mock import Mock
    req = Mock()
    req.client.host = "1.2.3.4"
    req.headers = {"cf-connecting-ip": "9.9.9.9"}
    assert security.ip_cliente(req) == "1.2.3.4"  # sin flag, ignora el header


def test_ip_cliente_con_proxy_usa_cf_connecting_ip(monkeypatch):
    from unittest.mock import Mock
    from app.config import settings
    monkeypatch.setattr(settings, "confiar_proxy", True)
    req = Mock()
    req.client.host = "10.0.0.1"
    req.headers = {"cf-connecting-ip": "181.30.1.2"}
    assert security.ip_cliente(req) == "181.30.1.2"
    req.headers = {}
    assert security.ip_cliente(req) == "10.0.0.1"  # con flag pero sin header, fallback
```

En `api/tests/test_auth.py` (fija que el rate limit usa el helper):

```python
def test_rate_limit_por_ip_del_proxy(db, cliente, monkeypatch):
    from app.config import settings
    from app import security
    monkeypatch.setattr(settings, "confiar_proxy", True)
    security.limiter_login._hits.clear()
    for i in range(10):
        cliente.post("/auth/login", json={"email": "x@example.com", "clave": "mala-clave"},
                     headers={"CF-Connecting-IP": "200.1.1.1"})
    r = cliente.post("/auth/login", json={"email": "x@example.com", "clave": "mala-clave"},
                     headers={"CF-Connecting-IP": "200.1.1.1"})
    assert r.status_code == 429
    r2 = cliente.post("/auth/login", json={"email": "x@example.com", "clave": "mala-clave"},
                      headers={"CF-Connecting-IP": "200.2.2.2"})
    assert r2.status_code == 401  # otra IP real → otro bucket
```

- [ ] **Step 2:** `cd api && .venv/bin/python -m pytest -q tests/test_security.py tests/test_auth.py` → FAIL (no existe `ip_cliente`).

- [ ] **Step 3: Implementar.**
  - `config.py`: agregar `confiar_proxy: bool = False`.
  - `security.py`:
```python
def ip_cliente(request: Request) -> str:
    """IP real del cliente. Detrás del tunnel de Cloudflare (CT_CONFIAR_PROXY=true),
    la conexión llega desde el proxy y la IP real viaja en CF-Connecting-IP."""
    if settings.confiar_proxy:
        cf = request.headers.get("cf-connecting-ip")
        if cf:
            return cf
    return request.client.host if request.client else "desconocido"
```
  - `routers/auth.py`: en `login` y `login_unidad`, reemplazar `request.client.host` por `security.ip_cliente(request)` en las claves del limiter.
  - `.env.example`: agregar `CT_CONFIAR_PROXY=  # true detrás de cloudflared: usa CF-Connecting-IP para el rate limit`.

- [ ] **Step 4:** suite completa `cd api && .venv/bin/python -m pytest -q` → 92 passed.

- [ ] **Step 5: Commit** — `git add api && git commit -m "API: IP real del cliente detrás del tunnel para el rate limit"` (+ trailer).

### Task A2: Descarga forzada de documentos en R2

**Files:**
- Modify: `api/app/storage.py`, `api/app/routers/documentos.py`
- Test: `api/tests/test_documentos_api.py`

- [ ] **Step 1: Test que falla.** En `api/tests/test_documentos_api.py`:

```python
def test_url_firmada_pide_descarga_para_documentos_pero_no_informes(db, auditor, monkeypatch):
    from .test_liquidaciones_api import subir
    llamadas = []
    class StorageEspia:
        def url_firmada(self, key, segundos=900, descarga=False):
            llamadas.append((key, descarga))
            return "https://r2.example/" + key
        def leer(self, key): return b""
        def guardar(self, key, data): pass
        def existe(self, key): return True
        def borrar(self, key): pass
    liq_id = subir(auditor).json()["id"]
    auditor.post(f"/liquidaciones/{liq_id}/publicar")
    d = models.Documento(liquidacion_id=liq_id, tipo="factura", archivo_key="comprobantes/2026-08/f.pdf")
    db.add(d)
    db.commit()
    from app.main import app
    espia = StorageEspia()
    original = app.state.storage
    app.state.storage = espia
    try:
        auditor.get(f"/documentos/{d.id}/contenido")
        auditor.get("/informes/2026-08/html")
    finally:
        app.state.storage = original
    assert (d.archivo_key, True) in llamadas          # documento → attachment
    assert any(k.startswith("informes/") and not desc for k, desc in llamadas)  # informe → inline
```

- [ ] **Step 2:** correr → FAIL (`url_firmada` no acepta `descarga`).

- [ ] **Step 3: Implementar.**
  - `storage.py`: `LocalStorage.url_firmada(self, key, segundos=900, descarga=False)` (sigue devolviendo None). `R2Storage.url_firmada(self, key, segundos=900, descarga=False)`: `params = {"Bucket": ..., "Key": key}`; si `descarga`: `params["ResponseContentDisposition"] = "attachment"`; presign con esos params.
  - `routers/documentos.py`: `_servir(request, key, attachment=True)` ya distingue informes de documentos por el parámetro existente — pasar `descarga=attachment` a `url_firmada` en la rama del 307. (Leer el código real: tras el fix `1f31f43`/ronda de cierre, `_servir` tiene el parámetro `attachment`; conectarlo.)

- [ ] **Step 4:** suite api completa → 93 passed.

- [ ] **Step 5: Commit** — `"API: URLs firmadas de documentos con descarga forzada"` (+ trailer).

### Task A3: `middleware.ts` → `proxy.ts`

**Files:**
- Modify/rename: `web/middleware.ts` → `web/proxy.ts`

- [ ] **Step 1:** `cd web && npx @next/codemod@canary middleware-to-proxy . ` (si el codemod no existe con ese nombre, leer `node_modules/next/dist/docs/` — la convención y el codemod exactos están ahí; hacerlo a mano es renombrar el archivo y la función exportada según esa doc).
- [ ] **Step 2:** verificar que la guardia quedó idéntica (redirect a `/entrar` sin cookie `ct_sesion`, mismo matcher). `npm test` → 29 passed; `npm run build` → **sin** el warning de deprecación.
- [ ] **Step 3:** smoke manual: `npm run dev` + `curl -I localhost:3000/panel` → 307 a `/entrar`; matar el server.
- [ ] **Step 4: Commit** — `"Web: migración a la convención proxy de Next 16"` (+ trailer).

### Task A4: Alembic baseline

**Files:**
- Create: `api/migrations/` (alembic init), revisión inicial
- Modify: `api/pyproject.toml` (dep `alembic>=1.13`), `api/alembic.ini`, `docs/DEPLOY.md`

- [ ] **Step 1:** `cd api && .venv/bin/pip install -e '.[dev]'` tras agregar `"alembic>=1.13"` a dependencies. `.venv/bin/alembic init migrations`.
- [ ] **Step 2:** `migrations/env.py`: importar `from app.db import Base` y `from app import models  # registra las tablas`; `target_metadata = Base.metadata`; tomar la URL de `app.config.settings.database_url` (override de `sqlalchemy.url`).
- [ ] **Step 3:** `CT_DATABASE_URL=sqlite:////tmp/alembic-base.db .venv/bin/alembic revision --autogenerate -m "esquema inicial etapa 1"` — revisar la revisión generada a mano: debe crear las 9 tablas (consorcio, unidades, usuarios, liquidaciones, gastos, documentos, hallazgos, hallazgo_eventos, informes) con sus constraints (incluida `UniqueConstraint(liquidacion_id, origen, clave)`).
- [ ] **Step 4: Verificar:** sobre una base vacía, `CT_DATABASE_URL=sqlite:////tmp/alembic-test.db .venv/bin/alembic upgrade head` corre limpio; borrar los /tmp. La suite api sigue verde (los tests usan create_all, no alembic — no deben verse afectados).
- [ ] **Step 5:** `docs/DEPLOY.md`: en el paso 5 (datos iniciales), antes del `cli.py init`, agregar `docker compose exec api alembic upgrade head` con una línea explicando que versiona el esquema (create_all del arranque es inofensivo porque el esquema coincide).
- [ ] **Step 6: Commit** — `"API: esquema versionado con Alembic (revisión inicial)"` (+ trailer).

### Task A5: Front deployable a Cloudflare Workers

**Files:**
- Create: `web/wrangler.jsonc`, `web/open-next.config.ts`, `web/.env.production`
- Modify: `web/package.json` (scripts), `web/.gitignore` (artefactos del adapter)

- [ ] **Step 1:** `cd web && npm i -D @opennextjs/cloudflare wrangler`. LEER la doc del adapter instalado (`node_modules/@opennextjs/cloudflare/README.md` o docs que traiga) — la config exacta (compatibility_date, flags `nodejs_compat`, assets binding, main) sale de ahí, no de memoria.
- [ ] **Step 2:** crear `web/wrangler.jsonc` con `"name": "panel-consorcio"` y lo que pida el adapter; `web/open-next.config.ts` con el default del adapter; `web/.env.production` con `NEXT_PUBLIC_API_URL=https://api-consorcio.neuralcore.dev` (no es secreto, se commitea — ajustar el `.gitignore` de web si `.env*` lo tapa: agregar `!.env.production`).
- [ ] **Step 3:** scripts en `package.json`: `"deploy:cf": "opennextjs-cloudflare build && opennextjs-cloudflare deploy"`, `"preview:cf": "opennextjs-cloudflare build && opennextjs-cloudflare preview"` (nombres exactos según el binario que instale el adapter — verificar en node_modules/.bin).
- [ ] **Step 4: Verificar SIN deployar:** `npx opennextjs-cloudflare build` termina OK (genera `.open-next/`); agregar `.open-next/` al `.gitignore` de web. `npm test` sigue 29 passed.
- [ ] **Step 5: Commit** — `"Web: adapter OpenNext y configuración de Cloudflare Workers"` (+ trailer).

**Cierre de Fase A:** las 3 suites verdes + `npm run build` web. Merge de `deploy-etapa-1` a `main` con las revisiones habituales (spec + calidad por tarea si se ejecuta con subagentes) y push.

---

## FASE B — Operación en la máquina final (con Lucas presente)

Seguir `docs/DEPLOY.md` como base; esto lo ordena y agrega lo nuevo. Cada paso se verifica antes del siguiente.

- [ ] **B1. Máquina lista:** repo clonado, suites verdes, datos privados copiados (`~/consorcio-transparente-privado/` con liquidaciones, comprobantes y reglamento), `.env` raíz con credenciales Redconar copiado a mano.
- [ ] **B2. Neon:** crear cuenta/proyecto (región AWS São Paulo), base `consorcio`; guardar la connection string `postgresql+psycopg://...` (pooled).
- [ ] **B3. R2:** en el dashboard de Cloudflare (cuenta 2fc07d6ef1fc55d3ed725a811cc572fb): crear bucket `consorcio-transparente` (privado) y un API token de R2 con lectura/escritura limitado al bucket; anotar endpoint, access key y secret.
- [ ] **B4. `api/.env`:** desde `.env.example`, completar TODO: Neon, R2, `CT_JWT_SECRET` (generar con `python3 -c "import secrets; print(secrets.token_urlsafe(48))"`), `CT_CORS_ORIGIN=https://panel-consorcio.neuralcore.dev`, `CT_COOKIE_SEGURA=true`, `CT_COOKIE_DOMINIO=.neuralcore.dev`, `CT_CONFIAR_PROXY=true`, `CT_STORAGE_DIR` vacío.
- [ ] **B5. API arriba:** `docker compose up -d --build` → `curl -s localhost:8080/salud` → `{"ok":true}`. (Si el build falla, el sospechoso es el empaquetado — ver nota final de DEPLOY.md.)
- [ ] **B6. Esquema y datos iniciales:** `docker compose exec api alembic upgrade head` → `docker compose exec api python cli.py init "Rivadavia 2069" --direccion "Av. Rivadavia 2069, CABA"` → `docker compose exec -it api python cli.py usuario <email-real> "Lucas" auditor`.
- [ ] **B7. Tunnel:** `cloudflared tunnel login` → `create consorcio` → `route dns consorcio api-consorcio.neuralcore.dev` → config.yml según DEPLOY.md → `cloudflared tunnel run consorcio` → `curl -s https://api-consorcio.neuralcore.dev/salud` → instalar como servicio (`sudo cloudflared service install`).
- [ ] **B8. Front:** `cd web && npm install && npm run deploy:cf` (login de wrangler si lo pide) → en el dashboard, custom domain `panel-consorcio.neuralcore.dev` para el worker → abrir la URL: pantalla de entrada.
- [ ] **B9. Smoke E2E de producción con datos reales:** entrar como auditor → subir el PDF real de julio (`~/consorcio-transparente-privado/liquidaciones/2026-07-...pdf`, período 2026-07) → luego agosto → verificar cuadre y hallazgos (deben aparecer los ~20 conocidos) → **medir el tiempo del ZIP real** de comprobantes de agosto al subirlo (si > 90 s: anotar en ESTADO mover el cruce a background; si Cloudflare corta con 504, reintentar es seguro — idempotente) → revisar hallazgos, publicar los que correspondan → publicar el informe → generar el código de una unidad de prueba → entrar como propietario en otra ventana → informe visible, Excel descargable, PDF de un comprobante se descarga como attachment.
- [ ] **B10. Cierre:** actualizar `docs/ESTADO.md` (producción andando, URLs, tiempo medido del ZIP, próximos pasos: segundo sistema de liquidación / reglas de mercado / MCP+actualización de datos / gating por rol antes de dar acceso a consejo) + commit + push. Verificar backups: Neon hace los suyos; los documentos quedan en R2.
