# Endurecer el cruce de comprobantes (ciclo C) — Plan de implementación

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Cinco endurecimientos del cruce calibrados con los casos reales de agosto 2026: pago declarado sin comprobante propio, cuotas (re-etiqueta duplicados), matching robusto con aviso de incertidumbre, importe de factura adjunta vs gasto, y certificador=ejecutor.

**Architecture:** Funciones puras nuevas en `engine/ct/comprobantes.py` llamadas desde `cruzar` (testeables con `Documento`/`Gasto` sintéticos, sin PDFs), un refinamiento en la rama dup-fact de `engine/ct/historia.py` (claves intactas → el triage no se pierde), y una regla nueva en `engine/ct/rules.py`. La API no cambia: ya llama a todo.

**Tech Stack:** Python stdlib, pytest con fixtures reales. Spec: `docs/superpowers/specs/2026-09-06-endurecer-cruce-design.md`.

**Convenciones:** commits en español con trailer `Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>`. Tests motor: `cd /opt/consorcios-transparentes/engine && .venv/bin/python -m pytest -q tests` (hoy: 73 passed). Suite API al final: `cd /opt/consorcios-transparentes/api && .venv/bin/python -m pytest -q` (hoy: 168 passed). El cwd del shell se resetea: rutas absolutas o `cd` en el mismo comando.

**Números reales para tests** (verificados contra la base de producción el 06-09-2026):
- Roth: FC 4182/4183/4191 (mayo), total facturado $7.950.000; cuotas de $2.650.000 en julio (transferencia 13-07 adjunta) y agosto (declarada 21-08, SIN comprobante propio; adjuntos del 29-05 y 13-07).
- Saczewiczyk: FC 7, total $4.552.000 = $2.000.000 (julio, efectivo) + $2.552.000 (agosto, transferencia 12-08 adjunta).
- Peñaloza (gasto 8 de agosto, el primero con factura del fixture): importe $4.333.333,33, factura_importe $9.000.000 — TAMBIÉN cuotas; por eso dos tests existentes de duplicados deben fijar `factura_importe` explícito.

---

### Task 1: Cuotas en `historia_duplicado`

**Files:**
- Modify: `engine/ct/historia.py` (rama dup-fact de `r_duplicado`, líneas ~62-74)
- Test: `engine/tests/test_historia.py`

- [ ] **Step 1: Ajustar los dos tests existentes y agregar los nuevos (fallan)**

En `engine/tests/test_historia.py`, los tests `test_duplicado_por_numero_mismo_importe_es_critico`, `test_duplicado_por_numero_distinto_importe_es_alto` y `test_duplicado_borde_de_un_peso` usan `_gasto_con_factura(agosto)` = Peñaloza, cuyo `factura_importe` ($9M) duplica el importe ($4,33M): con el refinamiento pasarían a MEDIO. En los TRES tests, inmediatamente después de obtener `g`, forzar el caso no-cuota con comentario:

```python
    g.factura_importe = g.importe   # el gasto real es en cuotas (FC $9M); acá probamos el caso no-cuota
```

(en cada test, ANTES de clonar, así el clon hereda el valor). Luego agregar al final del archivo:

```python
# Números reales de agosto 2026 (verificados contra la base el 06-09-2026)
ROTH_CUOTA = 2_650_000.0
ROTH_FACTURADO = 7_950_000.0        # FC 4182 + 4183 + 4191 (mayo 2026)
SACZ_JULIO, SACZ_AGOSTO, SACZ_FACTURADO = 2_000_000.0, 2_552_000.0, 4_552_000.0


def _duplicado_con(liq_importe, prev_importe, factura_importe):
    liq = _agosto()
    g = _gasto_con_factura(liq)
    g.importe, g.factura_importe = liq_importe, factura_importe
    prev = _julio()
    clon = copy.deepcopy(g)
    clon.importe = prev_importe
    prev.gastos.append(clon)
    hs = _hallazgos("historia_duplicado", liq, [prev], Config())
    return next(x for x in hs if x.clave == f"dup-fact|{prev.periodo}|{_norm_nro(g.factura_nro)}")


def test_duplicado_en_cuotas_mismo_importe_es_medio():
    h = _duplicado_con(ROTH_CUOTA, ROTH_CUOTA, ROTH_FACTURADO)
    assert h.severidad == "MEDIO"
    assert "cuotas" in h.titulo


def test_duplicado_en_cuotas_distinto_importe_es_medio():
    h = _duplicado_con(SACZ_AGOSTO, SACZ_JULIO, SACZ_FACTURADO)
    assert h.severidad == "MEDIO"
    assert "cuotas" in h.titulo


def test_duplicado_suma_mayor_al_facturado_sigue_critico():
    h = _duplicado_con(2_650_000.0, 2_650_000.0, 4_000_000.0)   # 5,3M pagados de 4M facturados
    assert h.severidad == "CRÍTICO"


def test_duplicado_sin_factura_importe_mantiene_severidad():
    h = _duplicado_con(1_000_000.0, 1_000_000.0, None)
    assert h.severidad == "CRÍTICO"
```

- [ ] **Step 2: Verificar que fallan**

Run: `cd /opt/consorcios-transparentes/engine && .venv/bin/python -m pytest -q tests/test_historia.py -k cuotas or facturado`
Expected: los 2 de cuotas FALLAN (hoy salen CRÍTICO/ALTO); los otros 2 pasan (comportamiento actual).

- [ ] **Step 3: Implementar**

En `engine/ct/historia.py`, dentro del loop de la rama por número de `r_duplicado`, reemplazar el `out.append(...)` único por:

```python
            mismo = abs(g.importe - gp.importe) <= 1
            cuotas = bool(g.factura_importe) and g.importe + gp.importe <= g.factura_importe + 1
            if cuotas:
                out.append(Hallazgo(
                    "historia_duplicado", "MEDIO", "Respaldo documental",
                    f"Posible pago en cuotas de la factura {g.factura_nro} de {g.proveedor}",
                    f"{periodo_prev}: gasto {gp.n} por {fmt(gp.importe)}; este mes: gasto {g.n} por "
                    f"{fmt(g.importe)}. La suma ({fmt(g.importe + gp.importe)}) no supera el total "
                    f"facturado ({fmt(g.factura_importe)}).",
                    0, "Pedir el comprobante de cada cuota y el detalle del plan de pagos.",
                    [str(g.n)], clave=f"dup-fact|{periodo_prev}|{nro}"))
                continue
            out.append(Hallazgo(
                "historia_duplicado", "CRÍTICO" if mismo else "ALTO", "Respaldo documental",
                ...  # el Hallazgo existente, sin cambios
```

La clave NO cambia: al reprocesar, el hallazgo del triage se actualiza en el lugar.

- [ ] **Step 4: Suite del motor completa**

Run: `cd /opt/consorcios-transparentes/engine && .venv/bin/python -m pytest -q tests`
Expected: 77 passed (73 + 4 nuevos).

- [ ] **Step 5: Commit**

```bash
cd /opt/consorcios-transparentes && git add engine/ct/historia.py engine/tests/test_historia.py && git commit -m "Motor: duplicados que caben en el total facturado son posible pago en cuotas (MEDIO)

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

### Task 2: `chequear_pagos_declarados` (el detector del 21-08 de Roth)

**Files:**
- Modify: `engine/ct/comprobantes.py` (función nueva + llamada en `cruzar`)
- Create: `engine/tests/test_cruce_reglas.py`

- [ ] **Step 1: Tests que fallan**

Crear `engine/tests/test_cruce_reglas.py`:

```python
"""Chequeos puros del cruce, con Gasto/Documento sintéticos (sin PDFs, nunca se saltean).
Números reales de agosto 2026: cuotas de Roth (FC de mayo por $7.950.000, cuota de agosto
declarada el 21-08 sin comprobante propio) y saldo de Saczewiczyk."""
from datetime import date

from ct.comprobantes import (Documento, chequear_pagos_declarados)
from ct.model import Gasto, Pago


def _gasto(n=25, proveedor="MARIO LEONARDO ROTH", importe=2_650_000.0, pagos=(), **kw):
    g = Gasto(n=n, categoria="ABONOS Y SERVICIOS", proveedor=proveedor,
              concepto="Cambio de serpentina", columna="A", importe=importe, **kw)
    g.pagos = list(pagos)
    return g


def _pago_doc(fecha, importe, archivo="transf.pdf"):
    d = Documento(archivo=archivo, gasto_n=25, tipo="pago")
    d.fecha, d.importe = fecha, importe
    return d


def test_pago_declarado_sin_comprobante_dispara():
    # Roth agosto: declara transferencia 21-08; los adjuntos son del 29-05 y 13-07
    g = _gasto(pagos=[Pago(date(2026, 8, 21), 2_650_000.0, "BANCO", "Transferencia")])
    docs = [_pago_doc(date(2026, 5, 29), 2_650_000.0), _pago_doc(date(2026, 7, 13), 2_650_000.0)]
    hs = chequear_pagos_declarados(g, docs)
    assert len(hs) == 1
    h = hs[0]
    assert h.severidad == "ALTO"
    assert h.clave == "pago-sin-comp|2026-08-21"
    assert "2026-05-29" in h.evidencia and "2026-07-13" in h.evidencia


def test_pago_declarado_con_comprobante_no_dispara():
    # Roth julio: declara 13-07 y la transferencia del 13-07 está adjunta
    g = _gasto(n=27, pagos=[Pago(date(2026, 7, 13), 2_650_000.0, "BANCO", "Transferencia")])
    docs = [_pago_doc(date(2026, 5, 29), 2_650_000.0), _pago_doc(date(2026, 7, 13), 2_650_000.0)]
    assert chequear_pagos_declarados(g, docs) == []


def test_transferencia_combinada_por_mas_importe_no_dispara():
    # una sola transferencia paga varios gastos: el doc trae el total, misma fecha
    g = _gasto(importe=100_000.0, pagos=[Pago(date(2026, 8, 10), 100_000.0, "BANCO", "Transferencia")])
    assert chequear_pagos_declarados(g, [_pago_doc(date(2026, 8, 10), 350_000.0)]) == []


def test_efectivo_y_debito_no_se_evaluan():
    g = _gasto(pagos=[Pago(date(2026, 8, 21), 500_000.0, "CAJA", "Efectivo"),
                      Pago(date(2026, 8, 21), 500_000.0, "BANCO", "Débito automático")])
    assert chequear_pagos_declarados(g, [_pago_doc(date(2026, 1, 1), 1.0)]) == []


def test_sin_ningun_comprobante_no_dispara():
    # eso ya lo cubre la regla existente de respaldo documental
    g = _gasto(pagos=[Pago(date(2026, 8, 21), 2_650_000.0, "BANCO", "Transferencia")])
    assert chequear_pagos_declarados(g, []) == []


def test_tolerancia_de_fecha_tres_dias():
    g = _gasto(pagos=[Pago(date(2026, 8, 21), 2_650_000.0, "BANCO", "Transferencia")])
    assert chequear_pagos_declarados(g, [_pago_doc(date(2026, 8, 18), 2_650_000.0)]) == []
    assert len(chequear_pagos_declarados(g, [_pago_doc(date(2026, 8, 17), 2_650_000.0)])) == 1
```

- [ ] **Step 2: Verificar que fallan**

Run: `cd /opt/consorcios-transparentes/engine && .venv/bin/python -m pytest -q tests/test_cruce_reglas.py`
Expected: FAIL con ImportError (`chequear_pagos_declarados` no existe).

- [ ] **Step 3: Implementar**

En `engine/ct/comprobantes.py`, antes de la sección `# --- cruce` agregar:

```python
DIAS_TOLERANCIA_PAGO = 3


def chequear_pagos_declarados(g: Gasto, pagos_docs: list[Documento]) -> list[Hallazgo]:
    """La liquidación declara una transferencia pero ningún comprobante adjunto corresponde a
    ESE pago (caso real: cuotas viejas recicladas como respaldo de la cuota nueva). El doc
    puede traer un importe mayor (una transferencia que paga varios gastos): alcanza con que
    la fecha coincida (±3 días) y el importe del doc cubra el pago declarado."""
    if not pagos_docs:
        return []      # sin ningún comprobante lo cubre la regla de respaldo documental
    out: list[Hallazgo] = []
    for p in g.pagos:
        if not p.fecha or p.caja.upper() == "CAJA" or not p.forma.lower().startswith("transf"):
            continue
        ok = any(d.fecha and abs((d.fecha - p.fecha).days) <= DIAS_TOLERANCIA_PAGO
                 and d.importe is not None and d.importe >= p.importe - 1
                 for d in pagos_docs)
        if ok:
            continue
        fechas = ", ".join(sorted({str(d.fecha) for d in pagos_docs if d.fecha})) or "sin fecha legible"
        out.append(Hallazgo(
            "comprobantes", "ALTO", "Control de pagos",
            f"{g.proveedor}: la transferencia declarada el {p.fecha} por {fmt(p.importe)} no tiene comprobante adjunto",
            f"Los comprobantes de pago adjuntos son de otras fechas: {fechas}.",
            p.importe, "Pedir el comprobante de esa transferencia.",
            [str(g.n)], clave=f"pago-sin-comp|{p.fecha.isoformat()}"))
    return out
```

Y en `cruzar`, dentro del bloque por-gasto (después de calcular `pagos` — los docs tipo "pago" sin créditos — y de los chequeos existentes de pagos), agregar:

```python
        hs.extend(chequear_pagos_declarados(g, pagos))
```

- [ ] **Step 4: Verificar**

Run: `cd /opt/consorcios-transparentes/engine && .venv/bin/python -m pytest -q tests`
Expected: 83 passed (77 + 6). Las pruebas de cruce con PDFs reales (si la carpeta privada está) no deben romperse; si alguna se rompe porque la regla nueva dispara sobre datos reales, verificar A MANO si el hallazgo es genuino antes de tocar nada, y reportarlo.

- [ ] **Step 5: Commit**

```bash
cd /opt/consorcios-transparentes && git add engine/ct/comprobantes.py engine/tests/test_cruce_reglas.py && git commit -m "Motor: pago declarado sin comprobante propio (transferencias con fecha que no coincide)

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

### Task 3: `chequear_importe_factura`

**Files:**
- Modify: `engine/ct/comprobantes.py`
- Test: `engine/tests/test_cruce_reglas.py`

- [ ] **Step 1: Tests que fallan**

Agregar a `engine/tests/test_cruce_reglas.py`:

```python
def _factura_doc(importe, archivo="fact.pdf"):
    d = Documento(archivo=archivo, gasto_n=25, tipo="factura")
    d.importe = importe
    return d


def test_facturas_roth_cierran_por_la_suma():
    # tres facturas (2,9M + 4,9M + 0,15M = 7,95M) contra un gasto de 2,65M con facturado 7,95M
    g = _gasto(importe=2_650_000.0, factura_importe=7_950_000.0)
    facts = [_factura_doc(2_900_000.0), _factura_doc(4_900_000.0), _factura_doc(150_000.0)]
    assert chequear_importe_factura(g, facts, total_proveedor_mes=2_740_000.0) == []


def test_factura_que_no_cierra_dispara():
    g = _gasto(importe=300_000.0, factura_importe=None)
    hs = chequear_importe_factura(g, [_factura_doc(500_000.0)], total_proveedor_mes=300_000.0)
    assert len(hs) == 1
    assert hs[0].severidad == "MEDIO"
    assert hs[0].clave == "imp-fact"


def test_factura_igual_al_gasto_no_dispara():
    g = _gasto(importe=300_000.0)
    assert chequear_importe_factura(g, [_factura_doc(300_000.0)], 300_000.0) == []


def test_factura_igual_al_total_del_proveedor_no_dispara():
    g = _gasto(importe=300_000.0)
    assert chequear_importe_factura(g, [_factura_doc(750_000.0)], total_proveedor_mes=750_000.0) == []


def test_factura_sin_importe_legible_no_cuenta():
    g = _gasto(importe=300_000.0)
    assert chequear_importe_factura(g, [_factura_doc(None)], 300_000.0) == []
```

Actualizar el import del archivo: `from ct.comprobantes import (Documento, chequear_importe_factura, chequear_pagos_declarados)`.

- [ ] **Step 2: Verificar que fallan** — mismo comando, ImportError.

- [ ] **Step 3: Implementar**

En `engine/ct/comprobantes.py`, junto a la función de la Task 2:

```python
def _cerca(a: float, b: float) -> bool:
    return abs(a - b) <= max(1.0, 0.02 * max(abs(a), abs(b)))


def chequear_importe_factura(g: Gasto, facts: list[Documento], total_proveedor_mes: float) -> list[Hallazgo]:
    """El importe leído de las facturas adjuntas tiene que cerrar contra algo: el gasto, el
    total facturado según la liquidación (caso cuotas) o el total del proveedor en el mes
    (una factura que cubre varias líneas). Si nada cierra, hay que mirarlo."""
    importes = [f.importe for f in facts if f.importe]
    if not importes:
        return []
    suma = round(sum(importes), 2)
    objetivos = [g.importe, total_proveedor_mes] + ([g.factura_importe] if g.factura_importe else [])
    if any(_cerca(x, obj) for x in importes + [suma] for obj in objetivos):
        return []
    return [Hallazgo(
        "comprobantes", "MEDIO", "Respaldo documental",
        f"{g.proveedor}: las facturas adjuntas suman {fmt(suma)} pero el gasto es {fmt(g.importe)}",
        f"Importes de las facturas adjuntas: {', '.join(fmt(x) for x in importes)}."
        + (f" Total facturado según la liquidación: {fmt(g.factura_importe)}." if g.factura_importe else ""),
        abs(suma - g.importe), "Cotejar las facturas con el gasto liquidado.",
        [str(g.n)], clave="imp-fact")]
```

Y en `cruzar`, en el bloque por-gasto (junto a la llamada de la Task 2):

```python
        total_prov = round(sum(x.importe for x in liq.gastos if x.proveedor == g.proveedor), 2)
        hs.extend(chequear_importe_factura(g, facts, total_prov))
```

- [ ] **Step 4: Suite del motor** — Expected: 88 passed. Mismo criterio que Task 2 si dispara sobre PDFs reales.

- [ ] **Step 5: Commit**

```bash
cd /opt/consorcios-transparentes && git add engine/ct/comprobantes.py engine/tests/test_cruce_reglas.py && git commit -m "Motor: el importe de las facturas adjuntas tiene que cerrar contra el gasto o el facturado

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

### Task 4: `_match_gasto` robusto + hallazgo de atribución incierta

**Files:**
- Modify: `engine/ct/comprobantes.py` (`_match_gasto` y su único caller en `cruzar`)
- Test: `engine/tests/test_cruce_reglas.py`

- [ ] **Step 1: Tests que fallan**

Agregar a `engine/tests/test_cruce_reglas.py` (imports: `from ct.comprobantes import ItemManifiesto, _match_gasto` y `from ct.model import Liquidacion`):

```python
def _liq_con(*gastos):
    liq = Liquidacion(sistema="test", periodo="Agosto 2026")
    liq.gastos = list(gastos)
    return liq


def test_match_unico_por_importe_es_certero():
    liq = _liq_con(_gasto(n=1, importe=100.0))
    g, certero = _match_gasto(ItemManifiesto(None, "X", 100.0, None, []), liq)
    assert g.n == 1 and certero


def test_match_empatado_desempata_por_factura():
    liq = _liq_con(_gasto(n=1, importe=100.0, factura_nro="0001-11"),
                   _gasto(n=2, importe=100.0, factura_nro="0001-22"))
    g, certero = _match_gasto(ItemManifiesto(None, "X", 100.0, "0001-22", []), liq)
    assert g.n == 2 and certero


def test_match_empatado_desempata_por_fecha():
    g1 = _gasto(n=1, importe=100.0, pagos=[Pago(date(2026, 8, 1), 100.0, "BANCO", "Transferencia")])
    g2 = _gasto(n=2, importe=100.0, pagos=[Pago(date(2026, 8, 9), 100.0, "BANCO", "Transferencia")])
    g, certero = _match_gasto(ItemManifiesto(date(2026, 8, 9), "X", 100.0, None, []), _liq_con(g1, g2))
    assert g.n == 2 and certero


def test_match_irresoluble_devuelve_primero_sin_certeza():
    liq = _liq_con(_gasto(n=1, importe=100.0), _gasto(n=2, importe=100.0))
    g, certero = _match_gasto(ItemManifiesto(None, "X", 100.0, None, []), liq)
    assert g.n == 1 and not certero


def test_match_sin_candidatos():
    g, certero = _match_gasto(ItemManifiesto(None, "X", 999.0, None, []), _liq_con(_gasto(n=1, importe=100.0)))
    assert g is None and certero
```

- [ ] **Step 2: Verificar que fallan** — hoy `_match_gasto` devuelve un solo valor: TypeError al desempaquetar.

- [ ] **Step 3: Implementar**

Reemplazar `_match_gasto` en `engine/ct/comprobantes.py`:

```python
def _match_gasto(item: ItemManifiesto, liq: Liquidacion) -> tuple[Optional[Gasto], bool]:
    """(gasto, certero). certero=False cuando varios gastos comparten el importe y ni el número
    de factura ni la fecha desempatan; se elige el primero para no perder el cruce, pero la
    incertidumbre se hace visible (nota en el doc + hallazgo agregado)."""
    cands = [g for g in liq.gastos if abs(g.importe - item.importe) < 0.01]
    if len(cands) == 1:
        return cands[0], True
    if item.factura_nro:
        c = [g for g in cands if g.factura_nro and g.factura_nro.replace(" ", "") == item.factura_nro.replace(" ", "")]
        if len(c) == 1:
            return c[0], True
    if item.fecha:
        c = [g for g in cands if g.fecha_pago == item.fecha]
        if len(c) == 1:
            return c[0], True
    return (cands[0], False) if cands else (None, True)
```

En `cruzar`, adaptar el caller: donde hoy dice `g = _match_gasto(it, liq)`, pasar a:

```python
        g, certero = _match_gasto(it, liq)
```

acumulando `inciertos: list[int] = []` (declararla junto a `matched`) con `if g and not certero: inciertos.append(g.n)`, y al interpretar cada adjunto de un item incierto agregar la nota:

```python
            if g and not certero:
                d.notas.append("Atribución incierta: varios gastos del mes comparten este importe.")
```

(después de `d = interpretar(...)`). Al final de `cruzar` (antes del dedupe), emitir el agregado:

```python
    if inciertos:
        u = sorted(set(inciertos))
        names = [next((x.proveedor for x in liq.gastos if x.n == n), str(n)) for n in u]
        hs.append(Hallazgo("comprobantes", "BAJO", "Calidad de datos",
                           f"{len(u)} gasto(s) con comprobantes atribuidos con incertidumbre",
                           f"Varios gastos del mes comparten importe; se atribuyó al primero. Gastos: {', '.join(names)}.",
                           0, "Verificar a mano a qué gasto corresponde cada comprobante.",
                           [str(n) for n in u], clave="atribucion-incierta"))
```

- [ ] **Step 4: Suite del motor completa** — Expected: 93 passed. Si las pruebas con PDFs reales de la carpeta privada cambian de conteo porque ahora aparece el hallazgo BAJO agregado, ajustar esas pruebas para filtrar por lo que verifican (reportarlo), nunca aflojar la regla.

- [ ] **Step 5: Commit**

```bash
cd /opt/consorcios-transparentes && git add engine/ct/comprobantes.py engine/tests/test_cruce_reglas.py && git commit -m "Motor: matching de comprobantes con desempate por factura y aviso de atribución incierta

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

### Task 5: Regla `certificador` (certificador = ejecutor)

**Files:**
- Modify: `engine/ct/rules.py` (regla nueva al final, antes de `evaluar`)
- Create: `engine/tests/test_rules_certificador.py`

- [ ] **Step 1: Tests que fallan**

Crear `engine/tests/test_rules_certificador.py`:

```python
"""Certificador = ejecutor, contra los fixtures reales: Roth certifica los equipos térmicos
(gasto 26 en julio, 24 en agosto) y además ejecuta reparaciones (27 en julio, 25 en agosto)."""
import pathlib

from ct.redconar import parse_text
from ct.rules import Config, evaluar

FIXTURES = pathlib.Path(__file__).resolve().parent / "fixtures"


def _hallazgos(fixture):
    liq = parse_text((FIXTURES / fixture).read_text(encoding="utf-8"))
    return liq, [h for h in evaluar(liq, None, Config()) if h.regla == "certificador"]


def test_roth_certifica_y_ejecuta_en_julio():
    liq, hs = _hallazgos("redconar_202607.txt")
    h = next(x for x in hs if "ROTH" in x.titulo.upper())
    assert h.severidad == "MEDIO"
    assert {"26", "27"} <= set(h.refs)
    assert h.clave.startswith("cert-ejecutor|")


def test_roth_certifica_y_ejecuta_en_agosto():
    liq, hs = _hallazgos("redconar_202608.txt")
    h = next(x for x in hs if "ROTH" in x.titulo.upper())
    assert {"24", "25"} <= set(h.refs)


def test_sin_certificacion_no_dispara():
    liq, hs = _hallazgos("redconar_202607.txt")
    for g in liq.gastos:
        g.concepto = g.concepto.replace("CERTIFICACION", "REVISION")
    hs2 = [h for h in evaluar(liq, None, Config()) if h.regla == "certificador"]
    assert [h for h in hs2 if "ROTH" in h.titulo.upper()] == []
```

- [ ] **Step 2: Verificar que fallan** — `cd /opt/consorcios-transparentes/engine && .venv/bin/python -m pytest -q tests/test_rules_certificador.py` → StopIteration (la regla no existe).

- [ ] **Step 3: Implementar**

En `engine/ct/rules.py`, después de la última regla de mercado y antes de `evaluar`:

```python
# ------------------------------------------------------------------ certificador = ejecutor
RE_CERTIFICA = re.compile(r"certificaci[oó]n|certificado", re.I)
RE_EJECUTA = re.compile(r"reparaci[oó]n|cambio de|instalaci[oó]n|coloca|obra de", re.I)


@rule("certificador")
def r_certificador(liq, prev, cfg):
    """El mismo proveedor certifica instalaciones del edificio y además ejecuta trabajos:
    conflicto de interés potencial (quien controla no puede ser quien cobra por arreglar)."""
    out = []
    grupos: dict[str, list[Gasto]] = {}
    for g in liq.gastos:
        clave = re.sub(r"[^a-z0-9]", "", g.proveedor.lower())
        if clave:
            grupos.setdefault(clave, []).append(g)
    for clave, gs in sorted(grupos.items()):
        certs = [g for g in gs if RE_CERTIFICA.search(g.concepto or "")]
        ns_cert = {g.n for g in certs}
        obras = [g for g in gs if g.n not in ns_cert and RE_EJECUTA.search(g.concepto or "")]
        if not certs or not obras:
            continue
        out.append(Hallazgo(
            "certificador", "MEDIO", "Obras / contratación",
            f"{gs[0].proveedor} certifica y también ejecuta trabajos en el edificio",
            f"Certifica: {certs[0].concepto[:90]}. Ejecuta: {obras[0].concepto[:90]}.",
            round(sum(g.importe for g in obras), 2),
            "Conflicto de interés potencial: pedir certificación independiente para los trabajos que ejecuta.",
            [str(g.n) for g in certs + obras], clave=f"cert-ejecutor|{clave}"))
    return out
```

- [ ] **Step 4: Suite del motor completa** — Expected: 96 passed. OJO: `test_rules_claves.py` y otros tests existentes que cuenten hallazgos totales pueden verse afectados por la regla nueva sobre los fixtures reales; si alguno cuenta hallazgos de OTRA regla no cambia nada, si alguno cuenta el total, revisar y ajustar el test con comentario (reportarlo).

- [ ] **Step 5: Commit**

```bash
cd /opt/consorcios-transparentes && git add engine/ct/rules.py engine/tests/test_rules_certificador.py && git commit -m "Motor: regla certificador=ejecutor (conflicto de interés potencial en obras)

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

### Task 6: Suite API + docs

**Files:**
- Modify: `docs/reglas.md`, `docs/ESTADO.md`

- [ ] **Step 1: Suite completa de la API (sin cambios de código)**

Run: `cd /opt/consorcios-transparentes/api && .venv/bin/python -m pytest -q`
Expected: 168 passed. La API llama a `cruzar`/`evaluar`/`evaluar_historia` sin conocer las reglas nuevas. Si algún test de la API cuenta hallazgos y cambia por las reglas nuevas, mismo criterio: ajustar el test con comentario y reportar.

- [ ] **Step 2: Actualizar `docs/reglas.md`**

Leer el archivo y, respetando su formato: agregar las reglas nuevas del cruce (pago declarado sin comprobante, importe de factura que no cierra, atribución incierta), el refinamiento de cuotas en `historia_duplicado`, y la regla `certificador`; marcar resuelto el pendiente "conflicto de interés certificador = ejecutor"; anotar como pendiente futuro la correlatividad de numeración por emisor (retomar con 6+ meses de datos).

- [ ] **Step 3: Actualizar `docs/ESTADO.md`**

Ciclo C hecho (06-09-2026) con resumen de dos líneas y referencia a la spec; pendientes quedan B (prorrateo vs escritura) → D (OCR). Nota: "pendiente de deploy + reproceso de julio y agosto (re-etiqueta los duplicados como cuotas y agrega los hallazgos nuevos)".

- [ ] **Step 4: Commit**

```bash
cd /opt/consorcios-transparentes && git add docs/reglas.md docs/ESTADO.md docs/superpowers/plans/2026-09-06-endurecer-cruce.md && git commit -m "Docs: catálogo y estado con el ciclo C (cruce endurecido)

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

### Verificación final (la corre el orquestador)

- [ ] Suites completas motor + API en verde; revisión final de todo el rango.
- [ ] Deploy solo con confirmación del usuario: rebuild api/worker/mcp, reprocesar julio y agosto, y verificar en producción: (a) los dup de Roth/Saczewiczyk re-etiquetados como "posible pago en cuotas" MEDIO conservando estado del triage; (b) hallazgo nuevo ALTO "transferencia declarada el 2026-08-21 sin comprobante" en el gasto 25 de agosto; (c) certificador=ejecutor para Roth en ambos meses; (d) ningún hallazgo espurio nuevo (revisar el listado completo).
