# Ciclo D-QR: leer y cruzar el QR de ARCA de las facturas (diseño aprobado 07-09-2026)

Redefinición del ciclo D ("OCR de imágenes"): las facturas electrónicas llevan el QR obligatorio
de ARCA con los datos autoritativos (CUIT emisor, tipo/PtoVta/número, fecha, importe total, CUIT
receptor, CAE). Leerlo evita OCR para casi todo (solo 5 de 575 documentos son imágenes ciegas) y
da cross-checks que los falsos positivos de ayer (EDESUR, Tecno Sim) hubieran evitado.

## 1. Módulo `engine/ct/qr.py` (dependencia OPCIONAL, patrón embeddings)

- `leer_qr(path) -> Optional[dict]`: si `path` es PDF, renderiza la primera página con
  `pdftoppm -r 200 -f 1 -l 1 -png` (poppler ya está); si es imagen, directo. Decodifica QRs con
  `pyzbar` (import perezoso dentro de try/except: sin `pyzbar`/`libzbar`, devuelve None y el
  motor sigue como hoy — el motor NO gana una dependencia dura). Busca el QR cuyo dato sea la
  URL `afip.gob.ar/fe/qr/?p=<base64>`; decodifica el JSON. Timeouts y cualquier error → None.
- `decodificar_payload(url) -> Optional[dict]` (función pura, testeable sin imágenes): extrae y
  parsea el base64; devuelve dict normalizado: `{cuit_emisor, tipo_cmp, pto_vta, nro_cmp, fecha
  (ISO), importe, moneda, cuit_receptor (si tipoDocRec=80), cae}`. Base64 con padding faltante,
  JSON roto, campos ausentes → None o campos None (nunca excepción).

## 2. Integración en `interpretar()` (`comprobantes.py`)

- Para docs clasificados `factura` o `imagen`: `qr = leer_qr(path)`; se guarda en el campo nuevo
  `Documento.qr: Optional[dict] = None` (viaja solo a la API vía `to_dict()`/metadatos — sin
  migración).
- **El QR es autoritativo**: si hay QR, pisa `emisor_cuit`, `importe`, `fecha` y arma
  `factura_nro = f"{pto_vta:04d}-{nro_cmp:08d}"`; si `cuit_receptor` viene, pisa `receptor_cuit`.
  Los valores parseados del texto que difieran materialmente (importe ±$1, CUIT distinto) se
  registran en `notas` ("El texto de la factura dice X pero el QR de ARCA dice Y").
- Un doc `imagen` con QR pasa a `tipo="factura"` con nota "Clasificada por el QR de ARCA (sin
  texto extraíble)". Deja de ser ciego.

## 3. Cross-checks nuevos en `cruzar`

1. **QR vs texto** (`qr-texto`): si el texto parseado traía importe o CUIT emisor y difieren del
   QR (importe ±$1; CUIT distinto) → **ALTO**, "el texto de la factura no coincide con su QR de
   ARCA" (indicador de adulteración o de PDF mal generado), clave `qr-texto`, refs `[n]`.
2. **Numeración** (`qr-numeracion`): si la liquidación cita `factura_nro` y el QR trae otra
   numeración (normalizadas con `_norm_nro`) → **MEDIO**, "la factura adjunta no es la citada en
   la liquidación", clave `qr-numeracion`.
3. **Receptor**: sin regla nueva — el `receptor_cuit` autoritativo del QR alimenta la regla
   existente de "factura emitida a un tercero" (y con el fix de ayer, sin falsos positivos).
   Ídem `chequear_importe_factura`: el importe QR ya entra por `f.importe`.

## 4. Infraestructura

- `api/requirements*.txt` (el que exista): `pyzbar`; Dockerfile de la imagen api/worker/mcp:
  `libzbar0` en el apt-get (verificar el Dockerfile real). En dev sin zbar todo sigue andando
  (los tests del QR de imagen se saltean con `pytest.importorskip`/skipif).

## 5. Pruebas

- `engine/tests/test_qr.py`: `decodificar_payload` puro — payload real de ejemplo (armar el
  base64 en el test con el JSON documentado de ARCA), padding faltante, JSON roto, URL no-ARCA,
  `tipoDocRec` distinto de 80 (sin cuit_receptor). Integración con imagen: generar en el test un
  QR sintético con `pyzbar`+`qrcode`… NO: `qrcode` no está — usar un PNG fixture chico commiteado
  en `engine/tests/fixtures/qr_arca.png` generado una única vez durante el desarrollo (es un QR
  de datos de ejemplo, no privado), y skipif sin pyzbar.
- `interpretar` con QR (monkeypatch de `leer_qr`): pisa importe/CUIT/nro, nota de divergencia,
  imagen→factura.
- `cruzar`: los dos checks nuevos con `Documento` sintéticos (qr dict presente).
- Smoke real: correr `leer_qr` sobre los documentos reales de la carpeta privada; reportar
  cuántas facturas tienen QR legible y verificar 2-3 payloads a mano contra el PDF.

## Fuera de alcance

Constatación online contra ARCA (WSCDC: requiere clave fiscal/certificados — anotado como etapa
opcional), OCR de manuscritos (quedan ~5 docs ciegos; si tras el QR siguen siendo relevantes se
evalúa visión), regla de correlatividad por emisor (la habilita este ciclo — próxima).
