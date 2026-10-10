# Voto del propietario desde su teléfono — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Sumar a la app de asamblea un segundo modo de votación en el que cada propietario vota desde su
teléfono, con bloqueo de unidad en el servidor, conviviendo con el modo moderador actual.

**Architecture:** Backend nuevo en la API del panel (FastAPI + Postgres): tres tablas
(`asamblea_sesion` con el estado "blando" en JSON + `version`; `asamblea_claim` con `UNIQUE(sesion_id,uf)` =
el candado; `asamblea_voto` con `UNIQUE(sesion_id,mocion_idx,uf)`) y endpoints de estado/claim/voto/override.
El cliente (`apps/asamblea/make_votacion.py`) deja de sincronizar contra la hoja de Google y pasa a hablar
con la API cada ~2s, sumando el alta del propietario y la vista "Tus unidades".

**Tech Stack:** Python 3 / FastAPI / SQLAlchemy (`Mapped`/`mapped_column`) / Postgres (SQLite en tests) /
pytest; cliente JS vanilla embebido por `make_votacion.py`, tests con `node:test`.

**Spec:** `docs/superpowers/specs/2026-10-10-voto-propietario-design.md`

**Convenciones del repo (leer antes de empezar):**
- Tests de la API: `cd api && .venv/bin/python -m pytest -q`. SQLite en memoria vía `tests/conftest.py`
  (setea `CT_*` por env antes de importar `app`). Fixtures `db` y `cliente` (TestClient) ya existen.
- Settings: `api/app/config.py`, prefijo `CT_`, `.env`. **Regla de oro: en `api/.env` se AGREGAN líneas,
  nunca se reescribe el archivo entero.**
- Tablas: se crean con `Base.metadata.create_all(engine)` (ya en `api/app/main.py`).
- Helpers de modelos en `api/app/models.py`: `JSONDict`, `FechaUTC`, `ahora()`.
- Cliente: `cd apps/asamblea && node --test` (26 tests hoy). Generar: `cd apps/asamblea &&
  CT_ASAMBLEA_TOKEN=... python3 make_votacion.py` (escribe `pages-out/index.html`). El JS puro de lógica va
  en `logica.js` (no debe contener la secuencia `</script`).
- Commits en español, sin auto-commit salvo que el plan lo indique como paso.

---

## BLOQUE A — API (backend)

### Task 1: Settings + modelos de las tres tablas

**Files:**
- Modify: `api/app/config.py` (agregar `asamblea_mod_token`)
- Modify: `api/app/models.py` (tres clases nuevas al final)
- Test: `api/tests/test_asamblea_estado.py` (nuevo)

- [ ] **Step 1: Escribir el test que falla (las tablas existen y crean filas)**

Crear `api/tests/test_asamblea_estado.py`:

```python
from app.db import SessionLocal
from app.models import AsambleaSesion, AsambleaClaim, AsambleaVoto


def test_modelos_crean_filas(db):
    s = AsambleaSesion(titulo="Asamblea test", doc={"mociones": []}, version=1)
    db.add(s)
    db.flush()
    db.add(AsambleaClaim(sesion_id=s.id, uf=3, device_id="dev-1", rol="titular"))
    db.add(AsambleaVoto(sesion_id=s.id, mocion_idx=0, uf=3, opcion_idx=1, device_id="dev-1"))
    db.commit()
    assert db.query(AsambleaClaim).filter_by(sesion_id=s.id, uf=3).one().device_id == "dev-1"
    assert db.query(AsambleaVoto).filter_by(sesion_id=s.id, uf=3).one().opcion_idx == 1


def test_claim_uf_es_unico(db):
    import pytest
    from sqlalchemy.exc import IntegrityError
    s = AsambleaSesion(titulo="t", doc={}, version=1)
    db.add(s); db.flush()
    db.add(AsambleaClaim(sesion_id=s.id, uf=5, device_id="a", rol="titular")); db.commit()
    db.add(AsambleaClaim(sesion_id=s.id, uf=5, device_id="b", rol="titular"))
    with pytest.raises(IntegrityError):
        db.commit()
```

- [ ] **Step 2: Correr el test y verlo fallar**

Run: `cd api && .venv/bin/python -m pytest tests/test_asamblea_estado.py -q`
Expected: FAIL con `ImportError: cannot import name 'AsambleaSesion'`.

- [ ] **Step 3: Agregar el setting**

En `api/app/config.py`, debajo de `asamblea_origin`, agregar:

```python
    asamblea_mod_token: str = ""             # secreto de moderador para acciones sensibles (vacío = override deshabilitado)
```

- [ ] **Step 4: Agregar los modelos**

Al final de `api/app/models.py` (ya importa `Boolean, ForeignKey, Integer, String, UniqueConstraint`,
`JSONDict`, `FechaUTC`, `ahora`):

```python
class AsambleaSesion(Base):
    __tablename__ = "asamblea_sesion"
    id: Mapped[int] = mapped_column(primary_key=True)
    consorcio_id: Mapped[int | None] = mapped_column(ForeignKey("consorcio.id"), default=None)
    titulo: Mapped[str] = mapped_column(String(200), default="")
    doc: Mapped[dict] = mapped_column(JSONDict, default=dict)   # estado "blando": mociones/agenda/palabra/…/units
    version: Mapped[int] = mapped_column(Integer, default=1)
    creada: Mapped[datetime] = mapped_column(FechaUTC, default=ahora)
    actualizada: Mapped[datetime] = mapped_column(FechaUTC, default=ahora, onupdate=ahora)


class AsambleaClaim(Base):
    __tablename__ = "asamblea_claim"
    __table_args__ = (UniqueConstraint("sesion_id", "uf", name="uq_claim_sesion_uf"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    sesion_id: Mapped[int] = mapped_column(ForeignKey("asamblea_sesion.id"))
    uf: Mapped[int] = mapped_column(Integer)
    device_id: Mapped[str] = mapped_column(String(64))
    rol: Mapped[str] = mapped_column(String(16), default="titular")   # 'titular' | 'mandatario'
    presente: Mapped[bool] = mapped_column(Boolean, default=True)
    nombre: Mapped[str] = mapped_column(String(120), default="")
    creada: Mapped[datetime] = mapped_column(FechaUTC, default=ahora)


class AsambleaVoto(Base):
    __tablename__ = "asamblea_voto"
    __table_args__ = (UniqueConstraint("sesion_id", "mocion_idx", "uf", name="uq_voto_sesion_mocion_uf"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    sesion_id: Mapped[int] = mapped_column(ForeignKey("asamblea_sesion.id"))
    mocion_idx: Mapped[int] = mapped_column(Integer)
    uf: Mapped[int] = mapped_column(Integer)
    opcion_idx: Mapped[int] = mapped_column(Integer)
    device_id: Mapped[str] = mapped_column(String(64), default="")
    ts: Mapped[datetime] = mapped_column(FechaUTC, default=ahora)
```

- [ ] **Step 5: Correr el test y verlo pasar**

Run: `cd api && .venv/bin/python -m pytest tests/test_asamblea_estado.py -q`
Expected: PASS (2 passed).

- [ ] **Step 6: Commit**

```bash
cd /opt/consorcios-transparentes && git add api/app/config.py api/app/models.py api/tests/test_asamblea_estado.py
git commit -m "Asamblea API: tablas de sesión/claim/voto + setting mod_token"
```

---

### Task 2: Módulo de estado — sesión activa + ensamblado + lógica de claim/voto

**Files:**
- Create: `api/app/asamblea_estado.py`
- Test: `api/tests/test_asamblea_estado.py` (agregar casos)

Este módulo tiene toda la lógica (sin HTTP): obtener la sesión activa, ensamblar el estado compatible con el
cliente, y las operaciones con bloqueo. Los endpoints (Task 3/4) son cáscaras finas.

- [ ] **Step 1: Escribir los tests que fallan**

Agregar a `api/tests/test_asamblea_estado.py`:

```python
from app import asamblea_estado as ae


def test_sesion_activa_es_singleton(db):
    s1 = ae.sesion_activa(db)
    s2 = ae.sesion_activa(db)
    assert s1.id == s2.id


def test_ensamblar_estado_forma_compatible(db):
    s = ae.sesion_activa(db)
    s.doc = {"mociones": [{"titulo": "M1", "opciones": ["A", "B"], "regla": "abs", "abierta": True}],
             "activa": 0, "agenda": {}, "palabra": [], "respuestas": {}, "objeciones": {}, "cumplimiento": {},
             "units": [{"uf": 3, "prop": "X"}, {"uf": 4, "prop": "X"}, {"uf": 5, "prop": "Y"}]}
    db.add(AsambleaClaim(sesion_id=s.id, uf=3, device_id="d", rol="titular", presente=True))
    db.add(AsambleaVoto(sesion_id=s.id, mocion_idx=0, uf=3, opcion_idx=1, device_id="d"))
    db.commit()
    est = ae.ensamblar_estado(db, s)
    assert est["presentes"] == {"3": True}
    assert est["mociones"][0]["votos"] == {"3": 1}
    assert est["mociones"][0]["abierta"] is True
    assert est["claims"]["3"]["rol"] == "titular"
    assert "version" in est


def test_reclamar_bloquea_y_rechaza_conflicto(db):
    s = ae.sesion_activa(db)
    s.doc = {"units": [{"uf": 3, "prop": "X"}]}
    db.commit()
    r = ae.reclamar(db, s, device="d1", uf=3, representados=[], nombre="Juan")
    assert r["ok"] is True
    r2 = ae.reclamar(db, s, device="d2", uf=3, representados=[], nombre="Otro")
    assert r2["ok"] is False and 3 in r2["conflicto"]


def test_reclamar_tope_cinco_propietarios(db):
    s = ae.sesion_activa(db)
    # mandatario UF 1; representa 6 UF de 6 propietarios distintos → el 6º excede
    s.doc = {"units": [{"uf": i, "prop": f"P{i}"} for i in range(1, 8)]}
    db.commit()
    r = ae.reclamar(db, s, device="d", uf=1, representados=[2, 3, 4, 5, 6], nombre="M")
    assert r["ok"] is True
    r2 = ae.reclamar(db, s, device="d", uf=1, representados=[2, 3, 4, 5, 6, 7], nombre="M")
    assert r2["ok"] is False and r2.get("motivo")


def test_reclamar_condominio_cuenta_uno(db):
    s = ae.sesion_activa(db)
    # 5 propietarios pero uno (Z) tiene 3 UF → representa 7 UF = 5 propietarios: OK
    s.doc = {"units": [{"uf": 1, "prop": "M"},
                       {"uf": 2, "prop": "A"}, {"uf": 3, "prop": "B"}, {"uf": 4, "prop": "C"},
                       {"uf": 5, "prop": "D"}, {"uf": 6, "prop": "Z"}, {"uf": 7, "prop": "Z"},
                       {"uf": 8, "prop": "Z"}]}
    db.commit()
    r = ae.reclamar(db, s, device="d", uf=1, representados=[2, 3, 4, 5, 6, 7, 8], nombre="M")
    assert r["ok"] is True


def test_votar_requiere_ventana_abierta_y_dueno(db):
    s = ae.sesion_activa(db)
    s.doc = {"mociones": [{"titulo": "M", "opciones": ["A", "B"], "regla": "abs", "abierta": False}],
             "units": [{"uf": 3, "prop": "X"}]}
    db.commit()
    ae.reclamar(db, s, device="d1", uf=3, representados=[], nombre="J")
    assert ae.votar(db, s, device="d1", mocion=0, uf=3, opcion=1)["ok"] is False  # cerrada
    s.doc["mociones"][0]["abierta"] = True
    ae.set_doc(db, s, s.doc)
    assert ae.votar(db, s, device="d1", mocion=0, uf=3, opcion=1)["ok"] is True   # ok
    assert ae.votar(db, s, device="dX", mocion=0, uf=3, opcion=0)["ok"] is False  # no dueño
```

- [ ] **Step 2: Correr y ver fallar**

Run: `cd api && .venv/bin/python -m pytest tests/test_asamblea_estado.py -q`
Expected: FAIL con `ModuleNotFoundError: No module named 'app.asamblea_estado'`.

- [ ] **Step 3: Implementar el módulo**

Crear `api/app/asamblea_estado.py`:

```python
"""Lógica de estado de asamblea en vivo (sin HTTP). Bloqueo por fila UNIQUE.

Corte duro/blando: claims y votos son filas (concurrencia segura); el resto (mociones,
agenda, oradores, etc.) vive en `AsambleaSesion.doc` con `version` (último-gana)."""
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from .models import AsambleaClaim, AsambleaSesion, AsambleaVoto

SOFT_KEYS = ("mociones", "activa", "agenda", "palabra", "respuestas", "objeciones", "cumplimiento", "units")


def sesion_activa(db: Session) -> AsambleaSesion:
    """La asamblea activa (una sola). Se crea vacía si no existe."""
    s = db.query(AsambleaSesion).order_by(AsambleaSesion.id.desc()).first()
    if s is None:
        s = AsambleaSesion(titulo="", doc={"mociones": []}, version=1)
        db.add(s)
        db.commit()
        db.refresh(s)
    return s


def set_doc(db: Session, s: AsambleaSesion, doc: dict) -> None:
    """Reemplaza el doc blando y sube la versión."""
    s.doc = doc
    s.version = (s.version or 0) + 1
    db.add(s)
    db.commit()


def _prop_por_uf(s: AsambleaSesion) -> dict:
    return {u["uf"]: u.get("prop", "") for u in (s.doc or {}).get("units", [])}


def ensamblar_estado(db: Session, s: AsambleaSesion) -> dict:
    """Arma la forma que el cliente ya entiende + `claims` y `abierta` por moción."""
    doc = dict(s.doc or {})
    claims = db.query(AsambleaClaim).filter_by(sesion_id=s.id).all()
    votos = db.query(AsambleaVoto).filter_by(sesion_id=s.id).all()
    presentes, poderes, claims_out = {}, {}, {}
    for c in claims:
        k = str(c.uf)
        if c.presente:
            presentes[k] = True
        if c.rol == "mandatario":
            poderes[k] = c.nombre or True
        claims_out[k] = {"device": c.device_id, "rol": c.rol, "nombre": c.nombre}
    votos_por_mocion: dict[int, dict] = {}
    for v in votos:
        votos_por_mocion.setdefault(v.mocion_idx, {})[str(v.uf)] = v.opcion_idx
    mociones = []
    for i, m in enumerate(doc.get("mociones", [])):
        mociones.append({**m, "votos": votos_por_mocion.get(i, {})})
    return {
        "titulo": s.titulo,
        "version": s.version,
        "mociones": mociones,
        "activa": doc.get("activa", 0),
        "agenda": doc.get("agenda", {}),
        "palabra": doc.get("palabra", []),
        "respuestas": doc.get("respuestas", {}),
        "objeciones": doc.get("objeciones", {}),
        "cumplimiento": doc.get("cumplimiento", {}),
        "presentes": presentes,
        "poderes": poderes,
        "claims": claims_out,
    }


def _cuenta_propietarios(s: AsambleaSesion, device: str, nuevos_rep: list[int]) -> int:
    """Propietarios distintos representados por `device` (condominio = 1), incluidos los nuevos."""
    pmap = _prop_por_uf(s)
    props = {pmap.get(uf, f"uf{uf}") for uf in nuevos_rep}
    return len(props)


def reclamar(db: Session, s: AsambleaSesion, device: str, uf: int,
             representados: list[int], nombre: str) -> dict:
    """Toma la unidad propia (titular) + las representadas (mandatario), todo-o-nada.
    Devuelve {ok:True,...} o {ok:False, conflicto:[uf]} / {ok:False, motivo:str}."""
    representados = [int(x) for x in (representados or []) if int(x) != int(uf)]
    if _cuenta_propietarios(s, device, representados) > 5:
        return {"ok": False, "motivo": "Un mandatario no puede representar a más de cinco propietarios (art. 25 h)."}
    objetivo = [(int(uf), "titular")] + [(r, "mandatario") for r in representados]
    # Chequeo previo de conflicto (unidad tomada por OTRO device)
    tomadas = {c.uf: c.device_id for c in db.query(AsambleaClaim).filter_by(sesion_id=s.id).all()}
    conflicto = [u for u, _ in objetivo if u in tomadas and tomadas[u] != device]
    if conflicto:
        return {"ok": False, "conflicto": conflicto}
    # Insert atómico; si una carrera mete la misma uf, el UNIQUE lo corta
    try:
        for u, rol in objetivo:
            if tomadas.get(u) == device:
                continue  # ya es de este device: idempotente
            db.add(AsambleaClaim(sesion_id=s.id, uf=u, device_id=device, rol=rol,
                                 presente=True, nombre=nombre if rol == "titular" else ""))
        db.commit()
    except IntegrityError:
        db.rollback()
        return {"ok": False, "conflicto": [u for u, _ in objetivo]}
    return {"ok": True}


def liberar(db: Session, s: AsambleaSesion, uf: int, device: str | None) -> dict:
    """Suelta el claim de `uf`. Si `device` viene, solo si le pertenece (propietario);
    con device=None es override del moderador. Al liberar, borra los votos de esa uf."""
    q = db.query(AsambleaClaim).filter_by(sesion_id=s.id, uf=int(uf))
    if device is not None:
        q = q.filter_by(device_id=device)
    c = q.first()
    if not c:
        return {"ok": False}
    db.query(AsambleaVoto).filter_by(sesion_id=s.id, uf=int(uf)).delete()
    db.delete(c)
    db.commit()
    return {"ok": True}


def votar(db: Session, s: AsambleaSesion, device: str, mocion: int, uf: int, opcion: int,
          override: bool = False) -> dict:
    """Emite/cambia un voto. Sin override exige ventana abierta y que `device` sea dueño de `uf`."""
    mociones = (s.doc or {}).get("mociones", [])
    if mocion < 0 or mocion >= len(mociones):
        return {"ok": False, "motivo": "moción inexistente"}
    if not override:
        if not mociones[mocion].get("abierta"):
            return {"ok": False, "motivo": "La votación de esta moción no está abierta."}
        c = db.query(AsambleaClaim).filter_by(sesion_id=s.id, uf=int(uf)).first()
        if not c or c.device_id != device:
            return {"ok": False, "motivo": "Esa unidad no es tuya."}
    v = db.query(AsambleaVoto).filter_by(sesion_id=s.id, mocion_idx=int(mocion), uf=int(uf)).first()
    if v:
        v.opcion_idx = int(opcion)
        v.device_id = device
    else:
        db.add(AsambleaVoto(sesion_id=s.id, mocion_idx=int(mocion), uf=int(uf),
                            opcion_idx=int(opcion), device_id=device))
    db.commit()
    return {"ok": True}


def set_claim_mod(db: Session, s: AsambleaSesion, uf: int, presente: bool, rol: str, nombre: str) -> dict:
    """Override del moderador: fija/forza presencia o poder de una unidad (device='mod')."""
    c = db.query(AsambleaClaim).filter_by(sesion_id=s.id, uf=int(uf)).first()
    if c:
        c.device_id, c.rol, c.presente, c.nombre = "mod", rol, presente, nombre
    else:
        db.add(AsambleaClaim(sesion_id=s.id, uf=int(uf), device_id="mod", rol=rol,
                             presente=presente, nombre=nombre))
    db.commit()
    return {"ok": True}


def reset(db: Session, s: AsambleaSesion) -> dict:
    db.query(AsambleaVoto).filter_by(sesion_id=s.id).delete()
    db.query(AsambleaClaim).filter_by(sesion_id=s.id).delete()
    db.commit()
    return {"ok": True}
```

- [ ] **Step 4: Correr y ver pasar**

Run: `cd api && .venv/bin/python -m pytest tests/test_asamblea_estado.py -q`
Expected: PASS (todos). Si `test_votar_requiere_ventana_abierta_y_dueno` falla por mutación del JSON,
verificar que `set_doc` reasigna `s.doc` (MutableDict ya trackea, pero el test usa `s.doc["..."]=` + `set_doc`).

- [ ] **Step 5: Commit**

```bash
cd /opt/consorcios-transparentes && git add api/app/asamblea_estado.py api/tests/test_asamblea_estado.py
git commit -m "Asamblea API: módulo de estado (sesión, ensamblado, claim/voto con bloqueo)"
```

---

### Task 3: Endpoints de propietario (estado, claim, release, voto)

**Files:**
- Modify: `api/app/routers/asamblea.py` (agregar endpoints + helper de auth)
- Test: `api/tests/test_asamblea_api.py` (nuevo)

- [ ] **Step 1: Escribir los tests que fallan**

Crear `api/tests/test_asamblea_api.py`:

```python
import pytest
from app.config import settings


@pytest.fixture(autouse=True)
def token(monkeypatch):
    monkeypatch.setattr(settings, "asamblea_token", "secreto")
    monkeypatch.setattr(settings, "asamblea_mod_token", "modsecreto")


H = {"X-Asamblea-Token": "secreto"}
HM = {"X-Asamblea-Token": "secreto", "X-Asamblea-Mod": "modsecreto"}


def _init_mociones(cliente):
    doc = {"mociones": [{"titulo": "M1", "opciones": ["A favor", "En contra"], "regla": "abs", "abierta": False}],
           "activa": 0, "units": [{"uf": 3, "prop": "X"}, {"uf": 4, "prop": "Y"}]}
    r = cliente.post("/asamblea/mod/doc", json={"doc": doc}, headers=HM)
    assert r.status_code == 200


def test_estado_requiere_token(cliente):
    assert cliente.get("/asamblea/estado").status_code == 401


def test_claim_y_conflicto(cliente):
    _init_mociones(cliente)
    r = cliente.post("/asamblea/claim", json={"device": "d1", "uf": 3, "nombre": "Juan"}, headers=H)
    assert r.status_code == 200 and r.json()["ok"] is True
    r2 = cliente.post("/asamblea/claim", json={"device": "d2", "uf": 3}, headers=H)
    assert r2.status_code == 409 and 3 in r2.json()["conflicto"]


def test_voto_cerrada_luego_abierta(cliente):
    _init_mociones(cliente)
    cliente.post("/asamblea/claim", json={"device": "d1", "uf": 3}, headers=H)
    assert cliente.post("/asamblea/voto", json={"device": "d1", "mocion": 0, "uf": 3, "opcion": 0},
                        headers=H).status_code == 403
    cliente.post("/asamblea/mod/ventana", json={"mocion": 0, "abierta": True}, headers=HM)
    assert cliente.post("/asamblea/voto", json={"device": "d1", "mocion": 0, "uf": 3, "opcion": 0},
                        headers=H).status_code == 200
    est = cliente.get("/asamblea/estado", headers=H).json()
    assert est["mociones"][0]["votos"] == {"3": 0}


def test_voto_no_dueno_prohibido(cliente):
    _init_mociones(cliente)
    cliente.post("/asamblea/claim", json={"device": "d1", "uf": 3}, headers=H)
    cliente.post("/asamblea/mod/ventana", json={"mocion": 0, "abierta": True}, headers=HM)
    assert cliente.post("/asamblea/voto", json={"device": "dX", "mocion": 0, "uf": 3, "opcion": 0},
                        headers=H).status_code == 403


def test_release_permite_reclaim(cliente):
    _init_mociones(cliente)
    cliente.post("/asamblea/claim", json={"device": "d1", "uf": 3}, headers=H)
    assert cliente.post("/asamblea/release", json={"device": "d1", "uf": 3}, headers=H).status_code == 200
    assert cliente.post("/asamblea/claim", json={"device": "d2", "uf": 3}, headers=H).json()["ok"] is True
```

- [ ] **Step 2: Correr y ver fallar**

Run: `cd api && .venv/bin/python -m pytest tests/test_asamblea_api.py -q`
Expected: FAIL (404 en los endpoints nuevos).

- [ ] **Step 3: Implementar los endpoints de propietario + auth**

En `api/app/routers/asamblea.py`, agregar imports y endpoints (mantener el endpoint de convocatoria):

```python
from fastapi import Body, Depends
from sqlalchemy.orm import Session
from .. import asamblea_estado as ae
from ..db import get_db


def _auth(x_asamblea_token: str | None):
    if not settings.asamblea_token or x_asamblea_token != settings.asamblea_token:
        raise HTTPException(401, "Token inválido")


@router.get("/asamblea/estado")
def estado(desde: int | None = None, x_asamblea_token: str | None = Header(default=None),
           db: Session = Depends(get_db)):
    _auth(x_asamblea_token)
    s = ae.sesion_activa(db)
    if desde is not None and s.version <= desde:
        return {"sin_cambios": True, "version": s.version}
    return ae.ensamblar_estado(db, s)


@router.post("/asamblea/claim")
def claim(payload: dict = Body(...), x_asamblea_token: str | None = Header(default=None),
          db: Session = Depends(get_db)):
    _auth(x_asamblea_token)
    s = ae.sesion_activa(db)
    r = ae.reclamar(db, s, device=payload["device"], uf=int(payload["uf"]),
                    representados=payload.get("representados", []), nombre=payload.get("nombre", ""))
    if not r["ok"] and "conflicto" in r:
        raise HTTPException(409, detail=r)
    if not r["ok"]:
        raise HTTPException(400, detail=r)
    return r


@router.post("/asamblea/release")
def release(payload: dict = Body(...), x_asamblea_token: str | None = Header(default=None),
            db: Session = Depends(get_db)):
    _auth(x_asamblea_token)
    s = ae.sesion_activa(db)
    return ae.liberar(db, s, uf=int(payload["uf"]), device=payload["device"])


@router.post("/asamblea/voto")
def voto(payload: dict = Body(...), x_asamblea_token: str | None = Header(default=None),
         db: Session = Depends(get_db)):
    _auth(x_asamblea_token)
    s = ae.sesion_activa(db)
    r = ae.votar(db, s, device=payload["device"], mocion=int(payload["mocion"]),
                 uf=int(payload["uf"]), opcion=int(payload["opcion"]))
    if not r["ok"]:
        raise HTTPException(403, detail=r)
    return r
```

> Nota: FastAPI serializa el `detail` dict tal cual; el cliente lee `resp.json().detail.conflicto`.
> Los endpoints de moderador (`mod/doc`, `mod/ventana`) los agrega la Task 4, pero el test de esta tarea los
> usa — por eso corré el archivo completo recién al final de la Task 4. Para esta tarea, verificá solo los
> tests que no dependen de `mod/*`.

- [ ] **Step 4: Verificar lo que no depende de `mod/*`**

Run: `cd api && .venv/bin/python -m pytest "tests/test_asamblea_api.py::test_estado_requiere_token" -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
cd /opt/consorcios-transparentes && git add api/app/routers/asamblea.py api/tests/test_asamblea_api.py
git commit -m "Asamblea API: endpoints de propietario (estado/claim/release/voto)"
```

---

### Task 4: Endpoints de moderador (doc, ventana, claim, voto, release, reset)

**Files:**
- Modify: `api/app/routers/asamblea.py`
- Test: `api/tests/test_asamblea_api.py` (agregar casos de moderador)

- [ ] **Step 1: Agregar los tests de moderador**

Agregar a `api/tests/test_asamblea_api.py`:

```python
def test_mod_requiere_secreto(cliente):
    r = cliente.post("/asamblea/mod/ventana", json={"mocion": 0, "abierta": True},
                     headers={"X-Asamblea-Token": "secreto"})  # sin X-Asamblea-Mod
    assert r.status_code == 401


def test_mod_voto_override_sin_ventana(cliente):
    _init_mociones(cliente)  # ventana cerrada
    r = cliente.post("/asamblea/mod/voto", json={"mocion": 0, "uf": 4, "opcion": 1}, headers=HM)
    assert r.status_code == 200
    est = cliente.get("/asamblea/estado", headers=H).json()
    assert est["mociones"][0]["votos"] == {"4": 1}


def test_mod_claim_y_release(cliente):
    _init_mociones(cliente)
    cliente.post("/asamblea/mod/claim", json={"uf": 3, "presente": True, "rol": "titular", "nombre": "Ana"},
                 headers=HM)
    assert cliente.get("/asamblea/estado", headers=H).json()["presentes"] == {"3": True}
    cliente.post("/asamblea/mod/release", json={"uf": 3}, headers=HM)
    assert cliente.get("/asamblea/estado", headers=H).json()["presentes"] == {}


def test_mod_reset_borra_todo(cliente):
    _init_mociones(cliente)
    cliente.post("/asamblea/claim", json={"device": "d1", "uf": 3}, headers=H)
    cliente.post("/asamblea/mod/reset", json={}, headers=HM)
    assert cliente.get("/asamblea/estado", headers=H).json()["claims"] == {}
```

- [ ] **Step 2: Correr y ver fallar**

Run: `cd api && .venv/bin/python -m pytest tests/test_asamblea_api.py -q`
Expected: FAIL (404 en `mod/*`).

- [ ] **Step 3: Implementar los endpoints de moderador**

Agregar a `api/app/routers/asamblea.py`:

```python
def _auth_mod(x_asamblea_token, x_asamblea_mod):
    _auth(x_asamblea_token)
    if not settings.asamblea_mod_token or x_asamblea_mod != settings.asamblea_mod_token:
        raise HTTPException(401, "Secreto de moderador inválido")


@router.post("/asamblea/mod/doc")
def mod_doc(payload: dict = Body(...), x_asamblea_token: str | None = Header(default=None),
            x_asamblea_mod: str | None = Header(default=None), db: Session = Depends(get_db)):
    _auth_mod(x_asamblea_token, x_asamblea_mod)
    s = ae.sesion_activa(db)
    ae.set_doc(db, s, payload["doc"])
    return {"ok": True, "version": s.version}


@router.post("/asamblea/mod/ventana")
def mod_ventana(payload: dict = Body(...), x_asamblea_token: str | None = Header(default=None),
                x_asamblea_mod: str | None = Header(default=None), db: Session = Depends(get_db)):
    _auth_mod(x_asamblea_token, x_asamblea_mod)
    s = ae.sesion_activa(db)
    doc = dict(s.doc or {})
    mociones = doc.get("mociones", [])
    i = int(payload["mocion"])
    if 0 <= i < len(mociones):
        mociones[i] = {**mociones[i], "abierta": bool(payload["abierta"])}
        doc["mociones"] = mociones
        ae.set_doc(db, s, doc)
    return {"ok": True}


@router.post("/asamblea/mod/claim")
def mod_claim(payload: dict = Body(...), x_asamblea_token: str | None = Header(default=None),
              x_asamblea_mod: str | None = Header(default=None), db: Session = Depends(get_db)):
    _auth_mod(x_asamblea_token, x_asamblea_mod)
    s = ae.sesion_activa(db)
    return ae.set_claim_mod(db, s, uf=int(payload["uf"]), presente=bool(payload.get("presente", True)),
                            rol=payload.get("rol", "titular"), nombre=payload.get("nombre", ""))


@router.post("/asamblea/mod/voto")
def mod_voto(payload: dict = Body(...), x_asamblea_token: str | None = Header(default=None),
             x_asamblea_mod: str | None = Header(default=None), db: Session = Depends(get_db)):
    _auth_mod(x_asamblea_token, x_asamblea_mod)
    s = ae.sesion_activa(db)
    return ae.votar(db, s, device="mod", mocion=int(payload["mocion"]), uf=int(payload["uf"]),
                    opcion=int(payload["opcion"]), override=True)


@router.post("/asamblea/mod/release")
def mod_release(payload: dict = Body(...), x_asamblea_token: str | None = Header(default=None),
                x_asamblea_mod: str | None = Header(default=None), db: Session = Depends(get_db)):
    _auth_mod(x_asamblea_token, x_asamblea_mod)
    s = ae.sesion_activa(db)
    return ae.liberar(db, s, uf=int(payload["uf"]), device=None)


@router.post("/asamblea/mod/reset")
def mod_reset(payload: dict = Body(default={}), x_asamblea_token: str | None = Header(default=None),
              x_asamblea_mod: str | None = Header(default=None), db: Session = Depends(get_db)):
    _auth_mod(x_asamblea_token, x_asamblea_mod)
    s = ae.sesion_activa(db)
    return ae.reset(db, s)
```

- [ ] **Step 4: Correr toda la suite de asamblea**

Run: `cd api && .venv/bin/python -m pytest tests/test_asamblea_api.py tests/test_asamblea_estado.py -q`
Expected: PASS (todos).

- [ ] **Step 5: Correr la suite completa (no romper nada)**

Run: `cd api && .venv/bin/python -m pytest -q`
Expected: PASS (todo el proyecto, incluidos los nuevos).

- [ ] **Step 6: Commit**

```bash
cd /opt/consorcios-transparentes && git add api/app/routers/asamblea.py api/tests/test_asamblea_api.py
git commit -m "Asamblea API: endpoints de moderador (doc/ventana/claim/voto/release/reset)"
```

---

### Task 5: Config de despliegue (.env.example)

**Files:**
- Modify: `api/.env.example`

- [ ] **Step 1: Agregar la variable al ejemplo**

Agregar al final de `api/.env.example`:

```
# Secreto de moderador para las acciones sensibles de la app de asamblea
# (override de votos, reset, agenda). No se embebe en la app; lo carga el moderador una vez.
CT_ASAMBLEA_MOD_TOKEN=
```

- [ ] **Step 2: Commit**

```bash
cd /opt/consorcios-transparentes && git add api/.env.example
git commit -m "Asamblea API: documentar CT_ASAMBLEA_MOD_TOKEN en .env.example"
```

> El valor real en `api/.env` lo agrega el dueño en el deploy (AGREGAR la línea, no reescribir el archivo).

---

## BLOQUE B — Cliente (`apps/asamblea/make_votacion.py`)

> Contexto del cliente: estado en `S` (`fresh()` en ~L859); `sync` (objeto en ~L1195) hoy postea/pollea la
> hoja (`CFG.url`); `apply(st)` (~L1207) vuelca el estado del server en `S` y hace `renderAll()`. `UNITS` =
> `votacion_units.json`. El PIN es `'2069'` (~L1265); `MOD` en `localStorage` (~L1267). Los taps de
> no-moderador saltan el PIN por los listeners de captura en ~L1294-1296.

### Task 6: `sync` contra la API (reemplaza la hoja) + flag de backend

**Files:**
- Modify: `apps/asamblea/make_votacion.py` (objeto `sync`, `apply`, markers `__API_URL__`/`__ASAMBLEA_TOKEN__`)

- [ ] **Step 1: Agregar el device_id y el marker del mod-token**

En `make_votacion.py`, cerca de donde se define `API_URL` (L10) agregar el env del mod-token (vacío por
defecto; el moderador lo carga a mano, así que NO se embebe un valor real):

```python
ASAMBLEA_MOD_TOKEN = ""  # se carga en el cliente a mano; marker presente por si se quiere prefijar en dev
```

En el JS, junto a `const API_URL='__API_URL__', ASAMBLEA_TOKEN='__ASAMBLEA_TOKEN__';` (L842), agregar:

```javascript
let MOD_TOKEN = ''; try{ MOD_TOKEN = localStorage.getItem(KEY+'-modtok')||''; }catch(e){}
const DEVICE_ID = (()=>{ try{ let d=localStorage.getItem(KEY+'-dev'); if(!d){ d='dev-'+Math.random().toString(36).slice(2,10); localStorage.setItem(KEY+'-dev', d);} return d; }catch(e){ return 'dev-x'; } })();
const BACKEND = (()=>{ try{ return localStorage.getItem(KEY+'-backend')||'api'; }catch(e){ return 'api'; } })(); // 'api' | 'hoja'
```

- [ ] **Step 2: Reemplazar el objeto `sync` por el cliente de API**

Sustituir el objeto `sync` (de `const sync = {` hasta su cierre `};` antes de `sync.start();`, ~L1195-1213)
por esta versión que habla con la API (deja la rama `hoja` como fallback mínimo llamando a lo viejo si
`BACKEND==='hoja'`; para simplificar, si `BACKEND==='hoja'` se mantiene el comportamiento anterior vía
`CFG.url`). Implementación API:

```javascript
const sync = {
  status:'inactiva', timer:null, lastVersion:0, sending:false,
  dot(c){ const d=$('#syncdot'); if(d){ d.className='syncdot '+(c||''); d.title='Sincronización: '+sync.status; } },
  hdr(mod){ const h={'Content-Type':'application/json','X-Asamblea-Token':ASAMBLEA_TOKEN}; if(mod) h['X-Asamblea-Mod']=MOD_TOKEN; return h; },
  start(){ clearInterval(sync.timer); if(!API_URL){ sync.status='inactiva'; sync.dot(''); return; } sync.status='conectando'; sync.dot('busy'); sync.pull(); sync.timer=setInterval(sync.pull, 2000); },
  async pull(){ if(sync.sending) return; try{ const r=await fetch(API_URL+'/asamblea/estado?desde='+sync.lastVersion,{headers:sync.hdr(false)}); const j=await r.json(); if(j && !j.sin_cambios){ sync.lastVersion=j.version||sync.lastVersion; sync.apply(j); } sync.status='ok'; sync.dot('ok'); }catch(e){ sync.status='error'; sync.dot('err'); } },
  // POST de una acción puntual; mod=true agrega el header de moderador.
  async act(path, body, mod){ sync.sending=true; sync.dot('busy'); try{ const r=await fetch(API_URL+path,{method:'POST',headers:sync.hdr(mod),body:JSON.stringify(body)}); const j=await r.json().catch(()=>({})); sync.sending=false; await sync.pull(); return {status:r.status, body:j}; }catch(e){ sync.sending=false; sync.status='error'; sync.dot('err'); return {status:0, body:{}}; } },
  // Push del doc "blando" completo (agenda/mociones/cumplimiento/…); lo usa el moderador.
  pushDoc(){ const doc={ mociones:S.mociones.map(m=>({titulo:m.titulo,opciones:m.opciones,regla:m.regla,abierta:!!m.abierta})), activa:S.activa, agenda:S.agenda||{}, palabra:S.palabra||[], respuestas:S.respuestas||{}, objeciones:S.objeciones||{}, cumplimiento:S.cumplimiento||{}, units:UNITS.map(u=>({uf:u.uf,prop:u.prop,pct:u.pct})) }; return sync.act('/asamblea/mod/doc',{doc}, true); },
  apply(st){ if(!st||!st.mociones) return; const act=Math.min(S.activa, Math.max(0,st.mociones.length-1));
    S={ presentes:st.presentes||{}, poderes:st.poderes||{}, claims:st.claims||{},
        mociones:st.mociones.map(m=>({titulo:m.titulo,opciones:m.opciones,regla:m.regla,abierta:!!m.abierta,votos:m.votos||{}})),
        activa:act, agenda:st.agenda||{}, palabra:st.palabra||[], respuestas:st.respuestas||{}, objeciones:st.objeciones||{},
        cumplimiento:st.cumplimiento||S.cumplimiento||{presidentePropietario:null,dosFirmantes:null,antelacionOk:null} };
    save(); renderAll(); }
};
sync.start();
```

> `S.claims` es nuevo (mapa `uf→{device,rol,nombre}`); `fresh()` debe inicializarlo (Step 3). `m.abierta` es
> nuevo en cada moción.

- [ ] **Step 3: Inicializar los campos nuevos en `fresh()`**

En `fresh()` (~L859) agregar `claims:{}` al objeto, y a cada moción de la lista inicial agregar `abierta:false`.
Ejemplo del objeto raíz: `return ({ presentes:{}, poderes:{}, claims:{}, activa:0, agenda:{}, palabra:[], ... })`
y cada moción `{ titulo:'…', opciones:[…], regla:'abs', abierta:false, votos:{} }`.

- [ ] **Step 4: Generar y verificar que no explota**

Run: `cd apps/asamblea && CT_ASAMBLEA_TOKEN=test python3 make_votacion.py && node --test`
Expected: `ok` al generar y 26 tests de `logica.js` en verde (esta tarea no toca la lógica pura, así que
siguen pasando). Verificá además que el HTML tiene el nuevo `sync`: `grep -c "asamblea/estado" pages-out/index.html` → ≥1.

- [ ] **Step 5: Commit**

```bash
cd /opt/consorcios-transparentes && git add apps/asamblea/make_votacion.py
git commit -m "Asamblea app: sync contra la API del panel (reemplaza la hoja) + device_id y flag de backend"
```

---

### Task 7: Las escrituras del moderador van por la API (con header de moderador)

**Files:**
- Modify: `apps/asamblea/make_votacion.py` (reemplazar `sync.send({...})` por llamadas `sync.act/pushDoc`)

Hoy el código emite `sync.send({t:'voto'|'presente'|'poder'|'agenda'|'mociones'|'reset'|…})`. Esas son
acciones del MODERADOR (pasan por el gate MOD) → ahora van firmadas.

- [ ] **Step 1: Cargar/guardar el mod-token en el alta de moderador**

En el handler del PIN OK (`$('#pinOk')...`, ~L1271), después de `setMod(true)`, pedir el secreto si falta:

```javascript
if(!MOD_TOKEN){ const t=prompt('Secreto de moderador (se guarda en este dispositivo):',''); if(t){ MOD_TOKEN=t.trim(); try{ localStorage.setItem(KEY+'-modtok', MOD_TOKEN); }catch(e){} } }
```

- [ ] **Step 2: Reemplazar presencia/poder/voto por acciones de moderador**

- `setPresent` (~L1049): en vez de `sync.send({t:'presente',...})`, llamar
  `sync.act('/asamblea/mod/claim',{uf:u.uf, presente:!!val, rol:'titular', nombre:u.prop}, true)` cuando
  `val` es true; cuando es false, `sync.act('/asamblea/mod/release',{uf:u.uf}, true)`.
- `setVote` (~L1062): reemplazar `sync.send({t:'voto',...})` por
  `sync.act('/asamblea/mod/voto',{mocion:S.activa, uf:u.uf, opcion:i}, true)`.
- Asignación de poder (`setPoder`/el flujo de mandatario, ~L1055-1060): `sync.act('/asamblea/mod/claim',
  {uf:u.uf, presente:true, rol:'mandatario', nombre:mandatario||''}, true)`.
- `resetVotacion` (~L1149): `sync.act('/asamblea/mod/reset',{}, true)` en vez de `sync.send({t:'reset'})`.
- Cambios de agenda y de la lista de mociones (`sync.send({t:'agenda',...})`, `sync.send({t:'mociones',...})`,
  cumplimiento, respuestas, objeciones): reemplazar por `sync.pushDoc()` (empuja el doc blando completo).
- Oradores (`$('#palOk')` y `data-pal-done`): como `palabra` vive en el doc blando, después de mutar
  `S.palabra` llamar `sync.pushDoc()` (con header mod si el que opera es moderador; si querés permitir que
  cualquiera pida la palabra, dejá ese `pushDoc` sin mod y agregá un endpoint público — **fuera de alcance
  este ciclo**: por ahora la lista de oradores la consolida el moderador).

> Mantener los `save()` locales para que el moderador siga viendo su cambio al instante; el `pull()` que hace
> `sync.act` reconcilia con el server.

- [ ] **Step 3: Quitar la config de URL de la hoja del diálogo de settings (o dejarla como "hoja legacy")**

En `openSettings`/el form de settings (~L1103-1112), el campo `#sUrl` ya no controla el backend de sync.
Dejar el campo pero etiquetarlo "Hoja de Google (solo exportación/legacy)"; que guardar ya NO llame a
`sync.start()` con la hoja. El backend por defecto es la API (`BACKEND==='api'`).

- [ ] **Step 4: Generar y probar a mano contra una API local**

Run: `cd apps/asamblea && CT_ASAMBLEA_TOKEN=test CT_ASAMBLEA_API_URL=http://localhost:8000 python3 make_votacion.py`
Levantar la API local (`cd api && .venv/bin/uvicorn app.main:app` con `CT_ASAMBLEA_TOKEN=test
CT_ASAMBLEA_MOD_TOKEN=mod` en el entorno) y, abriendo `pages-out/index.html`, entrar como moderador, marcar
una presencia y un voto; verificar en `GET /asamblea/estado` que se reflejan.
Expected: el estado del server muestra la presencia y el voto cargados por el moderador.

- [ ] **Step 5: Commit**

```bash
cd /opt/consorcios-transparentes && git add apps/asamblea/make_votacion.py
git commit -m "Asamblea app: escrituras del moderador vía API firmadas con el secreto de moderador"
```

---

### Task 8: Alta del propietario (claim) + identidad del dispositivo

**Files:**
- Modify: `apps/asamblea/make_votacion.py` (diálogo de alta, estado `mi`, banner en Votar)

- [ ] **Step 1: Estado "mi" persistente**

Agregar cerca del `DEVICE_ID`:

```javascript
let MI = null; try{ MI = JSON.parse(localStorage.getItem(KEY+'-mi')||'null'); }catch(e){}  // {uf, nombre, representados:[uf]}
function setMi(v){ MI=v; try{ localStorage.setItem(KEY+'-mi', JSON.stringify(v)); }catch(e){} renderAll(); }
```

- [ ] **Step 2: Banner "Reclamar mi unidad" en Votar (para no-moderador, no identificado)**

En el render de la barra de Votar (donde hoy está `#modbar`/encabezado de Votar), si `!MOD && !MI`, mostrar:

```javascript
`<div class="card"><h3>¿Sos propietario?</h3><p class="note">Votá desde tu teléfono.</p><button class="btn primary" id="btnReclamar">Reclamar mi unidad</button></div>`
```

- [ ] **Step 3: Diálogo de alta**

Agregar un `<dialog id="dlgReclamar">` con: un `<select id="recUf">` (unidades libres), un input de nombre
`<input id="recNombre">`, un bloque para agregar representadas (`<select id="recRep">` + botón "Agregar", lista
`<div id="recReps">` con contador "representás N/5"), y botones Cancelar / Confirmar. Poblar `#recUf` y
`#recRep` solo con unidades no presentes en `S.claims`:

```javascript
function unidadesLibres(){ return UNITS.filter(u=> !S.claims[u.uf]); }
$('#btnReclamar') && ($('#btnReclamar').onclick=()=>{ recRepsSel=[]; ufOptions($('#recUf'), u=>!S.claims[u.uf]); $('#recNombre').value=''; renderRecReps(); $('#dlgReclamar').showModal(); });
let recRepsSel=[];
function renderRecReps(){ const libres=unidadesLibres().filter(u=>u.uf!=+$('#recUf').value && !recRepsSel.includes(u.uf)); ufOptions($('#recRep'), u=>libres.includes(u)); $('#recReps').innerHTML = recRepsSel.map(uf=>`<span class="chip">${esc(ufInfo(uf).piso)} <button data-rmrep="${uf}">×</button></span>`).join('') + `<div class="note">representás ${new Set(recRepsSel.map(uf=>ufInfo(uf).prop)).size}/5</div>`; }
```

(Reusar el helper `ufOptions` existente y un `ufInfo(uf)` que devuelva la unidad por uf — si no existe, usar
`UNITS.find(x=>x.uf===uf)`.)

- [ ] **Step 4: Confirmar el claim contra la API**

```javascript
$('#recConfirm').onclick = async ()=>{ const uf=+$('#recUf').value; if(!uf){ toast('Elegí tu unidad'); return; }
  const r = await sync.act('/asamblea/claim', {device:DEVICE_ID, uf, representados:recRepsSel, nombre:$('#recNombre').value.trim()}, false);
  if(r.status===200){ setMi({uf, nombre:$('#recNombre').value.trim(), representados:recRepsSel.slice()}); $('#dlgReclamar').close(); toast('Listo, ya podés votar desde tu teléfono'); }
  else if(r.status===409){ toast('Esa unidad ya fue tomada'); sync.pull(); }
  else { toast((r.body&&r.body.detail&&r.body.detail.motivo)||'No se pudo reclamar'); } };
```

- [ ] **Step 5: "Salir / no soy esta unidad"**

Donde se muestre la identidad (Task 9 la usa), un botón que haga
`await sync.act('/asamblea/release',{device:DEVICE_ID, uf:MI.uf}, false); setMi(null);` (y también soltar las
representadas con release por cada una).

- [ ] **Step 6: Generar y probar el conflicto**

Run: `cd apps/asamblea && CT_ASAMBLEA_TOKEN=test CT_ASAMBLEA_API_URL=http://localhost:8000 python3 make_votacion.py`
Con la API local corriendo: abrir dos ventanas, reclamar la misma unidad en ambas; la segunda debe decir "ya
fue tomada".
Expected: el candado del server rechaza el segundo claim (toast de conflicto).

- [ ] **Step 7: Commit**

```bash
cd /opt/consorcios-transparentes && git add apps/asamblea/make_votacion.py
git commit -m "Asamblea app: alta del propietario (claim con bloqueo) e identidad por dispositivo"
```

---

### Task 9: Vista "Tus unidades" (voto propio) + ventana por agenda + overrides del moderador

**Files:**
- Modify: `apps/asamblea/make_votacion.py`

- [ ] **Step 1: La ventana se abre/cierra con la agenda**

En el handler de iniciar/cerrar tratamiento de un punto (`data-pt-act`, ~L1326-1331): al poner un punto
`en curso`, si tiene moción vinculada (`mocIndexByTitle`), setear `S.mociones[mi].abierta=true`; al `cerrar
punto`, `=false`. Luego `sync.pushDoc()` (ya empuja `abierta` por moción).

- [ ] **Step 2: Toggle manual de ventana en la config de la moción (para mociones sueltas)**

En `openSettings`/el form de la moción (~L1103), agregar un checkbox "Voto abierto" ligado a
`S.mociones[S.activa].abierta`; al guardar, `sync.act('/asamblea/mod/ventana',{mocion:S.activa,
abierta:!!checked}, true)`.

- [ ] **Step 3: Vista "Tus unidades" para el propietario**

En el render de Votar, si `MI` (y `!MOD`), en vez de la lista completa mostrar una tarjeta enfocada con la(s)
unidad(es) de `MI` (la propia + representadas) y, para la moción activa:

```javascript
function renderMisUnidades(){ const m=S.mociones[S.activa]; const abierta=!!(m&&m.abierta);
  const ufs=[MI.uf, ...(MI.representados||[])];
  return `<div class="card"><h3>Tus unidades</h3>${abierta?'':'<p class="note">La votación de esta moción todavía no está abierta.</p>'}`+
    ufs.map(uf=>{ const u=UNITS.find(x=>x.uf===uf)||{}; const voto=(m&&m.votos&&m.votos[uf]); 
      return `<div class="miuf"><b>${esc(u.piso||uf)}</b> ${esc(u.prop||'')}<div class="vrow">`+
        (m?m.opciones.map((o,i)=>`<button class="tog ${voto===i?'on':''}" ${abierta?'':'disabled'} data-mivoto="${uf}" data-opt="${i}">${esc(o)}</button>`).join(''):'')+
        `</div></div>`; }).join('')+
    `<div class="actions"><button class="btn sm" id="btnSalirMi">No soy esta unidad / salir</button></div></div>`; }
```

- [ ] **Step 4: Emitir el voto propio**

Delegación de click en la vista Votar:

```javascript
// dentro del listener de #view-votar:
const bv=e.target.closest('button[data-mivoto]'); if(bv){ const uf=+bv.dataset.mivoto, opt=+bv.dataset.opt;
  const r=await sync.act('/asamblea/voto',{device:DEVICE_ID, mocion:S.activa, uf, opcion:opt}, false);
  if(r.status!==200){ toast((r.body&&r.body.detail&&r.body.detail.motivo)||'No se pudo votar'); } return; }
const bs=e.target.closest('#btnSalirMi'); if(bs){ for(const uf of [MI.uf, ...(MI.representados||[])]) await sync.act('/asamblea/release',{device:DEVICE_ID, uf}, false); setMi(null); return; }
```

> El listener de captura que hoy fuerza el PIN a los no-moderador (~L1294) debe **excluir** los botones
> `data-mivoto` y `#btnReclamar`/`#btnSalirMi` (para que el propietario pueda tocarlos sin PIN). Ajustar la
> condición: `if(!MOD && e.target.closest('button[data-act]') && !e.target.closest('[data-mivoto],#btnReclamar,#btnSalirMi'))`.

- [ ] **Step 5: Ícono de teléfono + overrides en "pasar lista" (moderador)**

En el render de la lista de unidades del moderador (chips/filas), si `S.claims[uf] && S.claims[uf].device!=='mod'`,
mostrar un 📱 al lado. El moderador ya puede corregir voto (Task 7) y, para soltar una unidad trabada, un
botón que llame `sync.act('/asamblea/mod/release',{uf}, true)`.

- [ ] **Step 6: Estilos mínimos**

Agregar al CSS (donde están los estilos de `.chipu`/`.tog`): `.miuf{padding:10px 0;border-top:1px solid
var(--hair)} .miuf .vrow{display:flex;gap:8px;margin-top:8px;flex-wrap:wrap} .miuf .tog{flex:1 1 0;min-height:48px}`.

- [ ] **Step 7: Generar, test de lógica y prueba manual e2e**

Run: `cd apps/asamblea && CT_ASAMBLEA_TOKEN=test CT_ASAMBLEA_API_URL=http://localhost:8000 python3 make_votacion.py && node --test`
Expected: genera `ok`, 26 tests en verde. Con la API local: moderador abre el punto (ventana abre) → un
segundo navegador reclama una unidad y vota → el resultado aparece en el panel del moderador; cerrar el punto
bloquea nuevos votos.

- [ ] **Step 8: Commit**

```bash
cd /opt/consorcios-transparentes && git add apps/asamblea/make_votacion.py
git commit -m "Asamblea app: vista 'Tus unidades' (voto propio), ventana por agenda y overrides del moderador"
```

---

## Cierre

- [ ] **Deploy (lo ejecuta el dueño, con confirmación):**
  1. En `api/.env`, **AGREGAR** la línea `CT_ASAMBLEA_MOD_TOKEN=<secreto largo>` (no reescribir el archivo).
  2. Rebuild de la API (crea las tablas nuevas vía `create_all`): `docker compose build api && docker compose up -d api`.
  3. Regenerar la app con el token embebido y la URL de la API:
     `cd apps/asamblea && CT_ASAMBLEA_TOKEN=<token> CT_ASAMBLEA_API_URL=https://api-consorcio.neuralcore.dev python3 make_votacion.py`.
  4. Deploy a Pages: `npx wrangler pages deploy pages-out --project-name asamblea-rivadavia --branch main --commit-dirty=true`.
  5. El moderador entra con PIN 2069 y carga el secreto de moderador una vez.
  6. Prueba e2e en dos teléfonos.

- [ ] **Actualizar la memoria** `app-asamblea-ciclo.md` con el cierre de este ciclo.
