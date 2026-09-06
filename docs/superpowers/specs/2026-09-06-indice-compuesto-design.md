# Índice de transparencia compuesto (diseño aprobado 06-09-2026)

Evolución del índice: de "% del dinero verificado" a un score compuesto 0-100, reproducible y
abrible componente por componente. Pesos definidos por el dueño. Ninguna cifra la genera una IA:
constantes nombradas + fórmula impresa en el panel y en el MCP.

## 1. Fórmula (en `api/app/analitica.py`, constantes módulo-level documentadas)

```python
PESOS = {"documentacion": 0.30, "conciliacion": 0.30, "trazabilidad": 0.20,
         "consistencia": 0.10, "explicaciones": 0.10}
PENALIZACION_POR_CRITICO = 2      # puntos por cada CRÍTICO abierto
PENALIZACION_TOPE = 25
```

- **documentacion** = `dinero_con_factura / dinero_total` (0 si total 0).
- **conciliacion** = `dinero_pago_respaldado / dinero_total`.
- **trazabilidad** = `dinero_verificado / dinero_total` (el índice viejo, ahora componente).
- **consistencia** = períodos que cuadran / períodos con liquidación en el rango:
  numerador = liquidaciones `procesada`/`publicada`; denominador = las mismas **más las
  `no_cuadra`** (los `error`/`procesando` no cuentan: son operativos, no del documento). Para
  esto `metricas` consulta también las `no_cuadra` del rango — solo el conteo, jamás sus datos.
- **explicaciones** = `hallazgos_resueltos / (abiertos_totales + resueltos)`; **1.0 si no hay
  ningún hallazgo** (nada que explicar = todo explicado).
- `penalizacion = min(PENALIZACION_TOPE, PENALIZACION_POR_CRITICO * criticos_abiertos)`.
- `indice = max(0, min(100, round(sum(peso_i * valor_i * 100) - penalizacion)))`.

Aplica igual a los totales del rango y a cada período (`periodos[]`): cada mes con su propia
penalización; la consistencia de un mes que está en `periodos[]` es 1.0 por construcción (los
`no_cuadra` solo afectan el componente global del rango).

**Vista del propietario** (`solo_publicado`): misma fórmula sobre lo publicado. Su consistencia
se calcula solo sobre períodos publicados (siempre 1.0 hoy): la vista del propietario afirma
únicamente sobre lo publicado — un `no_cuadra` sin publicar no se filtra ni como conteo.

## 2. Respuesta de `/analitica/indice` (compatible: se agrega, no se saca)

`totales` y cada elemento de `periodos[]` suman:

```json
"componentes": {
  "documentacion":  {"peso": 0.30, "valor": 0.64, "puntos": 19.2},
  "conciliacion":   {"peso": 0.30, "valor": 0.54, "puntos": 16.2},
  "trazabilidad":   {"peso": 0.20, "valor": 0.10, "puntos": 2.0},
  "consistencia":   {"peso": 0.10, "valor": 0.80, "puntos": 8.0,
                     "periodos_cuadran": 8, "periodos_totales": 10},
  "explicaciones":  {"peso": 0.10, "valor": 0.0, "puntos": 0.0}
},
"penalizacion": {"criticos_abiertos": 36, "por_critico": 2, "tope": 25, "puntos": 25}
```

(`puntos` = `peso*valor*100` redondeado a 1 decimal.) `indice` pasa a ser el compuesto — mismo
key, nuevo significado; `pct_trazable` y todo lo existente se conservan. El router no cambia.

## 3. MCP

`indice_transparencia` responde el número + la tabla de componentes (peso, valor, puntos y el
respaldo: importes/conteos) + la penalización con su cuenta ("36 críticos × 2 = 72 → tope 25").
"¿Cuál es el índice de transparencia?" devuelve el porqué completo y reproducible.

## 4. Panel y mi-unidad

- `panel/transparencia`, CardIndice: el número grande + tabla del desglose (componente, peso,
  valor, puntos) + línea de penalización + la fórmula. Reemplaza la leyenda actual.
- `mi-unidad`: mismo desglose compacto (sin datos internos: lo que venga del endpoint filtrado).

## 5. Pruebas

- API: fórmula a mano con un caso construido (componentes conocidos → índice esperado exacto);
  tope de penalización; explicaciones=1.0 sin hallazgos; consistencia con una `no_cuadra` en el
  rango (denominador crece, numerador no, y sus gastos NO aparecen en ninguna otra métrica);
  propietario: consistencia solo sobre publicadas y sin conteos de no_cuadra. Actualizar los
  tests existentes del índice viejo (documentando el cambio de fórmula).
- MCP: el texto incluye componentes y la cuenta de la penalización.
- Web: fixtures con `componentes`/`penalizacion`; el desglose se renderiza en ambas vistas.

## Fuera de alcance

Pesos configurables desde el panel (anotado; hoy constantes con nombre), componente
"destino del trabajo por UF" (sin datos aún — sigue pendiente del conocimiento del edificio),
histórico del índice como serie temporal persistida (se recalcula siempre en vivo).
