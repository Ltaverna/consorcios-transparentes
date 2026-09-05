# Deploy de la API en la máquina del tunnel

Checklist para dejar la API corriendo en una máquina nueva detrás de `cloudflared`, publicada como
`api-consorcio.neuralcore.dev`. (El front `web/` NO corre acá: va a Cloudflare Workers — Plan 3.)

## 1. Prerrequisitos en la máquina nueva

- git, Docker (con el daemon corriendo) y `cloudflared` (`brew install cloudflared` / paquete de Cloudflare).
- Acceso a la cuenta de Cloudflare dueña de `neuralcore.dev`.

## 2. Clonar y configurar

```bash
git clone https://github.com/LTaverna/consorcios-transparentes.git
cd consorcios-transparentes
cp api/.env.example api/.env    # completar (ver abajo)
```

`api/.env` — **nada de esto va al repo**:
- `CT_DATABASE_URL`: la connection string de Neon (`postgresql+psycopg://...`). Para arrancar sin Neon,
  modo local con SQLite: ver los comentarios de `docker-compose.yml`.
- `CT_JWT_SECRET`: generar uno largo: `python3 -c "import secrets; print(secrets.token_urlsafe(48))"`.
- `CT_R2_*`: credenciales del bucket R2 (privado). Sin R2, setear `CT_STORAGE_DIR` (modo local).
- `CT_CORS_ORIGIN=https://panel-consorcio.neuralcore.dev`
- `CT_CONFIAR_PROXY=true` — detrás del tunnel, el rate limit usa la IP real de `CF-Connecting-IP`.
- `CT_COOKIE_SEGURA=true`
- `CT_COOKIE_DOMINIO=.neuralcore.dev` — front y API viven en subdominios distintos (`panel-consorcio` y
  `api-consorcio`); sin esto la cookie queda host-only y el panel nunca la recibe, lo que produce un loop
  infinito de redirects al login.

**Guardas de arranque**: con R2 configurado, la API se niega a arrancar si `CT_JWT_SECRET` sigue en el
default o si `CT_COOKIE_SEGURA` no está en true. Es intencional.

## 3. Lo que se copia a mano (nunca por git)

- `~/consorcio-transparente-privado/` completa (liquidaciones PDF, comprobantes, reglamento, planillas).
- Las credenciales de Redconar (si se va a usar `ct descargar` desde esa máquina): variables
  `CT_REDCONAR_USUARIO` / `CT_REDCONAR_CLAVE` o ingreso por consola. No se guardan en archivos del repo.

## 4. Build y arranque

```bash
docker compose build
docker compose run --rm api alembic upgrade head   # crea/versiona el esquema antes de arrancar
docker compose up -d
curl -s localhost:8080/salud     # → {"ok":true}
```

El `create_all` que ejecuta la API al arrancar es inofensivo después de `alembic upgrade head`:
usa `checkfirst=True` y el esquema ya coincide, así que no toca nada.

## 5. Datos iniciales (una sola vez)

```bash
docker compose exec api python cli.py init "Rivadavia 2069" --direccion "Av. Rivadavia 2069, CABA"
docker compose exec -it api python cli.py usuario <tu-email> "Lucas" auditor   # pide la clave por consola
# Los códigos por unidad se generan después desde el panel (Consorcio → Generar código),
# o por CLI: docker compose exec api python cli.py codigo <uf>
```

## 6. Tunnel cloudflared

```bash
cloudflared tunnel login                      # abre el navegador, elegir neuralcore.dev
cloudflared tunnel create consorcio
cloudflared tunnel route dns consorcio api-consorcio.neuralcore.dev
```

`~/.cloudflared/config.yml`:

```yaml
tunnel: consorcio
credentials-file: /Users/<usuario>/.cloudflared/<id-del-tunnel>.json
ingress:
  - hostname: api-consorcio.neuralcore.dev
    service: http://localhost:8080
  - service: http_status:404
```

```bash
cloudflared tunnel run consorcio             # probar
# como servicio permanente:
sudo cloudflared service install             # (macOS: launchd; Linux: systemd)
```

Verificar: `curl -s https://api-consorcio.neuralcore.dev/salud` → `{"ok":true}`.

## 7. Notas

- **Rate limit detrás del tunnel**: con `CT_CONFIAR_PROXY=true` la API toma la IP real del header
  `CF-Connecting-IP`. Ese header es confiable solo si la API no es alcanzable de forma directa:
  el contenedor publica el puerto solo en localhost y el único camino externo es el tunnel.
- **Warning esperado en el deploy del front**: `npm run deploy:cf` avisa "Node.js middleware support is
  experimental in cloudflare" — es por `proxy.ts`, que solo lee la cookie y redirige; no bloquea. Ante
  dudas, probar antes con `npm run preview:cf` (requiere la API de producción accesible).
- **Actualizar**: `git pull && docker compose build && docker compose run --rm api alembic upgrade head
  && docker compose up -d`.
- **Backup**: la base es Neon (backups propios) o `datos-api/` en modo local; los documentos, R2 o `datos-api/storage`.
- **Primer uso real**: medir la subida del ZIP de comprobantes de un mes real (el endpoint es sincrónico;
  si tarda más de ~90 s habrá que moverlo a background — anotado).
- El build de la imagen quedó verificado por inspección pero no ejecutado en la máquina de desarrollo
  (daemon apagado): el primer `docker compose build` en la máquina nueva es la prueba real. Si falla,
  el sospechoso más probable es el empaquetado (`pip install ./engine ./api`) — ambos pyproject ya
  declaran sus paquetes explícitamente.
