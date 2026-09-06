# MCP de Consorcio Transparente — guía de conexión

Servidor MCP de **solo lectura** con los datos del Consorcio Rivadavia 2069 (CABA): liquidaciones de
expensas, gastos, comprobantes con su texto, hallazgos de auditoría, deudores y el reglamento de
copropiedad. Se conecta a Claude (claude.ai / Claude Code) y a ChatGPT, y permite preguntar en lenguaje
natural: la IA consulta los datos reales por vos.

## URL

```
https://mcp-consorcio.neuralcore.dev/mcp/<TOKEN>
```

El `<TOKEN>` es **personal**: el administrador crea uno por persona y lo entrega por un canal privado.
Se puede revocar individualmente sin afectar a los demás.
**Tratá la URL completa como una contraseña**: quien la tenga puede leer los datos del consorcio.
No la publiques ni la pegues en lugares compartidos. Si se filtra, avisá: se rota en un minuto.

## Descripción para el conector (copiar y pegar)

> Datos del Consorcio Rivadavia 2069 (CABA). Consultas de solo lectura sobre las liquidaciones de
> expensas: gastos con filtros (proveedor, categoría, concepto, período, importe), búsqueda por texto y
> semántica dentro de las facturas, totales agregados con variación mensual, hallazgos de la auditoría
> (con evidencia y estado), deudores, estado y cuadre de las liquidaciones, resumen mensual y el
> reglamento de copropiedad. Usalo para responder cuánto se pagó a un proveedor, qué gastos subieron,
> qué problemas detectó la auditoría, qué dice el reglamento, o cualquier análisis del dinero del
> consorcio. Montos en pesos argentinos; períodos en formato AAAA-MM.

## Cómo conectarlo

- **claude.ai**: Configuración → Conectores → *Agregar conector personalizado* → pegar la URL completa
  (con el token) y la descripción.
- **ChatGPT**: Configuración → Conectores (o *modo desarrollador*) → agregar servidor MCP con la URL.
  Si pregunta por autenticación: "sin autenticación" (la credencial ya viaja en la URL).
- **Claude Code**: `claude mcp add --transport http consorcio "https://mcp-consorcio.neuralcore.dev/mcp/<TOKEN>"`

Tras conectar, la primera pregunta puede pedirte aprobar el uso de las herramientas: aceptá y listo.

## Qué se puede preguntar (16 herramientas)

| Sobre… | Herramientas | Ejemplos |
|---|---|---|
| Gastos y totales | `consultar_gastos`, `agregados` | "¿Cuánto le pagamos a X en total?" · "¿Qué proveedor subió más este mes?" |
| Facturas por dentro | `leer_comprobante`, `buscar_en_comprobantes`, `buscar_semantico` | "¿Qué CUIT figura en la factura del gasto 12?" · "Buscá gastos relacionados con seguridad del edificio" |
| Auditoría | `listar_hallazgos`, `detalle_hallazgo` | "¿Qué problemas críticos encontró la auditoría en agosto?" |
| Liquidaciones | `estado_liquidaciones`, `detalle_liquidacion`, `resumen_mensual` | "¿Cerró bien agosto?" · "Dame el resumen del mes" |
| Deudores | `deudores` | "¿Quién debe y hace cuántos meses?" |
| Reglamento | `reglamento` | "¿Qué dice el reglamento sobre los poderes en asambleas?" |
| Transparencia | `indice_transparencia`, `estado_gastos` | "¿Qué tan auditable es el consorcio?" · "¿A qué gastos les falta respaldo en agosto?" |
| Compatibilidad ChatGPT | `search`, `fetch` | (las usa solo el modo investigación de ChatGPT) |

Todo es de **solo lectura**: nada de lo que se pregunte puede modificar, publicar ni borrar datos.

## Notas

- Los datos se actualizan solos: el sistema sincroniza con el portal de la administración todas las
  mañanas.
- La transcripción del reglamento es asistida por OCR del escaneo de 1982 (verificada contra las
  imágenes; las citas formales conviene cotejarlas con el PDF original, descargable desde el panel).
