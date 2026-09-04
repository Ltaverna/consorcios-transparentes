# Auditoría manual de agosto 2026 (referencia)

Scripts con los que se hizo la primera auditoría de Rivadavia 2069 antes de que existiera el motor. Se conservan porque documentan
cada hallazgo con su evidencia (`alerts.py`) y porque generan el Excel de 16 hojas y la presentación HTML que se usaron en la asamblea.

- `build_data.py` → `datos/data.json` a partir de `datos/exp.txt` (pdftotext de la liquidación de agosto) y datos cargados a mano.
- `alerts.py` catálogo de 20 hallazgos, bullets y hallazgos documentales.
- `make_excel.py` → `salida/Rivadavia 2069 - Analisis expensas Agosto 2026.xlsx`.
- `make_html.py` → presentación HTML autocontenida.
- `analyze_receipts.py` lectura de los comprobantes descargados (requiere la carpeta privada, ver `CLAUDE.md`).
- `download_attachments.js` código que se corrió en el navegador para bajar los adjuntos del portal (hoy lo reemplaza `ct descargar`).
- `patch_asamblea.py` parche aplicado a la app de asamblea.

Todo esto lo reproduce el motor (`engine/`); no hace falta volver a correrlo.
