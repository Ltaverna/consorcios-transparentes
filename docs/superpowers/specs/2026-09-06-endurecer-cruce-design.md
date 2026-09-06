# Endurecer el cruce de comprobantes (ciclo C — diseño aprobado 06-09-2026)

Segundo de los cuatro ciclos de mejora de hallazgos (A históricas ✓ → **C** → B prorrateo → D OCR).
Calibrado con dos casos reales de agosto 2026 que el ciclo A destapó: las cuotas de Roth
(FC 4182/4183/4191 de mayo, $7.950.000 en tercios de $2.650.000, y la cuota de agosto declarada
el 21-08 sin comprobante propio) y el saldo de Saczewiczyk (FC 7, $2.000.000 + $2.552.000 =
$4.552.000 exactos, saldo transferido a un tercero).

## 1. Pago declarado sin comprobante propio (`comprobantes.py`, dentro de `cruzar`)

- Nueva función pura `chequear_pagos_declarados(g, pagos_docs) -> list[Hallazgo]`, llamada desde
  `cruzar` en el bloque por-gasto (recibe los docs tipo "pago" ya filtrados, sin créditos).
- Para cada pago de `g.pagos` con forma transferencia (no efectivo, no débito automático) y con
  fecha: existe comprobante adjunto con `|doc.importe − pago.importe| ≤ $1` **y** fecha dentro de
  ±3 días. Si no existe **y hay al menos un comprobante de pago adjunto al gasto** (si no hay
  ninguno, ya lo cubre la regla existente "sin comprobante de pago") → **ALTO**, área "Control de
  pagos": "la transferencia declarada el {fecha} por {importe} no tiene comprobante adjunto; los
  adjuntos son de otras fechas ({fechas de los docs})". Clave `pago-sin-comp|{fecha ISO}`,
  refs `[n]`. Tolerancias como constantes del módulo (patrón existente), no en Config.
- Caso real que debe detectar: Roth agosto (pago declarado 21-08, adjuntos del 29-05 y 13-07).
  Caso que NO debe disparar: Roth julio (pago declarado 13-07, transferencia del 13-07 adjunta).

## 2. Cuotas: refinamiento de `historia_duplicado` (`historia.py`)

- En la rama por número de factura: si `g.factura_importe` está presente y
  `g.importe + gp.importe ≤ g.factura_importe + $1` → los pagos caben en el total facturado:
  **MEDIO** en vez de CRÍTICO/ALTO, título "posible pago en cuotas de la factura {nro} de {prov}",
  evidencia con ambos pagos y el total facturado, recomendación "Pedir el comprobante de cada
  cuota y el detalle del plan de pagos". Aplica a ambas sub-ramas (mismo importe y distinto).
- Si la suma **supera** el total facturado (o no hay `factura_importe`): severidades actuales
  (CRÍTICO mismo importe / ALTO distinto). La clave `dup-fact|…` NO cambia: al reprocesar, el
  hallazgo existente se actualiza en el lugar y conserva estado/respuesta del triage.
- Casos reales: Roth (2.650.000 + 2.650.000 ≤ 7.950.000 → MEDIO cuotas) y Saczewiczyk
  (2.000.000 + 2.552.000 = 4.552.000 → MEDIO cuotas). Un verdadero doble pago (suma > facturado)
  sigue CRÍTICO.

## 3. Matching robusto en `_match_gasto` (`comprobantes.py`)

- Firma nueva: `_match_gasto(item, liq) -> tuple[Optional[Gasto], bool]` (gasto, certero).
- Orden dentro de los candidatos por importe (±0,01, como hoy): único → certero; si varios:
  desempate por número de factura normalizado (único) → certero; desempate por fecha (único) →
  certero; si sigue ambiguo → `(cands[0], False)`.
- En `cruzar`: los docs de un item incierto reciben la nota "Atribución incierta: varios gastos
  del mes comparten este importe." y se emite **un** hallazgo agregado **BAJO** por corrida
  ("{N} comprobante(s) atribuidos con incertidumbre"), área "Calidad de datos", refs = los `n`
  involucrados, clave `atribucion-incierta` (agregado: las refs no entran en la clave, como
  morosidad).
- El comportamiento actual (elegir `cands[0]`) se mantiene para no perder cruces; solo se hace
  visible la incertidumbre.

## 4. Importe de la factura adjunta vs el gasto (`comprobantes.py`, dentro de `cruzar`)

- Nueva función pura `chequear_importe_factura(g, facts, total_proveedor_mes) -> list[Hallazgo]`.
- Evaluación a nivel gasto (no por factura, para no multiplicar ruido): con
  `S = suma de importes de las facturas adjuntas con importe legible`, el gasto está OK si
  **alguno** de {cada `f.importe`, `S`} coincide (±2% o ±$1, lo que sea mayor) con **alguno** de
  {`g.importe`, `g.factura_importe`, `total_proveedor_mes`}. Si nada cierra → **MEDIO**, área
  "Respaldo documental": "las facturas adjuntas suman {S} pero el gasto es {importe}
  (facturado: {factura_importe})", clave `imp-fact`, refs `[n]`.
- Caso real que debe quedar OK: Roth (facturas 2,9M + 4,9M + 0,15M = 7,95M = `factura_importe`,
  aunque ninguna coincide con el gasto de 2,65M). Facturas sin importe legible no cuentan.

## 5. Certificador = ejecutor (`rules.py`, regla nueva sobre la liquidación sola)

- `r_certificador`: proveedores (normalizados) que en el mismo mes tienen un gasto cuyo
  concepto+proveedor matchea `certificaci[oó]n|certificado` y otro gasto distinto que matchea
  obra/reparación (`reparaci[oó]n|cambio de|instalaci[oó]n|coloca|obra de`) → **MEDIO**, área
  "Obras / contratación", título "{prov} certifica y también ejecuta trabajos en el edificio",
  evidencia con ambos conceptos, recomendación pedir certificación independiente para los
  trabajos que ejecuta. Clave `cert-ejecutor|{prov_norm}`, refs = los `n` de ambos gastos.
- Caso real: Roth en julio y agosto (certificación de equipos térmicos + cambio de serpentina /
  reparación de cupla). Redacción factual: "conflicto de interés potencial", jamás acusación.
- Cierra el pendiente anotado en `docs/reglas.md` ("conflicto de interés certificador = ejecutor").

## Fuera de alcance

Correlatividad de numeración por emisor (ruido con 2 meses de datos; retomar con 6+), OCR de
imágenes (ciclo D), CAE/ARCA online. `factura_fecha` vs período ya lo cubre la regla de atrasos.

## Pruebas (fixtures reales primero; sin depender de la carpeta privada)

- `engine/tests/test_cruce_reglas.py` (nuevo): las funciones puras (`chequear_pagos_declarados`,
  `chequear_importe_factura`) y `_match_gasto` se prueban con `Gasto`/`Pago`/`Documento`
  construidos a mano con los números reales de Roth y Saczewiczyk (constantes con comentario del
  origen). Sin PDFs: no se saltean nunca.
  - pagos_declarados: caso Roth-agosto dispara; caso Roth-julio no; efectivo/débito no evalúan;
    gasto sin ningún pago adjunto no dispara (lo cubre la regla vieja).
  - importe_factura: caso Roth OK por la suma; un gasto con factura adjunta que no cierra por
    ningún lado dispara; factura sin importe legible no cuenta.
  - match: único por importe certero; empate resuelto por nro certero; empate irresoluble
    devuelve `(cands[0], False)`.
- `engine/tests/test_historia.py`: cuotas → MEDIO con los números de Roth (mismo importe) y
  Saczewiczyk (distinto importe); suma > facturado → sigue CRÍTICO; sin `factura_importe` →
  comportamiento actual.
- `engine/tests/test_rules_*`: `r_certificador` contra el fixture real de julio (Roth certifica
  y repara: refs 26 y 27) y agosto; un mes sin el patrón no dispara.
- API: sin cambios de código (el cruce y la ingesta ya llaman a todo); correr la suite completa
  para confirmar que nada se rompe. Smoke post-deploy: reprocesar julio y agosto y verificar el
  re-etiquetado de los 9 hallazgos históricos (los dup pasan a MEDIO cuotas) y los nuevos
  (pago 21-08 sin comprobante, certificador=ejecutor).
