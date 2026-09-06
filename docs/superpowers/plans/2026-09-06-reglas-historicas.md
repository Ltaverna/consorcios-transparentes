# Reglas históricas — Plan de implementación

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Hallazgos que comparan la liquidación actual contra toda su serie histórica: duplicados entre meses (por número de factura y por hash de comprobante), saltos de gastos recurrentes neutralizados por inflación, y concentración de proveedores.

**Architecture:** Módulo nuevo `engine/ct/historia.py` sin dependencias de base (`evaluar_historia(liq, serie, cfg, docs_actual, docs_previos)`); la API arma la serie re-parseando archivos guardados (generalización de `cargar_anterior`) y recalcula con `upsert_hallazgos(origen="historia")` de forma idempotente en `procesar()` y tras `cruzar_comprobantes()`, dentro de un savepoint para que una falla jamás tire la ingesta.

**Tech Stack:** Python stdlib (motor), pytest con fixtures reales `redconar_202607/202608.txt`, FastAPI+SQLAlchemy (api). Spec: `docs/superpowers/specs/2026-09-06-reglas-historicas-design.md`.

**Convenciones del repo:** commits en español con trailer `Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>`. Tests: `cd /opt/consorcios-transparentes/engine && .venv/bin/python -m pytest -q tests` y `cd /opt/consorcios-transparentes/api && .venv/bin/python -m pytest -q`. El cwd del shell se resetea entre comandos: usar siempre rutas absolutas o `cd` dentro del mismo comando.

**Nota de la spec refinada acá:** la spec decía un solo `docs_por_periodo` "incluido el actual"; el motor no puede saber cuál clave es el período actual (su `liq.periodo` es texto tipo "Agosto 2026" y las claves son ISO), así que la interfaz se parte en `docs_actual` (lista) y `docs_previos` (dict por período ISO). Mismo contenido, sin ambigüedad.

---

### Task 1: Campos nuevos de Config

**Files:**
- Modify: `engine/ct/rules.py` (dataclass `Config`, después de `abono_limpieza_ref`)
- Test: `engine/tests/test_rules_config.py`

- [ ] **Step 1: Test que falla**

Agregar al final de `engine/tests/test_rules_config.py`:

```python
def test_config_trae_umbrales_historicos_con_default():
    cfg = Config()
    assert cfg.salto_puntos_medio == 0.25
    assert cfg.salto_puntos_alto == 0.50
    assert cfg.salto_importe_min == 50_000
    assert cfg.concentracion_proveedor == 0.25
```

- [ ] **Step 2: Verificar que falla**

Run: `cd /opt/consorcios-transparentes/engine && .venv/bin/python -m pytest -q tests/test_rules_config.py -k historicos`
Expected: FAIL con `AttributeError: ... 'salto_puntos_medio'`

- [ ] **Step 3: Implementar**

En `engine/ct/rules.py`, dentro de `Config`, después de `abono_limpieza_ref: float = 0.0`:

```python
    # --- reglas históricas (serie de meses previos) ---
    salto_puntos_medio: float = 0.25       # exceso sobre la mediana de variaciones del mes
    salto_puntos_alto: float = 0.50
    salto_importe_min: float = 50_000      # gastos chicos no ameritan hallazgo
    concentracion_proveedor: float = 0.25  # share de un proveedor sobre el gasto sin sueldos
```

- [ ] **Step 4: Verificar que pasa (y que nada se rompió)**

Run: `cd /opt/consorcios-transparentes/engine && .venv/bin/python -m pytest -q tests`
Expected: todo verde (los nuevos campos entran solos al panel: la API expone umbrales con `fields(Config)` y el form del front itera las claves del default).

- [ ] **Step 5: Commit**

```bash
cd /opt/consorcios-transparentes && git add engine/ct/rules.py engine/tests/test_rules_config.py && git commit -m "Config: umbrales de las reglas históricas (salto y concentración)

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

### Task 2: Módulo `historia.py` — esqueleto y helpers

**Files:**
- Create: `engine/ct/historia.py`
- Create: `engine/tests/test_historia.py`

- [ ] **Step 1: Tests que fallan**

Crear `engine/tests/test_historia.py`:

```python
"""Reglas históricas contra la serie real (julio y agosto 2026) y variantes sintéticas.

La serie real disponible en fixtures tiene UN solo período previo (julio) para agosto:
`salto` y `concentracion` exigen ≥2 previos, así que sobre la serie real se verifica que NO
corren; para ejercitarlas se derivan períodos sintéticos copiando el parse real."""
import copy
import pathlib

from ct.historia import _excluida, _norm, _norm_nro, evaluar_historia
from ct.redconar import parse_text
from ct.rules import Config

FIXTURES = pathlib.Path(__file__).resolve().parent / "fixtures"


def _parse(nombre):
    return parse_text((FIXTURES / nombre).read_text(encoding="utf-8"))


def _julio():
    return _parse("redconar_202607.txt")


def _agosto():
    return _parse("redconar_202608.txt")


def _hallazgos(regla, *args, **kw):
    return [h for h in evaluar_historia(*args, **kw) if h.regla == regla]


def test_norm_nro():
    assert _norm_nro("0003-00001234") == "3-1234"
    assert _norm_nro("0001-00000002") is None   # menos de 3 dígitos significativos: relleno
    assert _norm_nro("0000-00000000") is None
    assert _norm_nro("s/n") is None
    assert _norm_nro(None) is None


def test_excluida():
    assert _excluida("SUELDOS Y CARGAS SOCIALES")
    assert _excluida("Cargas sociales")
    assert not _excluida("ABONOS DE MANTENIMIENTO")


def test_serie_vacia_no_emite_nada():
    assert evaluar_historia(_agosto(), [], Config()) == []
```

- [ ] **Step 2: Verificar que fallan**

Run: `cd /opt/consorcios-transparentes/engine && .venv/bin/python -m pytest -q tests/test_historia.py`
Expected: FAIL con `ModuleNotFoundError: No module named 'ct.historia'`

- [ ] **Step 3: Implementar**

Crear `engine/ct/historia.py`:

```python
"""Reglas históricas: la liquidación actual contra la serie de meses previos.

`evaluar_historia` devuelve hallazgos que SIEMPRE involucran a `liq` (el mes actual): un
duplicado julio↔agosto cuelga de agosto y no se re-emite al procesar septiembre. `serie` va
ordenada por período ascendente y puede ser vacía. Sin dependencias de base de datos: los
comprobantes llegan como tuplas `(gasto_n, hash, archivo)` — `docs_actual` es la lista del mes
y `docs_previos` un dict por período; si faltan, el chequeo por hash simplemente no corre.
"""
from __future__ import annotations
import re
from statistics import median
from typing import Callable, Optional

from .model import Liquidacion
from .rules import Config, Hallazgo, fmt, pct

Doc = tuple[Optional[int], str, str]    # (gasto_n, hash, archivo)
RuleH = Callable[..., list[Hallazgo]]
RULES_H: list[tuple[str, RuleH]] = []


def rule_h(name: str):
    def deco(fn: RuleH) -> RuleH:
        RULES_H.append((name, fn))
        return fn
    return deco


def _norm(s: str) -> str:
    return re.sub(r"[^a-z0-9]", "", (s or "").lower())


def _excluida(categoria: str) -> bool:
    """Sueldos y cargas sociales quedan afuera de salto/concentración: el SAC de junio y
    diciembre y los aportes distorsionan, y ya los cubren sueldo_mercado y costos."""
    c = categoria.upper()
    return "SUELDO" in c or "CARGA" in c


def _norm_nro(nro: Optional[str]) -> Optional[str]:
    """'0003-00001234' -> '3-1234'. None si no llega a 3 dígitos significativos (relleno)."""
    partes = re.findall(r"\d+", nro or "")
    if not partes:
        return None
    if int("".join(str(int(p)) for p in partes)) < 100:
        return None
    return "-".join(str(int(p)) for p in partes)


def evaluar_historia(liq: Liquidacion, serie: list[Liquidacion], cfg: Optional[Config] = None,
                     docs_actual: Optional[list[Doc]] = None,
                     docs_previos: Optional[dict[str, list[Doc]]] = None) -> list[Hallazgo]:
    cfg = cfg or Config()
    out: list[Hallazgo] = []
    for _, fn in RULES_H:
        out.extend(fn(liq, serie, cfg, docs_actual, docs_previos))
    return out
```

- [ ] **Step 4: Verificar que pasan**

Run: `cd /opt/consorcios-transparentes/engine && .venv/bin/python -m pytest -q tests/test_historia.py`
Expected: PASS (3 tests)

- [ ] **Step 5: Commit**

```bash
cd /opt/consorcios-transparentes && git add engine/ct/historia.py engine/tests/test_historia.py && git commit -m "Motor: módulo de reglas históricas (esqueleto y helpers)

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

### Task 3: Regla `historia_duplicado`

**Files:**
- Modify: `engine/ct/historia.py` (agregar al final)
- Test: `engine/tests/test_historia.py`

- [ ] **Step 1: Tests que fallan**

Agregar a `engine/tests/test_historia.py`:

```python
def _gasto_con_factura(liq):
    return next(g for g in liq.gastos if _norm_nro(g.factura_nro))


def test_duplicado_por_numero_mismo_importe_es_critico():
    liq = _agosto()
    g = _gasto_con_factura(liq)
    prev = _julio()
    prev.gastos.append(copy.deepcopy(g))    # la misma factura ya figuraba el mes pasado
    hs = _hallazgos("historia_duplicado", liq, [prev], Config())
    h = next(x for x in hs if x.clave == f"dup-fact|{prev.periodo}|{_norm_nro(g.factura_nro)}")
    assert h.severidad == "CRÍTICO"
    assert str(g.n) in h.refs
    assert prev.periodo in h.titulo or prev.periodo in h.evidencia


def test_duplicado_por_numero_distinto_importe_es_alto():
    liq = _agosto()
    g = _gasto_con_factura(liq)
    prev = _julio()
    clon = copy.deepcopy(g)
    clon.importe = round(g.importe + 500, 2)
    prev.gastos.append(clon)
    hs = _hallazgos("historia_duplicado", liq, [prev], Config())
    h = next(x for x in hs if x.clave == f"dup-fact|{prev.periodo}|{_norm_nro(g.factura_nro)}")
    assert h.severidad == "ALTO"


def test_duplicado_por_hash_entre_meses():
    hs = _hallazgos("historia_duplicado", _agosto(), [_julio()], Config(),
                    docs_actual=[(12, "abc123def456", "factura.pdf")],
                    docs_previos={"2026-07": [(3, "abc123def456", "factura.pdf")]})
    dup = [h for h in hs if h.clave.startswith("dup-hash|")]
    assert len(dup) == 1
    assert dup[0].severidad == "ALTO"
    assert dup[0].clave == "dup-hash|2026-07|abc123def456"
    assert dup[0].refs == ["12"]


def test_sin_docs_el_chequeo_de_hash_no_corre():
    hs = _hallazgos("historia_duplicado", _agosto(), [_julio()], Config(),
                    docs_actual=[(12, "abc", "f.pdf")], docs_previos=None)
    assert [h for h in hs if h.clave.startswith("dup-hash|")] == []
```

- [ ] **Step 2: Verificar que fallan**

Run: `cd /opt/consorcios-transparentes/engine && .venv/bin/python -m pytest -q tests/test_historia.py -k duplicado`
Expected: FAIL (la regla no existe, `_hallazgos` devuelve listas vacías → `StopIteration`/asserts)

- [ ] **Step 3: Implementar**

Agregar al final de `engine/ct/historia.py`:

```python
# ------------------------------------------------------------- duplicados entre meses
@rule_h("historia_duplicado")
def r_duplicado(liq, serie, cfg, docs_actual, docs_previos):
    out: list[Hallazgo] = []
    previos: dict[tuple[str, str], list] = {}
    for pl in serie:
        for g in pl.gastos:
            nro = _norm_nro(g.factura_nro)
            if nro:
                previos.setdefault((_norm(g.proveedor), nro), []).append((pl.periodo, g))
    for g in liq.gastos:
        nro = _norm_nro(g.factura_nro)
        for periodo_prev, gp in (previos.get((_norm(g.proveedor), nro), []) if nro else []):
            mismo = abs(g.importe - gp.importe) <= 1
            out.append(Hallazgo(
                "historia_duplicado", "CRÍTICO" if mismo else "ALTO", "Respaldo documental",
                f"La factura {g.factura_nro} de {g.proveedor} ya figuraba en la liquidación de {periodo_prev}"
                + (" por el mismo importe" if mismo else ""),
                f"{periodo_prev}: gasto {gp.n} por {fmt(gp.importe)}; este mes: gasto {g.n} por {fmt(g.importe)}.",
                g.importe if mismo else 0,
                "Verificar que la misma factura no se haya pagado dos veces." if mismo
                else "Pedir la factura de este mes: el número repetido puede ser un error de carga.",
                [str(g.n)], clave=f"dup-fact|{periodo_prev}|{nro}"))
    if docs_actual and docs_previos:
        hprev: dict[str, tuple[str, Optional[int]]] = {}
        for periodo in sorted(docs_previos):
            for gn, h, _archivo in docs_previos[periodo]:
                if h and h not in hprev:
                    hprev[h] = (periodo, gn)
        vistos: set[str] = set()
        for gn, h, archivo in docs_actual:
            if not h or h not in hprev:
                continue
            periodo_prev, gn_prev = hprev[h]
            clave = f"dup-hash|{periodo_prev}|{h}"
            if clave in vistos:
                continue
            vistos.add(clave)
            out.append(Hallazgo(
                "historia_duplicado", "ALTO", "Respaldo documental",
                f"El comprobante {archivo} ya respaldaba un gasto de {periodo_prev}",
                f"El mismo archivo está adjunto al gasto {gn_prev if gn_prev is not None else '?'} de "
                f"{periodo_prev} y al gasto {gn if gn is not None else '?'} de este mes.",
                0, "Verificar que un mismo comprobante no respalde dos pagos distintos.",
                [str(gn)] if gn is not None else [], clave=clave))
    return out
```

- [ ] **Step 4: Verificar que pasan**

Run: `cd /opt/consorcios-transparentes/engine && .venv/bin/python -m pytest -q tests/test_historia.py`
Expected: PASS. Si `test_serie_vacia_no_emite_nada` u otro fallara porque julio y agosto REALES comparten un número de factura del mismo proveedor, eso es un hallazgo genuino: verificarlo a mano en los fixtures y ajustar el test para filtrar por la clave esperada (no relajar la regla).

- [ ] **Step 5: Commit**

```bash
cd /opt/consorcios-transparentes && git add engine/ct/historia.py engine/tests/test_historia.py && git commit -m "Motor: historia_duplicado — la misma factura o el mismo comprobante en dos meses

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

### Task 4: Regla `historia_salto`

**Files:**
- Modify: `engine/ct/historia.py`
- Test: `engine/tests/test_historia.py`

- [ ] **Step 1: Tests que fallan**

Agregar a `engine/tests/test_historia.py`:

```python
def _serie_sintetica():
    """Tres meses derivados del parse real de agosto: la serie sube pareja ~10 % por mes
    (inflación), así la mediana de variaciones queda ~0,10 y solo un salto real la excede."""
    base = _agosto()
    prev2 = copy.deepcopy(base)
    prev2.periodo = "Junio 2026"
    for g in prev2.gastos:
        g.importe = round(g.importe / 1.21, 2)
    prev1 = copy.deepcopy(base)
    prev1.periodo = "Julio 2026"
    for g in prev1.gastos:
        g.importe = round(g.importe / 1.10, 2)
    return [prev2, prev1], base


def _clave_objetivo(liq):
    g = max((x for x in liq.gastos if not _excluida(x.categoria) and x.importe > 60_000),
            key=lambda x: x.importe)
    return _norm(g.proveedor), _norm(g.categoria), g


def test_salto_y_concentracion_exigen_dos_previos():
    liq, serie = _agosto(), [_julio()]
    assert _hallazgos("historia_salto", liq, serie, Config()) == []
    assert _hallazgos("historia_concentracion", liq, serie, Config()) == []


def test_salto_contra_la_propia_serie_es_alto():
    serie, liq = _serie_sintetica()
    prov, cat, obj = _clave_objetivo(liq)
    for g in liq.gastos:
        if _norm(g.proveedor) == prov and _norm(g.categoria) == cat:
            g.importe = round(g.importe * 2.2, 2)    # salta al doble; el resto sube ~10 %
    hs = _hallazgos("historia_salto", liq, serie, Config())
    assert len(hs) == 1
    h = hs[0]
    assert h.severidad == "ALTO"
    assert h.clave == f"salto|{prov}|{cat}"
    assert str(obj.n) in h.refs


def test_salto_moderado_es_medio():
    serie, liq = _serie_sintetica()
    prov, cat, _ = _clave_objetivo(liq)
    for g in liq.gastos:
        if _norm(g.proveedor) == prov and _norm(g.categoria) == cat:
            g.importe = round(g.importe * 1.45, 2)   # ~+59 % vs mediana ~10 %: exceso ~0,49
    hs = _hallazgos("historia_salto", liq, serie, Config())
    assert [h.severidad for h in hs] == ["MEDIO"]


def test_salto_respeta_importe_minimo():
    serie, liq = _serie_sintetica()
    prov, cat, _ = _clave_objetivo(liq)
    for g in liq.gastos:
        if _norm(g.proveedor) == prov and _norm(g.categoria) == cat:
            g.importe = round(g.importe * 2.2, 2)
    assert _hallazgos("historia_salto", liq, serie, Config(salto_importe_min=10**9)) == []


def test_salto_excluye_sueldos():
    serie, liq = _serie_sintetica()
    sueldos = [g for g in liq.gastos if _excluida(g.categoria)]
    assert sueldos, "el fixture real tiene sueldos"
    for g in sueldos:
        g.importe = round(g.importe * 3, 2)
    assert _hallazgos("historia_salto", liq, serie, Config()) == []
```

- [ ] **Step 2: Verificar que fallan**

Run: `cd /opt/consorcios-transparentes/engine && .venv/bin/python -m pytest -q tests/test_historia.py -k salto`
Expected: FAIL (la regla no existe todavía; `test_salto_y_concentracion_exigen_dos_previos` pasa trivialmente, el resto no)

- [ ] **Step 3: Implementar**

Agregar a `engine/ct/historia.py`:

```python
# ------------------------------------------------------------- salto vs. la propia serie
def _sumas(l: Liquidacion) -> dict[tuple[str, str], float]:
    out: dict[tuple[str, str], float] = {}
    for g in l.gastos:
        if _excluida(g.categoria):
            continue
        k = (_norm(g.proveedor), _norm(g.categoria))
        out[k] = round(out.get(k, 0.0) + g.importe, 2)
    return out


@rule_h("historia_salto")
def r_salto(liq, serie, cfg, *_):
    if len(serie) < 2:
        return []
    mensuales = [(pl.periodo, _sumas(pl)) for pl in serie]
    apariciones: dict[tuple[str, str], int] = {}
    for _, m in mensuales:
        for k in m:
            apariciones[k] = apariciones.get(k, 0) + 1
    act, ult = _sumas(liq), mensuales[-1][1]
    variaciones = {k: act[k] / ult[k] - 1
                   for k, veces in apariciones.items()
                   if veces >= 2 and k in act and ult.get(k, 0) > 0}
    if len(variaciones) < 3:    # sin masa de recurrentes la mediana no dice nada
        return []
    med = median(variaciones.values())
    out: list[Hallazgo] = []
    for k, v in sorted(variaciones.items()):
        exceso = v - med
        if exceso <= cfg.salto_puntos_medio or act[k] <= cfg.salto_importe_min:
            continue
        gs = [g for g in liq.gastos if (_norm(g.proveedor), _norm(g.categoria)) == k]
        historia = " → ".join(f"{p}: {fmt(m[k])}" for p, m in mensuales if k in m)
        out.append(Hallazgo(
            "historia_salto", "ALTO" if exceso > cfg.salto_puntos_alto else "MEDIO",
            "Evolución de costos",
            f"{gs[0].proveedor}: subió {pct(v)} en el mes cuando la mediana de los gastos "
            f"recurrentes fue {pct(med)}",
            f"Serie: {historia} → este mes: {fmt(act[k])}. Exceso de {pct(exceso)} sobre la "
            f"mediana de {len(variaciones)} gastos recurrentes.",
            round(act[k] - ult[k] * (1 + med), 2),
            "Pedir qué justifica el aumento (presupuesto, acuerdo o factura nueva).",
            [str(g.n) for g in gs], clave=f"salto|{k[0]}|{k[1]}"))
    return out
```

- [ ] **Step 4: Verificar que pasan**

Run: `cd /opt/consorcios-transparentes/engine && .venv/bin/python -m pytest -q tests/test_historia.py`
Expected: PASS. Si `test_salto_contra_la_propia_serie_es_alto` diera más de un hallazgo, revisar si el redondeo de la serie sintética generó otro exceso legítimo y ajustar el multiplicador del test (no los umbrales).

- [ ] **Step 5: Commit**

```bash
cd /opt/consorcios-transparentes && git add engine/ct/historia.py engine/tests/test_historia.py && git commit -m "Motor: historia_salto — gasto recurrente que salta contra su serie, neto de inflación

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

### Task 5: Regla `historia_concentracion`

**Files:**
- Modify: `engine/ct/historia.py`
- Test: `engine/tests/test_historia.py`

- [ ] **Step 1: Tests que fallan**

Agregar a `engine/tests/test_historia.py`:

```python
def _boost_hasta_share(liq, prov_norm, objetivo):
    """Escala los gastos del proveedor para que su share (sin sueldos) quede en `objetivo`."""
    mios = [g for g in liq.gastos if not _excluida(g.categoria) and _norm(g.proveedor) == prov_norm]
    resto = sum(g.importe for g in liq.gastos
                if not _excluida(g.categoria) and _norm(g.proveedor) != prov_norm)
    factor = (objetivo / (1 - objetivo) * resto) / sum(g.importe for g in mios)
    for g in mios:
        g.importe = round(g.importe * factor, 2)


def test_concentracion_por_encima_del_umbral():
    serie, liq = _serie_sintetica()
    prov, _, obj = _clave_objetivo(liq)
    _boost_hasta_share(liq, prov, 0.30)
    hs = _hallazgos("historia_concentracion", liq, serie, Config())
    h = next(x for x in hs if x.clave == f"concentracion|{prov}")
    assert h.severidad == "MEDIO"
    assert str(obj.n) in h.refs


def test_concentracion_creciente_sin_superar_umbral():
    serie, liq = _serie_sintetica()
    prov, _, _ = _clave_objetivo(liq)
    _boost_hasta_share(serie[0], prov, 0.10)
    _boost_hasta_share(serie[1], prov, 0.14)
    _boost_hasta_share(liq, prov, 0.18)
    hs = _hallazgos("historia_concentracion", liq, serie, Config())
    h = next(x for x in hs if x.clave == f"concentracion|{prov}")
    assert h.severidad == "MEDIO"
    assert "creciente" in h.titulo


def test_concentracion_estable_y_baja_no_dispara():
    serie, liq = _serie_sintetica()
    prov, _, _ = _clave_objetivo(liq)
    for l in (serie[0], serie[1], liq):
        _boost_hasta_share(l, prov, 0.12)
    assert [h for h in _hallazgos("historia_concentracion", liq, serie, Config())
            if h.clave == f"concentracion|{prov}"] == []
```

- [ ] **Step 2: Verificar que fallan**

Run: `cd /opt/consorcios-transparentes/engine && .venv/bin/python -m pytest -q tests/test_historia.py -k concentracion`
Expected: FAIL (`StopIteration`: la regla no emite nada)

- [ ] **Step 3: Implementar**

Agregar a `engine/ct/historia.py`:

```python
# ------------------------------------------------------------- concentración de proveedores
def _shares(l: Liquidacion) -> dict[str, float]:
    gastos = [g for g in l.gastos if not _excluida(g.categoria)]
    total = sum(g.importe for g in gastos)
    if total <= 0:
        return {}
    by: dict[str, float] = {}
    for g in gastos:
        by[_norm(g.proveedor)] = by.get(_norm(g.proveedor), 0.0) + g.importe
    return {k: v / total for k, v in by.items()}


@rule_h("historia_concentracion")
def r_concentracion(liq, serie, cfg, *_):
    if len(serie) < 2:
        return []
    s_act, s_prev1, s_prev2 = _shares(liq), _shares(serie[-1]), _shares(serie[-2])
    out: list[Hallazgo] = []
    for k, sh in sorted(s_act.items()):
        alto = sh > cfg.concentracion_proveedor
        creciente = s_prev2.get(k, 0.0) < s_prev1.get(k, 0.0) < sh
        if not alto and not (creciente and sh > 0.15):
            continue
        gs = [g for g in liq.gastos if not _excluida(g.categoria) and _norm(g.proveedor) == k]
        titulo = (f"{gs[0].proveedor} concentra {pct(sh)} del gasto del mes (sin sueldos)" if alto
                  else f"{gs[0].proveedor} concentra una parte creciente del gasto: {pct(sh)} este mes")
        out.append(Hallazgo(
            "historia_concentracion", "MEDIO", "Proveedores", titulo,
            f"Share sobre el gasto sin sueldos: {serie[-2].periodo}: {pct(s_prev2.get(k, 0.0))} → "
            f"{serie[-1].periodo}: {pct(s_prev1.get(k, 0.0))} → este mes: {pct(sh)}. "
            f"Umbral: {pct(cfg.concentracion_proveedor)}.",
            round(sum(g.importe for g in gs), 2),
            "Pedir presupuestos alternativos o el detalle de la contratación.",
            [str(g.n) for g in gs], clave=f"concentracion|{k}"))
    return out
```

- [ ] **Step 4: Verificar que pasan (suite completa del motor)**

Run: `cd /opt/consorcios-transparentes/engine && .venv/bin/python -m pytest -q tests`
Expected: todo verde (las suites previas eran 53; ahora más).

- [ ] **Step 5: Commit**

```bash
cd /opt/consorcios-transparentes && git add engine/ct/historia.py engine/tests/test_historia.py && git commit -m "Motor: historia_concentracion — proveedor con share alto o creciente del gasto

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

### Task 6: Integración en la API — `cargar_serie`, `recalcular_historia` y despublicación

**Files:**
- Modify: `api/app/ingesta.py`
- Create: `api/tests/test_historia_api.py`
- Modify: `api/tests/test_comprobantes_api.py` (un test nuevo al final)

- [ ] **Step 1: Tests que fallan**

Crear `api/tests/test_historia_api.py`:

```python
"""Integración de las reglas históricas: recálculo idempotente, contención de fallas
y despublicación al rechazar. El cálculo en sí se prueba en el motor; acá se stubbea."""
from app import ingesta, models
from app.storage import LocalStorage
from ct.rules import Hallazgo as HallazgoMotor

from .conftest import FIXTURES


def preparar(db, tmp_path, periodo="2026-08", fixture="redconar_202608.txt"):
    st = LocalStorage(str(tmp_path))
    key = f"liquidaciones/{periodo}.txt"
    st.guardar(key, (FIXTURES / fixture).read_bytes())
    liq = models.Liquidacion(periodo=periodo, archivo_key=key)
    db.add(liq)
    db.commit()
    return st, liq


def _canned(*_args, **_kw):
    return [HallazgoMotor("historia_duplicado", "ALTO", "Respaldo documental",
                          "La factura X ya figuraba en julio", "evidencia", 0,
                          "Verificar", ["1"], clave="dup-fact|2026-07|3-1234")]


def test_procesar_genera_hallazgos_de_historia(db, tmp_path, monkeypatch):
    monkeypatch.setattr(ingesta, "evaluar_historia", _canned)
    st, liq = preparar(db, tmp_path)
    ingesta.procesar(db, liq.id, st)
    db.refresh(liq)
    assert liq.estado == "procesada"
    hs = db.query(models.Hallazgo).filter_by(liquidacion_id=liq.id, origen="historia").all()
    assert len(hs) == 1 and hs[0].regla == "historia_duplicado"


def test_recalcular_es_idempotente_y_conserva_la_clave(db, tmp_path, monkeypatch):
    monkeypatch.setattr(ingesta, "evaluar_historia", _canned)
    st, liq = preparar(db, tmp_path)
    ingesta.procesar(db, liq.id, st)
    fila = db.query(models.Hallazgo).filter_by(liquidacion_id=liq.id, origen="historia").one()
    ingesta.recalcular_historia(db, liq, st)
    db.commit()
    tras = db.query(models.Hallazgo).filter_by(liquidacion_id=liq.id, origen="historia").one()
    assert (tras.id, tras.clave) == (fila.id, fila.clave)


def test_falla_de_historia_no_rompe_la_ingesta(db, tmp_path, monkeypatch):
    def explota(*_a, **_k):
        raise RuntimeError("boom")
    monkeypatch.setattr(ingesta, "evaluar_historia", explota)
    st, liq = preparar(db, tmp_path)
    ingesta.procesar(db, liq.id, st)
    db.refresh(liq)
    assert liq.estado == "procesada"
    assert db.query(models.Hallazgo).filter_by(liquidacion_id=liq.id, origen="historia").count() == 0


def test_limpiar_al_rechazar_despublica_historia(db, tmp_path):
    st, liq = preparar(db, tmp_path)
    ingesta.procesar(db, liq.id, st)
    h = models.Hallazgo(liquidacion_id=liq.id, clave="dup-fact|x|1", origen="historia",
                        regla="historia_duplicado", severidad="ALTO", area="a",
                        titulo="t", evidencia="e", publicado=True)
    db.add(h)
    db.commit()
    ingesta.limpiar_al_rechazar(db, liq)
    db.commit()
    assert h.publicado is False


def test_serie_y_docs_llegan_al_motor(db, tmp_path, monkeypatch):
    """Con julio procesado con un documento, el recálculo de agosto recibe la serie con julio
    y sus comprobantes como previos."""
    recibido = {}

    def espia(liq, serie, cfg, docs_actual=None, docs_previos=None):
        recibido.update(serie=[l.periodo for l in serie], docs_previos=docs_previos)
        return []

    st, liq_jul = preparar(db, tmp_path, "2026-07", "redconar_202607.txt")
    ingesta.procesar(db, liq_jul.id, st)
    db.add(models.Documento(liquidacion_id=liq_jul.id, gasto_n=3, tipo="factura",
                            archivo_key="comprobantes/2026-07/f.pdf", hash="abc123", metadatos={}))
    db.commit()
    st.guardar("liquidaciones/2026-08.txt", (FIXTURES / "redconar_202608.txt").read_bytes())
    liq_ago = models.Liquidacion(periodo="2026-08", archivo_key="liquidaciones/2026-08.txt")
    db.add(liq_ago)
    db.commit()
    monkeypatch.setattr(ingesta, "evaluar_historia", espia)
    ingesta.procesar(db, liq_ago.id, st)
    assert recibido["serie"] and "julio" in recibido["serie"][0].lower()
    assert recibido["docs_previos"] == {"2026-07": [(3, "abc123", "f.pdf")]}
```

Y al final de `api/tests/test_comprobantes_api.py`:

```python
def test_subir_comprobantes_recalcula_historia(db, auditor, monkeypatch):
    from app import ingesta
    llamadas = []
    monkeypatch.setattr(ingesta, "recalcular_historia", lambda *a, **k: llamadas.append(1))
    liq_id = subir(auditor).json()["id"]
    datos = db.get(models.Liquidacion, liq_id).datos
    r = auditor.post(f"/liquidaciones/{liq_id}/comprobantes",
                     files={"archivo": ("agosto.zip", zip_comprobantes(datos), "application/zip")})
    assert r.status_code == 200
    assert llamadas  # el cruce dispara el recálculo histórico
```

- [ ] **Step 2: Verificar que fallan**

Run: `cd /opt/consorcios-transparentes/api && .venv/bin/python -m pytest -q tests/test_historia_api.py tests/test_comprobantes_api.py`
Expected: FAIL con `AttributeError: module 'app.ingesta' has no attribute 'evaluar_historia'` (y `recalcular_historia` inexistente)

- [ ] **Step 3: Implementar**

En `api/app/ingesta.py`:

1. Import (junto a los otros de `ct`):

```python
from ct.historia import evaluar_historia
```

2. Después de `cargar_anterior` agregar:

```python
def cargar_serie(db: Session, storage, periodo: str) -> list[LiqMotor]:
    """Liquidaciones procesadas/publicadas anteriores al período, ascendente. Un mes que
    falle al parsear se saltea con warning: mejor una serie incompleta que ninguna (mismo
    criterio que cargar_anterior)."""
    filas = (db.query(models.Liquidacion)
               .filter(models.Liquidacion.periodo < periodo,
                       models.Liquidacion.estado.in_(("procesada", "publicada")))
               .order_by(models.Liquidacion.periodo).all())
    out = []
    for fila in filas:
        try:
            out.append(cargar_engine(storage, fila))
        except Exception:
            logger.warning("No se pudo cargar %s para la serie histórica", fila.periodo, exc_info=True)
    return out


def recalcular_historia(db: Session, liq_row: models.Liquidacion, storage,
                        liq: LiqMotor | None = None) -> None:
    """Idempotente: corre al final de `procesar` y tras `cruzar_comprobantes` (los docs del
    mes recién existen ahí). Cualquier falla se loguea y el savepoint se revierte: la
    ingesta JAMÁS se cae por las reglas históricas."""
    try:
        with db.begin_nested():
            if liq is None:
                liq = cargar_engine(storage, liq_row)
            serie = cargar_serie(db, storage, liq_row.periodo)
            docs_actual = [(d.gasto_n, d.hash, d.archivo_key.rsplit("/", 1)[-1])
                           for d in db.query(models.Documento)
                                      .filter_by(liquidacion_id=liq_row.id).all()]
            docs_previos: dict[str, list] = {}
            previas = (db.query(models.Documento, models.Liquidacion.periodo)
                         .join(models.Liquidacion,
                               models.Documento.liquidacion_id == models.Liquidacion.id)
                         .filter(models.Liquidacion.periodo < liq_row.periodo,
                                 models.Liquidacion.estado.in_(("procesada", "publicada")))
                         .all())
            for d, per in previas:
                docs_previos.setdefault(per, []).append(
                    (d.gasto_n, d.hash, d.archivo_key.rsplit("/", 1)[-1]))
            hs = evaluar_historia(liq, serie, config_consorcio(db), docs_actual, docs_previos)
            upsert_hallazgos(db, liq_row, hs, origen="historia")
    except Exception:
        logger.warning("Falló el recálculo de hallazgos históricos de %s (la ingesta sigue)",
                       liq_row.periodo, exc_info=True)
```

3. En `procesar()`, inmediatamente después de `upsert_hallazgos(db, liq_row, hs, origen="liquidacion")`:

```python
        recalcular_historia(db, liq_row, storage, liq=liq)
```

4. En `cruzar_comprobantes()`, entre `upsert_hallazgos(db, liq_row, hallazgos, origen="comprobantes")` y `db.commit()`:

```python
        recalcular_historia(db, liq_row, storage, liq=liq)
```

5. En `limpiar_al_rechazar()`, reemplazar el loop de despublicación:

```python
    for h in db.query(models.Hallazgo).filter_by(liquidacion_id=liq_row.id, origen="liquidacion").all():
        h.publicado = False
```

por:

```python
    for h in (db.query(models.Hallazgo)
                .filter(models.Hallazgo.liquidacion_id == liq_row.id,
                        models.Hallazgo.origen.in_(("liquidacion", "historia"))).all()):
        h.publicado = False
```

y en el docstring de esa función, cambiar "(los de esta liquidación, no los de comprobantes)"
por "(los de esta liquidación e históricos, no los de comprobantes)".

- [ ] **Step 4: Verificar que pasa la suite completa de la API**

Run: `cd /opt/consorcios-transparentes/api && .venv/bin/python -m pytest -q`
Expected: todo verde (162 previos + los nuevos). Atención a `test_procesar_usa_el_mes_anterior_si_existe`: ahora también corre historia con serie de 1 (no debe emitir nada nuevo que rompa conteos exactos; si algún test viejo asume un total exacto de hallazgos, revisar si el nuevo origen lo afecta y ajustar el filtro del test por origen, no la implementación).

- [ ] **Step 5: Commit**

```bash
cd /opt/consorcios-transparentes && git add api/app/ingesta.py api/tests/test_historia_api.py api/tests/test_comprobantes_api.py && git commit -m "API: recálculo idempotente de hallazgos históricos en la ingesta y el cruce

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

### Task 7: Documentación

**Files:**
- Modify: `docs/reglas.md` (agregar sección de reglas históricas al catálogo)
- Modify: `docs/ESTADO.md` (ciclo A hecho; pendientes C → B → D)

- [ ] **Step 1: Actualizar `docs/reglas.md`**

Agregar una sección "Reglas históricas (serie de meses)" con el mismo formato tabular del
catálogo existente (leer el archivo primero y respetar su estructura), cubriendo:

- `historia_duplicado`: misma factura (número normalizado + proveedor) o mismo archivo (hash)
  en dos meses; CRÍTICO si coincide el importe, ALTO si no. Cuelga del mes más reciente.
- `historia_salto`: recurrentes (≥2 meses previos, sin sueldos/cargas) cuya variación excede la
  mediana del mes en `salto_puntos_medio`/`salto_puntos_alto`; mínimo `salto_importe_min`;
  necesita ≥2 previos y ≥3 recurrentes.
- `historia_concentracion`: share sin sueldos > `concentracion_proveedor`, o creciente 3
  períodos y > 15 %.
- Limitación conocida: si se reprocesa un mes viejo corregido, los hallazgos históricos de los
  meses posteriores no se recalculan solos (se recalculan al reprocesar ese mes posterior o en
  su próximo cruce de comprobantes).

- [ ] **Step 2: Actualizar `docs/ESTADO.md`**

En la sección de hecho/pendientes: marcar el ciclo A (reglas históricas) como hecho con fecha
06-09-2026 y dejar el orden pendiente C (endurecer el cruce) → B (prorrateo vs escritura) →
D (OCR de imágenes), citando la spec de este ciclo.

- [ ] **Step 3: Commit**

```bash
cd /opt/consorcios-transparentes && git add docs/reglas.md docs/ESTADO.md && git commit -m "Docs: catálogo y estado con las reglas históricas del ciclo A

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

### Verificación final (fuera de tareas, la corre el orquestador)

- [ ] Suites completas: `cd /opt/consorcios-transparentes/engine && .venv/bin/python -m pytest -q tests` y `cd /opt/consorcios-transparentes/api && .venv/bin/python -m pytest -q` — todo verde.
- [ ] Revisión adversarial (spec review + code review) antes del deploy.
- [ ] Deploy a producción **solo con confirmación del usuario** (patrón del proyecto): rebuild de imágenes api/worker, `alembic upgrade head` no hace falta (no hay migraciones nuevas), reprocesar agosto y triage manual de los hallazgos históricos que aparezcan antes de publicar nada.
