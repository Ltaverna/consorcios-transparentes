# MCP: tokens por persona (diseño aprobado 06-09-2026 — etapa 1 de acceso individual)

Cada persona recibe su propia URL del MCP con su token; revocar a una no afecta a las demás.
Etapa 2 (OAuth 2.1 completo con login) queda anotada como pendiente para cuando el grupo crezca.

## 1. Modelo y migración

- Tabla nueva `mcp_tokens`: `id`, `nombre` (único, p.ej. "lucas", "amigo-juan"), `token_sha256`
  (hex, indexado — el token es de alta entropía, sha256 alcanza y permite lookup directo),
  `activo` (bool, default true), `creado` (timestamp). Migración Alembic.
- El token en claro solo existe en el momento de la creación (se muestra una vez); en la base
  queda el hash.

## 2. Validación en el server MCP

- El server deja el mount fijo por env y pasa a rutear `/mcp/{token}/...` dinámico: un wrapper ASGI
  propio valida el token ANTES de pasar al app MCP (path reescrito al mount interno fijo). Token
  inválido → 404 pelado, como hoy.
- Validación: (a) el token del env `CT_MCP_TOKEN` sigue siendo válido (token maestro del
  administrador — los conectores ya configurados no se tocan); (b) los de la tabla, vía un endpoint
  nuevo de la API `POST /auth/mcp-token/validar {token}` → `{valido, nombre}` (sin sesión: solo
  confirma un secreto que el llamador ya posee; con el rate limit del limiter existente por IP).
- Cache en memoria del MCP: token→(válido, nombre) con TTL 60 s (positivo y negativo) — la revocación
  tarda ≤1 minuto en hacer efecto y la API no recibe un hit por request.
- Log de uso: al validar un token de la tabla, el server loguea el `nombre` (visibilidad de quién usa
  el MCP en `docker logs`), nunca el token.

## 3. Administración

- Subcomandos en `api/cli.py` (contenedor de la API, acceso directo a la base):
  - `mcp-token crear <nombre>` → genera `secrets.token_urlsafe(24)`, guarda el hash, imprime la URL
    completa UNA vez.
  - `mcp-token revocar <nombre>` → `activo=false`.
  - `mcp-token listar` → nombre, activo, creado (sin hashes).
- Sin UI en el panel por ahora (lo administra el auditor por CLI; upgrade posible después).

## 4. Pruebas

- API (+2): validar acepta token vigente y rechaza revocado/inexistente (mismo mensaje); rate limit
  aplicado.
- MCP (+3): wrapper acepta el token del env; acepta uno de tabla vía cliente stub; 404 con inválido;
  la cache evita revalidar dentro del TTL y expira (con reloj monkeypatcheado).
- CLI: crear/listar/revocar contra la base de tests (smoke en el mismo estilo de los subcomandos ya
  testeados o verificación manual reportada).

## Fuera de alcance (etapa 2, pendiente anotado)

OAuth 2.1 completo (authorization server con login del panel, PKCE, registro dinámico, tokens con
expiración), UI de administración en el panel, scopes por herramienta.
