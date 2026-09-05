# SSO de Google para el equipo — Plan de implementación

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** los roles del equipo entran con el botón de Google además de la clave; los propietarios siguen solo con código por unidad.

**Architecture:** botón de Google Identity Services en `/entrar` que obtiene un ID token en el navegador y lo POSTea a `/auth/login-google`; la API verifica firma RS256 contra las JWKS de Google (PyJWT + PyJWKClient), exige alta previa del email en `usuarios` y setea la misma cookie `ct_sesion` de siempre. Apagado por defecto: sin `CT_GOOGLE_CLIENT_ID` el endpoint da 404 y el botón no aparece.

**Tech Stack:** lo existente + extra `pyjwt[crypto]` (RS256). Sin client secret (flujo de ID token).

**Spec:** `docs/superpowers/specs/2026-09-05-sso-google-design.md`.

**Contexto de la máquina:** venv `api/.venv` (suite hoy: 94 passed). Web: Node 22.11 → tests con `NODE_OPTIONS='--experimental-require-module' npm test` (hoy: 34 passed). Rama de trabajo: `sso-google` desde `main`. Commits en español + trailer de la sesión. El client ID real ya está en el `.env` de la raíz (`GOOGLE_CLIENT_ID`; el `GOOGLE_CLIENT_SECRET` de al lado NO se usa) — la configuración de producción es parte de la Task 3, no de las tareas de código.

---

### Task 1: API — config, verificación del ID token y `POST /auth/login-google`

**Files:**
- Modify: `api/pyproject.toml` (extra crypto), `api/app/config.py`, `api/app/security.py`, `api/app/routers/auth.py`, `api/.env.example`
- Test: `api/tests/test_security.py`, `api/tests/test_auth.py`

- [ ] **Step 1: Dependencia.** En `api/pyproject.toml`, cambiar `"pyjwt>=2.9"` por `"pyjwt[crypto]>=2.9"`. Instalar: `cd api && .venv/bin/pip install -e '.[dev]'`.

- [ ] **Step 2: Tests que fallan.** En `api/tests/test_security.py`:

```python
def test_verificar_id_token_google_basura_da_401():
    from fastapi import HTTPException
    with pytest.raises(HTTPException) as e:
        security.verificar_id_token_google("no-es-un-jwt")
    assert e.value.status_code == 401
```

(Este caso no toca la red: PyJWT rechaza el token al parsear el header, antes de buscar la clave.)

En `api/tests/test_auth.py`:

```python
def test_login_google_sin_configurar_da_404(db, cliente):
    r = cliente.post("/auth/login-google", json={"credential": "x"})
    assert r.status_code == 404


def test_login_google_sin_alta_da_403(db, cliente, monkeypatch):
    from app.config import settings
    monkeypatch.setattr(settings, "google_client_id", "cid-test")
    monkeypatch.setattr(security, "verificar_id_token_google", lambda c: "desconocido@gmail.com")
    r = cliente.post("/auth/login-google", json={"credential": "tok"})
    assert r.status_code == 403


def test_login_google_con_alta_entra(db, cliente, monkeypatch):
    from app.config import settings
    monkeypatch.setattr(settings, "google_client_id", "cid-test")
    monkeypatch.setattr(security, "verificar_id_token_google", lambda c: "consejo@example.com")
    admin.crear_usuario(db, "consejo@example.com", "Vecina", "consejo", "clave-x")
    r = cliente.post("/auth/login-google", json={"credential": "tok"})
    assert r.status_code == 200
    assert r.json() == {"rol": "consejo", "nombre": "Vecina"}
    assert security.COOKIE in r.cookies
```

(Verificar los imports del archivo: `admin` y `security` ya se importan en `conftest.py`; si `test_auth.py` no los importa, agregarlos como hacen los tests vecinos.)

- [ ] **Step 3: Verificar que fallan.** `cd api && .venv/bin/python -m pytest -q tests/test_security.py tests/test_auth.py` → FAIL (no existe el helper ni la ruta; el 404 del primer test va a dar 404 igual PERO por ruta inexistente — confirmar que tras implementar sigue pasando por el motivo correcto: el endpoint existe y devuelve 404 por config vacía).

- [ ] **Step 4: Implementar config.** `api/app/config.py`: agregar `google_client_id: str = ""` junto a los demás settings. `api/.env.example`: agregar `CT_GOOGLE_CLIENT_ID=  # client ID de OAuth para el botón de Google (vacío = SSO apagado; sin secret: flujo de ID token)`.

- [ ] **Step 5: Implementar el helper.** En `api/app/security.py` (arriba con los imports ya está `jwt`; `HTTPException` también):

```python
_JWKS_GOOGLE = jwt.PyJWKClient("https://www.googleapis.com/oauth2/v3/certs")


def verificar_id_token_google(credential: str) -> str:
    """Valida el ID token del botón de Google y devuelve el email (en minúsculas).

    Firma RS256 contra las JWKS de Google, audiencia = nuestro client ID, issuer de Google
    y email verificado. Cualquier falla es 401: al usuario no le sirve saber el detalle."""
    try:
        clave = _JWKS_GOOGLE.get_signing_key_from_jwt(credential)
        datos = jwt.decode(credential, clave.key, algorithms=["RS256"],
                           audience=settings.google_client_id)
        if datos.get("iss") not in ("accounts.google.com", "https://accounts.google.com"):
            raise ValueError("issuer desconocido")
        if not datos.get("email_verified"):
            raise ValueError("email sin verificar")
        return datos["email"].lower()
    except Exception:
        raise HTTPException(401, "No pudimos validar la cuenta de Google")
```

- [ ] **Step 6: Implementar el endpoint.** En `api/app/routers/auth.py`:

```python
class LoginGoogle(BaseModel):
    credential: str
```

y debajo de `login`:

```python
@router.post("/login-google")
def login_google(datos: LoginGoogle, request: Request, response: Response, db: Session = Depends(get_db)):
    if not settings.google_client_id:
        raise HTTPException(404, "SSO de Google no configurado")
    if not security.limiter_login.permitir(f"{security.ip_cliente(request)}|google"):
        raise HTTPException(429, "Demasiados intentos; probá de nuevo en unos minutos")
    email = security.verificar_id_token_google(datos.credential)
    u = db.query(models.Usuario).filter_by(email=email).first()
    if not u:
        raise HTTPException(403, "Esa cuenta no tiene acceso; pedile al auditor que te dé de alta")
    _entrar(response, f"u:{u.id}", u.rol)
    return {"rol": u.rol, "nombre": u.nombre}
```

- [ ] **Step 7: Suite completa.** `cd api && .venv/bin/python -m pytest -q` → 98 passed (94 + 4).

- [ ] **Step 8: Commit.**

```bash
git add api/pyproject.toml api/app/config.py api/app/security.py api/app/routers/auth.py api/.env.example api/tests/test_security.py api/tests/test_auth.py
git commit -m "API: login con Google para el equipo (ID token verificado, alta previa)"
```

### Task 2: Web — `api.loginGoogle` y el botón de GIS en la pestaña Equipo

**Files:**
- Modify: `web/lib/api.ts` (objeto `api`, junto a `login`), `web/components/login-forms.tsx`, `web/.env.production` (línea vacía documentada)
- Test: `web/tests/entrar.test.tsx`

- [ ] **Step 1: Tests que fallan.** En `web/tests/entrar.test.tsx` (los tests existentes de la página quedan intactos; `vi` ya está disponible en el setup de Vitest — verificar el import del archivo):

```tsx
test("con client ID configurado aparece el botón de Google en la pestaña Equipo", () => {
  vi.stubEnv("NEXT_PUBLIC_GOOGLE_CLIENT_ID", "cid-test");
  render(<PaginaEntrar />);
  expect(screen.getByTestId("boton-google")).toBeInTheDocument();
  vi.unstubAllEnvs();
});

test("sin client ID no hay botón de Google", () => {
  render(<PaginaEntrar />);
  expect(screen.queryByTestId("boton-google")).not.toBeInTheDocument();
});
```

(Usar el mismo componente que rendericen los tests existentes del archivo — si renderizan `FormulariosEntrar` en vez de la página, seguir ese patrón con `alEntrar={() => {}}`.)

- [ ] **Step 2: Verificar que fallan.** `cd web && NODE_OPTIONS='--experimental-require-module' npm test` → 1 FAIL (el segundo pasa vacuamente; el primero falla porque el testid no existe).

- [ ] **Step 3: Implementar `api.loginGoogle`.** En `web/lib/api.ts`, dentro del objeto `api`, junto a `login`:

```ts
  loginGoogle(credential: string) {
    return pedir<{ rol: Rol; nombre: string }>("/auth/login-google", conJson("POST", { credential }));
  },
```

- [ ] **Step 4: Implementar el botón.** En `web/components/login-forms.tsx` (imports nuevos: `useEffect`, `useRef`):

```tsx
function BotonGoogle({ alEntrar, alError }: { alEntrar: (rol: Rol) => void; alError: (m: string) => void }) {
  const clientId = process.env.NEXT_PUBLIC_GOOGLE_CLIENT_ID;
  const contenedor = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!clientId) return;
    const iniciar = () => {
      const google = (window as unknown as { google?: any }).google;
      if (!google?.accounts?.id || !contenedor.current) return;
      google.accounts.id.initialize({
        client_id: clientId,
        callback: async (resp: { credential: string }) => {
          try {
            const res = await api.loginGoogle(resp.credential);
            alEntrar(res.rol);
          } catch (err) {
            alError(mensajeError(err));
          }
        },
      });
      google.accounts.id.renderButton(contenedor.current, { theme: "outline", size: "large" });
    };
    if ((window as unknown as { google?: any }).google?.accounts?.id) {
      iniciar();
      return;
    }
    const s = document.createElement("script");
    s.src = "https://accounts.google.com/gsi/client";
    s.async = true;
    s.onload = iniciar;
    document.head.appendChild(s);
  }, [clientId, alEntrar, alError]);

  if (!clientId) return null;
  return (
    <div className="flex flex-col gap-3 pt-3">
      <div className="flex items-center gap-2 text-xs text-tinta-suave">
        <div className="h-px flex-1 bg-borde-suave" />
        o
        <div className="h-px flex-1 bg-borde-suave" />
      </div>
      <div ref={contenedor} data-testid="boton-google" className="flex justify-center" />
    </div>
  );
}
```

En `FormEquipo`, el return pasa a un fragment con el botón después del `</form>` (comparte el estado de error existente):

```tsx
  return (
    <>
      <form onSubmit={alEnviar} className="flex flex-col gap-3">
        {/* ...contenido actual sin cambios... */}
      </form>
      <BotonGoogle alEntrar={alEntrar} alError={setError} />
    </>
  );
```

(Si las clases `text-tinta-suave`/`bg-borde-suave` no existen en el theme, usar las equivalentes que ya usen los componentes vecinos — verificar en `ficha.tsx`/`lista.tsx`.)

En `web/.env.production`, agregar:

```
# Client ID de OAuth del botón de Google (público por diseño; vacío = sin botón).
NEXT_PUBLIC_GOOGLE_CLIENT_ID=
```

- [ ] **Step 5: Verificar.** `NODE_OPTIONS='--experimental-require-module' npm test` → 36 passed (34 + 2). `npm run build` → OK.

- [ ] **Step 6: Commit.**

```bash
git add web/lib/api.ts web/components/login-forms.tsx web/.env.production web/tests/entrar.test.tsx
git commit -m "Web: botón de Google en la entrada del equipo"
```

### Task 3: Cierre — suites, estado, merge y producción

- [ ] **Step 1:** Suites completas: api → 98 passed · web → 36 passed · `npm run build` → OK.
- [ ] **Step 2:** `docs/ESTADO.md`: sacar el pendiente de SSO; anotar en producción "login con Google para el equipo (alta previa obligatoria; `CT_GOOGLE_CLIENT_ID` / `NEXT_PUBLIC_GOOGLE_CLIENT_ID`)".
- [ ] **Step 3: Commit + merge.**

```bash
git add docs/ESTADO.md
git commit -m "Estado: SSO de Google del equipo implementado"
git checkout main && git merge --no-ff sso-google -m "SSO de Google para los roles del equipo"
```

- [ ] **Step 4: Producción (CON confirmación de Lucas):** copiar el client ID del `.env` raíz: agregar `CT_GOOGLE_CLIENT_ID=<GOOGLE_CLIENT_ID>` a `api/.env` y el mismo valor en `NEXT_PUBLIC_GOOGLE_CLIENT_ID` de `web/.env.production` (es público: se commitea). Verificar con Lucas que el OAuth client tenga los JavaScript origins `https://panel-consorcio.neuralcore.dev` y `http://localhost:3000`. Después: push, `docker compose build && docker compose up -d`, `cd web && npm run deploy:cf`, y smoke: `/auth/login-google` con body basura → 401 (ya no 404), y el botón visible en `/entrar`.
