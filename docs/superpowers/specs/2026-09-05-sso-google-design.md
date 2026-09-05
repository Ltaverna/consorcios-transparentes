# SSO de Google para los roles del equipo (diseño aprobado 05-09-2026)

Los roles del equipo (auditor/consejo/moderador) pueden entrar con el botón de Google además de la clave.
Los propietarios siguen entrando solo con el código por unidad. Enfoque elegido: botón de Google Identity
Services en el front + verificación del ID token en la API (sin redirects, sin client secret). El login con
clave no se toca; conviven.

## 1. Config

- `api/app/config.py`: `google_client_id: str = ""` (env `CT_GOOGLE_CLIENT_ID`). Vacío = SSO apagado:
  `/auth/login-google` responde 404 y el front no muestra el botón. El client ID es público por diseño;
  no hay client secret en este flujo.
- `web/.env.production`: `NEXT_PUBLIC_GOOGLE_CLIENT_ID` (build-time, se commitea igual que la URL de la API).
- `api/.env.example`: línea nueva documentando `CT_GOOGLE_CLIENT_ID`.

## 2. API — `POST /auth/login-google`

Body `{"credential": "<id-token-de-google>"}`. Pasos:

1. `settings.google_client_id` vacío → 404.
2. Rate limit con `limiter_login` existente (clave `ip_cliente|google`).
3. Helper nuevo `security.verificar_id_token_google(credential) -> str` (devuelve el email en lower):
   verifica firma RS256 contra las JWKS de Google (`https://www.googleapis.com/oauth2/v3/certs`) con
   PyJWT + `PyJWKClient` cacheado a nivel módulo (se agrega la dependencia `cryptography` para RS256),
   `aud` = `settings.google_client_id`, `iss` ∈ {`accounts.google.com`, `https://accounts.google.com`}
   y `email_verified` true. Cualquier falla → 401 "No pudimos validar la cuenta de Google".
4. Buscar `usuarios` por ese email. Si no existe → 403 "Esa cuenta no tiene acceso; pedile al auditor que
   te dé de alta". No se crea ningún usuario (alta previa obligatoria, por CLI como hoy).
5. `_entrar(response, f"u:{u.id}", u.rol)` — cookie `ct_sesion` y respuesta idénticas al login con clave.

## 3. Front — botón en `/entrar`

En `web/components/login-forms.tsx`, pestaña Equipo, debajo del formulario: separador ("o") y el botón
oficial de GIS, solo si `NEXT_PUBLIC_GOOGLE_CLIENT_ID` está seteado. Script `https://accounts.google.com/gsi/client`
cargado on-demand; `google.accounts.id.initialize({ client_id, callback })` + `renderButton`. El callback
POSTea el `credential` vía `api.loginGoogle(credential)` (función nueva en `web/lib/api.ts`) y sigue el
mismo flujo post-login que el formulario (redirect al panel). Errores 401/403 → el mismo `MensajeError`
inline que usa el formulario del equipo (patrón existente; no toast).

## 4. Errores y bordes

- Cuenta de Google válida sin alta → 403 con mensaje claro; no revela nada más.
- Script de Google bloqueado (adblock) → el botón no aparece; la clave sigue disponible.
- `exp` del ID token lo valida PyJWT; sin nonce custom (no hay flujo propio que lo requiera).
- JWKS de Google inalcanzable desde la API → 401 genérico; la clave sigue funcionando.

## 5. Operación (Lucas, al estilo Fase B)

Google Cloud Console: proyecto → OAuth consent screen (externo, solo email/profile) → Credentials →
OAuth Client ID "Web application" con Authorized JavaScript origins `https://panel-consorcio.neuralcore.dev`
y `http://localhost:3000` (dev). Copiar el client ID a `api/.env` y `web/.env.production` → rebuild de la
API + redeploy del front.

## 6. Pruebas

- API (+3), mockeando `verificar_id_token_google` con monkeypatch (no se llama a Google en tests):
  credential inválido → 401; email verificado sin alta → 403; con alta → 200, cookie seteada y rol correcto.
  La validación real de firma queda cubierta por PyJWT.
- Web (+2): con `NEXT_PUBLIC_GOOGLE_CLIENT_ID` el contenedor del botón se renderiza en la pestaña Equipo
  y se dispara la carga del script; sin la variable, nada de eso aparece.

## Fuera de alcance

Alta de usuarios desde el panel (sigue por CLI), SSO para propietarios, refresh tokens/revocación (la
sesión sigue siendo el JWT propio con su vencimiento), otros IdP.
