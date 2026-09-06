# Backfill de sincronización desde noviembre 2025 (diseño aprobado 06-09-2026)

El período auditable arranca en noviembre 2025; la base tiene solo 2026-07 y 2026-08. El portal
expone todos los períodos en el select (`Redconar.periodos()`), así que el backfill es iterar el
pipeline mensual existente sobre los períodos viejos, del más antiguo al más nuevo (así
`cargar_anterior` y la serie histórica se construyen bien mes a mes).

## 1. `Sincronizador` (`engine/ct/sincronizar.py`)

- **Refactor sin cambio de comportamiento**: extraer los pasos por-período de `correr()` (bajar
  el PDF si no hay local → `descargar_mes` → subir a la API si falta → ZIP si cambió el hash) a
  `_sincronizar_periodo(periodo_portal, per, estado) -> bool` (True = sin fallas). La
  reconciliación con la API, la lectura/guardado de `sincronizacion.json` y el log de arranque
  quedan en `correr()`.
- **`correr(desde: str | None = None)`**:
  - `desde=None`: comportamiento idéntico al actual (solo `periodos[0]`) — el worker diario no
    cambia.
  - `desde="AAAA-MM"`: convierte cada período del portal con `periodo_api`, filtra los `>= desde`,
    los ordena ascendente y corre `_sincronizar_periodo` para cada uno. **Una falla en un mes no
    corta los siguientes** (log + sigue); devuelve 0 si todos OK, 1 si alguno falló. El estado
    existente hace idempotente el backfill (lo ya subido se saltea; el ZIP solo si cambió el hash).

## 2. CLI (`engine/ct/cli.py`)

- `ct sincronizar --desde AAAA-MM` (opcional; validar formato con regex, error claro si no).
- El worker llama `sincronizar(None)`: usar `getattr(args, "desde", None)` para tolerarlo.

## 3. Pruebas (`engine/tests/test_sincronizar.py`, con los fakes existentes)

- Backfill con `desde`: procesa todos los períodos `>= desde` en orden ascendente (verificar el
  orden de las subidas a la API fake).
- Los períodos ya subidos según el estado no se re-suben.
- Una falla del portal en un mes intermedio no impide los siguientes y `correr` devuelve 1.
- Sin `desde`: solo el período más reciente (regresión del comportamiento actual).
- CLI: `--desde` inválido → exit code 2 con mensaje.

## 4. Operativo (fuera del código, tras el deploy del worker)

1. Correr el backfill en el contenedor worker: `python -m ct sincronizar --desde 2025-11`
   (tiene credenciales, carpeta privada montada y red a la API). Mes a mes, más viejo primero.
2. Reprocesar 2026-06/07/08 en la API para regenerar sus hallazgos históricos contra la serie
   completa (la ingesta de un mes viejo no refresca los posteriores — limitación documentada).
3. Verificar: `estado_liquidaciones`, el índice de transparencia con ~10 meses, y el volumen del
   triage (cientos de pendientes esperables; nada se publica solo).

## Fuera de alcance

Paralelismo (el portal se scrapea secuencial, como el sync diario), reintentos automáticos por
mes (la corrida es re-ejecutable), UI de backfill.
