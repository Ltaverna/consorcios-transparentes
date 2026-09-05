# Sincronización mensual automática (diseño aprobado 05-09-2026)

Cuando aparece el mes nuevo en Redconar, la máquina del tunnel baja la liquidación y los comprobantes y los
ingesta al panel por la API (mismo camino que una subida manual: cuadre obligatorio, reproceso idempotente).
Timer diario. **Nunca publica**: el triage y la publicación siguen siendo manuales. Sin canal de aviso:
el resultado se ve en el panel y en el journal de systemd.

## 1. Engine — `ct descargar liquidacion <AAAA-MM>`

- `PortalRedconar` (en `engine/ct/portal.py`) gana un método que navega la sección Expensas del portal,
  ubica el PDF de la liquidación del período y lo devuelve (bytes + nombre original del portal, formato
  `2026-08-31-...-RIVADAVIA_2069.pdf`).
- El subcomando lo guarda en `$CT_PRIVADO/liquidaciones/` (o `--carpeta`). Si el período no está en el
  portal, termina OK con mensaje "todavía no hay" (exit 0).
- Test con fixture HTML de la página de Expensas en `engine/tests/fixtures/`, **sintético o anonimizado**
  (nada de datos reales del consorcio en el repo), siguiendo el patrón de los tests de portal existentes.

## 2. Engine — `ct sincronizar` (módulo nuevo `engine/ct/sincronizar.py`, solo stdlib)

Orquestador idempotente que corre el timer. Estado local en `$CT_PRIVADO/sincronizacion.json`:
por período, si la liquidación ya se subió y el hash del último ZIP de comprobantes subido.

Cada corrida:
1. Login al portal → períodos disponibles.
2. **Liquidación nueva** (en el portal y no en la carpeta local): la baja.
3. **Comprobantes**: corre el `ct descargar` existente para el período más reciente del portal
   (idempotente, regenera `manifest.json`).
4. **Ingesta a la API** (cliente urllib + cookie jar; login con el usuario bot):
   - Liquidación local no subida → `POST /liquidaciones` → poll de `GET /liquidaciones/{id}` hasta
     `procesada`. Si `no_cuadra` o `error`: log claro y corta la corrida con exit ≠ 0 (queda visible en el
     panel para revisión humana; no intenta comprobantes).
   - Con la liquidación procesada (o ya publicada): arma el ZIP de la carpeta del período + manifest y lo
     sube (`POST /liquidaciones/{id}/comprobantes`) **solo si el hash del ZIP cambió** respecto del estado.
5. Log resumen al journal: qué bajó, cuadre (checks ok/mal), documentos y hallazgos del cruce.
   Cualquier falla (portal caído, API caída, timeout) → exit ≠ 0; la corrida del día siguiente reintenta.

Determinismo del hash: el ZIP se arma con entradas ordenadas y timestamps fijos, para que "mismos archivos"
dé siempre el mismo hash.

## 3. Credenciales y config (`.env` raíz, chmod 600, jamás al repo)

Existentes: `USER_REDCONAR`, `PASSWORD_REDCONAR` (el comando los acepta también como
`CT_REDCONAR_USUARIO`/`CT_REDCONAR_CLAVE`, como hoy). Nuevos:
- `CT_API_URL` (default `https://api-consorcio.neuralcore.dev`)
- `CT_API_BOT_EMAIL`, `CT_API_BOT_CLAVE` — usuario bot `robot@consorcio-transparente.local`, rol auditor,
  creado una vez por CLI. Riesgo aceptado y anotado: el bot podría publicar si roban la clave; mejora
  futura si molesta: rol `carga` con permisos solo de ingesta.

## 4. systemd (`deploy/systemd/` en el repo + sección nueva en `docs/DEPLOY.md`)

- `ct-sincronizar.service`: oneshot, `User=ltaverna`, `EnvironmentFile=/opt/consorcios-transparentes/.env`,
  `ExecStart` con el python del venv del engine corriendo `python -m ct sincronizar`.
- `ct-sincronizar.timer`: diario 06:30 (hora local), `Persistent=true` (recupera corridas perdidas).
- Instalación documentada en DEPLOY.md (copiar a `/etc/systemd/system/`, `daemon-reload`, `enable --now`),
  mismo patrón que el servicio del tunnel.

## 5. Pruebas (engine; la API no cambia — cero endpoints nuevos)

- Parseo de Expensas: fixture HTML (sintético/anonimizado) → encuentra el PDF del período pedido; período
  ausente → None.
- `sincronizar`: lógica de decisión con portal y API falsos inyectados (sin red): baja solo lo nuevo,
  sube liquidación una vez, saltea ZIP con hash igual, re-sube ZIP con hash distinto, corta ante
  `no_cuadra` con exit ≠ 0, estado JSON actualizado solo tras éxito.
- El armado determinista del ZIP tiene test propio (mismo contenido → mismo hash).

## Fuera de alcance

Notificaciones (email/Telegram), multi-consorcio, publicación automática, rol `carga`, reintentos
intra-día (el timer diario es el reintento).
