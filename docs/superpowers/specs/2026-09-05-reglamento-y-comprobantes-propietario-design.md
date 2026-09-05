# Reglamento en el panel + comprobantes para propietarios (diseño aprobado 05-09-2026)

Dos ampliaciones de transparencia hacia el propietario: el reglamento de copropiedad consultable desde el
panel (transcripción legible + PDF escaneado como fuente de fe), y acceso de solo lectura a los hallazgos
**publicados** con descarga de sus comprobantes. La app de asamblea sigue separada (fuera de alcance).

## 1. API — reglamento del consorcio

- Claves fijas de storage: `consorcio/reglamento.pdf` y `consorcio/reglamento.md`.
- `POST /consorcio/reglamento` (solo auditor): multipart con archivos opcionales `pdf` y/o `transcripcion`
  (al menos uno), tope 20 MB por archivo. Reemplaza lo que hubiera.
- `GET /consorcio/reglamento/pdf` → descarga forzada (attachment, como todo documento de terceros).
- `GET /consorcio/reglamento/transcripcion` → el markdown crudo (`text/markdown`).
- Ambos GET con `security.sesion` (cualquier rol, propietarios incluidos); 404 si no se subió aún.

## 2. Web — página `/reglamento`

- Página nueva protegida por sesión (agregar `/reglamento` al matcher de `web/proxy.ts`).
- Renderiza la transcripción con `react-markdown` (dependencia nueva del front), conservando la advertencia
  de la transcripción ("verificar toda cita contra el PDF original"); botón "Descargar el PDF escaneado".
- Si no hay reglamento cargado: mensaje "todavía no está cargado" (sin link a Consorcio: la página vive
  fuera del layout del panel y no conoce el rol; el equipo sabe dónde se sube).
- Entradas: tarjeta/link en `/mi-unidad` y ítem "Reglamento" en el sidebar del panel.
- En `/panel/consorcio` (solo auditor, mismo gating por rol existente): sección para subir/reemplazar
  los dos archivos.

## 3. API — hallazgos publicados para propietarios

- `GET /hallazgos` y `GET /hallazgos/{id}`: el rol propietario pasa a estar permitido, pero ve **solo
  `publicado=true`**; el detalle para propietario **omite el historial de eventos** (notas internas del
  triage). Para el equipo nada cambia.
- `GET /documentos/{id}/contenido`: el propietario puede descargarlo solo si el documento pertenece a un
  hallazgo publicado (misma `liquidacion_id`, `gasto_n` presente en las `refs`, y **`origen="comprobantes"`**
  — las refs de hallazgos de origen "liquidacion" son UFs, no gastos; mismo criterio que `publicar.py`).
  Siempre con descarga forzada; `vista=1` sigue siendo exclusivo del equipo (con vista y rol propietario →
  403). Documento no accesible o inexistente → 403 uniforme para el propietario (sin enumeración de IDs).
- `GET /documentos?liquidacion_id=` (ajuste detectado al planificar): el propietario también puede listar,
  filtrado con el mismo predicado — sin esto el front no puede descubrir los IDs descargables.

## 4. Web — sección "Hallazgos publicados" en `/mi-unidad`

Debajo del informe embebido: lista de los hallazgos publicados (severidad, título, monto, evidencia,
qué pedir, respuesta de la administración si existe) con sus comprobantes como links de descarga.
Sin acciones: pura lectura.

## 5. Errores y bordes

- Reglamento parcial (solo PDF o solo transcripción): la página muestra lo que haya y ofrece lo demás
  cuando exista.
- El markdown con marcas `[dudoso]`/`[ilegible]` se muestra tal cual: es parte de la honestidad del
  documento transcripto.
- Propietario pidiendo un hallazgo no publicado → 404 (no revela si existe).

## 6. Pruebas

- API (+5): subir reglamento requiere auditor y sirve a cualquier sesión (pdf attachment, md como texto);
  propietario lista solo publicados; detalle de propietario sin eventos (y 404 para no publicado);
  documento de hallazgo publicado → 200 attachment para propietario; documento no asociado a publicado
  (o con `vista=1`) → 403.
- Web (+3): página `/reglamento` renderiza la transcripción y el botón del PDF (y el estado vacío);
  `/mi-unidad` lista hallazgos publicados con links de documentos; la subida en Consorcio solo aparece
  para auditor.

## Fuera de alcance

Integración de la app de asamblea al panel, comprobantes de gastos sin hallazgo publicado, versionado
histórico del reglamento, render del PDF embebido (se descarga).
