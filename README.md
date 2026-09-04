# Consorcio Transparente

Plataforma de control de expensas y asambleas para propietarios de consorcios. Un motor que lee liquidaciones y comprobantes,
verifica que cuadren al centavo, cruza factura con pago y detecta problemas; y una app de asamblea con votación por doble mayoría.

Estado (4 de septiembre de 2026): API del panel de auditoría completa en la rama `panel-api` (etapa 1). Caso piloto en producción: Consorcio Rivadavia 2069 (asamblea.neuralcore.dev).

> Estado del proyecto, enlaces y próximos pasos: [`docs/ESTADO.md`](docs/ESTADO.md). Instrucciones para trabajar con Claude Code: [`CLAUDE.md`](CLAUDE.md).

## Estructura

```
engine/          motor de análisis (Python 3.10+)
  ct/model.py       modelo de datos de una liquidación, independiente del sistema que la emitió
  ct/redconar.py    parser de liquidaciones Redconar / "Mis Expensas" (2 plantillas), con verificaciones de cuadre
  ct/rules.py       catálogo de reglas de detección (ver docs/reglas.md)
  ct/comprobantes.py cruce factura ↔ pago ↔ liquidación sobre los adjuntos del portal
  ct/cli.py         línea de comandos
  tests/            pruebas de regresión con 5 liquidaciones reales (2024, 2025, 2026)
api/             API del panel de auditoría (FastAPI + Postgres): liquidaciones, comprobantes, hallazgos con
                 estados, publicación de informes, auth por rol y por código de unidad (ver api/README.md)
apps/asamblea/   app de asamblea (agenda, votación, preguntas, proposiciones) + script de Google Sheets
docs/            plan de producto, diseño de la app de asamblea, catálogo de reglas, estado del proyecto
```

## Uso

```
cd engine
python3 -m ct analizar liquidacion.pdf --anterior liquidacion_mes_anterior.pdf --json salida.json
python3 -m ct analizar liquidacion.pdf --comprobantes ./comprobantes --manifiesto manifest.json --mes 2026-08
python3 -m pytest -q tests
```

`--comprobantes` activa el cruce documental: lee cada factura y ticket de pago (pdftotext), identifica emisor, receptor, CUIT,
cuenta de destino, fechas e importes, y detecta pagos a terceros, facturas a nombre de empleados o propietarios, comprobantes
reutilizados, pagos en exceso, devoluciones, facturas emitidas después del pago y gastos sin respaldo.

Requiere `pdftotext` (poppler-utils). Sin dependencias Python externas para el motor.

## Principios

1. Nada se publica si no cuadra: cada liquidación pasa por ~30 verificaciones aritméticas (líneas vs. totales por rubro y por clase,
   estado financiero, cuentas, deudores, prorrateo, estado de cuentas por unidad).
2. Hechos con documento, no acusaciones: cada hallazgo cita la línea, la factura o el comprobante.
3. Independencia: el producto no administra consorcios ni cobra porcentaje de expensas.

## Hoja de ruta

Ver `docs/plan-producto.html`. Próximo: ingesta de otros sistemas de liquidación, cruce automático de comprobantes, informe con marca.

### Descargar comprobantes del portal (Redconar / Mis Expensas)

```bash
cd engine
python -m ct descargar listar --carpeta ~/comprobantes            # períodos disponibles
python -m ct descargar 2026-8 --carpeta ~/comprobantes            # baja factura y ticket de cada gasto
python -m ct analizar liquidacion.pdf --comprobantes ~/comprobantes --manifiesto ~/comprobantes/manifest.json --mes 2026-08
```

Usuario y contraseña se piden por consola o se toman de `CT_REDCONAR_USUARIO` / `CT_REDCONAR_CLAVE`. No se guardan.
Se crea una subcarpeta por mes (`2026-08 Agosto/`) con un archivo por adjunto y un `manifest.json` (una fila por adjunto) que consume el cruce.
