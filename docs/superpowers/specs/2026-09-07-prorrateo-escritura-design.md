# Ciclo B: prorrateo de la liquidación vs escritura (diseño aprobado 07-09-2026)

La transcripción del reglamento (art. 6°, verificada contra el escaneo, suma exacta 100,0000%)
define los porcentuales de dominio de las 95 UFs + la Unidad Complementaria I (8,7361%). La
liquidación aplica porcentuales por UF en la **clase A** (expensas comunes — el art. 6° dice que
los porcentuales de dominio rigen las expensas). Nadie compara hoy ambos: este ciclo lo hace.

Hechos verificados sobre los datos reales que fijan el diseño:
- La clase A de la liquidación es el porcentual de la escritura **truncado** (no redondeado) a 2
  decimales: 1,4488→1,44; 1,1786→1,17. Tolerancia por UF: |liq − esc| ≤ 0,01.
- La liquidación tiene 116 unidades: las 95 de la escritura + **21 cocheras** (tipo "Cochera",
  UF 201+, 0,42% c/u = 8,82%) que materializan la Complementaria I. Se comparan como grupo.
- Total clase A real: 99,91% (pérdida por truncado, esperable).

## 1. Motor: `engine/ct/escritura.py` (sin dependencias, patrón historia)

- `parsear_porcentuales(texto_md) -> tuple[dict[int, float], Optional[float]]`: extrae del
  markdown de la transcripción los pares `número N: X,XXXX%` (regex, coma decimal) y el
  porcentual de la "Unidad Complementaria I" (`8,7361%` — buscar el patrón cerca de la mención).
  Texto sin la tabla → `({}, None)`. Nunca lanza.
- `evaluar_escritura(liq, porcentuales, complementaria) -> list[Hallazgo]` (regla
  `prorrateo_escritura`; solo corre si `porcentuales` no está vacío):
  1. **Por UF (1-95)**: `|pcts["A"] − esc| > 0,01` → **ALTO**, área "Prorrateo", "la UF {uf}
     ({piso_depto}) paga {liq}% pero la escritura le asigna {esc}%", monto 0, recomendación
     pedir la corrección del prorrateo, refs `[uf]`, clave `escritura|{uf}`. UF sin clase A en
     la liquidación se saltea.
  2. **UFs de la escritura ausentes en la liquidación** → un agregado **MEDIO** listándolas
     (clave `escritura-faltantes`, refs = esas UFs).
  3. **Unidades de la liquidación que no figuran** (fuera de las cocheras) → agregado **MEDIO**
     (clave `escritura-sobrantes`).
  4. **Cocheras como grupo**: suma de clase A de las unidades tipo "Cochera" vs `complementaria`,
     tolerancia escalada `0,01 × cantidad` → si excede, **MEDIO** "las cocheras cargan {X}% pero
     la Complementaria I de la escritura es {Y}%" (clave `escritura-cocheras`, refs = las UFs
     cochera). Con los datos de hoy (8,82 vs 8,7361, dif 0,0839 ≤ 0,21) NO dispara.
  5. **Sanidad de la transcripción**: si `sum(porcentuales) + complementaria` difiere de 100,0000
     en más de 0,0001 → **MEDIO** "la transcripción de la escritura no suma 100%" (clave
     `escritura-suma`, sin refs) — protege contra futuras ediciones rotas del md.
- Redacción factual; jamás conclusiones sobre personas.

## 2. API (`ingesta.py`)

- En `procesar()`: leer la transcripción de storage (`consorcio/reglamento.md`) si existe;
  `parsear_porcentuales`; extender los hallazgos de `evaluar(...)` con
  `evaluar_escritura(liq, ...)` ANTES del único `upsert_hallazgos(origen="liquidacion")` (el
  upsert reemplaza el set del origen: una sola llamada). Sin transcripción o con parseo vacío →
  no corre, sin ruido. Falla → warning, la ingesta sigue (try/except).
- **`analitica.REGLAS_REFS_UF` suma `"prorrateo_escritura"`** (sus refs son UFs, no gastos — sin
  esto el clasificador de estados marcaría gastos equivocados).

## 3. Pruebas

- Motor (`engine/tests/test_escritura.py`): `parsear_porcentuales` con un snippet sintético en
  formato real (valores inventados que suman 100 con una complementaria; los reales son privados);
  texto sin tabla; regla con una `Liquidacion` sintética de pocas UFs: discrepancia >0,01 dispara
  ALTO, truncado (1,4488 vs 1,44) no dispara, faltantes/sobrantes, cocheras dentro y fuera de la
  tolerancia escalada, suma ≠ 100 dispara `escritura-suma`, porcentuales vacíos → [].
- API: `procesar` con la transcripción presente en storage genera los hallazgos (stub del
  parser o md mínimo); sin transcripción no rompe nada; falla del parser no rompe la ingesta.
  `analitica`: un hallazgo `prorrateo_escritura` abierto NO baja el estado de ningún gasto.
- Smoke real post-deploy: reprocesar los 8 meses; expectativa honesta con los datos de hoy:
  **cero hallazgos por UF** (el truncado entra en la tolerancia) y cocheras dentro del margen —
  la regla existe para el día en que la administración toque un porcentual.

## Fuera de alcance

Porcentuales por clase distinta de A (D es otra distribución — anotar el análisis de qué es D
como pendiente), comparación de superficies del art. 2°, UI dedicada (los hallazgos salen por el
flujo normal).
