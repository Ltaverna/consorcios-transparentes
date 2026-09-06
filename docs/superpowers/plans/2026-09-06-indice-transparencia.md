# Índice de transparencia — Plan de implementación

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Estados por gasto (5, calculados) + índice de transparencia con métricas abribles, visible en el panel, para propietarios (solo lo publicado) y por MCP.

**Architecture:** Módulo puro `api/app/analitica.py` (clasificación y métricas derivadas de Gasto/Documento/Hallazgo, sin almacenar nada), router `/analitica/*` con el mismo gating por rol que `/hallazgos`, dos tools nuevas en `servidor_mcp.py`, página `panel/transparencia` + sección en `mi-unidad` (client components con el patrón de `panel/analisis`).

**Tech Stack:** FastAPI+SQLAlchemy, Next.js+Tailwind+shadcn (sin librerías nuevas), MSW en tests web. Spec: `docs/superpowers/specs/2026-09-06-indice-transparencia-design.md` (leerla: las fórmulas y la precedencia de estados son normativas).

**Convenciones:** commits en español + trailer `Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>`. Tests: api `cd /opt/consorcios-transparentes/api && .venv/bin/python -m pytest -q` (168 hoy); web `cd /opt/consorcios-transparentes/web && npm test` (42 hoy). El cwd del shell se resetea: rutas absolutas o `cd` en el mismo comando.

**Hechos del modelo que el plan usa** (verificados):
- `Hallazgo.estado ∈ (pendiente, preguntado, respondido, descartado, cerrado)`; abierto = los tres primeros. `Hallazgo.refs` son números de gasto como strings **salvo la regla `morosidad`** (UFs) — excluirla del mapeo por gasto.
- `Gasto.pagos` es JSON: `[{"fecha","importe","caja","forma"}]`; `Documento.tipo ∈ (factura, pago, recibo, imagen, otro)`, `Documento.gasto_n` nullable.
- `Liquidacion.estado`: propietario solo ve `publicada`; vista interna: `procesada` y `publicada`.
- Las claves de hallazgos del cruce nuevas contienen `pago-sin-comp` (substring en `Hallazgo.clave`).

---

### Task 1: Módulo `api/app/analitica.py`

**Files:**
- Create: `api/app/analitica.py`
- Create: `api/tests/test_analitica.py`

- [ ] **Step 1: Tests que fallan**

Crear `api/tests/test_analitica.py` (el `preparar` es el patrón de `test_ingesta.py`):

```python
"""Estados por gasto e índice: clasificación con hallazgos/documentos sintéticos sobre el
fixture real de agosto, fórmula verificada a mano, y vista propietario sin lo no publicado."""
from app import analitica, ingesta, models
from app.storage import LocalStorage

from .conftest import FIXTURES


def preparar(db, tmp_path, periodo="2026-08", fixture="redconar_202608.txt"):
    st = LocalStorage(str(tmp_path))
    key = f"liquidaciones/{periodo}.txt"
    st.guardar(key, (FIXTURES / fixture).read_bytes())
    liq = models.Liquidacion(periodo=periodo, archivo_key=key)
    db.add(liq)
    db.commit()
    ingesta.procesar(db, liq.id, st)
    db.refresh(liq)
    return st, liq


def _limpiar_hallazgos(db, liq):
    """Los tests de clasificación fijan su propio escenario: se borran los hallazgos que la
    ingesta generó sobre el fixture real para que no interfieran."""
    db.query(models.Hallazgo).filter_by(liquidacion_id=liq.id).delete()
    db.commit()


def _hallazgo(db, liq, n, severidad, estado="pendiente", publicado=False, regla="prueba", clave=None):
    h = models.Hallazgo(liquidacion_id=liq.id, clave=clave or f"t|{regla}|{severidad}|{n}|{estado}",
                        origen="liquidacion", regla=regla, severidad=severidad,
                        titulo="t", refs=[str(n)], estado=estado, publicado=publicado)
    db.add(h)
    db.commit()
    return h


def _doc(db, liq, n, tipo="factura"):
    d = models.Documento(liquidacion_id=liq.id, gasto_n=n, tipo=tipo,
                        archivo_key=f"comprobantes/{liq.periodo}/g{n}-{tipo}.pdf", metadatos={})
    db.add(d)
    db.commit()
    return d


def test_clasificar_precedencia():
    assert analitica.clasificar(True, {"CRÍTICO", "MEDIO"}) == "inconsistencia"
    assert analitica.clasificar(True, {"ALTO"}) == "anomalia"
    assert analitica.clasificar(False, set()) == "sin_informacion"
    assert analitica.clasificar(False, {"CRÍTICO"}) == "inconsistencia"   # 1-2 le ganan a sin-docs
    assert analitica.clasificar(True, {"MEDIO"}) == "requiere_explicacion"
    assert analitica.clasificar(True, set()) == "verificado"


def test_estados_sobre_gastos_reales(db, tmp_path):
    st, liq = preparar(db, tmp_path)
    _limpiar_hallazgos(db, liq)
    gastos = db.query(models.Gasto).filter_by(liquidacion_id=liq.id).order_by(models.Gasto.n).all()
    a, b, c, d_, e = (g.n for g in gastos[:5])
    _doc(db, liq, a); _hallazgo(db, liq, a, "CRÍTICO")                    # inconsistencia
    _doc(db, liq, b); _hallazgo(db, liq, b, "ALTO")                       # anomalia
    _doc(db, liq, c); _hallazgo(db, liq, c, "MEDIO")                      # requiere_explicacion
    _doc(db, liq, d_); _hallazgo(db, liq, d_, "CRÍTICO", estado="cerrado")  # resuelto → verificado
    # e: sin docs y sin hallazgos → sin_informacion
    filas, hs, abiertos = analitica.evaluar_liquidacion(db, liq, solo_publicado=False)
    por_n = {g.n: est for g, est, _h, _d in filas}
    assert por_n[a] == "inconsistencia"
    assert por_n[b] == "anomalia"
    assert por_n[c] == "requiere_explicacion"
    assert por_n[d_] == "verificado"
    assert por_n[e] == "sin_informacion"


def test_respondido_sigue_abierto_y_morosidad_no_clasifica(db, tmp_path):
    st, liq = preparar(db, tmp_path)
    _limpiar_hallazgos(db, liq)
    gastos = db.query(models.Gasto).filter_by(liquidacion_id=liq.id).order_by(models.Gasto.n).all()
    a, b = gastos[0].n, gastos[1].n
    _doc(db, liq, a); _hallazgo(db, liq, a, "ALTO", estado="respondido")
    _doc(db, liq, b); _hallazgo(db, liq, b, "CRÍTICO", regla="morosidad")   # refs de UF: no aplica
    filas, _, _ = analitica.evaluar_liquidacion(db, liq, solo_publicado=False)
    por_n = {g.n: est for g, est, _h, _d in filas}
    assert por_n[a] == "anomalia"        # respondido cuenta como abierto
    assert por_n[b] == "verificado"      # morosidad no baja el estado del gasto


def test_indice_formula_a_mano(db, tmp_path):
    st, liq = preparar(db, tmp_path)
    _limpiar_hallazgos(db, liq)
    gastos = db.query(models.Gasto).filter_by(liquidacion_id=liq.id).order_by(models.Gasto.n).all()
    total = round(sum(g.importe for g in gastos), 2)
    # todos sin docs (sin_informacion) salvo el primero, verificado
    _doc(db, liq, gastos[0].n)
    m = analitica.metricas(db, solo_publicado=False)
    t = m["totales"]
    assert t["dinero_total"] == total
    assert t["dinero_verificado"] == gastos[0].importe
    assert m["indice"] == round(gastos[0].importe / total * 100)
    assert t["gastos_por_estado"]["sin_informacion"]["cantidad"] == len(gastos) - 1
    assert m["periodos"][0]["periodo"] == "2026-08"


def test_vista_propietario_solo_lo_publicado(db, tmp_path):
    st, liq = preparar(db, tmp_path)
    _limpiar_hallazgos(db, liq)
    gastos = db.query(models.Gasto).filter_by(liquidacion_id=liq.id).order_by(models.Gasto.n).all()
    a = gastos[0].n
    _doc(db, liq, a)
    _hallazgo(db, liq, a, "CRÍTICO", publicado=False)
    filas_int, _, _ = analitica.evaluar_liquidacion(db, liq, solo_publicado=False)
    assert {g.n: e for g, e, _h, _d in filas_int}[a] == "inconsistencia"
    # liquidación no publicada: el propietario no ve NADA del período
    m = analitica.metricas(db, solo_publicado=True)
    assert m["periodos"] == [] and m["indice"] == 0
    liq.estado = "publicada"
    db.commit()
    filas_prop, _, _ = analitica.evaluar_liquidacion(db, liq, solo_publicado=True)
    assert {g.n: e for g, e, _h, _d in filas_prop}[a] == "verificado"   # el no publicado no lo baja


def test_pago_respaldado(db, tmp_path):
    st, liq = preparar(db, tmp_path)
    _limpiar_hallazgos(db, liq)
    gastos = db.query(models.Gasto).filter_by(liquidacion_id=liq.id).order_by(models.Gasto.n).all()
    ef = next(g for g in gastos if g.pagos and any((p.get("forma") or "").lower().startswith("efectivo") for p in g.pagos))
    tr = next(g for g in gastos if g.pagos and all((p.get("forma") or "").lower().startswith("transf") for p in g.pagos))
    _doc(db, liq, tr.n, tipo="pago")
    m = analitica.metricas(db, solo_publicado=False)
    t = m["totales"]
    assert t["dinero_pago_respaldado"] >= tr.importe          # transferencia con doc cuenta
    # el efectivo jamás cuenta: sumarle un doc de pago no lo respalda
    _doc(db, liq, ef.n, tipo="pago")
    t2 = analitica.metricas(db, solo_publicado=False)["totales"]
    assert t2["dinero_pago_respaldado"] == t["dinero_pago_respaldado"]
```

- [ ] **Step 2: Verificar que fallan**

Run: `cd /opt/consorcios-transparentes/api && .venv/bin/python -m pytest -q tests/test_analitica.py`
Expected: `ModuleNotFoundError`/ImportError (`app.analitica` no existe).

- [ ] **Step 3: Implementar `api/app/analitica.py`**

```python
"""Estados por gasto e índice de transparencia. Todo derivado (documentos + hallazgos +
triage); nada se almacena y ninguna cifra la genera una IA. Fórmulas y precedencia:
docs/superpowers/specs/2026-09-06-indice-transparencia-design.md."""
from sqlalchemy.orm import Session

from . import models

ABIERTOS = ("pendiente", "preguntado", "respondido")
RESUELTOS = ("descartado", "cerrado")
ESTADOS_GASTO = ("verificado", "requiere_explicacion", "anomalia", "inconsistencia", "sin_informacion")
SEVERIDADES = ("CRÍTICO", "ALTO", "MEDIO", "BAJO")
# los refs de morosidad son UFs, no números de gasto: esa regla no clasifica gastos
REGLAS_REFS_UF = {"morosidad"}


def clasificar(tiene_docs: bool, severidades_abiertas: set[str]) -> str:
    if "CRÍTICO" in severidades_abiertas:
        return "inconsistencia"
    if "ALTO" in severidades_abiertas:
        return "anomalia"
    if not tiene_docs:
        return "sin_informacion"
    if severidades_abiertas:
        return "requiere_explicacion"
    return "verificado"


def evaluar_liquidacion(db: Session, liq: models.Liquidacion, solo_publicado: bool):
    """[(gasto, estado, hallazgos_abiertos_que_lo_refieren, documentos)], hallazgos, abiertos."""
    gastos = (db.query(models.Gasto).filter_by(liquidacion_id=liq.id)
                .order_by(models.Gasto.n).all())
    docs = db.query(models.Documento).filter_by(liquidacion_id=liq.id).all()
    hs = db.query(models.Hallazgo).filter_by(liquidacion_id=liq.id).all()
    if solo_publicado:
        hs = [h for h in hs if h.publicado]
    abiertos = [h for h in hs if h.estado in ABIERTOS]
    docs_por_n: dict[int, list] = {}
    for d in docs:
        if d.gasto_n is not None:
            docs_por_n.setdefault(d.gasto_n, []).append(d)
    sev_por_n: dict[int, set[str]] = {}
    hall_por_n: dict[int, list] = {}
    for h in abiertos:
        if h.regla in REGLAS_REFS_UF:
            continue
        for r in (h.refs or []):
            if isinstance(r, str) and r.isdigit():
                n = int(r)
                sev_por_n.setdefault(n, set()).add(h.severidad)
                hall_por_n.setdefault(n, []).append(h)
    filas = []
    for g in gastos:
        dd = docs_por_n.get(g.n, [])
        filas.append((g, clasificar(bool(dd), sev_por_n.get(g.n, set())),
                      hall_por_n.get(g.n, []), dd))
    return filas, hs, abiertos


def _stats_vacias() -> dict:
    return {"dinero_total": 0.0, "dinero_verificado": 0.0, "dinero_con_factura": 0.0,
            "dinero_pago_respaldado": 0.0,
            "gastos_por_estado": {e: {"cantidad": 0, "importe": 0.0} for e in ESTADOS_GASTO},
            "hallazgos_abiertos": {s: 0 for s in SEVERIDADES}, "hallazgos_resueltos": 0}


def _pago_respaldado(g: models.Gasto, tiene_doc_pago: bool, sin_comp_abierto: bool) -> bool:
    """Efectivo jamás respaldado; débito automático siempre (resumen bancario); transferencias
    exigen doc de pago adjunto y ningún hallazgo abierto de pago sin comprobante."""
    pagos = g.pagos or []
    if not pagos:
        return False
    formas = [(p.get("forma") or "").lower() for p in pagos]
    cajas = [(p.get("caja") or "").upper() for p in pagos]
    if any(f.startswith("efectivo") for f in formas) or "CAJA" in cajas:
        return False
    if all(f.startswith(("débito", "debito")) for f in formas):
        return True
    return tiene_doc_pago and not sin_comp_abierto


def _cerrar(s: dict) -> dict:
    """Redondeos + porcentajes + índice del bloque de stats."""
    for k in ("dinero_total", "dinero_verificado", "dinero_con_factura", "dinero_pago_respaldado"):
        s[k] = round(s[k], 2)
    for v in s["gastos_por_estado"].values():
        v["importe"] = round(v["importe"], 2)
    total = s["dinero_total"]
    s["pct_trazable"] = round(s["dinero_verificado"] / total, 4) if total else 0.0
    s["pct_con_factura"] = round(s["dinero_con_factura"] / total, 4) if total else 0.0
    s["pct_pago_respaldado"] = round(s["dinero_pago_respaldado"] / total, 4) if total else 0.0
    s["indice"] = round(s["pct_trazable"] * 100)
    return s


def metricas(db: Session, desde: str = "", hasta: str = "", solo_publicado: bool = False) -> dict:
    estados_liq = ("publicada",) if solo_publicado else ("procesada", "publicada")
    q = db.query(models.Liquidacion).filter(models.Liquidacion.estado.in_(estados_liq))
    if desde:
        q = q.filter(models.Liquidacion.periodo >= desde)
    if hasta:
        q = q.filter(models.Liquidacion.periodo <= hasta)
    liqs = q.order_by(models.Liquidacion.periodo).all()
    agg, periodos = _stats_vacias(), []
    for liq in liqs:
        filas, hs, abiertos = evaluar_liquidacion(db, liq, solo_publicado)
        s = _stats_vacias()
        for g, estado, halls, dd in filas:
            for destino in (s, agg):
                destino["dinero_total"] += g.importe
                destino["gastos_por_estado"][estado]["cantidad"] += 1
                destino["gastos_por_estado"][estado]["importe"] += g.importe
            if estado == "verificado":
                s["dinero_verificado"] += g.importe
                agg["dinero_verificado"] += g.importe
            if any(d.tipo == "factura" for d in dd):
                s["dinero_con_factura"] += g.importe
                agg["dinero_con_factura"] += g.importe
            sin_comp = any("pago-sin-comp" in (h.clave or "") for h in halls)
            if _pago_respaldado(g, any(d.tipo == "pago" for d in dd), sin_comp):
                s["dinero_pago_respaldado"] += g.importe
                agg["dinero_pago_respaldado"] += g.importe
        for h in abiertos:
            if h.severidad in s["hallazgos_abiertos"]:
                s["hallazgos_abiertos"][h.severidad] += 1
                agg["hallazgos_abiertos"][h.severidad] += 1
        resueltos = sum(1 for h in hs if h.estado in RESUELTOS)
        s["hallazgos_resueltos"] += resueltos
        agg["hallazgos_resueltos"] += resueltos
        s["periodo"] = liq.periodo
        periodos.append(_cerrar(s))
    tot = _cerrar(agg)
    return {"indice": tot["indice"],
            "rango": {"desde": liqs[0].periodo if liqs else "", "hasta": liqs[-1].periodo if liqs else ""},
            "totales": tot, "periodos": periodos}
```

- [ ] **Step 4: Verificar** — `cd /opt/consorcios-transparentes/api && .venv/bin/python -m pytest -q tests/test_analitica.py` PASS (7), luego suite completa (175 esperados).

- [ ] **Step 5: Commit**

```bash
cd /opt/consorcios-transparentes && git add api/app/analitica.py api/tests/test_analitica.py && git commit -m "API: estados por gasto e índice de transparencia (módulo de cálculo)

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

### Task 2: Router `/analitica` y registro

**Files:**
- Create: `api/app/routers/analitica.py`
- Modify: `api/app/main.py` (registrar el router donde se registran los demás — buscar `include_router`)
- Test: `api/tests/test_analitica.py` (agregar tests de endpoint)

- [ ] **Step 1: Tests que fallan** — agregar a `api/tests/test_analitica.py`. IMPORTANTE: leer
  `api/tests/conftest.py` y `api/tests/test_hallazgos_api.py` para los fixtures de clientes
  (`auditor` existe; para propietario, reusar el patrón de login de propietario que usen los
  tests de hallazgos/documentos — copiar ese setup, no inventar).

```python
def test_endpoint_indice_para_auditor(db, tmp_path, auditor):
    st, liq = preparar(db, tmp_path)
    r = auditor.get("/analitica/indice")
    assert r.status_code == 200
    d = r.json()
    assert "indice" in d and d["periodos"][0]["periodo"] == "2026-08"


def test_endpoint_gastos_filtra_por_estado(db, tmp_path, auditor):
    st, liq = preparar(db, tmp_path)
    r = auditor.get("/analitica/gastos", params={"periodo": "2026-08", "estado": "verificado"})
    assert r.status_code == 200
    assert all(g["estado"] == "verificado" for g in r.json()["gastos"])
    assert auditor.get("/analitica/gastos", params={"periodo": "2026-08", "estado": "zzz"}).status_code == 422
    assert auditor.get("/analitica/gastos", params={"periodo": "2020-01"}).status_code == 404


def test_endpoint_requiere_sesion(db, cliente):
    assert cliente.get("/analitica/indice").status_code in (401, 403)
```

Más un test de propietario (con el fixture/patrón que exista): el propietario recibe 200 pero
con `solo_publicado` (con la liquidación en `procesada`, sus `periodos` vienen vacíos; al
publicarla, aparece). Escribirlo con el helper real que usen los demás tests de propietario.

- [ ] **Step 2: Verificar que fallan** — 404 en los endpoints.

- [ ] **Step 3: Implementar `api/app/routers/analitica.py`**

```python
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .. import analitica, models, security
from ..db import get_db

router = APIRouter(prefix="/analitica", tags=["analitica"])
ROLES = ("auditor", "consejo", "moderador", "propietario")


@router.get("/indice")
def indice(desde: str = "", hasta: str = "", db: Session = Depends(get_db),
           s: dict = Depends(security.requiere(*ROLES))):
    return analitica.metricas(db, desde, hasta, solo_publicado=s["rol"] == "propietario")


@router.get("/gastos")
def gastos(periodo: str, estado: str = "", db: Session = Depends(get_db),
           s: dict = Depends(security.requiere(*ROLES))):
    if estado and estado not in analitica.ESTADOS_GASTO:
        raise HTTPException(422, "Estado inválido; válidos: " + ", ".join(analitica.ESTADOS_GASTO))
    solo_pub = s["rol"] == "propietario"
    estados_liq = ("publicada",) if solo_pub else ("procesada", "publicada")
    liq = (db.query(models.Liquidacion).filter_by(periodo=periodo)
             .filter(models.Liquidacion.estado.in_(estados_liq)).first())
    if not liq:
        raise HTTPException(404, "No hay liquidación de ese período")
    filas, _hs, _abiertos = analitica.evaluar_liquidacion(db, liq, solo_pub)
    out = []
    for g, est, halls, dd in filas:
        if estado and est != estado:
            continue
        out.append({"n": g.n, "proveedor": g.proveedor, "categoria": g.categoria,
                    "concepto": g.concepto[:160], "importe": g.importe, "estado": est,
                    "hallazgos": [{"id": h.id, "severidad": h.severidad, "estado": h.estado,
                                   "titulo": h.titulo} for h in halls],
                    "documentos": [{"id": d.id, "tipo": d.tipo,
                                    "archivo": d.archivo_key.rsplit("/", 1)[-1]} for d in dd]})
    return {"periodo": periodo, "gastos": out}
```

Registrarlo en `api/app/main.py` igual que los demás routers (import + `app.include_router`).

Nota de diseño (desvío consciente de la spec, ya validado): el drill-down "cada métrica con su
lista de ids" se materializa vía `/analitica/gastos?periodo&estado=` (listas por estado con
hallazgos y documentos por gasto) en lugar de embeber ids en `/indice` — misma evidencia,
respuesta del índice más liviana.

- [ ] **Step 4: Suite completa de la API** — verde (≈180).

- [ ] **Step 5: Commit**

```bash
cd /opt/consorcios-transparentes && git add api/app/routers/analitica.py api/app/main.py api/tests/test_analitica.py && git commit -m "API: endpoints /analitica/indice y /analitica/gastos con gating por rol

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

### Task 3: MCP — `indice_transparencia` y `estado_gastos`

**Files:**
- Modify: `api/servidor_mcp.py` (dos tools + registrarlas donde se registran las demás — leer el archivo para encontrar el bloque de registro)
- Modify: `docs/MCP.md` (tabla de herramientas + conteo)
- Test: `api/tests/test_mcp.py` (leer sus stubs primero y seguir el patrón exacto)

- [ ] **Step 1: Tests que fallan** — en `api/tests/test_mcp.py`, con el stub de cliente que ya
usan las demás tools (mismo mecanismo de monkeypatch), agregar: `indice_transparencia` devuelve
un texto que contiene "ÍNDICE DE TRANSPARENCIA" y el número; `estado_gastos` lista gastos con
su estado. Respuestas stub mínimas con la forma de los endpoints de la Task 2.

- [ ] **Step 2: Verificar que fallan.**

- [ ] **Step 3: Implementar** — junto a las demás tools de `api/servidor_mcp.py`:

```python
@_con_api
def indice_transparencia(desde: str = "", hasta: str = "") -> str:
    """Índice de transparencia del consorcio: % del dinero trazable de punta a punta
    (gastos verificados), % con factura adjunta, % de pagos respaldados y cuestiones
    pendientes por severidad. Rango opcional de períodos AAAA-MM."""
    d = _cliente().get("/analitica/indice", {"desde": desde, "hasta": hasta})
    t = d["totales"]
    lineas = [
        f"ÍNDICE DE TRANSPARENCIA: {d['indice']} / 100 (rango {d['rango']['desde']}–{d['rango']['hasta']})",
        f"Dinero analizado: {_plata(t['dinero_total'])} — trazable de punta a punta: {t['pct_trazable']:.0%}",
        f"Con factura adjunta: {t['pct_con_factura']:.0%} · pagos respaldados: {t['pct_pago_respaldado']:.0%}",
        "Cuestiones abiertas: " + (", ".join(f"{k} {v}" for k, v in t["hallazgos_abiertos"].items() if v) or "ninguna")
        + f" · resueltas: {t['hallazgos_resueltos']}",
        "Gastos por estado:",
    ]
    for est, v in t["gastos_por_estado"].items():
        if v["cantidad"]:
            lineas.append(f"  {est}: {v['cantidad']} gasto(s), {_plata(v['importe'])}")
    lineas.append("Índice por período: " + " · ".join(f"{p['periodo']}: {p['indice']}" for p in d["periodos"]))
    return "\n".join(lineas)


@_con_api
def estado_gastos(periodo: str, estado: str = "") -> str:
    """Estado de cada gasto de un período (verificado, requiere_explicacion, anomalia,
    inconsistencia o sin_informacion), con los hallazgos y documentos que lo justifican.
    `estado` filtra por uno de esos valores."""
    d = _cliente().get("/analitica/gastos", {"periodo": periodo, "estado": estado})
    if not d["gastos"]:
        return f"Sin gastos {('en estado ' + estado) if estado else ''} en {periodo}."
    lineas = []
    for g in d["gastos"]:
        halls = "; ".join(f"[{h['severidad']}] {h['titulo'][:70]}" for h in g["hallazgos"]) or "sin hallazgos abiertos"
        docs = ", ".join(f"{x['tipo']}:{x['archivo']}" for x in g["documentos"]) or "sin documentos"
        lineas.append(f"gasto {g['n']} · {g['proveedor']} · {_plata(g['importe'])} · {g['estado'].upper()}\n"
                      f"    {halls}\n    docs: {docs}")
    return "\n".join(lineas)
```

Registrarlas en el mismo bloque donde se registran las demás (el archivo lo muestra; agregar
ambas). En `docs/MCP.md`: sumar una fila "Transparencia | `indice_transparencia`,
`estado_gastos` | \"¿Qué tan auditable es el consorcio?\" · \"¿Qué gastos les falta respaldo en
agosto?\"" y actualizar el conteo de herramientas del título de la tabla.

- [ ] **Step 4: Suite API completa** — verde.

- [ ] **Step 5: Commit**

```bash
cd /opt/consorcios-transparentes && git add api/servidor_mcp.py api/tests/test_mcp.py docs/MCP.md && git commit -m "MCP: índice de transparencia y estado de gastos como herramientas

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

### Task 4: Web — página `panel/transparencia`

**Files:**
- Modify: `web/lib/api.ts` (tipos + 2 métodos)
- Create: `web/components/estado-gasto.tsx` (chip de los 5 estados)
- Create: `web/app/panel/transparencia/page.tsx`
- Modify: `web/components/sidebar.tsx` (entrada de navegación)
- Test: `web/tests/transparencia.test.tsx`

Antes de codear, leer `web/app/panel/analisis/page.tsx`, `web/lib/api.ts`, `web/components/severidad.tsx`, `web/components/chip-base.ts` y `web/tests/analisis.test.tsx`: la página nueva DEBE calcar esos patrones (client component, `api.` tipada, Cards, Skeleton, tablas a mano, `moneda`/`mensajeError`, chips con `CHIP_BASE`).

- [ ] **Step 1: Test que falla** — `web/tests/transparencia.test.tsx`:

```tsx
import { http, HttpResponse } from "msw";
import { render, screen } from "@testing-library/react";
import { servidor, API } from "./msw";
import PaginaTransparencia from "@/app/panel/transparencia/page";

const INDICE = {
  indice: 62,
  rango: { desde: "2026-07", hasta: "2026-08" },
  totales: {
    dinero_total: 1000, dinero_verificado: 620, dinero_con_factura: 810, dinero_pago_respaldado: 700,
    pct_trazable: 0.62, pct_con_factura: 0.81, pct_pago_respaldado: 0.7, indice: 62,
    gastos_por_estado: {
      verificado: { cantidad: 10, importe: 620 }, requiere_explicacion: { cantidad: 3, importe: 100 },
      anomalia: { cantidad: 2, importe: 150 }, inconsistencia: { cantidad: 1, importe: 80 },
      sin_informacion: { cantidad: 1, importe: 50 },
    },
    hallazgos_abiertos: { "CRÍTICO": 1, ALTO: 2, MEDIO: 3, BAJO: 0 }, hallazgos_resueltos: 4,
  },
  periodos: [{ periodo: "2026-08", indice: 62, pct_trazable: 0.62, pct_con_factura: 0.81,
               pct_pago_respaldado: 0.7, dinero_total: 1000, dinero_verificado: 620,
               dinero_con_factura: 810, dinero_pago_respaldado: 700,
               gastos_por_estado: { verificado: { cantidad: 10, importe: 620 }, requiere_explicacion: { cantidad: 3, importe: 100 }, anomalia: { cantidad: 2, importe: 150 }, inconsistencia: { cantidad: 1, importe: 80 }, sin_informacion: { cantidad: 1, importe: 50 } },
               hallazgos_abiertos: { "CRÍTICO": 1, ALTO: 2, MEDIO: 3, BAJO: 0 }, hallazgos_resueltos: 4 }],
};

const GASTOS = { periodo: "2026-08", gastos: [
  { n: 25, proveedor: "MARIO LEONARDO ROTH", categoria: "ABONOS", concepto: "Serpentina",
    importe: 2650000, estado: "anomalia",
    hallazgos: [{ id: 7, severidad: "ALTO", estado: "pendiente", titulo: "transferencia sin respaldo" }],
    documentos: [{ id: 1, tipo: "factura", archivo: "fc.pdf" }] },
] };

test("muestra el índice, las métricas y el drill-down", async () => {
  servidor.use(
    http.get(`${API}/analitica/indice`, () => HttpResponse.json(INDICE)),
    http.get(`${API}/analitica/gastos`, () => HttpResponse.json(GASTOS)),
  );
  render(<PaginaTransparencia />);
  expect(await screen.findByText(/62/)).toBeInTheDocument();
  expect(screen.getByText(/trazable/i)).toBeInTheDocument();
  expect(await screen.findByText(/ROTH/)).toBeInTheDocument();
  expect(screen.getByText(/transferencia sin respaldo/)).toBeInTheDocument();
});
```

- [ ] **Step 2: Verificar que falla** — `cd /opt/consorcios-transparentes/web && npm test` (módulo inexistente).

- [ ] **Step 3: Implementar.**

`web/lib/api.ts` — tipos + métodos (seguir el patrón `pedir<T>` y `URLSearchParams` del archivo):

```tsx
export interface StatsTransparencia {
  periodo?: string;
  indice: number;
  dinero_total: number; dinero_verificado: number; dinero_con_factura: number; dinero_pago_respaldado: number;
  pct_trazable: number; pct_con_factura: number; pct_pago_respaldado: number;
  gastos_por_estado: Record<string, { cantidad: number; importe: number }>;
  hallazgos_abiertos: Record<string, number>;
  hallazgos_resueltos: number;
}
export interface IndiceTransparencia {
  indice: number;
  rango: { desde: string; hasta: string };
  totales: StatsTransparencia;
  periodos: StatsTransparencia[];
}
export interface GastoConEstado {
  n: number; proveedor: string; categoria: string; concepto: string; importe: number; estado: string;
  hallazgos: { id: number; severidad: string; estado: string; titulo: string }[];
  documentos: { id: number; tipo: string; archivo: string }[];
}
```

y en el objeto `api`:

```tsx
  indiceTransparencia(desde?: string, hasta?: string) {
    const p = new URLSearchParams();
    if (desde) p.set("desde", desde);
    if (hasta) p.set("hasta", hasta);
    const qs = p.toString();
    return pedir<IndiceTransparencia>(`/analitica/indice${qs ? `?${qs}` : ""}`);
  },
  gastosTransparencia(periodo: string, estado?: string) {
    const p = new URLSearchParams({ periodo });
    if (estado) p.set("estado", estado);
    return pedir<{ periodo: string; gastos: GastoConEstado[] }>(`/analitica/gastos?${p}`);
  },
```

`web/components/estado-gasto.tsx`:

```tsx
import { CHIP_BASE } from "@/components/chip-base";

export const ETIQUETAS_ESTADO_GASTO: Record<string, string> = {
  verificado: "✅ Verificado",
  requiere_explicacion: "🟡 Requiere explicación",
  anomalia: "🟠 Anomalía",
  inconsistencia: "🔴 Inconsistencia",
  sin_informacion: "⚪ Sin información",
};

const CLASES: Record<string, string> = {
  verificado: "bg-[#DCFCE7] text-[#0E7A4E]",
  requiere_explicacion: "bg-[#FEF0C7] text-[#93540B]",
  anomalia: "bg-[#FFEAD5] text-[#B93815]",
  inconsistencia: "bg-[#FEE4E2] text-[#B42318]",
  sin_informacion: "bg-[#E2E8F0] text-[#475569]",
};

export function ChipEstadoGasto({ estado }: { estado: string }) {
  return (
    <span className={`${CHIP_BASE} ${CLASES[estado] ?? CLASES.sin_informacion}`}>
      {ETIQUETAS_ESTADO_GASTO[estado] ?? estado}
    </span>
  );
}
```

`web/app/panel/transparencia/page.tsx` — client component, estructura (respetar el estilo de
`analisis`; el código exacto de barras/tablas queda a criterio del implementador PERO con estos
contenidos obligatorios):

1. Card grande del índice: número `indice` / 100 + rango + leyenda "porcentaje del dinero
   trazable de punta a punta" + fórmula en una línea chica (transparencia del cálculo).
2. Tres barras de progreso (divs con width %): trazable, con factura, pagos respaldados —
   cada una con su porcentaje y el importe.
3. Card "Estados de los gastos": tabla con chip + cantidad + importe por estado; cada fila es
   clickeable y carga el drill-down (`api.gastosTransparencia(periodo, estado)`).
4. Selector de período (los de `periodos`, default el último) + tabla drill-down: n, proveedor,
   importe (`moneda`), `ChipEstadoGasto`, hallazgos abiertos (título + severidad con el
   componente `Severidad` existente si aplica) y documentos (nombre).
5. Card "Cuestiones": hallazgos abiertos por severidad + resueltas.
6. Patrón de carga/error idéntico a `analisis` (Skeleton / Card con Reintentar / toast).

`web/components/sidebar.tsx`: agregar `{ href: "/panel/transparencia", texto: "Transparencia", Icono: Gauge }` (importar `Gauge` de lucide-react; si no existe, usar `ShieldCheck`) en `SECCIONES`, después de "Análisis".

- [ ] **Step 4: Verificar** — `cd /opt/consorcios-transparentes/web && npm test` todo verde (43+). Si el entorno exige `NODE_OPTIONS='--experimental-require-module'` (Node 22.11), usarlo.

- [ ] **Step 5: Commit**

```bash
cd /opt/consorcios-transparentes && git add web/lib/api.ts web/components/estado-gasto.tsx web/app/panel/transparencia/page.tsx web/components/sidebar.tsx web/tests/transparencia.test.tsx && git commit -m "Panel: página de transparencia con índice, métricas y drill-down por gasto

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

### Task 5: Web — sección Transparencia en `mi-unidad`

**Files:**
- Modify: `web/app/mi-unidad/page.tsx`
- Test: `web/tests/mi-unidad.test.tsx` (agregar un test)

- [ ] **Step 1: Test que falla** — en `web/tests/mi-unidad.test.tsx`, siguiendo sus mocks
existentes, agregar el handler `http.get(`${API}/analitica/indice`, ...)` con un JSON mínimo
(como el de la Task 4, puede ser reducido) y asertar que la página muestra "Transparencia",
el índice y al menos una métrica. Si la página ya tiene tests que fallan por el fetch nuevo
sin handler, agregar el handler a esos tests también (MSW responde 500 a lo no mockeado).

- [ ] **Step 2: Verificar que falla.**

- [ ] **Step 3: Implementar** — en `web/app/mi-unidad/page.tsx`, después de los links de
descarga/reglamento y antes del iframe del informe, una Card "Transparencia" que:
- fetch `api.indiceTransparencia()` (la API ya filtra por rol: el propietario recibe solo lo
  publicado — el front NO decide qué mostrar);
- muestra el índice grande + la leyenda "% del dinero con trazabilidad documental completa
  sobre las liquidaciones publicadas", las tres barras de porcentaje y los conteos por estado
  con `ChipEstadoGasto`;
- si `periodos` viene vacío (nada publicado aún), la card muestra "Todavía no hay períodos
  publicados." y nada más;
- errores: la card se oculta en silencio (el resto de mi-unidad no puede romperse por esto —
  mismo espíritu que el contador de pendientes del layout del panel).

- [ ] **Step 4: Verificar** — suite web completa verde.

- [ ] **Step 5: Commit**

```bash
cd /opt/consorcios-transparentes && git add web/app/mi-unidad/page.tsx web/tests/mi-unidad.test.tsx && git commit -m "Mi unidad: card de transparencia para propietarios sobre lo publicado

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

### Task 6: Docs

**Files:**
- Modify: `docs/ESTADO.md`

- [ ] **Step 1:** Leer `docs/ESTADO.md` y agregar la entrada del ciclo (06-09-2026): índice de
transparencia + estados por gasto (spec `docs/superpowers/specs/2026-09-06-indice-transparencia-design.md`),
página del panel + card de propietarios + 2 tools MCP; actualizar contadores de tests; nota
"pendiente de deploy (api + worker + mcp + web)". Pendientes siguen: B (prorrateo) → D (OCR).

- [ ] **Step 2: Commit**

```bash
cd /opt/consorcios-transparentes && git add docs/ESTADO.md docs/superpowers/plans/2026-09-06-indice-transparencia.md && git commit -m "Docs: estado con el índice de transparencia

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

### Verificación final (orquestador)

- [ ] Suites: api y web completas en verde; revisión final del rango.
- [ ] Deploy con confirmación del usuario: rebuild api/worker/mcp + `npm run deploy:cf` para el
  Worker del panel; smoke: `/analitica/indice` real de julio+agosto contra un conteo manual,
  la página en producción, la card de mi-unidad con un usuario propietario, y las 2 tools MCP.
