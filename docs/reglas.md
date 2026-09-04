# Catálogo de reglas de detección

Cada regla produce hallazgos con severidad (CRÍTICO, ALTO, MEDIO, BAJO), área, título, evidencia, monto involucrado y qué pedir.
Los umbrales están en `engine/ct/rules.py` (`Config`) y se ajustan por consorcio. Redacción: hechos con documento, sin conclusiones acusatorias.

| Regla | Qué mira | Umbral por defecto | Severidad |
|---|---|---|---|
| cuadre | Verificaciones aritméticas de la liquidación (líneas vs. totales por rubro y clase, estado financiero, cuentas, deudores, prorrateo, unidades) | cualquier diferencia > $0,05 | CRÍTICO |
| efectivo | Caja en efectivo sobre disponibilidades; pagos en efectivo sobre el gasto del mes; pagos grandes en efectivo | 40 % · 10 % · $300.000 | CRÍTICO / ALTO |
| liquidez | Disponibilidades vs. facturas pendientes; caída de disponibilidades en el mes | cobertura < 100 % · caída > 75 % | CRÍTICO / ALTO |
| obras_unidades | Trabajos dentro de unidades privadas liquidados como ordinarios | > 20 % del gasto | CRÍTICO |
| fechas | Factura pagada con atraso; factura fechada después del pago; F.931 pagado fuera de término | 60 días · 1 día · mes siguiente | MEDIO / ALTO |
| proveedor_nuevo | Factura con numeración muy baja por un monto relevante | N° ≤ 20 y ≥ $200.000 | ALTO |
| prorrateo | Se prorratea más que el gasto; misma obra en distinta clase que el mes anterior | > 3 % · cambio de clase con > $500.000 | ALTO |
| morosidad | Concentración de deuda y meses de expensa adeudados; dispersión de tasas de interés | 30 % o 3 meses · 5 puntos | ALTO / MEDIO |
| costos | Gastos bancarios sobre el gasto; suba de honorarios de administración vs. mes anterior | 1,2 % · 5 % | MEDIO |
| clasificacion | Retenciones de proveedores en "Sueldos"; rubros repetidos | — | MEDIO / BAJO |
| legales | Honorarios por cartas documento, mediaciones, patrocinio sin explicación del reclamo | — | ALTO |

## Reglas que requieren comprobantes (semana 2)

Necesitan los adjuntos del portal (factura y ticket de pago) y se implementan en el módulo de cruce:

- Pago a un tercero distinto del emisor de la factura (CUIT / cuenta destino).
- Factura emitida a nombre de un propietario o de un tercero, no del consorcio.
- Comprobante de pago reutilizado en más de un gasto.
- Gasto sin ningún adjunto; factura sin comprobante de pago; pago sin factura.
- Recibo manuscrito genérico por montos altos.
- Servicio contratado a nombre de un empleado o propietario (factura de servicios a otro titular).
- Mismo proveedor certifica y ejecuta (conflicto de interés), por CUIT.
- Transferencias por importes distintos a la factura (error de pago, devoluciones).

## Reglas por comparación con mercado (después)

Escala SUTERH para sueldos y cargas; honorarios de administración vs. referencia CAPHAI; abonos (ascensores, limpieza, seguridad) vs. edificios comparables.
