# Reglas históricas: hallazgos sobre la serie de liquidaciones (diseño aprobado 06-09-2026)

Hoy toda regla del motor mira a lo sumo un mes hacia atrás (`evaluar(liq, prev, cfg)`), pero la base
acumula la serie completa y crece sola con la sincronización diaria. Este proyecto agrega reglas que
comparan la liquidación actual contra toda su historia. Es el primero de cuatro ciclos aprobados
(A: históricas → C: endurecer el cruce → B: prorrateo vs escritura → D: OCR de imágenes).

## 1. Arquitectura

- **Módulo nuevo `engine/ct/historia.py`**, sin dependencias de base de datos, con:

  ```python
  def evaluar_historia(liq, serie, cfg, docs_por_periodo=None) -> list[Hallazgo]
  ```

  - `liq`: la liquidación actual (modelo del motor).
  - `serie`: lista de liquidaciones previas parseadas, ordenadas por período ascendente (puede ser
    vacía: sin historia, ninguna regla corre).
  - `docs_por_periodo`: opcional, `{periodo: [(gasto_n, hash, archivo)]}` con los comprobantes de
    cada período **incluido el actual** — lo arma la API desde la tabla `Documento`; el motor no
    sabe de dónde sale. (En la implementación quedó partido en dos parámetros, docs_actual y docs_previos, porque el motor no puede saber qué clave ISO es el período actual.)
  - Registro de reglas con el mismo patrón `@rule` de `rules.py` (decorador y lista propios del
    módulo, para no mezclar firmas distintas en `RULES`).
- **Las reglas solo emiten hallazgos que involucran a `liq`** (el mes actual contra su historia).
  Un duplicado julio↔agosto queda colgado de agosto y no se re-emite al ingerir septiembre.
- **Integración API** (`api/app/ingesta.py`):
  - `cargar_serie(db, storage, periodo)`: generaliza `cargar_anterior` — trae todas las
    liquidaciones `procesada`/`publicada` con período anterior al dado, re-parseando el archivo
    guardado (mismo patrón probado; los meses que fallen al parsear se saltean con warning).
  - `recalcular_historia(db, liq_row, storage)`: arma serie + `docs_por_periodo` (query a
    `Documento` join `Liquidacion` por período), llama `evaluar_historia` y hace
    `upsert_hallazgos(..., origen="historia")`. **Idempotente**: se llama al final de `procesar()`
    (si cuadra) y al final de `cruzar_comprobantes()` (los docs del mes recién llegan ahí). Como
    el upsert reemplaza el set completo del origen y las claves son estables, correrla dos veces
    no duplica nada. Si falla, no tira abajo la ingesta (try/except con log, como los embeddings).
  - Origen nuevo `"historia"`: el gating del visor de propietarios no cambia (solo habilita
    descargas el origen `"comprobantes"`); el triage y la publicación los tratan como a cualquier
    hallazgo. `limpiar_al_rechazar` despublica también los de origen `"historia"` de esa
    liquidación (si el mes no cuadra, sus hallazgos históricos tampoco pueden quedar visibles).

## 2. Las tres reglas

### `historia_duplicado` — la misma factura en dos meses distintos
- Por número: un gasto del mes actual cuyo `factura_nro` normalizado (sin espacios ni ceros a la
  izquierda en cada tramo) coincide con el de un gasto de un período previo **del mismo proveedor
  normalizado**. Si además los importes coinciden (±$1): **CRÍTICO** (posible doble pago); si solo
  coincide el número: **ALTO**. Números "de relleno" (menos de 3 dígitos significativos) se ignoran.
- Por archivo: un comprobante del mes actual cuyo `hash` aparece en un período previo
  (`docs_por_periodo`): **ALTO** — el mismo PDF respalda gastos de dos meses. Si no hay
  `docs_por_periodo`, este chequeo simplemente no corre.
- Evidencia: período y gasto del otro mes, números e importes. Refs: el/los `n` del mes actual.
- Claves: `dup-fact|{periodo_previo}|{nro_normalizado}` · `dup-hash|{periodo_previo}|{hash}`.

### `historia_salto` — gasto recurrente que salta contra su propia serie
- Gasto recurrente = mismo (proveedor normalizado, categoría) presente en ≥2 períodos previos.
  Se compara la suma mensual por esa clave (un proveedor puede tener varias líneas).
- Neutralización de la inflación: la variación del gasto se compara contra la **mediana de las
  variaciones de todos los recurrentes del mes**. Exceso = variación propia − mediana.
- Umbrales (Config): exceso > `salto_puntos_alto` (default 0,50) → **ALTO**; > `salto_puntos_medio`
  (default 0,25) → **MEDIO**. Solo si el importe actual supera `salto_importe_min` (default $50.000).
- Exclusiones: categorías de sueldos y cargas sociales (el SAC de junio/diciembre daría falsos
  positivos y ya están cubiertas por `sueldo_mercado`); se necesitan ≥3 recurrentes en el mes para
  que la mediana sea significativa.
- Evidencia: serie de importes por período y la mediana del mes. Refs: los `n` de las líneas del
  proveedor en el mes actual. Clave: `salto|{proveedor_normalizado}|{categoria_normalizada}`.

### `historia_concentracion` — proveedor que concentra el gasto
- Share = suma del proveedor / total de gastos del mes, excluyendo sueldos y cargas sociales del
  numerador y denominador. Con ≥2 períodos previos:
  - share actual > `concentracion_proveedor` (default 0,25) → **MEDIO**;
  - o share creciente estrictamente durante los últimos 3 períodos (incluido el actual) y actual
    > 0,15 → **MEDIO** (informativo: "viene creciendo");
  (con un paso mínimo de 0,5 pp por mes, para que el ruido de redondeo no cuente como crecimiento);
- Evidencia: shares por período. Refs: los `n` del proveedor en el mes. Clave:
  `concentracion|{proveedor_normalizado}`.

Redacción de los tres: hechos con documento y qué pedir, jamás conclusiones sobre personas.

## 3. Config (campos nuevos, con default razonable — nada que cargar para que funcione)

```
salto_puntos_medio: float = 0.25
salto_puntos_alto: float = 0.50
salto_importe_min: float = 50_000
concentracion_proveedor: float = 0.25
```

Editables desde la configuración del panel como los demás umbrales (`Config.desde_dict` ya ignora
claves desconocidas, así que bases existentes no rompen).

## 4. Pruebas (primero, con fixtures reales)

- Motor (`engine/tests/`): serie real julio+agosto 2026 (`redconar_202607.txt`, `redconar_202608.txt`)
  parseada con `parse_text`.
  - Con la serie real (un solo período previo), `salto` y `concentracion` no corren (exigen ≥2):
    el test lo verifica explícitamente. Para ejercitarlas con 2+ previos se agrega un tercer
    período derivado del parse real; la calibración de defaults se valida ahí y en el smoke
    real post-deploy (la base sí tiene junio, julio y agosto).
  - Casos sintéticos derivados del parse real (mutar importes/factura_nro de una copia) para:
    duplicado por número con y sin importe igual, duplicado por hash vía `docs_por_periodo`,
    salto por encima de ambos umbrales, exclusión de sueldos, serie vacía → sin hallazgos,
    `docs_por_periodo=None` → el chequeo de hash no corre.
- API (`api/tests/`): `recalcular_historia` corre en `procesar()` y en `cruzar_comprobantes()` sin
  duplicar hallazgos (idempotencia); origen `"historia"` se despublica en `limpiar_al_rechazar`;
  la falla de `recalcular_historia` no rompe la ingesta; claves estables entre reprocesos.
- Smoke real tras el deploy: reprocesar agosto y revisar qué hallazgos históricos aparecen antes
  de publicar nada (triage manual como siempre).

## Fuera de alcance

Endurecer el cruce (ciclo C), prorrateo vs escritura (B), OCR (D). Detección de gastos que
desaparecen/reaparecen, comparación entre consorcios, e índices de inflación externos: anotados,
no ahora.
