# Auth por Bearer para el worker → API interna

**Fecha:** 2026-09-20
**Estado:** aprobado, listo para plan

## Problema

El servicio `worker` (`ct sincronizar`) le habla a la API por su **URL pública**
(`CT_API_URL` default `https://api-consorcio.neuralcore.dev`): sale a internet → Cloudflare → tunnel para
alcanzar la API que corre en el contenedor de al lado. El DNS embebido de Docker en el host falla de
forma **intermitente** al resolver ese nombre externo (`[Errno -5] No address associated with hostname`):
el 18/09/2026 la corrida anduvo, el 19 y el 20 fallaron. Cuando el DNS hipa, la sincronización baja del
portal pero **no puede subir a la API y muere en código 1**.

Apuntar el worker a la red interna (`CT_API_URL=http://api:8080`) hoy **no funciona**: `ApiPanel`
(`engine/ct/sincronizar.py`) autentica por **cookie de sesión** (`CookieJar`), y la cookie de la API es
`Secure` + `Domain=.neuralcore.dev` → no viaja sobre HTTP plano ni matchea el host `api`. El login pasa
pero la siguiente llamada da `401 Hay que iniciar sesión`. `security.sesion` (api/app/security.py:43-47)
lee el token **solo** de la cookie; no acepta `Authorization: Bearer`.

## Objetivo

Que el worker sincronice contra `http://api:8080` (red interna), eliminando la dependencia del DNS
externo y del tunnel. Para eso la API acepta el JWT también por header `Authorization: Bearer`, y el
worker lo manda leyéndolo de su `CookieJar` tras el login.

## No-objetivos

- No se toca la auth del navegador: sigue siendo cookie `httpOnly` `Secure` `SameSite=lax`.
- No se agrega un mecanismo de tokens de servicio separado (YAGNI para un solo bot).
- No se arregla la causa raíz del DNS flaky de Docker: se elimina la dependencia, no el síntoma.

## Diseño

### Componentes que cambian

**1. `api/app/security.py` → `sesion()`**

Además de la cookie, aceptar `Authorization: Bearer <token>`. Orden: **cookie primero** (comportamiento
del navegador intacto), header como fallback. Mismo `leer_token`, mismo JWT HS256. `requiere()` y
`crear_token`/`leer_token` no cambian.

```python
def sesion(request: Request) -> dict:
    token = request.cookies.get(COOKIE)
    if not token:
        auth = request.headers.get("Authorization", "")
        if auth.startswith("Bearer "):
            token = auth[7:].strip()
    if not token:
        raise HTTPException(401, "Hay que iniciar sesión")
    return leer_token(token)
```

**2. `engine/ct/sincronizar.py` → `ApiPanel`**

- Nuevo atributo `self.token = None` en `__init__`.
- En `login()`, capturar los **headers de la respuesta** y parsear el `Set-Cookie` para extraer el valor
  de `ct_sesion=<jwt>`, guardándolo en `self.token`. **No se lee del `CookieJar`**: sobre `http://api:8080`
  la cookie trae `Domain=.neuralcore.dev`, que el jar rechaza por no matchear el host `api` (no la
  guarda). Parsear el header sortea esa política de dominio.
- En `_abrir(req)`, si `self.token`, agregar `req.add_header("Authorization", "Bearer " + self.token)`.
  Es el único chokepoint (todo pasa por `_abrir`). El header solo se agrega cuando hay token, así las
  requests sin sesión (p. ej. `/salud`) no lo llevan.
- El nombre de cookie (`ct_sesion`) se referencia por su literal en el motor: el motor no importa de la
  API. Un comentario deja anotada la correspondencia con `api/app/security.py:COOKIE`.

`login()` necesita acceder a los headers de la respuesta, que hoy `_abrir` descarta (solo lee el body).
Ajuste mínimo: `login()` arma su propio `Request` y lo abre capturando `resp.headers.get_all("Set-Cookie")`
(o equivalente), en vez de pasar por `_json`. El resto de los métodos siguen usando `_json`/`_multipart`.

**3. Config (deploy, fuera del repo)**

`CT_API_URL=http://api:8080` en el `.env` raíz del worker + recrear el worker. Se aplica al final del
ciclo, con confirmación del dueño.

### Flujo de datos

- **Worker**: `POST /auth/login` (body `email`+`clave`) → API responde `200` + `Set-Cookie` httpOnly. El
  worker parsea `ct_sesion` del header `Set-Cookie` → `self.token`. Las siguientes requests a `http://api:8080` llevan
  `Authorization: Bearer <jwt>`. `sesion()` no encuentra cookie válida → lee el header → `leer_token` → OK.
- **Navegador**: sin cambios. El login setea la cookie httpOnly; las requests van con cookie; `sesion()`
  la toma primero y ni mira el header.

### Manejo de errores

- Login sin `Set-Cookie` esperado (o sin `ct_sesion` en él) → `self.token = None` → requests sin header →
  `401` claro (mismo `ApiError` que hoy).
- Bearer vencido o malformado → `leer_token` tira `401 "Sesión inválida o vencida"` (ya existe).
- Bearer presente **y** cookie presente → gana la cookie (se evalúa primero); irrelevante para el worker,
  que no manda cookie sobre HTTP interno.

### Seguridad

- El Bearer es solo otro transporte del **mismo** JWT firmado con `jwt_secret`. No agrega superficie: un
  atacante necesita el JWT de todos modos.
- No se expone el token al navegador (la respuesta del login no cambia), así que `httpOnly` sigue
  protegiendo contra XSS.
- Bearer no se auto-envía → inmune a CSRF; no empeora la postura actual (que se apoya en `SameSite=lax`).

## Testing (TDD)

**API (`api/tests`)**

- `sesion()` unit: (a) cookie válida → OK; (b) sin cookie + `Authorization: Bearer <jwt válido>` → OK;
  (c) `Bearer <jwt inválido>` → 401; (d) sin cookie ni header → 401.
- Integración: un endpoint protegido (p. ej. `GET /liquidaciones`) responde `200` con Bearer y **sin**
  cookie.
- Regresión del navegador: los tests existentes de auth por cookie deben seguir en verde sin tocarlos.

**Motor (`engine/tests`)**

- `ApiPanel.login()`: con una respuesta de login que trae `Set-Cookie: ct_sesion=<jwt>; Domain=...;
  Secure; HttpOnly`, `self.token` queda con el `<jwt>` (parseado del header, no del jar).
- `ApiPanel._abrir`: con `self.token` seteado, la `Request` sale con `Authorization: Bearer <jwt>`; con
  `self.token = None`, sin ese header.
- Caso `Domain` no matchea el host interno: se verifica que el token igual se extrae del header (el jar
  puede haber descartado la cookie) y las requests autentican por Bearer.

## Rebuild / deploy

1. `docker compose build api worker` (API por `security.py`, worker por `sincronizar.py`).
2. Sin migración de base.
3. `docker compose up -d api worker`.
4. Aplicar `CT_API_URL=http://api:8080` en el `.env` raíz y recrear el worker.
5. Verificar con `docker compose run --rm worker python -m ct sincronizar`: debe subir sin el
   `error de red` y terminar en código 0.

## Archivos

- Modificar: `api/app/security.py` (`sesion()`).
- Modificar: `engine/ct/sincronizar.py` (`ApiPanel.__init__`, `login`, `_abrir`).
- Test: `api/tests/` (auth por Bearer), `engine/tests/` (ApiPanel con token).
- Config (fuera del repo): `.env` raíz (`CT_API_URL`).
