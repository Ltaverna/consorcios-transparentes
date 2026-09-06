# Índice de transparencia y estados por gasto (diseño 06-09-2026)

Origen: pedido de analítica del dueño + `consorcio_transparente_vision.md` (ChatGPT). El corazón
no son los gráficos: es poder afirmar "el X % del dinero tiene trazabilidad documental completa
y quedan N cuestiones pendientes de explicación". Todo determinista y abrible a su evidencia:
ninguna cifra la genera una IA.

Alcance aprobado: estados por gasto + índice con métricas + página en el panel (también para
propietarios, sobre lo publicado) + herramientas nuevas del MCP.

## 1. Estado por gasto (calculado, nunca almacenado)

Módulo nuevo `api/app/analitica.py`. Un gasto se clasifica con esta precedencia, usando lo que
ya existe (documentos adjuntos + hallazgos que lo refieren por `n` en sus `refs`):

- Hallazgo **abierto** = `estado in ("pendiente", "preguntado", "respondido")` (respondido: la
  explicación llegó pero el auditor todavía no la validó). **Resuelto** = `cerrado` o `descartado`.
1. 🔴 **inconsistencia**: lo refiere un hallazgo abierto **CRÍTICO**.
2. 🟠 **anomalía**: lo refiere un hallazgo abierto **ALTO**.
3. ⚪ **sin información**: no tiene ningún documento adjunto (`Documento` con su `gasto_n`).
4. 🟡 **requiere explicación**: lo refiere un hallazgo abierto MEDIO o BAJO.
5. ✅ **verificado**: tiene al menos un documento y ningún hallazgo abierto lo refiere
   (los resueltos no cuentan en contra: un hallazgo cerrado/descartado deja el gasto verificado).

Solo cuentan hallazgos cuyo `refs` contiene el `n` del gasto y cuyo origen es de esa liquidación
(`liquidacion`, `comprobantes`, `historia` — todos ya cuelgan de la liquidación correcta).

## 2. Métricas y el índice (fórmulas fijas, documentadas)

`metricas(db, desde, hasta, solo_publicado)` devuelve, por período y agregado del rango:

- **% del dinero trazable** (la métrica madre y el número del índice): suma de importes de
  gastos ✅ / suma total de importes. El índice 0-100 es esto, redondeado.
- **% del dinero con factura adjunta**: gastos con ≥1 doc tipo `factura`, ponderado por importe.
  Los docs tipo `imagen` (recibos manuscritos/fotos sin texto) NO cuentan como factura: son un
  respaldo pendiente de lectura (eso lo resuelve el ciclo D con OCR).
- **% del dinero con pago respaldado**: gastos cuyos pagos por transferencia no tienen ningún
  hallazgo abierto `pago-sin-comp` y que tienen ≥1 doc tipo `pago`, o cuya forma es débito
  automático (respaldo implícito del resumen bancario). Efectivo nunca cuenta como respaldado.
- **Cuestiones pendientes**: conteo de hallazgos abiertos por severidad, y resueltas
  (cerrado+descartado) para mostrar el avance del triage.
- **Distribución de estados**: cantidad de gastos e importe por cada uno de los 5 estados.
- Cada métrica lleva su lista de `gasto_id`/`hallazgo_id` para el drill-down (el panel y el MCP
  muestran la evidencia, no solo el número).

**Vista del propietario** (`solo_publicado=True`): solo liquidaciones `publicada` y solo
hallazgos `publicado=True`. Un hallazgo sin publicar NO baja el estado del gasto en esa vista
(regla de oro intacta: nada sin publicar se filtra, ni siquiera como número).

## 3. API

Router nuevo `api/app/routers/analitica.py`:
- `GET /analitica/indice?desde&hasta` → índice + métricas por período y agregado. Roles:
  auditor/consejo/moderador (vista completa) y propietario (solo_publicado). Igual patrón que
  `/hallazgos`.
- `GET /analitica/gastos?periodo&estado=` → drill-down: gastos con su estado calculado,
  hallazgos abiertos que los refieren (id+titulo+severidad) y documentos que los respaldan.
  Mismo gating por rol.
- Sin migraciones: todo derivado.

## 4. Panel (web)

- Página nueva `web/app/panel/transparencia/page.tsx` (auditor/consejo/moderador): el índice
  grande, las métricas con barra y su drill-down (clic → lista de gastos con estado y links a
  hallazgos/documentos ya existentes), la distribución de estados, y la serie mensual del índice.
- Vista del propietario: sección "Transparencia" en `mi-unidad` (o página propia si el layout lo
  pide — decidirlo al implementar siguiendo la navegación existente) con las MISMAS métricas
  calculadas sobre lo publicado, mismo componente, sin números de la vista interna.
- Sin librerías nuevas: barras/series con lo ya usado en `panel/analisis` (respetar su estilo).

## 5. MCP (2 herramientas nuevas → actualizar `docs/MCP.md`)

- `indice_transparencia(desde="", hasta="")` → el índice, las métricas y las cuestiones
  pendientes por severidad, formateado como las demás tools (texto legible, montos con `_plata`).
- `estado_gastos(periodo, estado="")` → drill-down de un período: cada gasto con su estado,
  y qué hallazgo/documento lo justifica.
- Ambas vía `ClienteApi` (credenciales del bot, vista completa) contra los endpoints nuevos.

## 6. Pruebas

- API (`api/tests/test_analitica.py`): con el fixture real de agosto procesado — clasificación
  de los 5 estados construyendo hallazgos/documentos sintéticos sobre gastos reales
  (CRÍTICO abierto → inconsistencia; cerrado → verificado si hay docs; sin docs → sin
  información; etc.); fórmula del índice verificada a mano con 2-3 gastos; la vista propietario
  no cuenta hallazgos sin publicar ni liquidaciones sin publicar; roles (propietario recibe la
  vista filtrada, anónimo 401).
- MCP (`api/tests/test_mcp.py`): las 2 tools nuevas con el stub existente del cliente.
- Web (`web/tests/`): la página renderiza el índice y el drill-down con datos mockeados; la
  vista propietario no muestra lo interno (mismo patrón de los tests existentes).
- Smoke post-deploy: el índice real de julio y agosto, verificado contra un conteo manual.

## Fuera de alcance

Índice ponderado por pesos configurables (la fórmula fija es defendible; se revisa con meses de
uso), "destino del trabajo" por UF como métrica (necesita datos que hoy no existen — anotado
para cuando el conocimiento del edificio esté cargado), comparación entre consorcios, export PDF.
