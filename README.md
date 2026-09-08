# Consorcio Transparente

Motor de análisis de liquidaciones de expensas + cruce de comprobantes + panel de auditoría + app de
asamblea. Trabaja para el **propietario**, no para la administración.

> ¿Tengo evidencia suficiente para afirmar que la administración de mi edificio es transparente?

El sistema lee la liquidación mensual, verifica que cuadre al centavo, cruza cada gasto contra la factura
y el pago que lo respaldan, aplica un catálogo de reglas, y resume todo en un **índice de transparencia
0-100** calculado con una fórmula pública. Cada hallazgo cita su línea, su factura o su comprobante.

Caso piloto en producción: **Consorcio Rivadavia 2069** (CABA), serie 2026-01 a 2026-08 cargada y auditada.

## Documentación

| Documento | Qué responde |
|---|---|
| [docs/ORIGEN.md](docs/ORIGEN.md) | Por qué existe esto, qué problema resuelve y con qué principios. |
| [docs/ARQUITECTURA.md](docs/ARQUITECTURA.md) | Cómo está construido: módulos, modelo de datos, decisiones y por qué. |
| [docs/PIPELINE.md](docs/PIPELINE.md) | Del portal al índice, paso a paso, con sus invariantes. |
| [docs/FUNCIONALIDADES.md](docs/FUNCIONALIDADES.md) | Qué hace cada pantalla, endpoint, comando y herramienta del MCP. |
| [docs/USO.md](docs/USO.md) | Cómo se usa: entorno, CLI, operación mensual, MCP, problemas conocidos. |
| [docs/ANALISIS-RIVADAVIA-2069.md](docs/ANALISIS-RIVADAVIA-2069.md) | Qué encontró el sistema sobre datos reales. |
| [docs/reglas.md](docs/reglas.md) | Catálogo de reglas de detección con sus umbrales. |
| [docs/DEPLOY.md](docs/DEPLOY.md) | Runbook de instalación y operación de la infraestructura. |
| [docs/MCP.md](docs/MCP.md) · [docs/MCP-TOKENS.md](docs/MCP-TOKENS.md) | Servidor MCP de consultas y administración de sus tokens. |
| [docs/ESTADO.md](docs/ESTADO.md) | Bitácora de ciclos, decisiones tomadas y próximos pasos. |
| [CLAUDE.md](CLAUDE.md) | Reglas de trabajo del repositorio. |

## Estructura

```
engine/            motor de análisis (Python 3.10+, sin dependencias salvo openpyxl)
  ct/model.py         modelo de una liquidación, independiente del sistema que la emitió
  ct/redconar.py      parser Redconar / "Mis Expensas" (2 plantillas) + ~30 verificaciones de cuadre
  ct/rules.py         catálogo de reglas del mes (ver docs/reglas.md)
  ct/historia.py      reglas sobre la serie (duplicados entre meses, saltos de precio, concentración)
  ct/comprobantes.py  cruce factura ↔ pago ↔ liquidación sobre los adjuntos del portal
  ct/qr.py            lectura del QR de ARCA: datos autoritativos que pisan el texto parseado
  ct/escritura.py     prorrateo contra los porcentuales de dominio del reglamento
  ct/cli.py           línea de comandos (`python -m ct`)
api/               API del panel (FastAPI + SQLAlchemy + Alembic; Postgres con pgvector)
  servidor_mcp.py     servidor MCP de consultas, solo lectura, 16 herramientas
  worker.py           sincronización diaria del portal (06:30) + backup de la base (07:00)
web/               panel y vista del propietario (Next.js + React + Tailwind + shadcn/ui)
apps/asamblea/     app de asamblea (agenda, votación por doble mayoría, preguntas, proposiciones)
tools/auditoria-manual/   scripts de la auditoría manual de agosto 2026 (referencia histórica)
docs/              documentación del proyecto
```

Tests: motor **151** · API **192** · web **64**.

## Empezar

```bash
# análisis de una liquidación: sin base de datos, sin cuenta, sin red
cd engine
python3 -m venv .venv && .venv/bin/pip install -e .
.venv/bin/python -m ct analizar liquidacion.pdf --solo-cuadre
```

Requiere `pdftotext` (poppler-utils). El cruce documental se activa con `--comprobantes`: lee cada factura
y ticket de pago, identifica emisor, receptor, CUIT, cuenta de destino, fechas e importes, y detecta pagos
a terceros, facturas a nombre de empleados o propietarios, comprobantes reutilizados, pagos en exceso,
devoluciones, facturas emitidas después del pago y gastos sin respaldo.

La guía completa —CLI del motor, CLI de la API, operación mensual, MCP y problemas conocidos— está en
[docs/USO.md](docs/USO.md).

## Principios

1. **Nada se publica si no cuadra al centavo.** Cada liquidación pasa por ~30 verificaciones aritméticas
   (líneas vs. totales por rubro y por clase, estado financiero, cuentas, deudores, prorrateo, estado de
   cuentas por unidad). Un hallazgo sobre un documento que no cierra es ruido, no un hallazgo.
2. **Hechos con documento, nunca acusaciones sobre personas.** Cada hallazgo dice qué se observó, dónde
   está la evidencia y qué pedir.
3. **Reproducibilidad.** Cualquiera con el PDF obtiene el mismo resultado. El índice sale de una fórmula
   publicada; ninguna cifra la genera un modelo de lenguaje.
4. **Antes de agregar una regla, la prueba con un fixture real.**
5. **Independencia.** No administramos consorcios ni cobramos porcentaje de expensas.
6. **Los datos del consorcio no entran al repositorio.**

## Datos privados

Liquidaciones PDF, comprobantes, manifiestos y planillas viven en `~/consorcio-transparente-privado/`
(o donde apunte `CT_PRIVADO`), fuera de git. Las credenciales del portal y de Cloudflare no se guardan en
ningún archivo del repo.
