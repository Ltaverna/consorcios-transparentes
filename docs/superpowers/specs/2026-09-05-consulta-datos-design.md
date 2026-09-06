# Consulta de datos: MCP + vista analítica (diseño aprobado 05-09-2026)

Para encontrar problemas rápido: los datos estructurados del consorcio (gastos, pagos, hallazgos,
liquidaciones) se vuelven consultables de dos maneras — una vista analítica en el panel para el equipo,
y un servidor MCP para preguntar en lenguaje natural desde Claude Code, claude.ai **y ChatGPT**.
Solo datos estructurados (sin OCR del contenido de los PDFs — fuera de alcance por ahora). Todo read-only.

## 1. Base compartida — endpoints de consulta (API, roles del equipo)

- `GET /consulta/gastos`: filtros combinables `proveedor` (substring, case-insensitive), `categoria`
  (substring), `periodo_desde`/`periodo_hasta` (AAAA-MM), `q` (texto en concepto), `importe_min`;
  devuelve `{filas: [...], total: <suma>, cantidad}` ordenado por importe desc. Cada fila: período,
  n, proveedor, categoría, concepto, importe, factura, pagos.
- `GET /consulta/agregados?por=proveedor|categoria|periodo` + mismo rango de períodos: grupos con
  `{clave, total, cantidad, variacion}` donde `variacion` compara contra el período inmediato anterior
  al rango (None si no hay). Orden por total desc.
- `requiere("auditor", "consejo", "moderador")` en ambos. Sin paginación (volúmenes chicos; si crece,
  se agrega).

## 2. Vista analítica — `/panel/analisis` (equipo)

Página nueva con ítem en el sidebar ("Análisis"):
- Ranking de proveedores por total del rango (default: todos los períodos cargados) con % de variación.
- Totales por categoría.
- Buscador de gastos con los filtros del endpoint (proveedor, texto, importe mínimo, rango).
Sin acciones de escritura; misma estética del panel.

## 3. MCP — servicio `mcp` en compose

- Server Python con el SDK oficial de MCP (`mcp` en PyPI), transporte **Streamable HTTP** — el estándar
  que aceptan los conectores remotos de claude.ai y de ChatGPT, y `claude mcp add` local.
- Sexto contenedor del stack (imagen propia liviana o la de la API + entrypoint distinto); llama a la
  API interna con las credenciales del bot (env del `.env` raíz); expone SOLO herramientas de lectura:
  - `consultar_gastos(proveedor?, categoria?, q?, periodo_desde?, periodo_hasta?, importe_min?)`
  - `agregados(por, periodo_desde?, periodo_hasta?)`
  - `listar_hallazgos(severidad?, estado?, regla?, periodo?)` y `detalle_hallazgo(id)`
  - `estado_liquidaciones()`
  - `search(query)` y `fetch(id)`: wrappers de compatibilidad con el modo investigación de ChatGPT
    (search → consultar_gastos+hallazgos por texto; fetch → detalle del recurso por id compuesto).
- **Auth pragmática**: los conectores no mandan headers custom, así que el server exige un segmento
  secreto largo en el path (`/mcp/<token>/`); token en el `.env` raíz (rotable) y 404 sin pistas ante
  un path incorrecto. Sin rate limit propio (decisión del review: el token de 24 bytes hace inviable el
  brute-force y los 404 son baratos; si hiciera falta, una rate rule de Cloudflare sobre el hostname).
  El access log del server va apagado (el path contiene el token) y el contenedor recibe SOLO las 4
  variables que necesita (mínimo privilegio: sin credenciales del portal).
- Publicación: regla de ingress nueva en `cloudflared/config.yml` → `mcp-consorcio.neuralcore.dev`
  hacia el contenedor `mcp`, + ruta DNS del tunnel. Alta en clientes: URL con el token en claude.ai
  (Conectores), ChatGPT (Conectores/modo desarrollador) y `claude mcp add --transport http`.

## 3b. Anexo (5/09, del primer uso real): herramienta de reglamento

La pregunta "¿qué dice el reglamento sobre X?" es consulta natural y el MCP no la cubría. Se agrega la
tool `reglamento(busqueda="")`: sin argumento devuelve el índice de secciones de la transcripción
(`GET /consorcio/reglamento/transcripcion`, ya accesible con la sesión del bot); con texto, las secciones
completas cuyo título o cuerpo lo contienen (case-insensitive, dividiendo por headers `##`/`###`).
`search` también busca en los títulos de secciones (id `reglamento:<indice>`) y `fetch` los resuelve.

## 4. Errores y bordes

- Con 2 períodos cargados los agregados son cortos — crecen solos con la sincronización mensual.
- El MCP degrada con mensajes claros si la API no responde; nunca expone stack traces.
- El token comprometido se rota editando el `.env` y recreando el contenedor (documentado en DEPLOY).

## 5. Pruebas

- API (+4): filtros combinados de gastos (con fixture de datos), agregados por proveedor con variación,
  agregados por período, roles (propietario → 403).
- MCP (+2): tools contra una API falsa (el server es un cliente HTTP — se testea con un stub); el
  gating del token (path malo → 404).
- Web (+2): la página renderiza ranking y buscador con MSW; el ítem del sidebar.

## Fuera de alcance

OAuth del MCP (el token en URL alcanza para un usuario; upgrade futuro), OCR/full-text de comprobantes,
escritura por MCP (jamás), multi-consorcio en las consultas.
