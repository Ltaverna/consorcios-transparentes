# Voto del propietario desde su teléfono (dos modos: moderador y autoservicio)

**Fecha:** 2026-10-10
**Estado:** en revisión del usuario
**Alcance:** app de asamblea (`apps/asamblea/`) + nuevos endpoints de estado en la API del panel
(`api/`, FastAPI + Postgres). Un solo subsistema, una sola spec. No toca el motor.

## Contexto

Hoy la app de asamblea sincroniza vía una hoja de Google (Apps Script, `Code.gs`): el **moderador**
(PIN `2069`, gate solo del lado del cliente) carga presencia, poderes y votos pasando lista desde su
teléfono, y todos los dispositivos abiertos sondean la hoja cada ~4s y ven el estado en vivo. El resto de
los propietarios miran en lectura.

Queremos **sumar un segundo modo**: que **cada propietario vote desde su propio teléfono**, conviviendo con
el modo moderador actual. Las dos formas operan sobre el mismo estado compartido.

Decisiones de fondo ya tomadas con el dueño:
- **Control de identidad: confianza + bloqueo.** Cada uno reclama su unidad de una lista; una vez tomada, se
  bloquea a su dispositivo; el moderador supervisa y corrige. Sin contraseñas por unidad (el voto de
  consorcio es nominal y el moderador está presente).
- **Ventana de voto: mixto automático.** El voto de una moción se abre cuando su punto pasa a "en
  tratamiento" en la Agenda y se cierra al cerrar el punto; más un override manual para mociones sueltas.
- **Alcance: autoservicio completo** (voto + presencia + poderes).
- **Representación: autodeclarada + bloqueo.** El mandatario agrega desde su teléfono las unidades que
  representa (tope art.25h ≤5 propietarios); cada una queda bloqueada.
- **Backend: API del panel + Postgres** (reusar lo desplegado), con **bloqueo en el servidor** (claim
  atómico). Se descartó seguir con la hoja (bloqueo lento/frágil con `LockService`) y montar algo nuevo
  (SQLite dedicado / Durable Object): Postgres ya está desplegado detrás de la API.
- **Moderador: 2069 local + secreto de servidor.** El PIN 2069 sigue como gate local para mostrar los
  controles; las acciones sensibles se firman con un secreto de servidor nuevo (`CT_ASAMBLEA_MOD_TOKEN`).

Defaults fijados: el voto sigue **nominal** (por unidad, no secreto); la **exportación a Google Sheets se
mantiene** (solo migra la *sincronización en vivo* de la hoja a la API); el sondeo pasa a **~2s** contra la
API (SSE/push = mejora futura).

## Arquitectura y roles

Tres roles sobre el mismo estado compartido (Postgres, vía la API):

- **Moderador** (2069 local + `X-Asamblea-Mod`): todo lo de hoy — presencia/poderes/votos de quienes no usan
  teléfono, agenda, abrir/cerrar ventana (automático por agenda), y **override** de cualquier claim o voto.
  Sus escrituras saltean el bloqueo.
- **Propietario** (teléfono, sin PIN): reclama su unidad → queda presente y con la unidad bloqueada a su
  dispositivo; agrega unidades que representa (tope art.25h); vota con la ventana abierta. Solo toca lo que
  reclamó.
- **Espectador** (no reclamó): ve todo en vivo, en lectura.

**Flujo de datos:** el cliente deja de hablarle a la hoja y le habla a la API
(`api-consorcio.neuralcore.dev`) con el `X-Asamblea-Token` que ya existe. `GET /asamblea/estado` cada ~2s;
las acciones son `POST` puntuales. El **modo moderador sigue andando offline** con estado local si se cae la
red (el voto propio de los teléfonos requiere red, igual que hoy la hoja).

**Integridad — corte duro vs blando:** lo que necesita concurrencia segura (claims/presencia y votos) vive
en filas con restricción `UNIQUE` → claim atómico real. Lo blando y de baja concurrencia (agenda, oradores,
respuestas, objeciones, cumplimiento, metadatos de mociones) va en un JSON con `version` (último-gana),
igual que hoy.

## Modelo de datos (`api/app/models.py`)

Patrón existente: SQLAlchemy `Mapped`/`mapped_column`, helpers `JSONDual`, `FechaUTC`; tablas creadas con
`Base.metadata.create_all` (ya en `main.py`); tests en SQLite.

**1. `asamblea_sesion`** — la asamblea (una activa por vez; multi-consorcio = futuro).
- `id` PK · `consorcio_id` FK · `titulo`
- `doc` JSONB → `{ mociones:[{titulo, opciones, regla, abierta}], activa, agenda, palabra, respuestas,
  objeciones, cumplimiento }` — **sin los votos** (van aparte). `abierta` por moción = la ventana de voto.
- `version` BigInteger → se incrementa en cada escritura del `doc`.
- `creada` / `actualizada` (FechaUTC).

**2. `asamblea_claim`** — bloqueo + presencia + poderes. Una fila por unidad reclamada.
- `id` PK · `sesion_id` FK · `uf` Integer
- **`UNIQUE(sesion_id, uf)`** ← el candado.
- `device_id` String (qué teléfono; el moderador usa `'mod'`)
- `rol` String → `'titular'` | `'mandatario'`
- `presente` Boolean · `nombre` String (opcional) · `creada` (FechaUTC)
- Tope art.25h (≤5 propietarios representados por dispositivo) validado en el servidor al reclamar.

**3. `asamblea_voto`** — votos individuales.
- `id` PK · `sesion_id` FK · `mocion_idx` Integer · `uf` Integer
- **`UNIQUE(sesion_id, mocion_idx, uf)`** ← un voto por unidad por moción.
- `opcion_idx` Integer · `device_id` String · `ts` (FechaUTC).

**Estado ensamblado:** `GET /asamblea/estado` arma las tres tablas en **la misma forma** que el `state` que
el cliente ya entiende (`presentes`, `poderes`, `mociones[].votos`, `agenda`, …) y agrega `claims` (para la
UI de "esta unidad ya fue tomada") y `abierta` por moción. El `apply()` del cliente casi no cambia.

**Atomicidad portable:** el claim se hace con `INSERT` capturando el `IntegrityError` del `UNIQUE` (conflicto
= unidad ya tomada). Funciona igual en Postgres y en el SQLite de los tests.

## Endpoints y autenticación (`api/app/routers/asamblea.py`)

Dos niveles sobre el `X-Asamblea-Token` que ya existe:
- **Propietario** → solo el token + un `device_id` generado por el teléfono. Toca únicamente lo que reclamó,
  con la ventana abierta.
- **Moderador** → además `X-Asamblea-Mod` (nuevo setting `CT_ASAMBLEA_MOD_TOKEN`, **no** embebido; el
  moderador lo carga una vez y queda en su `localStorage`). Único credencial nuevo a distribuir.

El PIN 2069 queda como gate local para *mostrar* los controles; las acciones que escriben al servidor van
firmadas con `X-Asamblea-Mod`.

*Lectura (cualquiera con token):*
- `GET /asamblea/estado?desde=<version>` → estado ensamblado + `version`. Si no cambió desde esa versión,
  responde vacío/304 (sondeo barato ~2s). Devuelve la sesión activa (una sola; la crea el moderador al
  cargar las mociones).

*Propietario (token + `device_id`):*
- `POST /asamblea/claim` `{device, uf, representados?:[uf], nombre?}` → atómico, todo-o-nada. Toma su unidad
  (titular, presente) + las representadas (tope 5). Devuelve `{ok, claims}` o **409** `{conflicto:[uf]}`.
- `POST /asamblea/release` `{device, uf?}` → suelta sus propios claims (no los de otros).
- `POST /asamblea/voto` `{device, mocion, uf, opcion}` → exige ventana abierta y que el `device` sea dueño
  del claim de esa `uf`. Upsert. **403** si cerrada o no es su unidad.

*Moderador (token + `X-Asamblea-Mod`):*
- `POST /asamblea/mod/doc` `{patch}` → agenda, metadatos de mociones, `activa`, cumplimiento, respuestas,
  objeciones, oradores. Al pasar un punto a "en curso" setea `abierta=true` en su moción; al cerrarlo,
  `false` (el mixto automático). Sube `version`.
- `POST /asamblea/mod/ventana` `{mocion, abierta}` → abrir/cerrar manual (override para mociones sueltas).
- `POST /asamblea/mod/claim` `{uf, presente, rol, nombre}` → fija presencia/poder de quien no usa teléfono
  (`device='mod'`) o fuerza la toma de una unidad.
- `POST /asamblea/mod/voto` `{mocion, uf, opcion}` → emite/corrige un voto sin importar ventana ni dueño.
- `POST /asamblea/mod/release` `{uf}` → libera un claim trabado.
- `POST /asamblea/mod/reset` → borra claims, votos y presencias (el "Reiniciar votación" actual).

En el cliente, el objeto `sync` deja de postear a la hoja y pasa a llamar estos endpoints; las acciones de
moderador (ya detrás del gate MOD) agregan el header `X-Asamblea-Mod`.

## Experiencia de uso (cliente, `make_votacion.py`)

**Propietario (su teléfono, sin PIN):** hoy un tap de no-moderador salta el PIN; eso cambia. En Votar, el
espectador ve un llamador **"¿Sos propietario? Votá desde tu teléfono → Reclamar mi unidad"**.

Alta (diálogo corto, mobile-first):
1. **"¿Cuál es tu unidad?"** → lista (piso/depto + propietario); las tomadas, deshabilitadas con "ya tomada".
2. **Nombre** (opcional).
3. **"¿Representás otras unidades? (carta poder)"** → hasta 5 de la lista de libres; muestra "representás
   N/5" (tope art.25h con los avisos que ya valida `logica.js`).
4. Confirmar → `POST /claim`. Éxito: el teléfono recuerda "soy la unidad X (+ representadas)" en
   `localStorage` y queda presente. **409**: "esa unidad ya fue tomada" y refresca.

Ya identificado, en Votar ve **"Tus unidades"** y, para la moción con ventana abierta, botones grandes A
favor / En contra / Abstención por unidad. Cerrada: "la votación de esta moción todavía no está abierta / ya
cerró". Igual ve resultados en vivo. **"No soy esta unidad / salir"** libera el candado (`/release`). **No
re-reclama en cada moción**: a medida que se abren ventanas, solo toca su voto.

**Moderador (todo lo de hoy + agregados):** lo que ya hace sigue igual, ahora escribiendo a la API con el
header de moderador; el quórum suma los auto-claims solo. La ventana se abre/cierra al iniciar/cerrar
tratamiento del punto, más un toggle manual en la config de la moción para las sueltas. En "pasar lista",
las unidades auto-reclamadas llevan un **ícono de teléfono**; el moderador puede corregir un voto,
forzar/soltar una unidad trabada, y marcar presencia/poder de los que no usan teléfono (override).

## Reglas de bloqueo y casos borde

- **Claim atómico / conflicto:** `INSERT` con `UNIQUE`; choque → 409 con las UF en conflicto. Claim con
  varias unidades = todo-o-nada (transacción): si una representada está tomada, se rechaza entero y se
  informa cuál, para reintentar sin esa.
- **Tope art.25h en servidor:** propietarios representados distintos por dispositivo ≤5 (condominio = 1,
  reusando el agrupamiento por propietario). Matices finos (admin no puede ser mandatario) = aviso del
  cliente + moderador.
- **Ventana cerrada:** voto → 403 salvo moderador. Cerrar congela los votos (no los borra); reabrir permite
  cambios otra vez.
- **Cambiar voto:** con la ventana abierta, el dueño re-vota (upsert); al cerrar queda firme.
- **Override del moderador:** siempre gana (`device='mod'`); típicamente corrige con la ventana ya cerrada.
- **Alguien se fue / perdió el teléfono:** la unidad queda tomada; el moderador la libera con `mod/release`.
  Si un propietario borra los datos del navegador pierde su `device_id` → su unidad figura tomada por el
  device viejo; el moderador la libera y vuelve a reclamar. (TTL de expiración automática = mejora futura.)
- **Quitar presencia = liberar:** despresentar una unidad reclamada libera el claim y borra sus votos (igual
  que hoy).
- **Versión del estado blando:** `version` incremental; el cliente ignora versiones viejas (como el
  `lastServer` actual). Claims y votos no usan versión (son filas, siempre reflejan la DB).
- **Caída de la API en vivo:** los teléfonos de propietarios no pueden votar ("sin conexión, reintenta"); el
  moderador sigue cargando en local y reconcilia al volver la red. Misma degradación que hoy con la hoja.
- **Concurrencia:** claim atómico + transacción por request; el pool de la API alcanza para ~60 claims casi
  simultáneos al abrir una ventana.

## Testing

**API** (pytest, SQLite en memoria, como el resto):
- claim de unidad libre (ok) y de unidad tomada (409).
- release libera y permite re-claim.
- voto con ventana abierta + dueño (ok); cerrada (403); no-dueño (403).
- tope 5 representados (6º rechazado); condominio cuenta 1.
- `mod/*` saltean reglas (override); `X-Asamblea-Mod` inválido → 401.
- `estado?desde=version` vacío si no cambió.
- `GET estado` ensambla la forma compatible (`presentes` / `poderes` / `mociones[].votos`).

**Cliente** (node:test): la lógica de representación/tope ya vive en `logica.js` (26 tests); se extiende si
hace falta. El `sync` nuevo se verifica a mano (fetch).

## Migración

- La app pasa a usar la API; la hoja **deja de ser backend de sync**, pero la **exportación a Google Sheets
  se mantiene** intacta.
- Flag en el cliente para elegir backend (API / hoja) por si hace falta rollback rápido; default **API**. El
  `Code.gs` legacy no se toca.
- Se **agrega** `CT_ASAMBLEA_MOD_TOKEN` al `api/.env` (regla de oro: agregar líneas, no reescribir). Nuevas
  tablas vía `create_all` en el rebuild.
- Deploy: rebuild de la API + redeploy de la app a Pages, con confirmación del dueño.

## Archivos

- Modificar: `api/app/models.py` (3 tablas), `api/app/routers/asamblea.py` (endpoints de estado),
  `api/app/config.py` (`asamblea_mod_token`), `api/.env` / `api/.env.example` (agregar `CT_ASAMBLEA_MOD_TOKEN`).
- Crear: `api/tests/test_asamblea_estado.py` (claim/voto/ventana/override).
- Modificar: `apps/asamblea/make_votacion.py` (reemplazar el `sync` de hoja por cliente de API; alta del
  propietario; vista "Tus unidades"; ícono de teléfono y overrides en pasar lista; flag de backend).
- Posible: `apps/asamblea/logica.js` (+ tests) si hay que extender la validación de representación.
- Sin cambios en el motor.

## Fuera de alcance (este ciclo)

- Push por SSE/websockets (queda el sondeo ~2s).
- TTL de expiración automática de claims.
- Jubilar el `Code.gs` legacy.
- Multi-consorcio / multi-asamblea simultánea.

## Verificación

- Suites de la API en verde (incluye los casos de bloqueo y override).
- `make_votacion.py` genera el `index.html` sin error, con el flujo de propietario.
- Prueba manual en teléfono y tablet: dos teléfonos reclaman unidades distintas y votan; un tercero intenta
  una unidad ya tomada (409); el moderador abre/cierra ventana por agenda y corrige un voto.
- Deploy a `api-consorcio.neuralcore.dev` + `asamblea.neuralcore.dev`, con confirmación del dueño.
