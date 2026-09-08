# Análisis del caso real: Consorcio Rivadavia 2069

Qué encontró el sistema sobre datos reales, qué aprendió de sus propios errores y qué queda abierto.
Foto tomada el **7 de septiembre de 2026**, después del triage de los hallazgos críticos. Los conteos
exactos del día deben leerse del panel (`/panel/transparencia`) o del MCP (`indice_transparencia`):
acá quedan registrados los del momento del triage, para tener línea de base.

Consorcio Rivadavia 2069 (CABA), administración Almazare, 95 unidades funcionales + 21 cocheras.
Sistema de liquidación: Redconar / "Mis Expensas".

## 1. La serie cargada

| | |
|---|---|
| Períodos en la base | **2026-01 a 2026-08** (8 meses) |
| Cuadre | los 8 cuadran al centavo (consistencia 8/8) |
| Documentos cruzados | ~575 adjuntos (facturas, tickets de pago, recibos, imágenes) |
| Hallazgos abiertos al momento del triage | ~361 |
| Críticos | 32, todos movidos a `preguntado` |

### Por qué el período arranca en enero de 2026

El backfill del 6/09 corrió con `--desde 2025-11` y trajo diez meses. **2025-11 y 2025-12 no cuadraron**
por diferencias reales del documento —noviembre: $149.000 de diferencia entre gastos y egresos;
diciembre: $300 corridos entre las columnas A y B— y quedaron en `no_cuadra`.

Como esos dos meses arrastraban el componente de consistencia sin aportar información auditable (el
sistema no puede afirmar nada sobre un mes que no cierra), el dueño decidió eliminarlos de la base: el
período auditable arranca en 2026-01. Los PDFs siguen en la carpeta privada y el reclamo a la
administración por esos dos meses se hace por fuera del sistema. Futuros backfills: `--desde 2026-01`.

## 2. Índice de transparencia

**24 / 100** al momento del triage (era 15/100 justo después del backfill, antes de los ciclos de
endurecimiento del cruce y del QR).

El desglose explica el número mejor que el número:

| Componente | Peso | Lectura |
|---|---|---|
| Documentación | 30% | Parte del dinero tiene factura adjunta; buena parte no. |
| Conciliación de pagos | 30% | El efectivo nunca cuenta como respaldado, y hay mucho efectivo. |
| Trazabilidad / destino | 20% | Hundida por los hallazgos abiertos: un gasto con crítico abierto es `inconsistencia`, no `verificado`. |
| Consistencia | 10% | **Completo**: 8 de 8 períodos cuadran. |
| Explicaciones | 10% | **En cero**: no hay ningún hallazgo resuelto todavía. |
| Penalización | −2 por crítico abierto (tope 25) | Con 32 críticos abiertos, la penalización está en el tope. |

Punto importante para leer la evolución: **el índice no sube por triagear**. Mover un hallazgo a
`preguntado` lo deja abierto — sigue contando y sigue penalizando. El índice sube cuando los hallazgos
se **cierran** (con la explicación de la administración) o se **descartan** (porque eran falsos
positivos). El componente "explicaciones" está en 0% justamente porque todavía no hay ninguno resuelto.

## 3. Los 32 hallazgos críticos

Agrupados como se preguntaron a la administración, en cinco bloques:

| Bloque | Hallazgos | Qué se observó |
|---|---|---|
| **Pagos y facturas por la unidad 13-B** | 7 | Pagos y facturas de terceros canalizados a través de la propietaria de una unidad, ~$9,9 M. |
| **Efectivo a proveedores** | 6 | ~$6,3 M pagados en efectivo, algunos con recibo manuscrito como único respaldo. |
| **Pagos a terceros** | 8 | Transferencias a CUITs que no son el emisor de la factura correspondiente. |
| **Obras en unidades privadas** | 5 | $38,7 M de trabajos dentro de unidades privadas liquidados como expensas ordinarias (entre 20% y 39,5% del gasto mensual según el mes). |
| **Estructura de caja** | 6 | Efectivo por encima del 60% de las disponibilidades (200,9% en marzo) y brechas de liquidez frente a facturas pendientes. |

Los 32 quedaron en estado `preguntado`, con la nota del bloque registrada en el historial de cada uno.
Redacción factual en todos los casos: qué se observó, con qué evidencia y qué documento pedir.

## 4. Dos investigaciones que cambiaron el motor

### Roth y Saczewiczyk: no eran pagos duplicados, eran cuotas

La regla `historia_duplicado` marcó como posible doble pago dos casos donde la misma factura aparecía
en dos meses consecutivos. Revisando la base y los PDFs originales quedó claro que no eran duplicados:

- **Roth**: dos pagos de $2.650.000 contra un total facturado de $7.950.000 (tres facturas).
- **Saczewiczyk**: $2.000.000 + $2.552.000 = $4.552.000 exactos.

En ambos, la suma de los pagos **cabía dentro del total facturado**: eran cuotas. La regla se refinó
para distinguirlos: si `factura_importe` está presente y la suma de ambos pagos no lo excede (±$1), el
hallazgo baja a MEDIO "posible pago en cuotas" en lugar de CRÍTICO. La clave del hallazgo no cambia,
así que el triage sobrevive.

Pero la investigación dejó algo más valioso: al reconstruir las cuotas apareció que una de ellas
(Roth, 21-08) **no tenía comprobante propio de esa fecha** — los adjuntos eran del 29-05 y del 13-07.
De ahí nació la regla `chequear_pagos_declarados`, que compara cada pago declarado contra las fechas de
los comprobantes adjuntos (±3 días) y verifica que el importe lo cubra. Encontró 6 casos genuinos.

### Numeración baja: la pregunta que quedó abierta

Una factura de Saczewiczyk con numeración muy baja para un proveedor con inicio de actividades en 2008,
seguida un mes después por la número siguiente, disparó la regla `proveedor_nuevo`. Los tres hallazgos
de numeración quedaron en `preguntado` con la pregunta concreta para la administración. Quedó anotado
en el backlog: extraer el "inicio de actividades" del texto de la factura para enriquecer la regla, y
una regla de correlatividad por emisor (que el QR de ARCA ahora habilita).

## 5. Falsos positivos encontrados y corregidos

El dueño reportó dos hallazgos que eran incorrectos. Los dos se arreglaron **de raíz en el parser**, no
con excepciones:

| Falso positivo | Causa real | Arreglo |
|---|---|---|
| "El pago de EDESUR ($976.203) fue a EDESUR (CUIT 00800521530), que no es el emisor de la factura" | `00800521530` es una **referencia de pago de 12 dígitos**, no un CUIT. El parser la tomaba como CUIT. | Validación de dígito verificador (`_cuit_o_none`) y lookarounds `(?<!\d)(\d{11})(?!\d)` para no morder números más largos. |
| "La factura de TECNO SIM está a nombre de Escuredo Luisa (propietaria de UC-13), no del consorcio" | El CUIT del emisor aparecía dos veces (CUIT + IIBB), lo que hacía que receptor = emisor; y el **email de contacto** de la propietaria matcheaba como titular. | Se excluye el emisor del resto, se eliminan los emails antes de buscar nombres vinculados, y se saltea cuando el receptor contiene "CONSORCIO". |

Además, el ciclo del QR encontró y corrigió un falso positivo propio antes de llegar a producción: las
liquidaciones citan números de factura sin punto de venta ("8675" contra el "0005-00008675" del QR), lo
que producía 50% de falsos positivos en `qr-numeracion` sobre los datos reales de agosto. Se corrigió
comparando las citas sin prefijo solo contra el número de comprobante.

Y la regla `imp-fact` (importes de factura que no cierran contra el gasto) tenía 50% de falsos
positivos por facturas cuyo concepto declara el importe bruto y las retenciones por separado (caso CSI);
se corrigió sumando los montos declarados en el concepto como objetivos válidos.

**Patrón**: cada falso positivo reportado sobre datos reales terminó en un arreglo del parser y en un
test de regresión. Es el mecanismo que mantiene el catálogo de reglas creíble.

## 6. El prorrateo: el primer verde

El ciclo B comparó la clase A de cada unidad contra los porcentuales de dominio del art. 6° del
reglamento de copropiedad (transcripción verificada contra el escaneo, suma exacta 100,0000%).

Resultado sobre los diez meses disponibles: **cero hallazgos**. La administración prorratea exactamente
la escritura, truncada a dos decimales (1,4488 → 1,44), lo que produce un total de clase A de 99,91% —
pérdida esperable por el truncado. Las 21 cocheras cargan 8,82% contra el 8,7361% de la Unidad
Complementaria I: diferencia de 0,0839, dentro de la tolerancia escalada.

Es el primer control que da verde de punta a punta. La regla queda igual: existe para el día en que un
porcentual se toque.

## 7. QR de ARCA: alcance real

De los ~575 documentos, **26 tienen QR legible** a 200 dpi. Es menos de lo esperado: muchos adjuntos son
escaneos de baja calidad o fotos. El re-cruce con QR produjo un hallazgo nuevo (Maxicopy, abril).

Quedan ~5 documentos completamente ciegos (recibos manuscritos fotografiados) que ninguna extracción de
texto puede leer. Mejoras anotadas: subir DPI y probar más páginas por documento; evaluar si los 5
ciegos justifican un paso de visión.

## 8. Qué queda abierto

Del backlog registrado en [ESTADO.md](ESTADO.md):

- **Cerrar el ciclo con la administración**: los 32 críticos están preguntados; el índice sube cuando
  las respuestas lleguen y los hallazgos se cierren o descarten.
- Qué distribución es la **clase D** del prorrateo (la B parece ser la de cocheras).
- Regla de **correlatividad de numeración** por emisor, habilitada por el QR.
- Extraer **inicio de actividades** del texto de las facturas.
- **Constatación online contra ARCA** (WSCDC): requiere clave fiscal y certificados.
- Subir DPI / más páginas en la lectura de QR.
- Los dos meses de 2025 que no cuadran: reclamo por fuera del sistema.

## 9. Cómo reproducir este análisis

```bash
cd engine
python -m ct analizar "$CT_PRIVADO/liquidaciones/2026-08-....pdf" \
  --anterior "$CT_PRIVADO/liquidaciones/2026-07-....pdf" \
  --comprobantes "$CT_PRIVADO/Comprobantes Rivadavia 2069" \
  --manifiesto "$CT_PRIVADO/Comprobantes Rivadavia 2069/manifest.json" \
  --mes 2026-08 --excel informe.xlsx --html informe.html
```

Sin la carpeta privada, el análisis del cuadre se puede reproducir con cualquier liquidación del mismo
sistema. Los hallazgos de este documento salen del motor, no de una interpretación: cada uno cita su
línea, su factura o su comprobante.
