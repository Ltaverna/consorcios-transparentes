# Plan 3 — Deploy de la etapa 1 (diseño aprobado 04-09-2026)

Poner en producción lo construido en los Planes 1 y 2: API detrás de `cloudflared` como
`api-consorcio.neuralcore.dev` y panel en Cloudflare Workers como `panel-consorcio.neuralcore.dev`,
con Neon (Postgres) y R2 (documentos). Runbook base: `docs/DEPLOY.md`.

**Contexto de ejecución**: la máquina de desarrollo NO es la máquina final del tunnel. El plan se divide en:
- **Fase A (código)**: ejecutable en cualquier máquina, con subagentes y doble revisión como los planes anteriores.
- **Fase B (operación)**: checklist en la máquina final, con Lucas presente (logins de Neon/Cloudflare, datos privados).

## Fase A — Código pre-deploy

1. **IP real detrás del tunnel**: nuevo setting `CT_CONFIAR_PROXY` (default false). Con proxy confiable,
   el rate limit de login usa el header `CF-Connecting-IP` (solo Cloudflare lo setea detrás del tunnel);
   sin el flag, sigue `request.client.host`. Helper único en `security.py`, con tests.
2. **Descarga forzada de documentos en R2**: `R2Storage.url_firmada(key, descarga=False)` agrega
   `ResponseContentDisposition: attachment` cuando `descarga=True`. `/documentos/{id}/contenido` la pide
   con descarga; `/informes/...` sin. Cierra el residuo de seguridad anotado (headers que el 307 no controla).
3. **`middleware.ts` → `proxy.ts`** en `web/` (convención Next 16; hoy warning de deprecación). Vía codemod
   oficial; la guardia de cookie queda idéntica.
4. **Alembic baseline** en `api/`: revisión inicial autogenerada desde los modelos; `alembic upgrade head`
   como paso de deploy (documentado en DEPLOY.md); dev/tests siguen con `create_all`. El esquema queda
   versionado antes de que existan datos reales que migrar.
5. **Front deployable**: adapter `@opennextjs/cloudflare`, `web/wrangler.jsonc` (proyecto `panel-consorcio`),
   `web/.env.production` con `NEXT_PUBLIC_API_URL=https://api-consorcio.neuralcore.dev` (no es secreto),
   scripts de build/deploy. En Fase A solo se verifica que el build del adapter corre; el deploy real es Fase B.

## Fase B — Operación en la máquina final

Orden: clonar + copiar lo privado → Neon (proyecto + connection string) → R2 (bucket + token API) →
`api/.env` completo (JWT largo, `CT_COOKIE_SEGURA=true`, `CT_COOKIE_DOMINIO=.neuralcore.dev`,
`CT_CONFIAR_PROXY=true`, CORS al panel) → `docker compose up -d --build` → `alembic upgrade head` →
`cli.py init` + usuario auditor → cloudflared tunnel + DNS `api-consorcio` → deploy del front +
DNS `panel-consorcio` → smoke E2E de producción con datos reales (subir la liquidación real de agosto
desde la carpeta privada, cruzar el ZIP real, publicar, entrar como propietario con un código) →
**medir el ZIP real** (si el cruce tarda > 90 s, anotar mover el endpoint a background como seguimiento).

## Criterio de éxito

`panel-consorcio.neuralcore.dev` usable con los datos reales de Rivadavia 2069; un propietario de prueba
entra con su código y ve el informe. La migración futura de la máquina del tunnel es solo mover el
contenedor + el tunnel (el estado vive en Neon/R2).

## Fuera de alcance

Fly.io (queda como upgrade opcional documentado), multiusuario/gating por rol en la UI (seguimiento
post-merge ya anotado), MCP y actualización automática de datos (diseño pendiente aparte).
