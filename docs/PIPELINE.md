# Pipeline: del portal de la administración al índice de transparencia

Recorrido completo de un mes de expensas, con los estados, las invariantes y qué pasa cuando algo sale
mal. Las piezas están descritas en [ARQUITECTURA.md](ARQUITECTURA.md); las reglas, en [reglas.md](reglas.md).

```
 (1) Portal Redconar
       │  ct sincronizar / ct descargar
 (2) Carpeta privada  ──────────────────────────────────┐
       │  POST /liquidaciones (PDF)                     │ POST /liquidaciones/{id}/comprobantes (ZIP)
 (3) Parseo ──▶ (4) CUADRE ──▶ (5) Reglas ──▶ (6) Gastos y unidades   (7) Cruce de comprobantes
       │            │ no cuadra                                              │
       │            └──▶ estado no_cuadra: se limpia y se despublica         │
       ▼                                                                     ▼
 (8) Hallazgos con clave estable  ◀───────────────────────────────────────────
       │
 (9) Reglas históricas sobre la serie
       │
(10) Triage del auditor  ──▶ (11) Publicación  ──▶ (12) Propietario / índice / MCP
```

## 1. Origen: el portal de la administración

La única fuente es el portal Redconar ("Mis Expensas") del consorcio, al que se entra con las
credenciales de propietario. `engine/ct/portal.py` implementa el cliente: login, listado de períodos,
egresos del mes, adjuntos por egreso (factura y ticket de pago) y el PDF de la liquidación.

No hay API oficial: es scraping de un portal PHP. Por eso el parser es defensivo y el cuadre es
obligatorio — si el portal cambia el layout, el sistema lo detecta como "no cuadra" o "error", nunca
publica datos torcidos.

```bash
python -m ct descargar listar --carpeta "$CT_PRIVADO/Comprobantes Rivadavia 2069"
python -m ct descargar 2026-8  --carpeta "$CT_PRIVADO/Comprobantes Rivadavia 2069"
python -m ct descargar-liquidacion 2026-8 --carpeta "$CT_PRIVADO/liquidaciones"
```

## 2. Sincronización automática

El servicio `worker` corre `ct sincronizar` todos los días a las 06:30 (hora de Buenos Aires) y una vez
más al arrancar el contenedor (cubre el caso "la máquina estuvo apagada").

`engine/ct/sincronizar.py` hace, para cada período pendiente:

1. Baja el PDF de la liquidación y todos los adjuntos del mes a la carpeta privada.
2. Arma un **ZIP determinista** (entradas ordenadas, timestamp fijo) para que el mismo mes produzca
   siempre el mismo hash.
3. Sube la liquidación y el ZIP a la API con el usuario bot.
4. Registra el resultado en `$CT_PRIVADO/sincronizacion.json` (qué está subido y con qué hash).

Es idempotente: si el hash no cambió, no vuelve a subir. **Nunca publica** — la decisión de publicar
es siempre humana. Un período que falla se reintenta al día siguiente.

`--desde AAAA-MM` activa el **backfill**: recorre todos los períodos del portal desde esa fecha, del
más viejo al más nuevo, con una pausa entre períodos y sin cortarse ante un mes que falle. Así se
cargó la serie 2026-01 a 2026-08.

## 3. Parseo

`redconar.parse_pdf()` corre `pdftotext -layout` y reconstruye la liquidación: gastos con proveedor,
concepto, categoría, columna (clase de prorrateo), importe, datos de la factura citada y pagos con
fecha, caja y forma; deudores; estado financiero; cuentas; situación patrimonial; estado de cuentas por
unidad con sus porcentuales; evolución de los últimos meses.

Soporta dos plantillas del sistema (2024 y 2025+) y las detecta por marcadores del texto. El resultado
es un `Liquidacion` del motor, independiente del sistema emisor: agregar un segundo sistema de
liquidación significa escribir otro parser que produzca el mismo objeto, sin tocar reglas ni API.

Validaciones tempranas de la ingesta (`api/app/ingesta.py:249-257`), todas causa de `error`:

- no se detecta período → "no se reconoce el documento como una liquidación";
- el período del documento no coincide con el declarado en la subida;
- no se produjo ninguna verificación de cuadre → formato desconocido.

## 4. Cuadre: la puerta de entrada

**Nada avanza si la liquidación no cierra al centavo.** El parser emite una lista de `Check`
(`nombre`, `esperado`, `obtenido`, `ok`) que se expanden a unas 30 verificaciones en un mes real,
porque varias son por cada rubro, clase, cuenta y unidad:

1. Suma de líneas = total de gastos
2. Total declarado de cada rubro = suma de sus líneas
3. Suma de rubros = suma de líneas
4. Total de cada columna/clase (A, B, D) = suma de sus líneas
5. Estado financiero: saldo anterior + ingresos − egresos = saldo de cierre
6. Egresos del estado financiero = total de gastos
7. Cada cuenta: saldo anterior + ingresos − egresos = cierre
8. Suma de cuentas = disponibilidades
9. Deudores: suma de la lista = total declarado
10. Estado de cuentas por unidad: suma de "a pagar" = total, suma de deudas, suma de pagos, cada clase
    contra el prorrateo total, cobertura patrimonial y expensas cobradas vs. pagos

Tolerancia: $0,05. Si algo no cierra, `liq.cuadra` es falso y la ingesta:

- guarda igual el parseo completo del documento **rechazado** en `datos` (el auditor necesita ver qué
  falló),
- borra los gastos y los informes de esa liquidación,
- **despublica** —sin borrar— los hallazgos de origen `liquidacion` e `historia`, conservando estado,
  respuesta y todo el historial de triage,
- deja el estado en `no_cuadra` y termina.

Así, un mes que deja de cuadrar desaparece de lo publicado sin que el auditor pierda su trabajo.

## 5. Reglas sobre la liquidación

Con el cuadre en verde corre `rules.evaluar(liq, anterior, config)`: 15 reglas sobre el mes, algunas
comparando contra el mes anterior (`costos`, `prorrateo`). Los umbrales salen de la `Config` del motor,
sobrescrita por el JSONB `umbrales` del consorcio — editable desde el panel, con 0 = regla apagada para
las reglas de mercado.

Enseguida, si la transcripción del reglamento está en storage (`consorcio/reglamento.md`), corre
`escritura.evaluar_escritura()`: compara la clase A de cada UF contra los porcentuales de dominio del
art. 6°, las UFs faltantes o sobrantes, las cocheras como grupo contra la Unidad Complementaria y la
sanidad de la propia transcripción (que sume 100,0000%). Sin transcripción no corre y no hace ruido.

Cada regla está aislada: una excepción se captura y las demás siguen.

## 6. Persistencia de gastos y unidades

- Los gastos se reemplazan completos (`liquidacion_id`, `n` únicos), con sus pagos como JSONB.
- Las unidades se sincronizan **solo si la liquidación es la más reciente**: se actualizan
  piso/depto, tipo, propietario y porcentuales, y **nunca** se toca el `codigo_hash` (el propietario no
  pierde su código porque llegó un mes nuevo).

## 7. Cruce de comprobantes

Segundo paso, disparado por `POST /liquidaciones/{id}/comprobantes` con el ZIP que produce
`ct descargar` (manifiesto incluido). Antes de tocar nada se valida el ZIP: sin rutas absolutas ni
`..`, máximo 1000 archivos y 500 MB descomprimidos, todos los archivos citados en el manifiesto
presentes y sin nombres repetidos dentro del mes.

Para cada adjunto, `comprobantes.interpretar()`:

1. Extrae el texto con `pdftotext -layout` y calcula el SHA256 del archivo.
2. Clasifica el documento: `factura`, `pago` (transferencia), `recibo`, `imagen` (sin texto) u `otro`.
3. Parsea emisor y receptor con CUIT **validado por dígito verificador**, tipo y número de factura,
   fecha, importe, destinatario y CUIT de la transferencia, motivo y número de operación.
4. **Lee el QR de ARCA** si está presente (`qr.py`: renderiza la primera página con `pdftoppm -r 200`
   y decodifica con pyzbar). El QR es autoritativo: pisa CUIT del emisor, importe, fecha, numeración
   y CUIT del receptor. Las divergencias con el texto quedan como nota y, si son materiales, como
   hallazgo `qr-texto`. Una imagen ciega con QR legible pasa a ser una factura.

Después `comprobantes.cruzar()` empareja documentos con gastos (por número de factura, fecha e
importe, con desempate explícito antes de declarar atribución incierta) y emite los hallazgos
documentales: pago a un tercero distinto del emisor, factura a nombre de un empleado o propietario,
transferencia declarada sin comprobante propio, importes que no cierran, comprobantes reutilizados,
pagos anteriores a la factura, faltantes, y demás (catálogo completo en [reglas.md](reglas.md)).

Los documentos se guardan en storage (`comprobantes/{periodo}/{archivo}`) con su hash y sus metadatos
—incluido el payload del QR—, y se embeben para la búsqueda semántica si hay API key configurada. Sin
key, o si el embedding falla, el documento queda sin vector y todo lo demás sigue.

## 8. Hallazgos con identidad estable

Todos los hallazgos entran por `upsert_hallazgos(..., origen)`, donde `origen` es `liquidacion`,
`comprobantes` o `historia`. La identidad es `(liquidacion_id, origen, clave)`, con la `clave` que
declara el motor (más refs y título como desempate).

Reglas del upsert, que son las que hacen viable reprocesar un mes cien veces:

- Un hallazgo que vuelve a aparecer **actualiza** severidad, título, evidencia, monto, recomendación y
  refs, pero **jamás** pisa `estado`, `publicado` ni `respuesta_admin`.
- Un hallazgo que deja de aparecer se borra **solo si** sigue `pendiente`, sin publicar, sin respuesta
  y sin ningún evento de historial. Si el auditor ya lo tocó, se conserva.
- Cada origen es un conjunto independiente: reprocesar la liquidación no borra los hallazgos del cruce.

## 9. Reglas históricas

Al final de `procesar()` y otra vez al final de `cruzar_comprobantes()` (recién ahí existen los
documentos del mes) corre `recalcular_historia()`: carga la serie completa de meses previos procesados
y evalúa las tres reglas de `historia.py` — misma factura en dos meses (con la distinción de pago en
cuotas cuando la suma cabe en el total facturado), saltos de precio contra la mediana de los gastos
recurrentes del mes (neutraliza inflación) y concentración de proveedores.

Corre dentro de un savepoint: si falla, se revierte solo ese bloque, se loguea el warning y la ingesta
termina bien. Lo mismo vale para la comparación contra la escritura y para los embeddings. **Ninguna
regla nueva puede hacer perder un mes.**

*Limitación conocida*: si se corrige y reprocesa un mes viejo, los hallazgos históricos de los meses
posteriores no se recalculan solos; se actualizan cuando esos meses se reprocesan o reciben comprobantes.

## 10. Triage

Los hallazgos nacen `pendiente`. El auditor los mueve por el panel (`/panel/hallazgos`) o por la API:

```
pendiente ──▶ preguntado ──▶ respondido ──▶ cerrado
     └────────────────────────────────────▶ descartado
```

- `preguntado`: se le pidió explicación a la administración (con la nota que queda en el historial).
- `respondido`: contestaron; la respuesta se guarda en `respuesta_admin`.
- `cerrado` / `descartado`: cuentan como **resueltos** en el índice.

Cada cambio registra un `hallazgo_evento` con estado anterior, estado nuevo, nota, usuario y timestamp.
Nada se pisa sin dejar rastro.

Publicar un hallazgo (`publicado = true`) es lo que lo hace visible para los propietarios.

## 11. Publicación

`POST /liquidaciones/{id}/publicar` exige estado `procesada` o `publicada` **y** que cuadre. Genera con
el motor el informe HTML autocontenido y el Excel, los sube a storage con clave versionada
(timestamp + uuid, no pisa archivos), registra la fila en `informes`, marca la liquidación como
`publicada` y borra los informes viejos. Antes de confirmar, relee la liquidación: si cambió mientras
se generaba, hace rollback.

Reprocesar una liquidación publicada **retira los informes** (los datos cambiaron; el auditor revisa y
vuelve a publicar). No hay auto-publicación en ningún punto del sistema.

## 12. Consumo

Con el mes publicado:

- **Propietarios** entran con su código y ven `/mi-unidad`: su estado de cuenta, el índice de
  transparencia, los hallazgos publicados y los comprobantes citados en ellos (solo esos).
- **Índice de transparencia**: se recalcula en cada consulta desde gastos + documentos + hallazgos +
  triage. No hay tabla de scores. La vista del propietario se computa **solo sobre lo publicado**, y
  los períodos `no_cuadra` no se filtran ni siquiera como conteo.
- **MCP**: 16 herramientas de solo lectura sobre la misma API, para preguntar en lenguaje natural desde
  Claude o ChatGPT.

## Invariantes del pipeline

1. Si no cuadra al centavo, no hay reglas, no hay gastos y no hay publicación.
2. Ningún hallazgo pierde su triage al reprocesar.
3. Ninguna carga opcional (historia, escritura, embeddings, QR) puede tumbar la ingesta.
4. La sincronización nunca publica.
5. Las cifras se derivan; no hay ningún número guardado que pueda editarse a mano.
6. Los datos privados no entran al repositorio.
