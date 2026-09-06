# MCP ampliado: comprobantes, deudores, cuadre y resumen (diseño aprobado 06-09-2026)

Cuatro capacidades nuevas de consulta, elegidas por el auditor sobre la base del MCP existente
(spec `2026-09-05-consulta-datos-design.md`). Todo read-only, mismos clientes (Claude/ChatGPT/panel bot).

## 1. API — texto de comprobantes

- `GET /documentos/{id}/texto` (equipo): extrae el texto del PDF con `pdftotext -layout` (poppler ya está
  en la imagen; los comprobantes del portal son mayormente PDFs digitales). Respuesta
  `{"texto": str, "extraible": bool}` — `extraible=false` con texto vacío para imágenes/escaneos
  (JPG/PNG o PDF sin capa de texto): sin OCR en esta etapa, honesto sobre el límite.
- Cache en memoria por `documento.hash` (el contenido es inmutable por hash; dict simple del módulo).
- `GET /consulta/comprobantes?q=&periodo=` (equipo): busca `q` (case-insensitive) en el texto extraído
  de todos los documentos del período (o todos si no se da) y devuelve
  `{"resultados": [{"documento_id", "gasto_n", "periodo", "tipo", "fragmento"}]}` — el fragmento son
  ±200 caracteres alrededor del primer match. La primera búsqueda extrae y cachea; las siguientes son
  en memoria.

## 2. API — deudores

- `GET /consulta/deudores?periodo=` (equipo; default: último período con liquidación): del `datos` de la
  liquidación, las unidades con deuda > 0: `{"uf", "piso_depto", "deuda", "meses_equivalentes"}`
  (deuda / expensa mensual de esa unidad), orden por deuda desc, más el total.
  (Verificar en el plan el shape real de `liq.datos` — la vista mi-unidad ya lee estado_cuenta por
  unidad de ahí.)

## 3. MCP — tools nuevas (sobre los endpoints de arriba + los existentes)

- `leer_comprobante(documento_id)`: el texto del PDF (o el aviso de no-extraíble + sugerencia de bajarlo
  del panel).
- `buscar_en_comprobantes(texto, periodo="")`: los fragmentos con contexto.
- `deudores(periodo="")`: tabla legible.
- `detalle_liquidacion(periodo)`: usa los endpoints existentes (listar + detalle por id): estado, cuadre,
  checks fallidos si hay, totales por categoría.
- `resumen_mensual(periodo="")` (default: último período): compone en UN llamado — estado/cuadre,
  top 10 gastos del período, hallazgos del período (título+severidad+estado), agregados con variación
  fuerte (|variación| > 20%), y total de deudores. Sin endpoint nuevo: orquesta los existentes.
- `search`/`fetch` NO cambian (los comprobantes se buscan con su tool propia — el fragmento necesita
  contexto de gasto que el shape de search no da).

## 4. Bordes

- PDFs no extraíbles → `extraible: false`, jamás un error. pdftotext con timeout (10 s) y tope de
  texto por documento (100 KB).
- La primera `buscar_en_comprobantes` de un período frío tarda unos segundos (extracción de ~80 PDFs)
  — aceptable; queda caliente para la sesión del contenedor.
- `resumen_mensual` degrada por partes: si una fuente falla, el resumen sale igual con esa sección
  marcada como no disponible.

## 5. Pruebas

- API (+4): texto de un PDF sintético (generarlo en el test con contenido conocido); no-extraíble
  (bytes que no son PDF); búsqueda con fragmento correcto; deudores ordenados con meses_equivalentes.
- MCP (+3): tools contra el stub extendido (leer/buscar/deudores/resumen — el resumen con una fuente
  rota degrada por partes).

## Fuera de alcance

OCR de escaneos (imágenes), escritura, search/fetch sobre comprobantes, endpoints públicos nuevos
(todo equipo-only).
