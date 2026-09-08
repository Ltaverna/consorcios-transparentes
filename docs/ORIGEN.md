# Origen y propósito

## El problema

Un consorcio de propiedad horizontal recibe todos los meses una liquidación de expensas de veinte o
treinta páginas. El propietario la recibe, ve el total a pagar, y paga. Prácticamente nadie verifica
—porque verificar a mano lleva un día entero por mes— si las sumas cierran, si cada gasto tiene una
factura detrás, si esa factura está a nombre del consorcio, si el pago fue a quien emitió la factura,
si un mismo trabajo se cobró dos veces o si el prorrateo respeta la escritura.

La administración cobra por administrar y, salvo que alguien mire, nadie mira. El propietario que
quiere mirar se encuentra con un portal, un PDF y ninguna herramienta.

## El caso que lo originó

En agosto de 2026, Lucas Taverna auditó a mano la liquidación del **Consorcio Rivadavia 2069** (CABA,
administración Almazare): bajó la liquidación y todos los comprobantes del portal, los cruzó uno por
uno y encontró 20 hallazgos, 10 de ellos críticos. Ese trabajo está en
`tools/auditoria-manual/` — se conserva como referencia histórica y como test de aceptación del motor:
el motor reproduce los mismos hallazgos automáticamente.

Los resultados se presentaron en la asamblea del 3 de septiembre de 2026, con un Excel de 16 hojas y
una presentación HTML, y con una app de votación por doble mayoría hecha para esa asamblea
(`apps/asamblea/`, hoy en `asamblea.neuralcore.dev`).

La conclusión operativa fue: **esto no se puede hacer a mano todos los meses, y no debería depender de
que un propietario sepa programar.**

## La pregunta que el sistema responde

> ¿Tengo evidencia suficiente para afirmar que la administración de mi edificio es transparente?

No "¿me están robando?" — esa pregunta no la puede contestar un software y el proyecto no la formula.
La pregunta es sobre la **evidencia disponible**: cuánto del dinero del mes tiene factura, cuánto tiene
un pago verificable contra esa factura, cuánto cierra al centavo, y qué quedó sin explicar. El índice
de transparencia es exactamente eso: un número reproducible que mide la calidad de la documentación,
no la honestidad de nadie.

## Principios

Estos principios están en `CLAUDE.md` y gobiernan cada decisión de diseño:

1. **Nada se publica si los totales no cuadran al centavo.** Un hallazgo sobre una liquidación que no
   cierra no es un hallazgo: es ruido. El cuadre es la puerta de entrada, no un chequeo posterior.

2. **Hechos con documento, nunca acusaciones sobre personas.** Cada hallazgo dice qué se observó, dónde
   está la evidencia (línea, factura, comprobante) y **qué pedir**. Nunca concluye sobre intenciones.
   La redacción es deliberadamente factual: "la factura está a nombre de X, no del consorcio; pedir la
   factura a nombre del consorcio", no "la administración facturó a nombre de un tercero".

3. **Reproducibilidad.** Cualquiera con el PDF puede correr `python -m ct analizar` y obtener el mismo
   resultado, sin base de datos, sin cuenta y sin red. El índice se calcula con una fórmula publicada.
   Ninguna cifra la genera un modelo de lenguaje.

4. **Antes de agregar una regla, la prueba con un fixture real.** Las reglas se calibran contra
   documentos reales, no contra intuiciones. Varias reglas de este proyecto nacieron ajustadas después
   de que una revisión encontrara un 50% de falsos positivos sobre los datos de producción.

5. **Independencia.** El producto no administra consorcios ni cobra un porcentaje de las expensas.
   Trabaja para el propietario, no para el administrador.

6. **Los datos del consorcio no entran al repositorio.** Liquidaciones, comprobantes, reglamento y
   planillas viven fuera de git; las credenciales no se guardan en ningún archivo del repo.

## Por qué existe cada pieza

| Pieza | Por qué |
|---|---|
| **Motor sin dependencias** | Para que un hallazgo sea verificable por un tercero con solo el PDF. Si hiciera falta levantar Postgres para reproducirlo, no serviría como prueba en una asamblea. |
| **Cruce de comprobantes** | El 90% de lo que se encuentra no está en la liquidación: está en la diferencia entre lo que la liquidación dice y lo que los adjuntos muestran. Ningún producto del mercado relevado hace esto. |
| **Reglas históricas** | Un mes aislado no muestra el duplicado entre meses, el salto de precio ni la concentración creciente en un proveedor. Hacen falta series. |
| **Prorrateo contra la escritura** | El reglamento de copropiedad define los porcentuales de dominio. Nadie los compara nunca contra lo que la liquidación efectivamente aplica. |
| **QR de ARCA** | La factura electrónica trae los datos autoritativos firmados por el fisco. Leerlos evita depender del parseo del texto y detecta PDFs que no coinciden con su propio QR. |
| **Índice de transparencia** | Sin un número, cada mes es una lista de problemas inconmensurable con la del mes anterior. Con un número compuesto y una fórmula pública, hay una línea de base y se puede exigir mejora. |
| **Panel + vista del propietario** | El hallazgo no sirve si vive en la terminal del auditor. Tiene que llegar al propietario con su comprobante al lado. |
| **MCP** | Para preguntar en lenguaje natural sobre los datos reales, sin que el modelo invente cifras: las herramientas devuelven lo que dice la base. |
| **App de asamblea** | Del hallazgo a la decisión: la auditoría termina en una votación por doble mayoría, que es donde el consorcio efectivamente decide. |

## Estado del producto

Nombre "Consorcio Transparente" provisorio. Repo personal (`Ltaverna/consorcios-transparentes`).
Caso piloto en producción: Rivadavia 2069, con la serie 2026-01 a 2026-08 cargada y auditada.

El plan de producto (`docs/plan-producto.html`) plantea tres puertas de entrada: consejo de propietarios
en autoservicio, servicio de auditoría, y administrador transparente que quiera mostrar su gestión. La
competencia relevada (Octopus, Redconar, ConsorcioAbierto, Dominium, AsambleasVirtuales y otros) apunta
a la administración: ninguno cruza comprobantes ni trabaja para el propietario.

Etapa actual: un solo consorcio. El multi-consorcio (filas por consorcio, ya previsto en el modelo)
llega después.

## Lecturas siguientes

- [ARQUITECTURA.md](ARQUITECTURA.md) — cómo está construido.
- [PIPELINE.md](PIPELINE.md) — del portal al índice, paso a paso.
- [ANALISIS-RIVADAVIA-2069.md](ANALISIS-RIVADAVIA-2069.md) — qué encontró el sistema en el caso real.
- [ESTADO.md](ESTADO.md) — bitácora de decisiones y próximos pasos.
