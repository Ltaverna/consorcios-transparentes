# Consorcio Transparente

Motor de análisis de liquidaciones de expensas + cruce de comprobantes + app de asamblea. Nombre provisorio.
Dueño: Lucas Taverna (repo personal `Ltaverna/consorcios-transparentes`, no el de Bold). Idioma del proyecto y de las respuestas: español rioplatense.

**Leé primero `docs/ESTADO.md`**: qué existe, decisiones tomadas, enlaces, pendientes y el próximo paso.

## Estructura
- `engine/` motor Python (sin dependencias salvo openpyxl para Excel; `pdftotext` de poppler para PDF). CLI: `python -m ct`.
- `engine/tests/` 27 pruebas; correr con `cd engine && python3 -m pytest -q tests`. Las de comprobantes se saltean si no está la carpeta privada.
- `apps/asamblea/` app de asamblea (un solo HTML generado por `make_votacion.py` + `asamblea_content.py`), backend `Code.gs` en Apps Script.
- `tools/auditoria-manual/` scripts de la primera auditoría (agosto 2026, Rivadavia 2069): generan el Excel y la presentación a mano. Referencia histórica; el motor reproduce sus hallazgos.
- `docs/` plan de producto, catálogo de reglas, diseño de la app de asamblea, estado.

## Datos privados (nunca al repo)
Liquidaciones PDF, comprobantes descargados, manifiestos y planillas del consorcio van en `~/consorcio-transparente-privado/`
(o la carpeta que indique `CT_PRIVADO`). Se copian de máquina a máquina por fuera de git. Estructura esperada:
`Comprobantes Rivadavia 2069/{2026-07 Julio, 2026-08 Agosto, manifest.json}`, `liquidaciones/*.pdf`, `VOTACION CONSORCIO 2026.xlsx`.
Las credenciales del portal (Redconar) y de Cloudflare no se guardan en ningún archivo del repo.

## Reglas de trabajo
- Nada se publica si los totales no cuadran al centavo con el documento (`ct analizar --solo-cuadre`).
- Los hallazgos describen hechos con comprobante y qué pedir; nunca conclusiones acusatorias sobre personas.
- Antes de agregar una regla, agregar la prueba con un fixture real en `engine/tests/fixtures/` (texto de `pdftotext -layout`).
- Commits en español, sin auto-commit: se commitea cuando el usuario lo pide.
