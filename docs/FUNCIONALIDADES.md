# Funcionalidades

Qué hace el sistema, superficie por superficie y rol por rol. Para cómo se usa cada cosa ver
[USO.md](USO.md); para el detalle de las reglas, [reglas.md](reglas.md).

## 1. Roles

| Rol | Cómo entra | Qué puede |
|---|---|---|
| **auditor** | email + clave, o Google | Todo: subir liquidaciones y comprobantes, triage, publicar, editar umbrales y datos del consorcio, generar códigos de unidad. |
| **consejo** | email + clave, o Google | Lee todo el panel. No escribe nada. |
| **moderador** | email + clave, o Google | Lee todo el panel. No escribe nada. (Rol pensado para la app de asamblea.) |
| **propietario** | UF + código de 8 caracteres | Solo `/mi-unidad` y `/reglamento`: su estado de cuenta, los hallazgos **publicados**, los comprobantes citados en ellos y el índice sobre períodos publicados. |

El alta de usuarios del equipo es siempre previa y manual (no hay auto-registro, ni siquiera con
Google). Los códigos de unidad los genera el auditor y se muestran una sola vez.

## 2. Panel web

### `/panel/hallazgos` — la mesa de trabajo

Lista completa de hallazgos con:

- **Filtros** por severidad, estado, regla y período, persistidos en la URL (se puede compartir un link
  a "los críticos abiertos de agosto").
- **Búsqueda** por texto sobre título, evidencia y proveedor.
- **Orden** por severidad, monto o período.
- **KPIs** arriba: cuántos críticos, altos, pendientes.
- **Selección en lote** para cambiar el estado de varios hallazgos de una vez con una nota común.
- **Drawer de triage** que abre el detalle sin perder el scroll ni los filtros: evidencia,
  recomendación, refs, documentos asociados con visor embebido, historial de cambios, y los controles
  para cambiar estado, publicar y registrar la respuesta de la administración.
- Página propia por hallazgo (`/panel/hallazgos/[id]`) para links directos.

### `/panel/liquidaciones`

- Lista de meses con estado (`procesando`, `procesada`, `no_cuadra`, `error`, `publicada`) y si cuadra.
- Subida del PDF de la liquidación y del ZIP de comprobantes (solo auditor).
- Detalle por mes: verificaciones de cuadre con las que fallaron y su diferencia exacta, totales por
  categoría, listado de gastos, y el botón de publicar.

### `/panel/transparencia`

- El índice compuesto en grande, con el desglose de los cinco componentes (peso, valor y puntos) y la
  cuenta de la penalización por críticos abiertos.
- Barras de progreso: dinero trazable, con factura y con pago respaldado.
- Tabla de gastos por estado con drill-down interactivo: al elegir un estado se listan los gastos con
  sus hallazgos y documentos.
- Card de cuestiones abiertas por severidad.

### `/panel/analisis`

Vista analítica de los datos: ranking de proveedores, totales por categoría, buscador de gastos con
total de lo filtrado y variación entre períodos.

### `/panel/consorcio`

- Datos del consorcio (nombre, dirección, CUIT, administración, marca de los informes).
- **Umbrales de las reglas**: todos los campos de la `Config` del motor, editables, con los valores por
  defecto al lado para poder volver atrás. Semántica PUT: se manda el dict completo; `{}` resetea.
- Subida del reglamento de copropiedad (PDF escaneado + transcripción markdown) y de la biblioteca de
  normativa (escala SUTERH, acuerdo paritario, honorarios de referencia).
- Tabla de unidades con generación de código de acceso por UF.

### `/mi-unidad` — vista del propietario

- Estado de cuenta de su unidad en el último período publicado.
- Card de transparencia con el índice y los conteos (se oculta en silencio si no hay períodos
  publicados o si hay un error de red: al propietario no se le muestran errores de infraestructura).
- Hallazgos publicados, colapsados por defecto, con los comprobantes que los respaldan descargables o
  visibles en un diálogo.
- Informe del mes embebido (HTML) y Excel descargable.
- Optimizada para teléfono; el panel es instalable como PWA.

### `/reglamento`

Reglamento de copropiedad consultable: transcripción navegable (markdown) y PDF original descargable.

## 3. Motor por línea de comandos

Análisis completo sin levantar nada:

```bash
python -m ct analizar LIQUIDACION.pdf \
  --anterior MES_ANTERIOR.pdf \
  --comprobantes CARPETA --manifiesto CARPETA/manifest.json --mes 2026-08 \
  --excel informe.xlsx --html informe.html --marca "Consorcio Transparente" \
  --json salida.json
```

| Flag | Para qué |
|---|---|
| `--anterior` | Habilita las reglas que comparan contra el mes previo (`costos`, `prorrateo`). |
| `--comprobantes` + `--manifiesto` + `--mes` | Activa el cruce documental. |
| `--solo-cuadre` | Solo las verificaciones aritméticas. Es la comprobación mínima antes de publicar nada. |
| `--json` | Vuelca el análisis completo para inspeccionarlo o diffearlo. |
| `--excel` / `--html` / `--marca` | Informes con marca. |

Otros subcomandos: `descargar` (comprobantes de un mes o `listar` los períodos),
`descargar-liquidacion` (el PDF del mes), `sincronizar [--desde AAAA-MM]` (pipeline completo
portal → API).

## 4. API

Autenticación por cookie httpOnly. Todos los paths requieren sesión salvo los de login.

### Auth

| Método | Path | Rol | Qué hace |
|---|---|---|---|
| POST | `/auth/login` | — | Email + clave (argon2id). |
| POST | `/auth/login-unidad` | — | UF + código del propietario. |
| POST | `/auth/login-google` | — | ID token de Google verificado contra el JWKS. |
| POST | `/auth/mcp-token/validar` | — | Valida un token del MCP (lo usa el wrapper del servidor MCP). |
| POST | `/auth/salir` | sesión | Borra la cookie. |
| GET | `/auth/yo` | sesión | Rol y nombre, o UF si es propietario. |

### Liquidaciones y documentos

| Método | Path | Rol | Qué hace |
|---|---|---|---|
| POST | `/liquidaciones` | auditor | Sube el PDF/TXT del mes; procesa en background. Tope `CT_MAX_LIQ_MB` (30). |
| GET | `/liquidaciones` | equipo | Lista con estado y cuadre. |
| GET | `/liquidaciones/{id}` | equipo | Checks fallidos, totales por categoría, gastos. |
| POST | `/liquidaciones/{id}/comprobantes` | auditor | Sube el ZIP; el cruce es sincrónico. Tope `CT_MAX_ZIP_MB` (100). |
| POST | `/liquidaciones/{id}/publicar` | auditor | Genera informes HTML + XLSX y publica. |
| GET | `/documentos?liquidacion_id=` | equipo + propietario | Documentos del mes; el propietario solo ve los citados en hallazgos publicados. |
| GET | `/documentos/{id}/contenido` | equipo + propietario | Descarga el archivo; `?vista=1` lo muestra embebido (solo equipo). |
| GET | `/documentos/{id}/texto` | equipo | Texto extraído del documento. |
| GET | `/informes/{periodo}/{tipo}` | sesión | Informe publicado (`html` o `xlsx`). |
| GET | `/mi-unidad` | propietario | Estado de cuenta de la unidad. |

### Hallazgos

| Método | Path | Rol | Qué hace |
|---|---|---|---|
| GET | `/hallazgos` | equipo + propietario | Filtros por severidad, estado, regla y período. El propietario solo ve publicados. |
| GET | `/hallazgos/{id}` | equipo + propietario | Detalle; el propietario no recibe el historial de eventos. |
| POST | `/hallazgos/{id}/estado` | auditor | Cambia el estado y registra el evento. |
| POST | `/hallazgos/{id}/publicar` | auditor | Publica o despublica. |
| POST | `/hallazgos/{id}/respuesta` | auditor | Registra la respuesta de la administración. |

### Consulta y analítica

| Método | Path | Rol | Qué hace |
|---|---|---|---|
| GET | `/consulta/gastos` | equipo | Busca por proveedor, categoría, concepto, rango de períodos e importe mínimo. |
| GET | `/consulta/agregados?por=` | equipo | Totales por proveedor, categoría o período, con variación entre períodos. |
| GET | `/consulta/comprobantes?q=` | equipo | Búsqueda literal dentro del texto de las facturas, con fragmentos de contexto. |
| GET | `/consulta/semantica?q=&k=` | equipo | Búsqueda por embeddings (503 si no hay API key configurada). |
| GET | `/consulta/deudores` | equipo | Unidades con deuda y meses equivalentes. |
| GET | `/analitica/indice` | equipo + propietario | Índice compuesto con desglose, global y por período. |
| GET | `/analitica/gastos?periodo=` | equipo + propietario | Gastos con su estado, hallazgos y documentos. |

### Consorcio

| Método | Path | Rol | Qué hace |
|---|---|---|---|
| GET / PUT | `/consorcio` | equipo / auditor | Datos y umbrales (el GET devuelve `umbrales` + `umbrales_default`). |
| GET / POST | `/consorcio/reglamento` | sesión / auditor | Estado y subida del PDF + transcripción. |
| GET | `/consorcio/reglamento/{tipo}` | sesión | Descarga (`pdf` o `transcripcion`). |
| GET / POST | `/consorcio/normativa[/{tipo}]` | sesión / auditor | Biblioteca de normativa de referencia. |
| GET | `/unidades` | auditor, consejo | Listado de UFs. |
| POST | `/unidades/{uf}/codigo` | auditor | Genera el código de acceso (se devuelve una sola vez). |

`GET /salud` responde `{"ok": true}` sin sesión: es lo que mira el deploy.

## 5. MCP — preguntar en lenguaje natural

Servidor de **solo lectura** en `mcp-consorcio.neuralcore.dev/mcp/<token>`, conectable a claude.ai,
Claude Code y ChatGPT. Guía de conexión en [MCP.md](MCP.md); administración de tokens en
[MCP-TOKENS.md](MCP-TOKENS.md).

| Herramienta | Responde a preguntas como |
|---|---|
| `consultar_gastos` | "¿Cuánto se le pagó a tal proveedor en el año?" |
| `agregados` | "¿Qué categoría creció más entre julio y agosto?" |
| `listar_hallazgos` / `detalle_hallazgo` | "¿Qué problemas críticos hay abiertos?" |
| `estado_liquidaciones` / `detalle_liquidacion` | "¿Cerró bien agosto? ¿Qué verificación falló en noviembre?" |
| `resumen_mensual` | "Dame el resumen del mes." |
| `leer_comprobante` / `buscar_en_comprobantes` | "¿Qué CUIT figura en la factura del gasto 12?" |
| `buscar_semantico` | "Buscá gastos relacionados con seguridad del edificio." |
| `deudores` | "¿Quién debe y hace cuántos meses?" |
| `reglamento` | "¿Qué dice el reglamento sobre poderes en asambleas?" |
| `indice_transparencia` | "¿Cuál es el índice y por qué?" |
| `estado_gastos` | "¿A qué gastos les falta respaldo en agosto?" |
| `search` / `fetch` | (las usa solo el modo investigación de ChatGPT.) |

Nada de lo que se pregunte puede modificar, publicar ni borrar datos.

## 6. Automatismos

| Cuándo | Qué |
|---|---|
| 06:30 (AR), diario | `ct sincronizar`: baja del portal lo nuevo y lo ingesta. Nunca publica. |
| Al arrancar el worker | Una corrida de sincronización, para cubrir apagones. |
| 07:00 (AR), diario | `pg_dump` comprimido a `datos-api/backups/`, rotación de los últimos 14. |
| En cada ingesta de comprobantes | Embeddings de los documentos nuevos (si hay API key). |
| Al final de cada `procesar` y cada cruce | Recálculo de las reglas históricas sobre toda la serie. |

## 7. App de asamblea (`apps/asamblea/`)

Pieza separada, ya en producción en `asamblea.neuralcore.dev`: votación por doble mayoría (unidades +
porcentual), registro de presentes, mociones en pestañas, agenda de la convocatoria, preguntas con
comprobante, proposiciones del art. 2060 con objeciones, documentos, PIN de moderador, exportación a
xlsx/PDF y sincronización entre teléfonos vía Apps Script + Google Sheet. Un solo HTML generado por
`make_votacion.py` + `asamblea_content.py`, con backend `Code.gs`.

Diseño en [2026-09-03-asamblea-app-design.md](2026-09-03-asamblea-app-design.md).
