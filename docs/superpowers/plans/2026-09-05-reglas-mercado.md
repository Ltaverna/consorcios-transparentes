# Reglas de mercado + biblioteca de normativa — Plan de implementación

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** tres reglas del motor que comparan sueldos, honorarios y abonos contra referencias de mercado cargadas por el auditor, más los PDFs de normativa de respaldo subibles al panel.

**Architecture:** los valores de referencia son campos nuevos de la `Config` de `engine/ct/rules.py` (el editor de umbrales del panel y la validación de la API son dinámicos sobre los campos de la dataclass — aparecen solos); las reglas siguen el patrón `@rule` con claves estables; la normativa replica el patrón del reglamento (slots fijos en storage) pero con lectura equipo-solo.

**Tech Stack:** lo existente; sin dependencias nuevas.

**Spec:** `docs/superpowers/specs/2026-09-05-reglas-mercado-design.md`.

**Contexto de la máquina:** suites hoy: engine 45 · api 106 (o 109 si el plan de portabilidad ya mergeó — usar el número que dé la corrida base) · web 40. Rama: `reglas-mercado` desde `main`. Commits en español + trailer. Los fixtures reales están en `engine/tests/fixtures/` (texto de `pdftotext -layout`); mirar cómo los cargan `test_rules_config.py`/`test_rules_claves.py` y `test_parser.py`.

---

### Task 1: Engine — `Config` + las tres reglas

**Files:**
- Modify: `engine/ct/rules.py`
- Test: `engine/tests/test_rules_mercado.py` (nuevo)
- Docs: `docs/reglas.md` (fila por regla nueva en el catálogo)

- [ ] **Step 0: Calibrar la detección contra el fixture real.** Antes de escribir tests, cargar la liquidación real de agosto como lo hacen los tests existentes e imprimir (script efímero o `pytest -s` temporal): los gastos con categoría que contenga `SUELDO`, los de categoría con `ADMINISTRACION`, y los que matcheen `ascensor|matafuego|extinguidor|limpieza` en concepto+proveedor. Con eso fijar los patrones de detección definitivos (el sueldo neto debe excluir F.931/cargas/retenciones; los honorarios son el total de la categoría de administración). Reportar en el resultado de la tarea qué gastos detecta cada patrón en agosto — es la evidencia de calibración.

- [ ] **Step 1: Tests que fallan.** Crear `engine/tests/test_rules_mercado.py` con el patrón de carga de fixture de los tests vecinos. Estructura de los casos (los montos exactos salen de la calibración del Step 0 — completarlos con los valores reales detectados):

```python
"""Reglas de mercado: comparación contra referencias cargadas por el auditor."""
from ct.rules import Config, evaluar
# + el helper de carga del fixture real que usen los tests vecinos (p.ej. cargar agosto)


def _hallazgos(regla, liq, cfg):
    return [h for h in evaluar(liq, None, cfg) if h.regla == regla]


def test_sueldo_sobre_la_referencia_dispara(liq_agosto):
    # referencia bien por debajo del neto real detectado → dispara hacia arriba
    cfg = Config(sueldo_encargado_ref=<neto_real * 0.7>, sueldo_tolerancia=0.10)
    hs = _hallazgos("sueldo_mercado", liq_agosto, cfg)
    assert len(hs) == 1 and hs[0].severidad == "ALTO"  # excede el doble de la tolerancia
    assert "sobre la referencia" in hs[0].titulo


def test_sueldo_bajo_escala_es_alto(liq_agosto):
    cfg = Config(sueldo_encargado_ref=<neto_real * 1.5>, sueldo_tolerancia=0.10)
    hs = _hallazgos("sueldo_mercado", liq_agosto, cfg)
    assert len(hs) == 1 and hs[0].severidad == "ALTO"
    assert "bajo la" in hs[0].titulo and "fuera de recibo" in hs[0].recomendacion


def test_sueldo_dentro_de_banda_no_dispara(liq_agosto):
    cfg = Config(sueldo_encargado_ref=<neto_real>, sueldo_tolerancia=0.10)
    assert _hallazgos("sueldo_mercado", liq_agosto, cfg) == []


def test_referencia_cero_apaga_las_reglas(liq_agosto):
    cfg = Config()  # todos los refs en 0
    for regla in ("sueldo_mercado", "honorarios_mercado", "abonos_mercado"):
        assert _hallazgos(regla, liq_agosto, cfg) == []


def test_honorarios_sobre_referencia(liq_agosto):
    cfg = Config(honorarios_ref=<honorarios_reales * 0.8>, honorarios_tolerancia=0.10)
    hs = _hallazgos("honorarios_mercado", liq_agosto, cfg)
    assert len(hs) == 1 and hs[0].severidad in ("MEDIO", "ALTO")
    # honorarios baratos NO disparan:
    assert _hallazgos("honorarios_mercado", liq_agosto,
                      Config(honorarios_ref=<honorarios_reales * 2>, honorarios_tolerancia=0.10)) == []


def test_abono_sobre_tope(liq_agosto):
    cfg = Config(abono_matafuegos_ref=<abono_real * 0.5>)
    hs = _hallazgos("abonos_mercado", liq_agosto, cfg)
    assert hs and all(h.severidad == "MEDIO" for h in hs)
    assert any("matafuego" in h.titulo.lower() or "extinguidor" in h.evidencia.lower() for h in hs)
```

(Los `<...>` se reemplazan por números concretos del Step 0 — NO son placeholders del plan sino de la calibración; el archivo final no tiene ninguno. Si agosto no tiene abono de matafuegos detectable, usar el rubro que sí exista y reportarlo.)

- [ ] **Step 2:** correr → FAIL (reglas inexistentes).

- [ ] **Step 3: Implementar en `rules.py`.**
  - `Config` gana (con comentarios estilo del archivo):

```python
    # --- referencias de mercado (0 = regla apagada; las carga el auditor por paritaria) ---
    sueldo_encargado_ref: float = 0.0      # neto mensual según escala SUTERH vigente
    sueldo_tolerancia: float = 0.10
    honorarios_ref: float = 0.0            # honorarios de administración de referencia (mensual)
    honorarios_tolerancia: float = 0.10
    abono_ascensores_ref: float = 0.0      # tope mensual por rubro de abono
    abono_matafuegos_ref: float = 0.0
    abono_limpieza_ref: float = 0.0
```

  - Tres reglas nuevas al final, patrón de las existentes (claves estables; detección con los patrones calibrados en el Step 0):

```python
@rule("sueldo_mercado")
def r_sueldo_mercado(liq, prev, cfg):
    if not cfg.sueldo_encargado_ref:
        return []
    netos = [g for g in liq.gastos if <patrón calibrado de sueldo neto>]
    if not netos:
        return []
    total = sum(g.importe for g in netos)
    desvio = total / cfg.sueldo_encargado_ref - 1
    if abs(desvio) <= cfg.sueldo_tolerancia:
        return []
    refs = [str(g.n) for g in netos]
    ev = (f"Sueldos netos del mes: {fmt(total)}; referencia de escala cargada por el auditor: "
          f"{fmt(cfg.sueldo_encargado_ref)} (desvío {pct(desvio)}).")
    if desvio > 0:
        sev = "ALTO" if desvio > 2 * cfg.sueldo_tolerancia else "MEDIO"
        return [Hallazgo("sueldo_mercado", sev, "Mercado", f"Sueldo {pct(desvio)} sobre la referencia de escala",
                         ev, total - cfg.sueldo_encargado_ref,
                         "Pedir el recibo de sueldo y la justificación del excedente (horas extra, retroactivos, plus).",
                         refs, clave="sueldo-sobre-escala")]
    return [Hallazgo("sueldo_mercado", "ALTO", "Mercado", f"Sueldo {pct(-desvio)} bajo la escala vigente",
                     ev, cfg.sueldo_encargado_ref - total,
                     "Verificar si hay pagos fuera de recibo: pagar bajo escala expone al consorcio a reclamos laborales.",
                     refs, clave="sueldo-bajo-escala")]
```

(`honorarios_mercado`: total de la categoría de administración vs `honorarios_ref * (1 + honorarios_tolerancia)`, solo hacia arriba, sev MEDIO / ALTO al doble, clave `honorarios-sobre-referencia`. `abonos_mercado`: constante de módulo `ABONOS = [("ascensores", r"ascensor", "abono_ascensores_ref"), ("matafuegos", r"matafuego|extinguidor", "abono_matafuegos_ref"), ("limpieza", r"limpieza", "abono_limpieza_ref")]`; por rubro con ref > 0, gastos que matcheen el patrón en concepto+proveedor; si `sum > ref` → MEDIO con clave `abono-caro:<rubro>`, evidencia con ambos montos. Escribir el código completo de las tres, no solo la primera.)

  - `docs/reglas.md`: una fila por regla nueva en la tabla del catálogo (umbral, severidad), y borrar/ajustar la línea "Escala SUTERH…" de la sección de pendientes si existe.

- [ ] **Step 4:** suite engine completa → 45 + 6 = 51 passed (ajustar al número real de tests escritos y reportar).

- [ ] **Step 5: Commit.**

```bash
git add engine/ct/rules.py engine/tests/test_rules_mercado.py docs/reglas.md
git commit -m "Engine: reglas de mercado (sueldo vs escala, honorarios y abonos vs referencia)"
```

### Task 2: API — biblioteca de normativa (equipo-solo)

**Files:**
- Modify: `api/app/routers/consorcio.py`
- Test: `api/tests/test_consorcio_api.py`

- [ ] **Step 1: Tests que fallan.** En `api/tests/test_consorcio_api.py` (los tests de reglamento del archivo son el patrón; para el 403 del propietario, usar el patrón login-unidad de los tests de documentos):

```python
def test_normativa_slots_subida_y_lectura_de_equipo(db, auditor):
    import io
    r = auditor.post("/consorcio/normativa/escala-suterh",
                     files={"archivo": ("escala.pdf", io.BytesIO(b"%PDF-escala"), "application/pdf")})
    assert r.status_code == 200
    est = auditor.get("/consorcio/normativa").json()
    assert est == {"escala-suterh": True, "acuerdo-paritario": False, "referencia-honorarios": False}
    d = auditor.get("/consorcio/normativa/escala-suterh")
    assert d.status_code == 200 and "attachment" in d.headers.get("content-disposition", "")
    assert auditor.get("/consorcio/normativa/otra-cosa").status_code == 404
    assert auditor.get("/consorcio/normativa/acuerdo-paritario").status_code == 404  # slot vacío


def test_normativa_es_solo_del_equipo(db, auditor, <fixture/armado de propietario>):
    # propietario logueado por login-unidad:
    assert propietario.get("/consorcio/normativa").status_code == 403
    assert propietario.get("/consorcio/normativa/escala-suterh").status_code == 403
    assert propietario.post("/consorcio/normativa/escala-suterh").status_code == 403
```

- [ ] **Step 2:** correr → FAIL.

- [ ] **Step 3: Implementar** en `consorcio.py`, junto al bloque del reglamento:

```python
SLOTS_NORMATIVA = ("escala-suterh", "acuerdo-paritario", "referencia-honorarios")


def _key_normativa(tipo: str) -> str:
    if tipo not in SLOTS_NORMATIVA:
        raise HTTPException(404, "No existe ese documento de normativa")
    return f"consorcio/normativa/{tipo}.pdf"


@router.get("/consorcio/normativa")
def estado_normativa(request: Request,
                     s: dict = Depends(security.requiere("auditor", "consejo", "moderador"))):
    st = request.app.state.storage
    return {t: st.existe(f"consorcio/normativa/{t}.pdf") for t in SLOTS_NORMATIVA}


@router.post("/consorcio/normativa/{tipo}")
def subir_normativa(tipo: str, request: Request, archivo: UploadFile,
                    s: dict = Depends(security.requiere("auditor"))):
    key = _key_normativa(tipo)
    data = archivo.file.read(MAX_REGLAMENTO_MB * 1024 * 1024 + 1)
    if len(data) > MAX_REGLAMENTO_MB * 1024 * 1024:
        raise HTTPException(413, f"El archivo supera los {MAX_REGLAMENTO_MB} MB")
    request.app.state.storage.guardar(key, data)
    return {"ok": True, "tipo": tipo}


@router.get("/consorcio/normativa/{tipo}")
def ver_normativa(tipo: str, request: Request,
                  s: dict = Depends(security.requiere("auditor", "consejo", "moderador"))):
    key = _key_normativa(tipo)
    if not request.app.state.storage.existe(key):
        raise HTTPException(404, "Ese documento todavía no está cargado")
    return _servir(request, key)
```

(Orden de rutas: el `GET /consorcio/normativa` estático antes del `/{tipo}`. El propietario recibe 403 del `requiere` — distinto del reglamento, que es de cualquier sesión: es material de trabajo del triage.)

- [ ] **Step 4:** suite api completa → base + 2 (reportar el número exacto).

- [ ] **Step 5: Commit.**

```bash
git add api/app/routers/consorcio.py api/tests/test_consorcio_api.py
git commit -m "API: biblioteca de normativa de referencia (equipo-solo)"
```

### Task 3: Web — Card "Normativa de referencia" en Consorcio

**Files:**
- Modify: `web/app/panel/consorcio/page.tsx`, `web/lib/api.ts`
- Test: `web/tests/consorcio.test.tsx`

- [ ] **Step 1: Test que falla.** En `web/tests/consorcio.test.tsx`: al test de consejo, sumar `expect(screen.queryByText(/Normativa/)).not.toBeInTheDocument();`; al test de auditor existente (el que ya mockea `/consorcio/reglamento`), sumar el handler `http.get(`${API}/consorcio/normativa`, () => HttpResponse.json({ "escala-suterh": false, "acuerdo-paritario": false, "referencia-honorarios": false }))` y el assert `expect(await screen.findByText(/Normativa de referencia/)).toBeInTheDocument();`.

- [ ] **Step 2:** correr → FAIL.

- [ ] **Step 3: Implementar.**
  - `web/lib/api.ts`: `estadoNormativa()` → `pedir<Record<string, boolean>>("/consorcio/normativa")`; `subirNormativa(tipo: string, form: FormData)` (POST multipart, patrón de `subirReglamento`); `urlNormativa(tipo: string)` (patrón `urlReglamento`).
  - `web/app/panel/consorcio/page.tsx`: componente `CardNormativa` (calcado de `CardReglamento`, en el mismo archivo) con los tres slots — etiquetas humanas: "Escala SUTERH", "Acuerdo paritario", "Referencia de honorarios" — cada uno con estado (cargado → link de descarga con `urlNormativa` / falta), input de archivo y botón subir. Renderizado junto a `CardReglamento` dentro del bloque de auditor.

- [ ] **Step 4:** `NODE_OPTIONS='--experimental-require-module' npm test` → base + 0 tests nuevos como archivos (asserts en tests existentes; si preferiste un test aparte, reportar el conteo). `npm run build` → OK.

- [ ] **Step 5: Commit.**

```bash
git add web/app/panel/consorcio/page.tsx web/lib/api.ts web/tests/consorcio.test.tsx
git commit -m "Web: biblioteca de normativa de referencia en Consorcio"
```

### Task 4: Cierre — suites, docs, merge y carga inicial (CON el usuario)

- [ ] **Step 1:** Suites completas (engine/api/web + build) — reportar conteos.
- [ ] **Step 2:** `docs/ESTADO.md`: reglas de mercado implementadas (pendiente 5 resuelto); commit + merge a `main`.
- [ ] **Step 3: Producción (CON confirmación):** push + rebuild API + deploy front.
- [ ] **Step 4: Investigación de valores vigentes (el controller de la sesión, no un subagente de código):** buscar con fuentes citadas la escala SUTERH vigente del período (pedirle al usuario la categoría del edificio y datos del encargado si hacen falta), la referencia de honorarios de administración (CAPHAI u otra fuente citable) y rangos de abonos. Presentar al usuario para validación — NADA se carga sin su ok.
- [ ] **Step 5: Carga inicial (tras validación):** setear los umbrales vía panel o API (`PUT /consorcio` con el dict de umbrales), subir los PDFs de normativa disponibles, y **reprocesar julio y agosto** re-subiendo cada PDF por la API (idempotente: el triage sobrevive por claves estables) para que las reglas nuevas corran sobre los meses cargados. Verificar los hallazgos nuevos en el panel y decidir su publicación (triage del usuario).
