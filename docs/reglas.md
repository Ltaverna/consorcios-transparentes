# Catálogo de reglas de detección

Cada regla produce hallazgos con severidad (CRÍTICO, ALTO, MEDIO, BAJO), área, título, evidencia, monto involucrado y qué pedir.
Los umbrales están en `engine/ct/rules.py` (`Config`) y se ajustan por consorcio (en la API, JSONB por consorcio vía `Config.desde_dict`).
Cada hallazgo declara además una `clave` estable (más sus `refs`) para que el panel conserve el estado del auditor al reprocesar
una liquidación corregida. Redacción: hechos con documento, sin conclusiones acusatorias.

## Sobre la liquidación (`ct/rules.py`)

| Regla | Qué mira | Umbral por defecto | Severidad |
|---|---|---|---|
| cuadre | Verificaciones aritméticas de la liquidación (líneas vs. totales por rubro y clase, estado financiero, cuentas, deudores, prorrateo, unidades) | cualquier diferencia > $0,05 | CRÍTICO |
| efectivo | Caja en efectivo sobre disponibilidades; pagos en efectivo sobre el gasto del mes; pagos grandes en efectivo | 40 % · 10 % · $300.000 | CRÍTICO / ALTO |
| liquidez | Disponibilidades vs. facturas pendientes; caída de disponibilidades en el mes | cobertura < 100 % · caída > 75 % | CRÍTICO / ALTO |
| obras_unidades | Trabajos dentro de unidades privadas liquidados como ordinarios | > 20 % del gasto | CRÍTICO |
| fechas | Factura pagada con atraso; factura fechada después del pago; F.931 pagado fuera de término | 60 días · 1 día (ALTO si > 7 días o ≥ $1 M) · mes siguiente | MEDIO / ALTO |
| proveedor_nuevo | Factura con numeración muy baja por un monto relevante | N° ≤ 20 y ≥ $200.000 | ALTO |
| prorrateo | Se prorratea más que el gasto; misma obra en distinta clase que el mes anterior | > 3 % · cambio de clase con > $500.000 | ALTO |
| morosidad | Concentración de deuda y meses de expensa adeudados; dispersión de tasas de interés | 30 % o 3 meses · 5 puntos | ALTO / MEDIO |
| costos | Gastos bancarios sobre el gasto; suba de honorarios de administración vs. mes anterior | 1,2 % · 5 % | MEDIO |
| clasificacion | Retenciones de proveedores en "Sueldos"; rubros repetidos | — | MEDIO / BAJO |
| legales | Honorarios por cartas documento, mediaciones, patrocinio sin explicación del reclamo | — | ALTO |
| sueldo_mercado | Sueldos netos del mes vs. referencia de escala SUTERH cargada por el auditor (`sueldo_encargado_ref`; 0 = apagada) | tolerancia 10 % (ALTO si excede el doble; bajo escala siempre ALTO) | MEDIO / ALTO |
| honorarios_mercado | Total de la categoría de administración vs. referencia mensual cargada por el auditor (`honorarios_ref`; 0 = apagada) | tolerancia 10 % (ALTO si excede el doble) | MEDIO / ALTO |
| abonos_mercado | Abonos por rubro (ascensores, matafuegos, limpieza) vs. tope mensual cargado por el auditor (`abono_*_ref`; 0 = apagada) | total del rubro > tope | MEDIO |

## Sobre los comprobantes (`ct/comprobantes.py`)

Requieren los adjuntos del portal (factura y ticket de pago por gasto). Cada documento se lee con `pdftotext` y se clasifica en
factura, pago (transferencia), recibo, imagen sin texto u otro. Se extraen emisor y receptor con CUIT (validado por dígito verificador),
tipo y número de factura, fecha, importe, destinatario y CUIT de la transferencia, motivo y número de operación.

| Hallazgo | Cómo se detecta | Severidad |
|---|---|---|
| Pago a un tercero distinto del emisor | CUIT del destinatario de la transferencia ≠ CUIT emisor de la factura | CRÍTICO |
| Factura a nombre de un empleado o propietario | El texto de la factura contiene el nombre de un empleado (rubro Sueldos) o de un propietario (estado de cuentas); tolera variantes de ortografía | CRÍTICO |
| Factura emitida a un tercero | CUIT del receptor válido, distinto del consorcio y del emisor | CRÍTICO |
| Pago en efectivo alto, con o sin recibo manuscrito | Gasto en efectivo ≥ $300.000; se indica si el único respaldo es una imagen | CRÍTICO |
| Pago mayor que el gasto | Transferencia > 102 % del gasto y distinta de la suma de gastos del mismo proveedor y fecha | ALTO |
| Devolución recibida | Comprobante de crédito adjunto a un gasto | ALTO |
| Pago como "acreditamiento de haberes" de algo que no es sueldo | Motivo de la transferencia | ALTO |
| Transferencia anterior a la factura | Fecha del ticket < fecha de emisión | ALTO |
| Mismo archivo o misma operación en varios gastos | Hash del archivo / número de operación repetido; BAJO si la suma de los gastos coincide con el importe | ALTO / BAJO |
| Sueldo neto distinto de lo transferido | Único pago adjunto menor al neto (adelantos no informados) | MEDIO |
| Gasto sin adjuntos, factura citada no adjunta, sin comprobante de pago | Faltantes (se exceptúan los débitos automáticos) | MEDIO |
| Leyenda de ARCA sobre la CUIT del consorcio | Texto "inactiva en los padrones" en la factura | BAJO |

Pendiente: recibos manuscritos (imágenes) requieren revisión visual o OCR; conflicto de interés certificador = ejecutor por CUIT.

## Reglas por comparación con mercado

Cubiertas por `sueldo_mercado`, `honorarios_mercado` y `abonos_mercado`: las referencias (escala SUTERH,
honorarios tipo CAPHAI, topes de abonos) las carga el auditor en la configuración del consorcio; con
referencia en 0 la regla queda apagada. Pendiente: abonos de seguridad y comparación automática contra
edificios comparables.
