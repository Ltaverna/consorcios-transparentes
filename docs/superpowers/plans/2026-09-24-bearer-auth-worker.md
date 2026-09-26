# Auth por Bearer para el worker → API interna — Plan de implementación

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** El worker de sincronización autentica contra la API por `Authorization: Bearer` para poder usar la red interna de Docker (`http://api:8080`), eliminando la dependencia del DNS externo y del tunnel.

**Architecture:** La API acepta el mismo JWT por header además de la cookie (cookie primero, header fallback). El worker (`ApiPanel`) parsea el JWT del header `Set-Cookie` de la respuesta del login —no del `CookieJar`, que sobre `http://api:8080` descarta la cookie por `Domain=.neuralcore.dev`— y lo manda como Bearer en cada request. El navegador no se toca. Cambio compatible hacia atrás: con la URL pública siguen andando cookie y Bearer a la vez.

**Tech Stack:** Python (FastAPI + `urllib` stdlib), pytest. Spec: `docs/superpowers/specs/2026-09-20-bearer-auth-worker-design.md`.

**Comandos de test:**
- API: `cd api && .venv/bin/python -m pytest -q`
- Motor: `cd engine && .venv/bin/python -m pytest -q tests`

---

## File Structure

- `api/app/security.py` — `sesion()` acepta Bearer como fallback de la cookie. (Modificar)
- `api/tests/test_auth.py` — tests de la auth por Bearer. (Modificar)
- `engine/ct/sincronizar.py` — helper `_token_de_set_cookie`, `ApiPanel.token`, `login()` parsea el token, `_abrir()` manda el Bearer. (Modificar)
- `engine/tests/test_sincronizar.py` — tests del helper y de `ApiPanel` contra un server local. (Modificar)

Config fuera del repo (Task 3, con confirmación del dueño): `CT_API_URL=http://api:8080` en el `.env` raíz.

---

## Task 1: API acepta Bearer en `sesion()`

**Files:**
- Modify: `api/app/security.py:43-47`
- Test: `api/tests/test_auth.py`

Estado actual de la función (para ubicarte):

```python
def sesion(request: Request) -> dict:
    token = request.cookies.get(COOKIE)
    if not token:
        raise HTTPException(401, "Hay que iniciar sesión")
    return leer_token(token)
```

- [ ] **Step 1: Escribir los tests que fallan**

Agregar al final de `api/tests/test_auth.py` (usa las fixtures `db`, `cliente` y la constante `security.COOKIE` ya importada en ese archivo vía `from app import admin, models, security`):

```python
def test_sesion_por_bearer_sin_cookie(db, cliente):
    admin.crear_usuario(db, "bearer@example.com", "Bearer", "auditor", "clave-de-test-larga")
    r = cliente.post("/auth/login", json={"email": "bearer@example.com", "clave": "clave-de-test-larga"})
    assert r.status_code == 200
    token = cliente.cookies.get(security.COOKIE)
    assert token
    cliente.cookies.clear()  # sin cookie: la sesión tiene que sostenerse por el header
    r2 = cliente.get("/auth/yo", headers={"Authorization": f"Bearer {token}"})
    assert r2.status_code == 200
    assert r2.json()["rol"] == "auditor"


def test_bearer_invalido_da_401(cliente):
    r = cliente.get("/auth/yo", headers={"Authorization": "Bearer no-es-un-jwt"})
    assert r.status_code == 401
```

- [ ] **Step 2: Correr los tests para verlos fallar**

Run: `cd api && .venv/bin/python -m pytest -q tests/test_auth.py::test_sesion_por_bearer_sin_cookie tests/test_auth.py::test_bearer_invalido_da_401`
Expected: FAIL — `test_sesion_por_bearer_sin_cookie` da 401 (la API todavía no lee el header). `test_bearer_invalido_da_401` puede pasar de casualidad (sin cookie ni token válido ya da 401); no importa, el que manda es el primero.

- [ ] **Step 3: Implementar el fallback a Bearer**

Reemplazar `sesion()` en `api/app/security.py` por:

```python
def sesion(request: Request) -> dict:
    token = request.cookies.get(COOKIE)
    if not token:
        # Fallback para clientes sin cookie (el worker sobre http://api:8080, donde la
        # cookie Secure+Domain no aplica). El navegador sigue usando la cookie httpOnly.
        autorizacion = request.headers.get("Authorization", "")
        if autorizacion.startswith("Bearer "):
            token = autorizacion[len("Bearer "):].strip()
    if not token:
        raise HTTPException(401, "Hay que iniciar sesión")
    return leer_token(token)
```

- [ ] **Step 4: Correr los tests para verlos pasar**

Run: `cd api && .venv/bin/python -m pytest -q tests/test_auth.py`
Expected: PASS (todos los tests de auth, incluidos los nuevos y los de cookie preexistentes).

- [ ] **Step 5: Correr toda la suite de la API (regresión del navegador)**

Run: `cd api && .venv/bin/python -m pytest -q`
Expected: PASS — 194 (los 192 previos + 2 nuevos).

- [ ] **Step 6: Commit**

```bash
git add api/app/security.py api/tests/test_auth.py
git commit -m "API: sesion() acepta Authorization: Bearer además de la cookie"
```

---

## Task 2: `ApiPanel` parsea el token y lo manda como Bearer

**Files:**
- Modify: `engine/ct/sincronizar.py` (`ApiPanel.__init__` ~70-77, `_abrir` ~79-90, `login` ~110-111; nuevo helper a nivel módulo)
- Test: `engine/tests/test_sincronizar.py`

Estado actual (para ubicarte):

```python
    def __init__(self, base_url: str, email: str, clave: str, timeout: int = 120):
        self.base = base_url.rstrip("/")
        self.email, self.clave = email, clave
        self.timeout = timeout
        self.jar = CookieJar()
        self.opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(self.jar))
        self.opener.addheaders = [("User-Agent", "ConsorcioTransparente/1.0")]

    def _abrir(self, req: urllib.request.Request):
        try:
            with self.opener.open(req, timeout=self.timeout) as r:
                cuerpo = r.read().decode("utf-8", "ignore")
        except urllib.error.HTTPError as e:
            cuerpo = e.read().decode("utf-8", "ignore")
            try:
                detalle = json.loads(cuerpo).get("detail", cuerpo)
            except (ValueError, AttributeError):
                detalle = cuerpo[:300]
            raise ApiError(f"la API respondió {e.code}: {detalle}") from None
        return json.loads(cuerpo) if cuerpo else None
    ...
    def login(self) -> None:
        self._json("/auth/login", {"email": self.email, "clave": self.clave})
```

- [ ] **Step 1: Escribir el test del helper puro (falla)**

Agregar a `engine/tests/test_sincronizar.py`:

```python
def test_token_de_set_cookie_extrae_el_jwt():
    from ct.sincronizar import _token_de_set_cookie
    hdrs = ["ct_sesion=abc.def.ghi; Domain=.neuralcore.dev; Path=/; Secure; HttpOnly"]
    assert _token_de_set_cookie(hdrs) == "abc.def.ghi"


def test_token_de_set_cookie_sin_la_cookie_devuelve_none():
    from ct.sincronizar import _token_de_set_cookie
    assert _token_de_set_cookie(["otra=1; Path=/"]) is None
    assert _token_de_set_cookie([]) is None
```

- [ ] **Step 2: Correr el test para verlo fallar**

Run: `cd engine && .venv/bin/python -m pytest -q tests/test_sincronizar.py::test_token_de_set_cookie_extrae_el_jwt`
Expected: FAIL — `ImportError: cannot import name '_token_de_set_cookie'`.

- [ ] **Step 3: Implementar el helper**

Agregar a nivel de módulo en `engine/ct/sincronizar.py` (cerca de la clase `ApiPanel`):

```python
COOKIE_SESION = "ct_sesion"  # debe coincidir con api/app/security.py:COOKIE


def _token_de_set_cookie(headers, nombre: str = COOKIE_SESION) -> str | None:
    """Extrae el valor de la cookie `nombre` de una lista de headers Set-Cookie.

    Se parsea a mano en vez de leer del CookieJar: sobre http://api:8080 la cookie
    llega con Domain=.neuralcore.dev, que el jar descarta por no matchear el host, así
    que su valor nunca queda en el jar."""
    for h in headers or []:
        primera = h.split(";", 1)[0].strip()      # 'ct_sesion=<jwt>'
        if "=" in primera:
            k, v = primera.split("=", 1)
            if k.strip() == nombre:
                return v.strip()
    return None
```

- [ ] **Step 4: Correr los tests del helper para verlos pasar**

Run: `cd engine && .venv/bin/python -m pytest -q tests/test_sincronizar.py::test_token_de_set_cookie_extrae_el_jwt tests/test_sincronizar.py::test_token_de_set_cookie_sin_la_cookie_devuelve_none`
Expected: PASS.

- [ ] **Step 5: Escribir el test de integración de `ApiPanel` (falla)**

Agregar a `engine/tests/test_sincronizar.py`:

```python
def test_apipanel_autentica_por_bearer_aunque_el_jar_descarte_la_cookie():
    import http.server
    import threading
    from ct.sincronizar import ApiPanel

    recibido = {}

    class Handler(http.server.BaseHTTPRequestHandler):
        def log_message(self, *a):
            pass

        def do_POST(self):  # /auth/login
            self.rfile.read(int(self.headers.get("Content-Length", 0) or 0))  # drena el body
            self.send_response(200)
            # Domain que NO matchea 127.0.0.1: el jar la descarta, el token sale del header.
            self.send_header("Set-Cookie",
                             "ct_sesion=jwt-de-prueba; Domain=.neuralcore.dev; Path=/; Secure; HttpOnly")
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(b"{}")

        def do_GET(self):  # /liquidaciones (protegido)
            recibido["authorization"] = self.headers.get("Authorization")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(b"[]")

    srv = http.server.HTTPServer(("127.0.0.1", 0), Handler)
    hilo = threading.Thread(target=srv.serve_forever, daemon=True)
    hilo.start()
    try:
        api = ApiPanel(f"http://127.0.0.1:{srv.server_address[1]}", "bot@x", "clave")
        api.login()
        assert api.token == "jwt-de-prueba"
        assert api.liquidaciones() == []
        assert recibido["authorization"] == "Bearer jwt-de-prueba"
    finally:
        srv.shutdown()
```

- [ ] **Step 6: Correr el test de integración para verlo fallar**

Run: `cd engine && .venv/bin/python -m pytest -q tests/test_sincronizar.py::test_apipanel_autentica_por_bearer_aunque_el_jar_descarte_la_cookie`
Expected: FAIL — `AttributeError: 'ApiPanel' object has no attribute 'token'` (o `api.token` es None y el `Authorization` recibido es None).

- [ ] **Step 7: Implementar `token` + `login()` que parsea + `_abrir()` que manda el Bearer**

En `ApiPanel.__init__`, agregar como última línea:

```python
        self.token: str | None = None  # JWT de sesión para Authorization: Bearer (ver login)
```

En `_abrir`, agregar el header antes del `try` (primera línea del método):

```python
    def _abrir(self, req: urllib.request.Request):
        if self.token:
            req.add_header("Authorization", "Bearer " + self.token)
        try:
            with self.opener.open(req, timeout=self.timeout) as r:
                cuerpo = r.read().decode("utf-8", "ignore")
        except urllib.error.HTTPError as e:
            cuerpo = e.read().decode("utf-8", "ignore")
            try:
                detalle = json.loads(cuerpo).get("detail", cuerpo)
            except (ValueError, AttributeError):
                detalle = cuerpo[:300]
            raise ApiError(f"la API respondió {e.code}: {detalle}") from None
        return json.loads(cuerpo) if cuerpo else None
```

Reemplazar `login()` por una versión que captura el `Set-Cookie` de la respuesta:

```python
    def login(self) -> None:
        body = json.dumps({"email": self.email, "clave": self.clave}).encode()
        req = urllib.request.Request(self.base + "/auth/login", data=body,
                                     headers={"Content-Type": "application/json"})
        try:
            with self.opener.open(req, timeout=self.timeout) as r:
                set_cookies = r.headers.get_all("Set-Cookie") or []
        except urllib.error.HTTPError as e:
            cuerpo = e.read().decode("utf-8", "ignore")
            try:
                detalle = json.loads(cuerpo).get("detail", cuerpo)
            except (ValueError, AttributeError):
                detalle = cuerpo[:300]
            raise ApiError(f"la API respondió {e.code}: {detalle}") from None
        self.token = _token_de_set_cookie(set_cookies)
```

- [ ] **Step 8: Correr el test de integración para verlo pasar**

Run: `cd engine && .venv/bin/python -m pytest -q tests/test_sincronizar.py::test_apipanel_autentica_por_bearer_aunque_el_jar_descarte_la_cookie`
Expected: PASS.

- [ ] **Step 9: Correr toda la suite del motor (regresión)**

Run: `cd engine && .venv/bin/python -m pytest -q tests`
Expected: PASS — 154 (los 151 previos + 3 nuevos; 2 skipped de comprobantes sin la carpeta privada).

- [ ] **Step 10: Commit**

```bash
git add engine/ct/sincronizar.py engine/tests/test_sincronizar.py
git commit -m "Motor: ApiPanel autentica por Bearer (token del Set-Cookie del login)"
```

---

## Task 3: Rebuild y verificación en el deploy (requiere confirmación del dueño)

**Files:**
- Config fuera del repo: `.env` raíz (`CT_API_URL`)

> Esta tarea toca producción (rebuild + escritura en la base real vía sincronización). **No la ejecuta un subagente.** El controlador la propone al dueño y la corre con su OK explícito, siguiendo la regla del repo de deploy con confirmación.

- [ ] **Step 1: Rebuild de las imágenes**

Run: `cd /opt/consorcios-transparentes && docker compose build api worker`
Expected: build OK de ambos servicios.

- [ ] **Step 2: Levantar API y worker con el código nuevo**

Run: `docker compose up -d api worker`
Expected: ambos `Up`. Sin migración de base (no hubo cambios de esquema).

- [ ] **Step 3: Apuntar el worker a la red interna**

Agregar `CT_API_URL=http://api:8080` al `.env` raíz y recrear el worker:

```bash
printf 'CT_API_URL=http://api:8080\n' >> .env
docker compose up -d worker
```

- [ ] **Step 4: Verificar una sincronización manual**

Run: `docker compose run --rm worker python -m ct sincronizar`
Expected: sin `error de red`, termina en **código 0**; lista el período más reciente del portal y, si no hay cambios, no resube nada.

- [ ] **Step 5: Confirmar que el navegador sigue igual**

Entrar al panel y verificar que el login y la carga de datos funcionan (la auth por cookie no cambió).

---

## Notas de cierre

- Actualizar `docs/ESTADO.md` con una línea del ciclo (auth Bearer del worker) y marcar como resuelto el punto de fragilidad de DNS del sync.
- La memoria `sync-worker-dns-auth` describe el problema; al cerrar, anotar que el arreglo de fondo quedó implementado.
