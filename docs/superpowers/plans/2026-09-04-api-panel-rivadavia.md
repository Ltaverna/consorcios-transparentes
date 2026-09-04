# Plan 1: API del panel de auditoría (Rivadavia 2069)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** API FastAPI con Postgres que persiste liquidaciones, gastos, documentos y hallazgos con estados, ingesta con la regla de oro del cuadre, auth por roles y por código de unidad, y publicación de informes.

**Architecture:** `api/` importa `engine/` como biblioteca (el motor no cambia salvo `Config.desde_dict`). SQLAlchemy 2 sobre Postgres (Neon en prod, SQLite en memoria para tests — el código evita SQL específico de dialecto). Storage detrás de una interfaz: `LocalStorage` (dev/tests) y `R2Storage` (prod). Sin cola: `BackgroundTasks`. Alembic llega en el Plan 3 (deploy), cuando haya una base real que migrar; hasta entonces `create_all`.

**Tech Stack:** Python 3.12+, FastAPI, SQLAlchemy 2, psycopg, argon2-cffi, PyJWT, boto3 (R2), pytest + httpx.

**Spec:** `docs/superpowers/specs/2026-09-04-panel-rivadavia-design.md`. Planes 2 (web Next.js) y 3 (deploy Fly/Neon/R2/Cloudflare) vienen después.

**Convenciones:** commits en español con el trailer `Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>`. Todos los comandos se corren desde `api/` salvo indicación. Los fixtures del motor (`engine/tests/fixtures/redconar_202607.txt` y `redconar_202608.txt`) son liquidaciones reales que cuadran: son la base de los tests de ingesta.

---

### Task 1: Andamiaje de `api/`

**Files:**
- Create: `api/pyproject.toml`, `api/app/__init__.py`, `api/tests/__init__.py`, `api/.env.example`

- [ ] **Step 1: Crear la estructura y el entorno**

```bash
mkdir -p api/app/routers api/tests
touch api/app/__init__.py api/app/routers/__init__.py api/tests/__init__.py
python3 -m venv api/.venv
```

- [ ] **Step 2: Escribir `api/pyproject.toml`**

```toml
[project]
name = "ct-api"
version = "0.1.0"
description = "API del panel de auditoría de Consorcio Transparente"
requires-python = ">=3.12"
dependencies = [
  "fastapi>=0.115",
  "uvicorn[standard]>=0.30",
  "sqlalchemy>=2.0",
  "psycopg[binary]>=3.2",
  "pydantic-settings>=2.4",
  "python-multipart>=0.0.9",
  "argon2-cffi>=23.1",
  "pyjwt>=2.9",
  "boto3>=1.34",
  "openpyxl>=3.1",
]

[project.optional-dependencies]
dev = ["pytest>=8", "httpx>=0.27"]

[tool.pytest.ini_options]
testpaths = ["tests"]

[tool.setuptools]
packages = ["app", "app.routers"]
```

- [ ] **Step 3: Escribir `api/.env.example`**

```bash
# Copiar a .env y completar. Nada de esto va al repo.
CT_DATABASE_URL=postgresql+psycopg://usuario:clave@host/db
CT_JWT_SECRET=cambiar-por-un-secreto-largo
CT_R2_ENDPOINT=https://<account>.r2.cloudflarestorage.com
CT_R2_ACCESS_KEY=
CT_R2_SECRET_KEY=
CT_R2_BUCKET=consorcio-transparente
# Si CT_STORAGE_DIR está seteado se usa disco local en lugar de R2 (dev)
CT_STORAGE_DIR=
CT_CORS_ORIGIN=http://localhost:3000
```

- [ ] **Step 4: Instalar dependencias y el motor**

```bash
cd api
.venv/bin/pip install -q -e ../engine -e '.[dev]'
.venv/bin/python -m pytest -q   # Expected: "no tests ran"
.venv/bin/python -c "import ct, fastapi, sqlalchemy; print('ok')"   # Expected: ok
```

- [ ] **Step 5: Ignorar el venv y el .env de la API**

Verificar que `.gitignore` (raíz) ya ignora `.env` y `.venv/` en cualquier nivel; si falta algo, agregarlo.

- [ ] **Step 6: Commit**

```bash
git add api/pyproject.toml api/app api/tests api/.env.example .gitignore
git commit -m "API: andamiaje de FastAPI con el motor como dependencia" -m "Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

### Task 2: `Config.desde_dict` en el motor

**Files:**
- Modify: `engine/ct/rules.py` (dataclass `Config`, línea ~17)
- Test: `engine/tests/test_rules_config.py`

- [ ] **Step 1: Escribir el test que falla** (`engine/tests/test_rules_config.py`)

```python
from ct.rules import Config


def test_desde_dict_aplica_conocidos_e_ignora_extras():
    cfg = Config.desde_dict({"efectivo_linea_alta": 100.0, "inventado": 1})
    assert cfg.efectivo_linea_alta == 100.0
    assert cfg.dias_factura_pago_max == 60  # default intacto


def test_desde_dict_vacio_o_none_da_defaults():
    assert Config.desde_dict({}) == Config()
    assert Config.desde_dict(None) == Config()
```

- [ ] **Step 2: Verificar que falla**

```bash
cd engine && .venv/bin/python -m pytest -q tests/test_rules_config.py
# Expected: FAIL — AttributeError: 'desde_dict'
```

- [ ] **Step 3: Implementar** — en `engine/ct/rules.py`, dentro de `Config` (y agregar `fields` al import de dataclasses de la línea 8):

```python
    @classmethod
    def desde_dict(cls, d: dict | None) -> "Config":
        conocidos = {f.name for f in fields(cls)}
        return cls(**{k: v for k, v in (d or {}).items() if k in conocidos})
```

- [ ] **Step 4: Verificar que pasa, y que nada se rompió**

```bash
cd engine && .venv/bin/python -m pytest -q tests
# Expected: 27 passed, 2 skipped
```

- [ ] **Step 5: Commit**

```bash
git add engine/ct/rules.py engine/tests/test_rules_config.py
git commit -m "Motor: Config.desde_dict para umbrales por consorcio" -m "Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

### Task 3: Configuración, base y modelos

**Files:**
- Create: `api/app/config.py`, `api/app/db.py`, `api/app/models.py`
- Test: `api/tests/conftest.py`, `api/tests/test_models.py`

- [ ] **Step 1: Escribir `api/app/config.py`**

```python
"""Configuración por variables de entorno (prefijo CT_)."""
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "sqlite://"          # en memoria si no se configura
    jwt_secret: str = "solo-para-desarrollo"
    jwt_horas: int = 12
    cookie_segura: bool = False              # True en producción (HTTPS)
    r2_endpoint: str = ""
    r2_access_key: str = ""
    r2_secret_key: str = ""
    r2_bucket: str = "consorcio-transparente"
    storage_dir: str = ""                    # si está seteado, disco local en vez de R2
    cors_origin: str = "http://localhost:3000"

    model_config = {"env_prefix": "CT_", "env_file": ".env"}


settings = Settings()
```

- [ ] **Step 2: Escribir `api/app/db.py`**

```python
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from sqlalchemy.pool import StaticPool

from .config import settings


class Base(DeclarativeBase):
    pass


def _crear_engine(url: str):
    if url.startswith("sqlite"):
        return create_engine(url, connect_args={"check_same_thread": False}, poolclass=StaticPool)
    return create_engine(url, pool_pre_ping=True)


engine = _crear_engine(settings.database_url)
SessionLocal = sessionmaker(bind=engine, autoflush=False)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

- [ ] **Step 3: Escribir el test que falla** (`api/tests/conftest.py` y `api/tests/test_models.py`)

`api/tests/conftest.py`:

```python
import pathlib

import pytest

from app.db import Base, engine, SessionLocal

FIXTURES = pathlib.Path(__file__).resolve().parents[2] / "engine" / "tests" / "fixtures"


@pytest.fixture()
def db():
    Base.metadata.create_all(engine)
    s = SessionLocal()
    yield s
    s.close()
    Base.metadata.drop_all(engine)
```

`api/tests/test_models.py`:

```python
from app import models


def test_hallazgo_unico_por_liquidacion_y_clave(db):
    liq = models.Liquidacion(periodo="2026-08", archivo_key="x.pdf")
    db.add(liq)
    db.flush()
    db.add(models.Hallazgo(liquidacion_id=liq.id, clave="efectivo|", regla="efectivo",
                           severidad="ALTO", area="Caja", titulo="t", evidencia="e"))
    db.commit()
    h = db.query(models.Hallazgo).one()
    assert h.estado == "pendiente" and h.publicado is False and h.origen == "liquidacion"


def test_consorcio_umbrales_json(db):
    c = models.Consorcio(nombre="Rivadavia 2069", umbrales={"efectivo_linea_alta": 500000})
    db.add(c)
    db.commit()
    assert db.query(models.Consorcio).one().umbrales["efectivo_linea_alta"] == 500000
```

- [ ] **Step 4: Verificar que falla**

```bash
cd api && .venv/bin/python -m pytest -q
# Expected: FAIL — ModuleNotFoundError / AttributeError sobre app.models
```

- [ ] **Step 5: Escribir `api/app/models.py`**

```python
"""Tablas del panel. Un solo consorcio (Rivadavia 2069); multi-consorcio = migración futura."""
from datetime import date, datetime, timezone

from sqlalchemy import (JSON, Boolean, Date, DateTime, Float, ForeignKey, Integer,
                        String, Text, UniqueConstraint)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base

JSONCol = JSON().with_variant(JSONB(), "postgresql")


def ahora() -> datetime:
    return datetime.now(timezone.utc)


class Consorcio(Base):
    __tablename__ = "consorcio"
    id: Mapped[int] = mapped_column(primary_key=True)
    nombre: Mapped[str] = mapped_column(String(200))
    direccion: Mapped[str] = mapped_column(String(200), default="")
    cuit: Mapped[str] = mapped_column(String(13), default="")
    admin_nombre: Mapped[str] = mapped_column(String(200), default="")
    admin_cuit: Mapped[str] = mapped_column(String(13), default="")
    marca: Mapped[str] = mapped_column(String(120), default="Consorcio Transparente")
    umbrales: Mapped[dict] = mapped_column(JSONCol, default=dict)


class Unidad(Base):
    __tablename__ = "unidades"
    id: Mapped[int] = mapped_column(primary_key=True)
    uf: Mapped[int] = mapped_column(Integer, unique=True)
    piso_depto: Mapped[str] = mapped_column(String(40), default="")
    tipo: Mapped[str] = mapped_column(String(40), default="")
    propietario: Mapped[str] = mapped_column(String(200), default="")
    porcentuales: Mapped[dict] = mapped_column(JSONCol, default=dict)
    codigo_hash: Mapped[str | None] = mapped_column(String(200), default=None)


class Usuario(Base):
    __tablename__ = "usuarios"
    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(200), unique=True)
    nombre: Mapped[str] = mapped_column(String(200), default="")
    clave_hash: Mapped[str] = mapped_column(String(200))
    rol: Mapped[str] = mapped_column(String(20))  # auditor | consejo | moderador


class Liquidacion(Base):
    __tablename__ = "liquidaciones"
    id: Mapped[int] = mapped_column(primary_key=True)
    periodo: Mapped[str] = mapped_column(String(7), unique=True)  # AAAA-MM
    sistema: Mapped[str] = mapped_column(String(40), default="")
    # procesando | no_cuadra | error | procesada | publicada
    estado: Mapped[str] = mapped_column(String(20), default="procesando")
    archivo_key: Mapped[str] = mapped_column(String(300))
    datos: Mapped[dict | None] = mapped_column(JSONCol, default=None)  # Liquidacion.to_dict() completo
    cuadra: Mapped[bool] = mapped_column(Boolean, default=False)
    error: Mapped[str] = mapped_column(Text, default="")
    creado: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=ahora)
    gastos: Mapped[list["Gasto"]] = relationship(back_populates="liquidacion", cascade="all, delete-orphan")
    hallazgos: Mapped[list["Hallazgo"]] = relationship(back_populates="liquidacion", cascade="all, delete-orphan")


class Gasto(Base):
    __tablename__ = "gastos"
    __table_args__ = (UniqueConstraint("liquidacion_id", "n"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    liquidacion_id: Mapped[int] = mapped_column(ForeignKey("liquidaciones.id", ondelete="CASCADE"))
    n: Mapped[int] = mapped_column(Integer)
    categoria: Mapped[str] = mapped_column(String(120), default="")
    proveedor: Mapped[str] = mapped_column(String(200), default="")
    concepto: Mapped[str] = mapped_column(Text, default="")
    columna: Mapped[str] = mapped_column(String(10), default="")
    importe: Mapped[float] = mapped_column(Float, default=0.0)
    factura_fecha: Mapped[date | None] = mapped_column(Date, default=None)
    factura_nro: Mapped[str | None] = mapped_column(String(40), default=None)
    factura_importe: Mapped[float | None] = mapped_column(Float, default=None)
    pagos: Mapped[list] = mapped_column(JSONCol, default=list)
    liquidacion: Mapped[Liquidacion] = relationship(back_populates="gastos")


class Documento(Base):
    __tablename__ = "documentos"
    id: Mapped[int] = mapped_column(primary_key=True)
    liquidacion_id: Mapped[int] = mapped_column(ForeignKey("liquidaciones.id", ondelete="CASCADE"))
    gasto_n: Mapped[int | None] = mapped_column(Integer, default=None)
    tipo: Mapped[str] = mapped_column(String(20), default="otro")  # factura | pago | recibo | imagen | otro
    archivo_key: Mapped[str] = mapped_column(String(300))
    hash: Mapped[str] = mapped_column(String(64), default="")
    metadatos: Mapped[dict] = mapped_column(JSONCol, default=dict)  # Documento.to_dict() del motor


class Hallazgo(Base):
    __tablename__ = "hallazgos"
    __table_args__ = (UniqueConstraint("liquidacion_id", "clave"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    liquidacion_id: Mapped[int] = mapped_column(ForeignKey("liquidaciones.id", ondelete="CASCADE"))
    clave: Mapped[str] = mapped_column(String(500))       # clave natural: sobrevive al reproceso
    origen: Mapped[str] = mapped_column(String(20), default="liquidacion")  # liquidacion | comprobantes
    regla: Mapped[str] = mapped_column(String(40))
    severidad: Mapped[str] = mapped_column(String(10))
    area: Mapped[str] = mapped_column(String(120), default="")
    titulo: Mapped[str] = mapped_column(Text)
    evidencia: Mapped[str] = mapped_column(Text, default="")
    monto: Mapped[float] = mapped_column(Float, default=0.0)
    recomendacion: Mapped[str] = mapped_column(Text, default="")
    refs: Mapped[list] = mapped_column(JSONCol, default=list)
    # pendiente | preguntado | respondido | descartado | cerrado
    estado: Mapped[str] = mapped_column(String(20), default="pendiente")
    publicado: Mapped[bool] = mapped_column(Boolean, default=False)
    respuesta_admin: Mapped[str] = mapped_column(Text, default="")
    liquidacion: Mapped[Liquidacion] = relationship(back_populates="hallazgos")
    eventos: Mapped[list["HallazgoEvento"]] = relationship(cascade="all, delete-orphan")


class HallazgoEvento(Base):
    __tablename__ = "hallazgo_eventos"
    id: Mapped[int] = mapped_column(primary_key=True)
    hallazgo_id: Mapped[int] = mapped_column(ForeignKey("hallazgos.id", ondelete="CASCADE"))
    usuario_id: Mapped[int | None] = mapped_column(ForeignKey("usuarios.id"), default=None)
    de: Mapped[str] = mapped_column(String(20), default="")
    a: Mapped[str] = mapped_column(String(20), default="")
    nota: Mapped[str] = mapped_column(Text, default="")
    ts: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=ahora)


class Informe(Base):
    __tablename__ = "informes"
    __table_args__ = (UniqueConstraint("liquidacion_id", "tipo"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    liquidacion_id: Mapped[int] = mapped_column(ForeignKey("liquidaciones.id", ondelete="CASCADE"))
    tipo: Mapped[str] = mapped_column(String(10))  # html | xlsx
    archivo_key: Mapped[str] = mapped_column(String(300))
    marca: Mapped[str] = mapped_column(String(120), default="")
    publicado_en: Mapped[datetime] = mapped_column(FechaUTC(), default=ahora)
```

- [ ] **Step 6: Verificar que pasa**

```bash
cd api && .venv/bin/python -m pytest -q
# Expected: 2 passed
```

- [ ] **Step 7: Commit**

```bash
git add api/app/config.py api/app/db.py api/app/models.py api/tests/conftest.py api/tests/test_models.py
git commit -m "API: modelo de datos (liquidaciones, gastos, documentos, hallazgos con estado, informes)" -m "Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

### Task 4: Seguridad — hashes, JWT, roles y rate limit

**Files:**
- Create: `api/app/security.py`
- Test: `api/tests/test_security.py`

- [ ] **Step 1: Escribir el test que falla** (`api/tests/test_security.py`)

```python
import pytest
from fastapi import HTTPException

from app import security


def test_hash_y_verificacion():
    h = security.hashear("secreto")
    assert security.verificar(h, "secreto")
    assert not security.verificar(h, "otro")
    assert not security.verificar("basura-no-hash", "secreto")


def test_token_ida_y_vuelta():
    tok = security.crear_token("u:1", "auditor")
    datos = security.leer_token(tok)
    assert datos == {"sub": "u:1", "rol": "auditor"}


def test_token_invalido():
    with pytest.raises(HTTPException):
        security.leer_token("no.es.jwt")


def test_rate_limiter():
    rl = security.RateLimiter(maximo=3, ventana=60)
    assert all(rl.permitir("ip") for _ in range(3))
    assert not rl.permitir("ip")
    assert rl.permitir("otra-ip")
```

- [ ] **Step 2: Verificar que falla**

```bash
cd api && .venv/bin/python -m pytest -q tests/test_security.py
# Expected: FAIL — ModuleNotFoundError: app.security
```

- [ ] **Step 3: Escribir `api/app/security.py`**

```python
"""Hashes (argon2), JWT en cookie httpOnly, dependencias de rol y rate limit simple."""
import time
from datetime import datetime, timedelta, timezone

import jwt
from argon2 import PasswordHasher
from fastapi import Depends, HTTPException, Request

from .config import settings

COOKIE = "ct_sesion"
_ph = PasswordHasher()


def hashear(secreto: str) -> str:
    return _ph.hash(secreto)


def verificar(hash_: str, secreto: str) -> bool:
    try:
        return _ph.verify(hash_, secreto)
    except Exception:
        return False


def crear_token(sub: str, rol: str) -> str:
    exp = datetime.now(timezone.utc) + timedelta(hours=settings.jwt_horas)
    return jwt.encode({"sub": sub, "rol": rol, "exp": exp}, settings.jwt_secret, algorithm="HS256")


def leer_token(token: str) -> dict:
    try:
        d = jwt.decode(token, settings.jwt_secret, algorithms=["HS256"])
        return {"sub": d["sub"], "rol": d["rol"]}
    except Exception:
        raise HTTPException(401, "Sesión inválida o vencida")


def sesion(request: Request) -> dict:
    token = request.cookies.get(COOKIE)
    if not token:
        raise HTTPException(401, "Hay que iniciar sesión")
    return leer_token(token)


def requiere(*roles: str):
    def dep(s: dict = Depends(sesion)) -> dict:
        if s["rol"] not in roles:
            raise HTTPException(403, "No autorizado para esta acción")
        return s
    return dep


class RateLimiter:
    """Ventana deslizante en memoria. Alcanza para un proceso único (etapa 1)."""

    def __init__(self, maximo: int = 10, ventana: int = 300):
        self.maximo, self.ventana = maximo, ventana
        self._hits: dict[str, list[float]] = {}

    def permitir(self, clave: str) -> bool:
        ahora = time.monotonic()
        hits = [t for t in self._hits.get(clave, []) if ahora - t < self.ventana]
        if len(hits) >= self.maximo:
            self._hits[clave] = hits
            return False
        hits.append(ahora)
        self._hits[clave] = hits
        return True


limiter_login = RateLimiter()
```

- [ ] **Step 4: Verificar que pasa**

```bash
cd api && .venv/bin/python -m pytest -q tests/test_security.py
# Expected: 4 passed
```

- [ ] **Step 5: Commit**

```bash
git add api/app/security.py api/tests/test_security.py
git commit -m "API: seguridad (argon2, JWT en cookie, roles, rate limit)" -m "Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

### Task 5: Storage — interfaz, LocalStorage y R2Storage

**Files:**
- Create: `api/app/storage.py`
- Test: `api/tests/test_storage.py`

- [ ] **Step 1: Escribir el test que falla** (`api/tests/test_storage.py`)

```python
from app.storage import LocalStorage


def test_local_guardar_leer_y_url(tmp_path):
    st = LocalStorage(str(tmp_path))
    st.guardar("liquidaciones/2026-08.pdf", b"contenido")
    assert st.leer("liquidaciones/2026-08.pdf") == b"contenido"
    assert st.url_firmada("liquidaciones/2026-08.pdf") is None  # local: se sirve por streaming
    assert st.existe("liquidaciones/2026-08.pdf")
    assert not st.existe("no/esta.pdf")


def test_local_no_escapa_del_directorio(tmp_path):
    st = LocalStorage(str(tmp_path))
    try:
        st.leer("../fuera.txt")
        assert False, "debería rechazar rutas fuera del directorio"
    except ValueError:
        pass
```

- [ ] **Step 2: Verificar que falla**

```bash
cd api && .venv/bin/python -m pytest -q tests/test_storage.py
# Expected: FAIL — ModuleNotFoundError: app.storage
```

- [ ] **Step 3: Escribir `api/app/storage.py`**

```python
"""Documentos privados: R2 en producción (URL firmada), disco local en dev y tests."""
import pathlib

from .config import settings


class LocalStorage:
    def __init__(self, base: str):
        self.base = pathlib.Path(base)

    def _ruta(self, key: str) -> pathlib.Path:
        p = (self.base / key).resolve()
        if not p.is_relative_to(self.base.resolve()):
            raise ValueError(f"clave fuera del directorio: {key}")
        return p

    def guardar(self, key: str, data: bytes) -> None:
        p = self._ruta(key)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(data)

    def leer(self, key: str) -> bytes:
        return self._ruta(key).read_bytes()

    def existe(self, key: str) -> bool:
        return self._ruta(key).exists()

    def url_firmada(self, key: str, segundos: int = 900) -> str | None:
        return None  # sin URL directa: la API sirve el archivo por streaming


class R2Storage:
    """Cloudflare R2 vía API S3. Sin tests unitarios: se prueba en el deploy (Plan 3)."""

    def __init__(self):
        import boto3
        self.bucket = settings.r2_bucket
        self.s3 = boto3.client(
            "s3", endpoint_url=settings.r2_endpoint,
            aws_access_key_id=settings.r2_access_key,
            aws_secret_access_key=settings.r2_secret_key,
            region_name="auto",
        )

    def guardar(self, key: str, data: bytes) -> None:
        self.s3.put_object(Bucket=self.bucket, Key=key, Body=data)

    def leer(self, key: str) -> bytes:
        return self.s3.get_object(Bucket=self.bucket, Key=key)["Body"].read()

    def existe(self, key: str) -> bool:
        try:
            self.s3.head_object(Bucket=self.bucket, Key=key)
            return True
        except Exception:
            return False

    def url_firmada(self, key: str, segundos: int = 900) -> str | None:
        return self.s3.generate_presigned_url(
            "get_object", Params={"Bucket": self.bucket, "Key": key}, ExpiresIn=segundos)


def storage_por_defecto():
    if settings.storage_dir:
        return LocalStorage(settings.storage_dir)
    if settings.r2_endpoint:
        return R2Storage()
    raise RuntimeError("Configurar CT_STORAGE_DIR (dev) o CT_R2_* (producción)")
```

- [ ] **Step 4: Verificar que pasa**

```bash
cd api && .venv/bin/python -m pytest -q tests/test_storage.py
# Expected: 2 passed
```

- [ ] **Step 5: Commit**

```bash
git add api/app/storage.py api/tests/test_storage.py
git commit -m "API: storage con URL firmada (R2) y disco local para dev/tests" -m "Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

### Task 6: Administración — consorcio inicial, usuarios y códigos de unidad

**Files:**
- Create: `api/app/admin.py`, `api/cli.py`
- Test: `api/tests/test_admin.py`

- [ ] **Step 1: Escribir el test que falla** (`api/tests/test_admin.py`)

```python
import pytest

from app import admin, models, security


def test_init_consorcio_es_idempotente(db):
    c1 = admin.init_consorcio(db, "Rivadavia 2069", direccion="Av. Rivadavia 2069, CABA")
    c2 = admin.init_consorcio(db, "Rivadavia 2069")
    assert c1.id == c2.id
    assert db.query(models.Consorcio).count() == 1


def test_crear_usuario_y_verificar(db):
    u = admin.crear_usuario(db, "lucas@example.com", "Lucas", "auditor", "clave-larga")
    assert u.rol == "auditor"
    assert security.verificar(u.clave_hash, "clave-larga")
    with pytest.raises(ValueError):
        admin.crear_usuario(db, "x@example.com", "X", "hacker", "123")  # rol inválido


def test_generar_codigo_de_unidad(db):
    db.add(models.Unidad(uf=27, piso_depto="13-B", propietario="Alguien"))
    db.commit()
    codigo = admin.generar_codigo(db, 27)
    unidad = db.query(models.Unidad).filter_by(uf=27).one()
    assert len(codigo) == 8
    assert security.verificar(unidad.codigo_hash, codigo)
    with pytest.raises(ValueError):
        admin.generar_codigo(db, 999)  # unidad inexistente
```

- [ ] **Step 2: Verificar que falla**

```bash
cd api && .venv/bin/python -m pytest -q tests/test_admin.py
# Expected: FAIL — ModuleNotFoundError: app.admin
```

- [ ] **Step 3: Escribir `api/app/admin.py`**

```python
"""Altas administrativas: consorcio, usuarios y códigos de acceso por unidad."""
import secrets

from sqlalchemy.orm import Session

from . import models, security

ROLES = ("auditor", "consejo", "moderador")
# Sin 0/O/1/I para poder dictarlo por teléfono
ALFABETO = "23456789abcdefghjkmnpqrstuvwxyz"


def init_consorcio(db: Session, nombre: str, **campos) -> models.Consorcio:
    c = db.query(models.Consorcio).first()
    if not c:
        c = models.Consorcio(nombre=nombre, **campos)
        db.add(c)
        db.commit()
    return c


def crear_usuario(db: Session, email: str, nombre: str, rol: str, clave: str) -> models.Usuario:
    if rol not in ROLES:
        raise ValueError(f"Rol inválido: {rol}. Válidos: {', '.join(ROLES)}")
    u = models.Usuario(email=email.lower(), nombre=nombre, rol=rol, clave_hash=security.hashear(clave))
    db.add(u)
    db.commit()
    return u


def generar_codigo(db: Session, uf: int) -> str:
    unidad = db.query(models.Unidad).filter_by(uf=uf).first()
    if not unidad:
        raise ValueError(f"No existe la unidad UF {uf}")
    codigo = "".join(secrets.choice(ALFABETO) for _ in range(8))
    unidad.codigo_hash = security.hashear(codigo)
    db.commit()
    return codigo  # se muestra una sola vez; solo queda el hash
```

- [ ] **Step 4: Verificar que pasa**

```bash
cd api && .venv/bin/python -m pytest -q tests/test_admin.py
# Expected: 3 passed
```

- [ ] **Step 5: Escribir `api/cli.py`** (envoltorio de consola, sin test propio: la lógica ya está probada)

```python
"""Comandos administrativos: python cli.py init|usuario|codigo ..."""
import argparse
import getpass

from app import admin
from app.db import Base, SessionLocal, engine


def main() -> int:
    ap = argparse.ArgumentParser(prog="ct-api")
    sub = ap.add_subparsers(dest="cmd", required=True)
    i = sub.add_parser("init", help="Crear las tablas y el consorcio")
    i.add_argument("nombre")
    i.add_argument("--direccion", default="")
    i.add_argument("--cuit", default="")
    u = sub.add_parser("usuario", help="Crear un usuario (pide la clave por consola)")
    u.add_argument("email"); u.add_argument("nombre"); u.add_argument("rol", choices=admin.ROLES)
    c = sub.add_parser("codigo", help="Generar el código de acceso de una unidad")
    c.add_argument("uf", type=int)
    args = ap.parse_args()

    Base.metadata.create_all(engine)
    db = SessionLocal()
    try:
        if args.cmd == "init":
            con = admin.init_consorcio(db, args.nombre, direccion=args.direccion, cuit=args.cuit)
            print(f"Consorcio listo: {con.nombre} (id {con.id})")
        elif args.cmd == "usuario":
            clave = getpass.getpass("Clave: ")
            usr = admin.crear_usuario(db, args.email, args.nombre, args.rol, clave)
            print(f"Usuario {usr.email} creado con rol {usr.rol}")
        elif args.cmd == "codigo":
            print(f"Código de la UF {args.uf}: {admin.generar_codigo(db, args.uf)} (guardalo: no se vuelve a mostrar)")
    finally:
        db.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 6: Commit**

```bash
git add api/app/admin.py api/cli.py api/tests/test_admin.py
git commit -m "API: altas de consorcio, usuarios y códigos por unidad (CLI incluida)" -m "Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

### Task 7: Ingesta de liquidaciones

**Files:**
- Create: `api/app/ingesta.py`
- Test: `api/tests/test_ingesta.py`

- [ ] **Step 1: Escribir los tests que fallan** (`api/tests/test_ingesta.py`)

```python
"""La ingesta usa los fixtures reales del motor (julio y agosto 2026, cuadran al 100 %)."""
from app import ingesta, models
from app.storage import LocalStorage

from .conftest import FIXTURES


def preparar(db, tmp_path, periodo="2026-08", fixture="redconar_202608.txt"):
    st = LocalStorage(str(tmp_path))
    key = f"liquidaciones/{periodo}.txt"
    st.guardar(key, (FIXTURES / fixture).read_bytes())
    liq = models.Liquidacion(periodo=periodo, archivo_key=key)
    db.add(liq)
    db.commit()
    return st, liq


def test_procesar_agosto_queda_procesada_con_gastos_y_hallazgos(db, tmp_path):
    st, liq = preparar(db, tmp_path)
    ingesta.procesar(db, liq.id, st)
    db.refresh(liq)
    assert liq.estado == "procesada" and liq.cuadra
    assert liq.sistema != "" and liq.datos["periodo"]
    assert db.query(models.Gasto).filter_by(liquidacion_id=liq.id).count() > 20
    assert db.query(models.Hallazgo).filter_by(liquidacion_id=liq.id).count() > 0
    assert db.query(models.Unidad).count() > 100  # las 116 unidades sincronizadas


def test_procesar_usa_el_mes_anterior_si_existe(db, tmp_path):
    st, liq_jul = preparar(db, tmp_path, "2026-07", "redconar_202607.txt")
    ingesta.procesar(db, liq_jul.id, st)
    st.guardar("liquidaciones/2026-08.txt", (FIXTURES / "redconar_202608.txt").read_bytes())
    liq_ago = models.Liquidacion(periodo="2026-08", archivo_key="liquidaciones/2026-08.txt")
    db.add(liq_ago)
    db.commit()
    ingesta.procesar(db, liq_ago.id, st)
    db.refresh(liq_ago)
    assert liq_ago.estado == "procesada"


def test_archivo_invalido_queda_en_error(db, tmp_path):
    st = LocalStorage(str(tmp_path))
    st.guardar("liquidaciones/2026-08.txt", b"esto no es una liquidacion")
    liq = models.Liquidacion(periodo="2026-08", archivo_key="liquidaciones/2026-08.txt")
    db.add(liq)
    db.commit()
    ingesta.procesar(db, liq.id, st)
    db.refresh(liq)
    assert liq.estado == "error" and liq.error


def test_periodo_equivocado_queda_en_error(db, tmp_path):
    st, liq = preparar(db, tmp_path, periodo="2026-05", fixture="redconar_202608.txt")
    ingesta.procesar(db, liq.id, st)
    db.refresh(liq)
    assert liq.estado == "error" and "2026-08" in liq.error


def test_no_cuadra_no_inserta_gastos(db, tmp_path, monkeypatch):
    from ct.model import Check, Liquidacion as LiqMotor
    falsa = LiqMotor(sistema="test", periodo="Agosto 2026")
    falsa.checks.append(Check("total", ok=False, esperado=1.0, obtenido=2.0))
    monkeypatch.setattr(ingesta, "parsear_bytes", lambda nombre, data: falsa)
    st, liq = preparar(db, tmp_path)
    ingesta.procesar(db, liq.id, st)
    db.refresh(liq)
    assert liq.estado == "no_cuadra" and not liq.cuadra
    assert db.query(models.Gasto).count() == 0
```

- [ ] **Step 2: Verificar que fallan**

```bash
cd api && .venv/bin/python -m pytest -q tests/test_ingesta.py
# Expected: FAIL — ModuleNotFoundError: app.ingesta
```

- [ ] **Step 3: Escribir `api/app/ingesta.py`**

```python
"""Del PDF a la base: parseo, cuadre, reglas y sincronización. La regla de oro vive acá:
si la liquidación no cuadra queda en `no_cuadra` y no se inserta ni publica nada."""
import pathlib
import tempfile
from datetime import date

from sqlalchemy.orm import Session

from ct.model import Liquidacion as LiqMotor
from ct.redconar import parse_pdf, parse_text
from ct.rules import Config, Hallazgo as HallazgoMotor, evaluar

from . import models

MESES = {"enero": 1, "febrero": 2, "marzo": 3, "abril": 4, "mayo": 5, "junio": 6,
         "julio": 7, "agosto": 8, "septiembre": 9, "octubre": 10, "noviembre": 11, "diciembre": 12}


def periodo_iso(texto: str) -> str | None:
    """'Agosto 2026' -> '2026-08'. None si no se reconoce."""
    partes = texto.lower().split()
    mes = next((MESES[p] for p in partes if p in MESES), None)
    anio = next((p for p in partes if p.isdigit() and len(p) == 4), None)
    return f"{anio}-{mes:02d}" if mes and anio else None


def periodo_anterior(periodo: str) -> str:
    anio, mes = int(periodo[:4]), int(periodo[5:7])
    return f"{anio - 1}-12" if mes == 1 else f"{anio}-{mes - 1:02d}"


def parsear_bytes(nombre: str, data: bytes) -> LiqMotor:
    if nombre.lower().endswith(".pdf"):
        with tempfile.NamedTemporaryFile(suffix=".pdf") as f:
            f.write(data)
            f.flush()
            return parse_pdf(f.name)
    return parse_text(data.decode("utf-8"))


def clave_natural(h: HallazgoMotor) -> str:
    """Estable entre reprocesos: regla + referencias; si no hay refs, regla + título."""
    if h.refs:
        return f"{h.regla}|" + "|".join(sorted(str(r) for r in h.refs))
    return f"{h.regla}|{h.titulo}"[:500]


def config_consorcio(db: Session) -> Config:
    c = db.query(models.Consorcio).first()
    return Config.desde_dict(c.umbrales if c else None)


def cargar_engine(storage, liq_row: models.Liquidacion) -> LiqMotor:
    return parsear_bytes(liq_row.archivo_key, storage.leer(liq_row.archivo_key))


def cargar_anterior(db: Session, storage, periodo: str) -> LiqMotor | None:
    prev = (db.query(models.Liquidacion)
              .filter(models.Liquidacion.periodo == periodo_anterior(periodo),
                      models.Liquidacion.estado.in_(("procesada", "publicada"))).first())
    return cargar_engine(storage, prev) if prev else None


def guardar_gastos(db: Session, liq_row: models.Liquidacion, liq: LiqMotor) -> None:
    db.query(models.Gasto).filter_by(liquidacion_id=liq_row.id).delete()
    for g in liq.gastos:
        db.add(models.Gasto(
            liquidacion_id=liq_row.id, n=g.n, categoria=g.categoria, proveedor=g.proveedor,
            concepto=g.concepto, columna=g.columna, importe=g.importe,
            factura_fecha=g.factura_fecha, factura_nro=g.factura_nro, factura_importe=g.factura_importe,
            pagos=[{"fecha": p.fecha.isoformat() if p.fecha else None,
                    "importe": p.importe, "caja": p.caja, "forma": p.forma} for p in g.pagos]))


def sincronizar_unidades(db: Session, liq: LiqMotor) -> None:
    existentes = {u.uf: u for u in db.query(models.Unidad).all()}
    for u in liq.unidades:
        row = existentes.get(u.uf)
        if not row:
            row = models.Unidad(uf=u.uf)
            db.add(row)
        row.piso_depto, row.tipo, row.propietario = u.piso_depto, u.tipo, u.propietario
        row.porcentuales = u.pcts  # el codigo_hash nunca se toca acá


def upsert_hallazgos(db: Session, liq_row: models.Liquidacion,
                     hallazgos: list[HallazgoMotor], origen: str) -> None:
    """Reprocesar actualiza la descripción pero jamás pisa estado/publicado/respuesta.
    Los hallazgos que desaparecen se borran solo si siguen `pendiente` y sin publicar."""
    existentes = {h.clave: h for h in db.query(models.Hallazgo)
                  .filter_by(liquidacion_id=liq_row.id, origen=origen).all()}
    vistos = set()
    for h in hallazgos:
        clave = clave_natural(h)
        if clave in vistos:      # dos hallazgos de la misma regla y refs: distingue por título
            clave = f"{clave}|{h.titulo}"[:500]
        vistos.add(clave)
        row = existentes.get(clave)
        if not row:
            row = models.Hallazgo(liquidacion_id=liq_row.id, clave=clave, origen=origen, regla=h.regla,
                                  severidad=h.severidad, area=h.area, titulo=h.titulo, evidencia=h.evidencia)
            db.add(row)
        row.severidad, row.area, row.titulo = h.severidad, h.area, h.titulo
        row.evidencia, row.monto, row.recomendacion = h.evidencia, h.monto, h.recomendacion
        row.refs = [str(r) for r in h.refs]
    for clave, row in existentes.items():
        if clave not in vistos and row.estado == "pendiente" and not row.publicado:
            db.delete(row)


def procesar(db: Session, liq_id: int, storage) -> None:
    liq_row = db.get(models.Liquidacion, liq_id)
    try:
        liq = parsear_bytes(liq_row.archivo_key, storage.leer(liq_row.archivo_key))
        detectado = periodo_iso(liq.periodo)
        if detectado and detectado != liq_row.periodo:
            raise ValueError(f"El documento es de {detectado}, no de {liq_row.periodo}")
        liq_row.datos, liq_row.sistema, liq_row.cuadra = liq.to_dict(), liq.sistema, liq.cuadra
        if not liq.cuadra:
            liq_row.estado = "no_cuadra"
            db.commit()
            return
        hs = evaluar(liq, cargar_anterior(db, storage, liq_row.periodo), config_consorcio(db))
        guardar_gastos(db, liq_row, liq)
        sincronizar_unidades(db, liq)
        upsert_hallazgos(db, liq_row, hs, origen="liquidacion")
        liq_row.estado, liq_row.error = "procesada", ""
        db.commit()
    except Exception as e:
        db.rollback()
        liq_row = db.get(models.Liquidacion, liq_id)
        liq_row.estado, liq_row.error = "error", str(e)
        db.commit()
```

- [ ] **Step 4: Verificar que pasa**

```bash
cd api && .venv/bin/python -m pytest -q tests/test_ingesta.py
# Expected: 5 passed
```

- [ ] **Step 5: Commit**

```bash
git add api/app/ingesta.py api/tests/test_ingesta.py
git commit -m "API: ingesta de liquidaciones con cuadre obligatorio y sincronización" -m "Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

### Task 8: Reproceso que no pisa estados

**Files:**
- Test: `api/tests/test_reproceso.py` (la lógica ya existe en `upsert_hallazgos`; esta tarea la verifica de punta a punta)

- [ ] **Step 1: Escribir el test** (`api/tests/test_reproceso.py`)

```python
"""Reprocesar el mismo mes debe conservar el trabajo del auditor sobre los hallazgos."""
from app import ingesta, models

from .test_ingesta import preparar


def test_reprocesar_conserva_estado_y_publicacion(db, tmp_path):
    st, liq = preparar(db, tmp_path)
    ingesta.procesar(db, liq.id, st)
    h = db.query(models.Hallazgo).filter_by(liquidacion_id=liq.id).first()
    h.estado, h.publicado, h.respuesta_admin = "preguntado", True, "Dijeron que lo revisan"
    db.commit()
    clave, cantidad = h.clave, db.query(models.Hallazgo).count()

    liq.estado = "procesando"
    db.commit()
    ingesta.procesar(db, liq.id, st)

    h2 = db.query(models.Hallazgo).filter_by(liquidacion_id=liq.id, clave=clave).one()
    assert h2.estado == "preguntado" and h2.publicado
    assert h2.respuesta_admin == "Dijeron que lo revisan"
    assert db.query(models.Hallazgo).count() == cantidad  # sin duplicados


def test_reprocesar_no_borra_hallazgos_de_comprobantes(db, tmp_path):
    st, liq = preparar(db, tmp_path)
    ingesta.procesar(db, liq.id, st)
    db.add(models.Hallazgo(liquidacion_id=liq.id, clave="cruce|x", origen="comprobantes",
                           regla="cruce", severidad="CRÍTICO", area="Comprobantes",
                           titulo="Pago a un tercero", evidencia="e"))
    db.commit()
    liq.estado = "procesando"
    db.commit()
    ingesta.procesar(db, liq.id, st)
    assert db.query(models.Hallazgo).filter_by(origen="comprobantes").count() == 1
```

- [ ] **Step 2: Verificar que pasa** (si falla, el bug está en `upsert_hallazgos`)

```bash
cd api && .venv/bin/python -m pytest -q tests/test_reproceso.py
# Expected: 2 passed
```

- [ ] **Step 3: Commit**

```bash
git add api/tests/test_reproceso.py
git commit -m "API: pruebas de reproceso sin pisar el trabajo del auditor" -m "Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

### Task 9: App FastAPI y login

**Files:**
- Create: `api/app/main.py`, `api/app/routers/auth.py`
- Modify: `api/tests/conftest.py`
- Test: `api/tests/test_auth.py`

- [ ] **Step 1: Ampliar `api/tests/conftest.py`** (cliente autenticable con storage local)

```python
import pathlib

import pytest
from fastapi.testclient import TestClient

from app import admin
from app.db import Base, SessionLocal, engine, get_db
from app.storage import LocalStorage

FIXTURES = pathlib.Path(__file__).resolve().parents[2] / "engine" / "tests" / "fixtures"


@pytest.fixture()
def db():
    Base.metadata.create_all(engine)
    s = SessionLocal()
    yield s
    s.close()
    Base.metadata.drop_all(engine)


@pytest.fixture()
def cliente(db, tmp_path):
    from app.main import app
    app.dependency_overrides[get_db] = lambda: db
    app.state.storage = LocalStorage(str(tmp_path))
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture()
def auditor(db, cliente):
    admin.crear_usuario(db, "auditor@example.com", "Auditor", "auditor", "clave-de-test")
    r = cliente.post("/auth/login", json={"email": "auditor@example.com", "clave": "clave-de-test"})
    assert r.status_code == 200
    return cliente  # el cliente conserva la cookie
```

- [ ] **Step 2: Escribir el test que falla** (`api/tests/test_auth.py`)

```python
from app import admin, models


def test_login_y_yo(auditor):
    r = auditor.get("/auth/yo")
    assert r.status_code == 200
    assert r.json()["rol"] == "auditor"


def test_login_clave_incorrecta(db, cliente):
    admin.crear_usuario(db, "a@example.com", "A", "auditor", "correcta")
    r = cliente.post("/auth/login", json={"email": "a@example.com", "clave": "incorrecta"})
    assert r.status_code == 401


def test_sin_sesion_401(cliente):
    assert cliente.get("/auth/yo").status_code == 401


def test_login_unidad(db, cliente):
    db.add(models.Unidad(uf=27, piso_depto="13-B"))
    db.commit()
    codigo = admin.generar_codigo(db, 27)
    r = cliente.post("/auth/login-unidad", json={"uf": 27, "codigo": codigo})
    assert r.status_code == 200
    yo = cliente.get("/auth/yo").json()
    assert yo["rol"] == "propietario" and yo["uf"] == 27


def test_login_unidad_codigo_malo(db, cliente):
    db.add(models.Unidad(uf=27))
    db.commit()
    admin.generar_codigo(db, 27)
    assert cliente.post("/auth/login-unidad", json={"uf": 27, "codigo": "malo1234"}).status_code == 401


def test_salir(auditor):
    auditor.post("/auth/salir")
    assert auditor.get("/auth/yo").status_code == 401
```

- [ ] **Step 3: Verificar que falla**

```bash
cd api && .venv/bin/python -m pytest -q tests/test_auth.py
# Expected: FAIL — ModuleNotFoundError: app.main
```

- [ ] **Step 4: Escribir `api/app/routers/auth.py`**

```python
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel
from sqlalchemy.orm import Session

from .. import models, security
from ..config import settings
from ..db import get_db

router = APIRouter(prefix="/auth", tags=["auth"])


class LoginUsuario(BaseModel):
    email: str
    clave: str


class LoginUnidad(BaseModel):
    uf: int
    codigo: str


def _entrar(response: Response, sub: str, rol: str) -> None:
    response.set_cookie(security.COOKIE, security.crear_token(sub, rol), httponly=True,
                        samesite="lax", secure=settings.cookie_segura,
                        max_age=settings.jwt_horas * 3600)


@router.post("/login")
def login(datos: LoginUsuario, request: Request, response: Response, db: Session = Depends(get_db)):
    if not security.limiter_login.permitir(f"{request.client.host}|{datos.email.lower()}"):
        raise HTTPException(429, "Demasiados intentos; probá de nuevo en unos minutos")
    u = db.query(models.Usuario).filter_by(email=datos.email.lower()).first()
    if not u or not security.verificar(u.clave_hash, datos.clave):
        raise HTTPException(401, "Email o clave incorrectos")
    _entrar(response, f"u:{u.id}", u.rol)
    return {"rol": u.rol, "nombre": u.nombre}


@router.post("/login-unidad")
def login_unidad(datos: LoginUnidad, request: Request, response: Response, db: Session = Depends(get_db)):
    if not security.limiter_login.permitir(f"{request.client.host}|uf:{datos.uf}"):
        raise HTTPException(429, "Demasiados intentos; probá de nuevo en unos minutos")
    unidad = db.query(models.Unidad).filter_by(uf=datos.uf).first()
    if not unidad or not unidad.codigo_hash or not security.verificar(unidad.codigo_hash, datos.codigo):
        raise HTTPException(401, "Unidad o código incorrectos")
    _entrar(response, f"uf:{unidad.uf}", "propietario")
    return {"rol": "propietario", "uf": unidad.uf, "piso_depto": unidad.piso_depto}


@router.post("/salir")
def salir(response: Response):
    response.delete_cookie(security.COOKIE)
    return {"ok": True}


@router.get("/yo")
def yo(s: dict = Depends(security.sesion)):
    out = {"rol": s["rol"]}
    if s["sub"].startswith("uf:"):
        out["uf"] = int(s["sub"][3:])
    return out
```

- [ ] **Step 5: Escribir `api/app/main.py`**

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import settings
from .db import Base, engine
from .routers import auth
from .storage import storage_por_defecto

app = FastAPI(title="Consorcio Transparente — API")
app.add_middleware(CORSMiddleware, allow_origins=[settings.cors_origin],
                   allow_credentials=True, allow_methods=["*"], allow_headers=["*"])
app.include_router(auth.router)


@app.on_event("startup")
def arrancar():
    # Guarda de producción: sin R2 no hay deploy real, pero si hay R2 configurado
    # el secreto JWT por defecto es inaceptable (quedó en el historial de git).
    if settings.r2_endpoint and settings.jwt_secret == "solo-para-desarrollo":
        raise RuntimeError("CT_JWT_SECRET sin configurar: generar uno largo antes de desplegar")
    Base.metadata.create_all(engine)  # Alembic llega con el primer deploy (Plan 3)
    if not hasattr(app.state, "storage"):
        app.state.storage = storage_por_defecto()


@app.get("/salud")
def salud():
    return {"ok": True}
```

Nota: en tests `app.state.storage` se setea antes de arrancar, y `storage_por_defecto()` no se ejecuta (el `if hasattr` lo evita). Con `CT_STORAGE_DIR` vacío y sin R2, el arranque en frío falla a propósito: mejor un error claro que un storage mudo.

- [ ] **Step 6: Verificar que pasa**

```bash
cd api && .venv/bin/python -m pytest -q
# Expected: todos los tests hasta acá en verde (test_auth: 6 passed)
```

- [ ] **Step 7: Commit**

```bash
git add api/app/main.py api/app/routers/auth.py api/tests/conftest.py api/tests/test_auth.py
git commit -m "API: aplicación FastAPI con login de usuarios y de unidades" -m "Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

### Task 10: Endpoints de liquidaciones

**Files:**
- Create: `api/app/routers/liquidaciones.py`
- Modify: `api/app/main.py` (incluir router)
- Test: `api/tests/test_liquidaciones_api.py`

- [ ] **Step 1: Escribir el test que falla** (`api/tests/test_liquidaciones_api.py`)

```python
from .conftest import FIXTURES


def subir(cliente, periodo="2026-08", fixture="redconar_202608.txt"):
    return cliente.post("/liquidaciones",
                        data={"periodo": periodo},
                        files={"archivo": (fixture, (FIXTURES / fixture).read_bytes(), "text/plain")})


def test_subir_procesa_en_background(auditor):
    r = subir(auditor)
    assert r.status_code == 200
    # TestClient ejecuta las BackgroundTasks antes de devolver el control
    det = auditor.get(f"/liquidaciones/{r.json()['id']}").json()
    assert det["estado"] == "procesada" and det["cuadra"]
    assert det["checks_ok"] > 20 and det["checks_mal"] == 0
    assert len(det["gastos"]) > 20


def test_resubir_mismo_periodo_reusa_la_fila(auditor):
    id1 = subir(auditor).json()["id"]
    id2 = subir(auditor).json()["id"]
    assert id1 == id2
    lista = auditor.get("/liquidaciones").json()
    assert len(lista) == 1 and lista[0]["periodo"] == "2026-08"


def test_periodo_invalido_422(auditor):
    assert subir(auditor, periodo="agosto").status_code == 422


def test_solo_auditor_sube(db, cliente):
    from app import admin
    admin.crear_usuario(db, "c@example.com", "C", "consejo", "clave-de-test")
    cliente.post("/auth/login", json={"email": "c@example.com", "clave": "clave-de-test"})
    assert subir(cliente).status_code == 403


def test_listar_requiere_sesion(cliente):
    assert cliente.get("/liquidaciones").status_code == 401
```

- [ ] **Step 2: Verificar que falla**

```bash
cd api && .venv/bin/python -m pytest -q tests/test_liquidaciones_api.py
# Expected: FAIL — 404 en /liquidaciones
```

- [ ] **Step 3: Escribir `api/app/routers/liquidaciones.py`**

```python
import re

from fastapi import (APIRouter, BackgroundTasks, Depends, HTTPException,
                     Request, UploadFile, Form)
from sqlalchemy.orm import Session

from .. import ingesta, models, security
from ..db import SessionLocal, get_db

router = APIRouter(prefix="/liquidaciones", tags=["liquidaciones"])
PERIODO = re.compile(r"^\d{4}-(0[1-9]|1[0-2])$")


def _procesar_en_background(liq_id: int, storage) -> None:
    db = SessionLocal()
    try:
        ingesta.procesar(db, liq_id, storage)
    finally:
        db.close()


@router.post("")
def subir(request: Request, tareas: BackgroundTasks, archivo: UploadFile,
          periodo: str = Form(...), db: Session = Depends(get_db),
          s: dict = Depends(security.requiere("auditor"))):
    if not PERIODO.match(periodo):
        raise HTTPException(422, "El período debe ser AAAA-MM, por ejemplo 2026-08")
    sufijo = ".pdf" if (archivo.filename or "").lower().endswith(".pdf") else ".txt"
    key = f"liquidaciones/{periodo}{sufijo}"
    request.app.state.storage.guardar(key, archivo.file.read())
    liq = db.query(models.Liquidacion).filter_by(periodo=periodo).first()
    if not liq:
        liq = models.Liquidacion(periodo=periodo, archivo_key=key)
        db.add(liq)
    liq.archivo_key, liq.estado, liq.error = key, "procesando", ""
    db.commit()
    tareas.add_task(_procesar_en_background, liq.id, request.app.state.storage)
    return {"id": liq.id, "periodo": periodo, "estado": "procesando"}


@router.get("")
def listar(db: Session = Depends(get_db), s: dict = Depends(security.sesion)):
    filas = db.query(models.Liquidacion).order_by(models.Liquidacion.periodo.desc()).all()
    return [{"id": l.id, "periodo": l.periodo, "estado": l.estado, "cuadra": l.cuadra,
             "sistema": l.sistema, "error": l.error} for l in filas]


@router.get("/{liq_id}")
def detalle(liq_id: int, db: Session = Depends(get_db),
            s: dict = Depends(security.requiere("auditor", "consejo", "moderador"))):
    liq = db.get(models.Liquidacion, liq_id)
    if not liq:
        raise HTTPException(404, "No existe esa liquidación")
    checks = (liq.datos or {}).get("checks", [])
    return {
        "id": liq.id, "periodo": liq.periodo, "estado": liq.estado, "cuadra": liq.cuadra,
        "sistema": liq.sistema, "error": liq.error,
        "checks_ok": sum(1 for c in checks if c["ok"]),
        "checks_mal": sum(1 for c in checks if not c["ok"]),
        "checks": [c for c in checks if not c["ok"]],
        "totales_categoria": (liq.datos or {}).get("totales_categoria", {}),
        "gastos": [{"n": g.n, "categoria": g.categoria, "proveedor": g.proveedor,
                    "concepto": g.concepto, "columna": g.columna, "importe": g.importe,
                    "factura_nro": g.factura_nro, "pagos": g.pagos} for g in liq.gastos],
    }
```

- [ ] **Step 4: Incluir el router en `api/app/main.py`**

```python
from .routers import auth, liquidaciones
# ...
app.include_router(auth.router)
app.include_router(liquidaciones.router)
```

- [ ] **Step 5: Verificar que pasa**

```bash
cd api && .venv/bin/python -m pytest -q
# Expected: test_liquidaciones_api: 5 passed; el resto en verde
```

- [ ] **Step 6: Commit**

```bash
git add api/app/routers/liquidaciones.py api/app/main.py api/tests/test_liquidaciones_api.py
git commit -m "API: subir, listar y ver liquidaciones con procesamiento en background" -m "Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

### Task 11: Endpoints de hallazgos

**Files:**
- Create: `api/app/routers/hallazgos.py`
- Modify: `api/app/main.py`
- Test: `api/tests/test_hallazgos_api.py`

- [ ] **Step 1: Escribir el test que falla** (`api/tests/test_hallazgos_api.py`)

```python
from app import models

from .test_liquidaciones_api import subir

ESTADOS = ("pendiente", "preguntado", "respondido", "descartado", "cerrado")


def con_datos(auditor):
    subir(auditor)
    return auditor


def test_listar_y_filtrar(db, auditor):
    con_datos(auditor)
    todos = auditor.get("/hallazgos").json()
    assert len(todos) > 0 and {"id", "regla", "severidad", "estado", "titulo"} <= set(todos[0])
    criticos = auditor.get("/hallazgos", params={"severidad": "CRÍTICO"}).json()
    assert all(h["severidad"] == "CRÍTICO" for h in criticos)


def test_cambiar_estado_crea_evento(db, auditor):
    con_datos(auditor)
    h = auditor.get("/hallazgos").json()[0]
    r = auditor.post(f"/hallazgos/{h['id']}/estado",
                     json={"estado": "preguntado", "nota": "Se preguntó en la asamblea"})
    assert r.status_code == 200
    det = auditor.get(f"/hallazgos/{h['id']}").json()
    assert det["estado"] == "preguntado"
    assert det["eventos"][0]["a"] == "preguntado"
    assert det["eventos"][0]["nota"] == "Se preguntó en la asamblea"
    assert det["eventos"][0]["usuario"] == "Auditor"


def test_estado_invalido_422(auditor):
    con_datos(auditor)
    h = auditor.get("/hallazgos").json()[0]
    assert auditor.post(f"/hallazgos/{h['id']}/estado", json={"estado": "inventado"}).status_code == 422


def test_publicar_y_respuesta(auditor):
    con_datos(auditor)
    h = auditor.get("/hallazgos").json()[0]
    auditor.post(f"/hallazgos/{h['id']}/publicar", json={"publicado": True})
    auditor.post(f"/hallazgos/{h['id']}/respuesta", json={"texto": "La administración respondió X"})
    det = auditor.get(f"/hallazgos/{h['id']}").json()
    assert det["publicado"] and det["respuesta_admin"] == "La administración respondió X"


def test_consejo_lee_pero_no_cambia(db, auditor):
    from app import admin
    con_datos(auditor)
    h = auditor.get("/hallazgos").json()[0]
    admin.crear_usuario(db, "c@example.com", "C", "consejo", "clave-de-test")
    auditor.post("/auth/login", json={"email": "c@example.com", "clave": "clave-de-test"})
    assert auditor.get("/hallazgos").status_code == 200
    assert auditor.post(f"/hallazgos/{h['id']}/estado", json={"estado": "cerrado"}).status_code == 403
```

- [ ] **Step 2: Verificar que falla**

```bash
cd api && .venv/bin/python -m pytest -q tests/test_hallazgos_api.py
# Expected: FAIL — 404 en /hallazgos
```

- [ ] **Step 3: Escribir `api/app/routers/hallazgos.py`**

```python
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from .. import models, security
from ..db import get_db

router = APIRouter(prefix="/hallazgos", tags=["hallazgos"])
ESTADOS = ("pendiente", "preguntado", "respondido", "descartado", "cerrado")
ORDEN_SEV = {"CRÍTICO": 0, "ALTO": 1, "MEDIO": 2, "BAJO": 3}


class CambioEstado(BaseModel):
    estado: str
    nota: str = ""


class CambioPublicado(BaseModel):
    publicado: bool


class Respuesta(BaseModel):
    texto: str


def _usuario(db: Session, s: dict) -> models.Usuario | None:
    return db.get(models.Usuario, int(s["sub"][2:])) if s["sub"].startswith("u:") else None


def _resumen(h: models.Hallazgo) -> dict:
    return {"id": h.id, "liquidacion_id": h.liquidacion_id, "periodo": h.liquidacion.periodo,
            "regla": h.regla, "origen": h.origen, "severidad": h.severidad, "area": h.area,
            "titulo": h.titulo, "monto": h.monto, "estado": h.estado, "publicado": h.publicado}


@router.get("")
def listar(severidad: str | None = None, estado: str | None = None, regla: str | None = None,
           periodo: str | None = None, db: Session = Depends(get_db),
           s: dict = Depends(security.requiere("auditor", "consejo", "moderador"))):
    q = db.query(models.Hallazgo).join(models.Liquidacion)
    if severidad:
        q = q.filter(models.Hallazgo.severidad == severidad)
    if estado:
        q = q.filter(models.Hallazgo.estado == estado)
    if regla:
        q = q.filter(models.Hallazgo.regla == regla)
    if periodo:
        q = q.filter(models.Liquidacion.periodo == periodo)
    filas = sorted(q.all(), key=lambda h: (ORDEN_SEV.get(h.severidad, 9), -abs(h.monto)))
    return [_resumen(h) for h in filas]


@router.get("/{h_id}")
def detalle(h_id: int, db: Session = Depends(get_db),
            s: dict = Depends(security.requiere("auditor", "consejo", "moderador"))):
    h = db.get(models.Hallazgo, h_id)
    if not h:
        raise HTTPException(404, "No existe ese hallazgo")
    eventos = sorted(h.eventos, key=lambda e: e.ts, reverse=True)
    usuarios = {u.id: u.nombre for u in db.query(models.Usuario).all()}
    return {**_resumen(h), "evidencia": h.evidencia, "recomendacion": h.recomendacion,
            "refs": h.refs, "respuesta_admin": h.respuesta_admin,
            "eventos": [{"de": e.de, "a": e.a, "nota": e.nota, "ts": e.ts.isoformat(),
                         "usuario": usuarios.get(e.usuario_id, "")} for e in eventos]}


@router.post("/{h_id}/estado")
def cambiar_estado(h_id: int, cambio: CambioEstado, db: Session = Depends(get_db),
                   s: dict = Depends(security.requiere("auditor"))):
    if cambio.estado not in ESTADOS:
        raise HTTPException(422, f"Estado inválido; válidos: {', '.join(ESTADOS)}")
    h = db.get(models.Hallazgo, h_id)
    if not h:
        raise HTTPException(404, "No existe ese hallazgo")
    u = _usuario(db, s)
    db.add(models.HallazgoEvento(hallazgo_id=h.id, usuario_id=u.id if u else None,
                                 de=h.estado, a=cambio.estado, nota=cambio.nota))
    h.estado = cambio.estado
    db.commit()
    return {"ok": True, "estado": h.estado}


@router.post("/{h_id}/publicar")
def publicar(h_id: int, cambio: CambioPublicado, db: Session = Depends(get_db),
             s: dict = Depends(security.requiere("auditor"))):
    h = db.get(models.Hallazgo, h_id)
    if not h:
        raise HTTPException(404, "No existe ese hallazgo")
    h.publicado = cambio.publicado
    db.commit()
    return {"ok": True, "publicado": h.publicado}


@router.post("/{h_id}/respuesta")
def registrar_respuesta(h_id: int, r: Respuesta, db: Session = Depends(get_db),
                        s: dict = Depends(security.requiere("auditor"))):
    h = db.get(models.Hallazgo, h_id)
    if not h:
        raise HTTPException(404, "No existe ese hallazgo")
    h.respuesta_admin = r.texto
    db.commit()
    return {"ok": True}
```

- [ ] **Step 4: Incluir el router en `api/app/main.py`** (`from .routers import auth, hallazgos, liquidaciones` + `app.include_router(hallazgos.router)`)

- [ ] **Step 5: Verificar que pasa**

```bash
cd api && .venv/bin/python -m pytest -q
# Expected: test_hallazgos_api: 5 passed; el resto en verde
```

- [ ] **Step 6: Commit**

```bash
git add api/app/routers/hallazgos.py api/app/main.py api/tests/test_hallazgos_api.py
git commit -m "API: hallazgos con estados, historial, publicación y respuesta" -m "Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

### Task 12: Comprobantes — ZIP, cruce y documentos

**Files:**
- Modify: `api/app/ingesta.py` (agregar `cruzar_comprobantes`)
- Modify: `api/app/routers/liquidaciones.py` (endpoint POST `/{id}/comprobantes`)
- Test: `api/tests/test_comprobantes_api.py`

- [ ] **Step 1: Escribir el test que falla** (`api/tests/test_comprobantes_api.py`)

El test arma un ZIP sintético con `manifest.json` estilo `ct descargar` y archivos de texto (no hay PDF reales en el repo; `pdftotext` sobre no-PDF devuelve vacío y el cruce igual detecta faltantes — eso alcanza para probar la tubería completa).

```python
import io
import json
import zipfile

from app import models

from .test_liquidaciones_api import subir


def zip_comprobantes(liq_datos):
    """Manifiesto con el formato de ct descargar: filas n/mes/archivo."""
    g = liq_datos["gastos"][0]
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr("2026-08 Agosto/gasto-001-factura.pdf", b"no es un pdf real")
        z.writestr("manifest.json", json.dumps([
            {"n": g["n"], "mes": "2026-08-01", "proveedor": g["proveedor"],
             "archivo": "2026-08 Agosto/gasto-001-factura.pdf"},
        ]))
    return buf.getvalue()


def test_subir_comprobantes_crea_documentos_y_hallazgos(db, auditor):
    liq_id = subir(auditor).json()["id"]
    datos = db.get(models.Liquidacion, liq_id).datos
    r = auditor.post(f"/liquidaciones/{liq_id}/comprobantes",
                     files={"archivo": ("agosto.zip", zip_comprobantes(datos), "application/zip")})
    assert r.status_code == 200
    assert db.query(models.Documento).filter_by(liquidacion_id=liq_id).count() >= 1
    cruce = db.query(models.Hallazgo).filter_by(liquidacion_id=liq_id, origen="comprobantes").all()
    assert len(cruce) > 0  # al menos los gastos sin comprobante


def test_resubir_no_duplica_documentos(db, auditor):
    liq_id = subir(auditor).json()["id"]
    datos = db.get(models.Liquidacion, liq_id).datos
    z = zip_comprobantes(datos)
    auditor.post(f"/liquidaciones/{liq_id}/comprobantes", files={"archivo": ("a.zip", z, "application/zip")})
    n1 = db.query(models.Documento).count()
    auditor.post(f"/liquidaciones/{liq_id}/comprobantes", files={"archivo": ("a.zip", z, "application/zip")})
    assert db.query(models.Documento).count() == n1


def test_zip_sin_manifiesto_da_error(db, auditor):
    liq_id = subir(auditor).json()["id"]
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr("suelto.txt", b"x")
    r = auditor.post(f"/liquidaciones/{liq_id}/comprobantes",
                     files={"archivo": ("malo.zip", buf.getvalue(), "application/zip")})
    assert r.status_code == 422
```

- [ ] **Step 2: Verificar que falla**

```bash
cd api && .venv/bin/python -m pytest -q tests/test_comprobantes_api.py
# Expected: FAIL — 404 en /liquidaciones/{id}/comprobantes
```

- [ ] **Step 3: Agregar a `api/app/ingesta.py`**

```python
# imports nuevos al tope del archivo
import io
import zipfile

from ct.comprobantes import cargar_manifiesto_redconar, cruzar


def cruzar_comprobantes(db: Session, liq_id: int, zip_bytes: bytes, storage) -> None:
    """Descomprime el ZIP del portal, corre el cruce del motor y persiste documentos y hallazgos."""
    liq_row = db.get(models.Liquidacion, liq_id)
    with tempfile.TemporaryDirectory() as tmp:
        with zipfile.ZipFile(io.BytesIO(zip_bytes)) as z:
            z.extractall(tmp)
        manifiestos = list(pathlib.Path(tmp).rglob("manifest.json"))
        if not manifiestos:
            raise ValueError("El ZIP no trae manifest.json (usar la carpeta que genera ct descargar)")
        carpeta = manifiestos[0].parent
        items = cargar_manifiesto_redconar(str(manifiestos[0]), str(carpeta), mes=liq_row.periodo)
        liq = cargar_engine(storage, liq_row)
        docs, hallazgos = cruzar(liq, items)

        db.query(models.Documento).filter_by(liquidacion_id=liq_row.id).delete()
        for d in docs:
            origen_path = pathlib.Path(d.archivo)
            rel = origen_path.relative_to(carpeta) if origen_path.is_relative_to(carpeta) else origen_path.name
            key = f"comprobantes/{liq_row.periodo}/{rel}"
            if origen_path.exists():
                storage.guardar(key, origen_path.read_bytes())
            db.add(models.Documento(liquidacion_id=liq_row.id, gasto_n=d.gasto_n, tipo=d.tipo,
                                    archivo_key=key, hash=d.hash, metadatos=d.to_dict()))
        upsert_hallazgos(db, liq_row, hallazgos, origen="comprobantes")
        db.commit()
```

- [ ] **Step 4: Agregar el endpoint a `api/app/routers/liquidaciones.py`**

```python
@router.post("/{liq_id}/comprobantes")
def subir_comprobantes(liq_id: int, request: Request, archivo: UploadFile,
                       db: Session = Depends(get_db),
                       s: dict = Depends(security.requiere("auditor"))):
    liq = db.get(models.Liquidacion, liq_id)
    if not liq:
        raise HTTPException(404, "No existe esa liquidación")
    if liq.estado not in ("procesada", "publicada"):
        raise HTTPException(409, f"La liquidación está en estado {liq.estado}; procesarla primero")
    try:
        # sincrónico: son segundos, y así el error llega directo al auditor
        ingesta.cruzar_comprobantes(db, liq.id, archivo.file.read(), request.app.state.storage)
    except ValueError as e:
        raise HTTPException(422, str(e))
    docs = db.query(models.Documento).filter_by(liquidacion_id=liq.id).count()
    cruce = db.query(models.Hallazgo).filter_by(liquidacion_id=liq.id, origen="comprobantes").count()
    return {"ok": True, "documentos": docs, "hallazgos_cruce": cruce}
```

- [ ] **Step 5: Verificar que pasa**

```bash
cd api && .venv/bin/python -m pytest -q
# Expected: test_comprobantes_api: 3 passed; el resto en verde
```

- [ ] **Step 6: Commit**

```bash
git add api/app/ingesta.py api/app/routers/liquidaciones.py api/tests/test_comprobantes_api.py
git commit -m "API: carga de comprobantes por ZIP con cruce del motor" -m "Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

### Task 13: Publicación de informes

**Files:**
- Create: `api/app/publicar.py`
- Modify: `api/app/routers/liquidaciones.py` (endpoint POST `/{id}/publicar`)
- Test: `api/tests/test_publicar.py`

- [ ] **Step 1: Escribir el test que falla** (`api/tests/test_publicar.py`)

```python
from app import models

from .test_liquidaciones_api import subir


def test_publicar_genera_informes_y_cambia_estado(db, auditor, tmp_path):
    liq_id = subir(auditor).json()["id"]
    for h in db.query(models.Hallazgo).limit(3):
        h.publicado = True
    db.commit()
    r = auditor.post(f"/liquidaciones/{liq_id}/publicar")
    assert r.status_code == 200
    liq = db.get(models.Liquidacion, liq_id)
    assert liq.estado == "publicada"
    informes = {i.tipo: i for i in db.query(models.Informe).filter_by(liquidacion_id=liq_id)}
    assert set(informes) == {"html", "xlsx"}
    assert (tmp_path / informes["html"].archivo_key).exists()
    html = (tmp_path / informes["html"].archivo_key).read_text()
    assert "Consorcio Transparente" in html


def test_no_publicable_si_no_esta_procesada(db, auditor):
    liq = models.Liquidacion(periodo="2026-01", archivo_key="x", estado="no_cuadra")
    db.add(liq)
    db.commit()
    assert auditor.post(f"/liquidaciones/{liq.id}/publicar").status_code == 409


def test_republicar_actualiza_sin_duplicar(db, auditor):
    liq_id = subir(auditor).json()["id"]
    auditor.post(f"/liquidaciones/{liq_id}/publicar")
    auditor.post(f"/liquidaciones/{liq_id}/publicar")
    assert db.query(models.Informe).filter_by(liquidacion_id=liq_id).count() == 2  # html y xlsx, una vez
```

- [ ] **Step 2: Verificar que falla**

```bash
cd api && .venv/bin/python -m pytest -q tests/test_publicar.py
# Expected: FAIL — 404 en /liquidaciones/{id}/publicar
```

- [ ] **Step 3: Escribir `api/app/publicar.py`**

```python
"""Publicar = generar los informes del motor con los hallazgos aprobados y marcar la liquidación."""
import pathlib
import tempfile
from datetime import date

from sqlalchemy.orm import Session

from ct.comprobantes import Documento as DocumentoMotor
from ct.informe import informe_excel, informe_html
from ct.rules import Hallazgo as HallazgoMotor

from . import ingesta, models


def _hallazgos_motor(liq_row: models.Liquidacion) -> list[HallazgoMotor]:
    orden = {"CRÍTICO": 0, "ALTO": 1, "MEDIO": 2, "BAJO": 3}
    filas = sorted((h for h in liq_row.hallazgos if h.publicado),
                   key=lambda h: (orden.get(h.severidad, 9), -abs(h.monto)))
    return [HallazgoMotor(regla=h.regla, severidad=h.severidad, area=h.area, titulo=h.titulo,
                          evidencia=h.evidencia, monto=h.monto, recomendacion=h.recomendacion,
                          refs=list(h.refs)) for h in filas]


def _documentos_motor(db: Session, liq_row: models.Liquidacion) -> list[DocumentoMotor]:
    docs = []
    for d in db.query(models.Documento).filter_by(liquidacion_id=liq_row.id):
        md = dict(d.metadatos)
        if md.get("fecha"):
            md["fecha"] = date.fromisoformat(md["fecha"])
        docs.append(DocumentoMotor(**md))
    return docs


def publicar(db: Session, liq_id: int, storage) -> dict:
    liq_row = db.get(models.Liquidacion, liq_id)
    if liq_row.estado not in ("procesada", "publicada"):
        raise ValueError(f"No se puede publicar en estado {liq_row.estado}: primero tiene que cuadrar")
    consorcio = db.query(models.Consorcio).first()
    marca = consorcio.marca if consorcio else "Consorcio Transparente"
    liq = ingesta.cargar_engine(storage, liq_row)
    prev = ingesta.cargar_anterior(db, storage, liq_row.periodo)
    hs = _hallazgos_motor(liq_row)
    docs = _documentos_motor(db, liq_row)

    with tempfile.TemporaryDirectory() as tmp:
        rutas = {"html": pathlib.Path(tmp) / "informe.html", "xlsx": pathlib.Path(tmp) / "informe.xlsx"}
        informe_html(liq, hs, str(rutas["html"]), prev, docs, marca)
        informe_excel(liq, hs, str(rutas["xlsx"]), prev, docs, marca)
        for tipo, ruta in rutas.items():
            key = f"informes/{liq_row.periodo}.{tipo}"
            storage.guardar(key, ruta.read_bytes())
            fila = db.query(models.Informe).filter_by(liquidacion_id=liq_row.id, tipo=tipo).first()
            if not fila:
                fila = models.Informe(liquidacion_id=liq_row.id, tipo=tipo, archivo_key=key)
                db.add(fila)
            fila.archivo_key, fila.marca, fila.publicado_en = key, marca, models.ahora()
    liq_row.estado = "publicada"
    db.commit()
    return {"hallazgos_publicados": len(hs)}
```

- [ ] **Step 4: Agregar el endpoint a `api/app/routers/liquidaciones.py`**

```python
# import nuevo al tope
from .. import publicar as publicacion


@router.post("/{liq_id}/publicar")
def publicar_liquidacion(liq_id: int, request: Request, db: Session = Depends(get_db),
                         s: dict = Depends(security.requiere("auditor"))):
    liq = db.get(models.Liquidacion, liq_id)
    if not liq:
        raise HTTPException(404, "No existe esa liquidación")
    try:
        out = publicacion.publicar(db, liq.id, request.app.state.storage)
    except ValueError as e:
        raise HTTPException(409, str(e))
    return {"ok": True, **out}
```

- [ ] **Step 5: Verificar que pasa**

```bash
cd api && .venv/bin/python -m pytest -q
# Expected: test_publicar: 3 passed; el resto en verde
```

- [ ] **Step 6: Commit**

```bash
git add api/app/publicar.py api/app/routers/liquidaciones.py api/tests/test_publicar.py
git commit -m "API: publicación de informes HTML y Excel desde la base" -m "Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

### Task 14: Consorcio, documentos firmados y vista del propietario

**Files:**
- Create: `api/app/routers/consorcio.py`, `api/app/routers/documentos.py`
- Modify: `api/app/main.py`
- Test: `api/tests/test_consorcio_api.py`, `api/tests/test_documentos_api.py`

- [ ] **Step 1: Escribir los tests que fallan**

`api/tests/test_consorcio_api.py`:

```python
from app import admin, models


def test_ver_y_editar_umbrales(db, auditor):
    admin.init_consorcio(db, "Rivadavia 2069")
    r = auditor.put("/consorcio", json={"umbrales": {"efectivo_linea_alta": 500000}})
    assert r.status_code == 200
    assert auditor.get("/consorcio").json()["umbrales"]["efectivo_linea_alta"] == 500000


def test_umbral_desconocido_422(db, auditor):
    admin.init_consorcio(db, "Rivadavia 2069")
    r = auditor.put("/consorcio", json={"umbrales": {"umbral_inventado": 1}})
    assert r.status_code == 422


def test_generar_codigo_por_endpoint(db, auditor):
    db.add(models.Unidad(uf=27, piso_depto="13-B"))
    db.commit()
    r = auditor.post("/unidades/27/codigo")
    assert r.status_code == 200 and len(r.json()["codigo"]) == 8
    assert auditor.get("/unidades").json()[0]["tiene_codigo"] is True
```

`api/tests/test_documentos_api.py`:

```python
from app import admin, models

from .test_liquidaciones_api import subir


def test_descargar_documento_con_rol(db, auditor, tmp_path):
    liq_id = subir(auditor).json()["id"]
    st_key = "comprobantes/2026-08/f.pdf"
    (tmp_path / "comprobantes/2026-08").mkdir(parents=True)
    (tmp_path / st_key).write_bytes(b"pdf")
    d = models.Documento(liquidacion_id=liq_id, tipo="factura", archivo_key=st_key)
    db.add(d)
    db.commit()
    r = auditor.get(f"/documentos/{d.id}/contenido")
    assert r.status_code == 200 and r.content == b"pdf"


def test_propietario_no_ve_documentos(db, cliente, auditor, tmp_path):
    liq_id = subir(auditor).json()["id"]
    d = models.Documento(liquidacion_id=liq_id, tipo="factura", archivo_key="x.pdf")
    db.add(d)
    db.add(models.Unidad(uf=1))
    db.commit()
    codigo = admin.generar_codigo(db, 1)
    cliente.post("/auth/login-unidad", json={"uf": 1, "codigo": codigo})
    assert cliente.get(f"/documentos/{d.id}/contenido").status_code == 403


def test_propietario_ve_informe_publicado(db, cliente, auditor):
    liq_id = subir(auditor).json()["id"]
    auditor.post(f"/liquidaciones/{liq_id}/publicar")
    uf = db.query(models.Unidad).first().uf
    codigo = admin.generar_codigo(db, uf)
    cliente.post("/auth/login-unidad", json={"uf": uf, "codigo": codigo})
    mi = cliente.get("/mi-unidad").json()
    assert mi["uf"] == uf and mi["periodo"] == "2026-08"
    r = cliente.get(f"/informes/2026-08/html")
    assert r.status_code == 200 and b"Consorcio" in r.content


def test_propietario_no_ve_informe_sin_publicar(db, cliente, auditor):
    subir(auditor)
    uf = db.query(models.Unidad).first().uf
    codigo = admin.generar_codigo(db, uf)
    cliente.post("/auth/login-unidad", json={"uf": uf, "codigo": codigo})
    assert cliente.get("/informes/2026-08/html").status_code == 404
    assert cliente.get("/mi-unidad").status_code == 404
```

- [ ] **Step 2: Verificar que fallan**

```bash
cd api && .venv/bin/python -m pytest -q tests/test_consorcio_api.py tests/test_documentos_api.py
# Expected: FAIL — 404 y 405 en las rutas nuevas
```

- [ ] **Step 3: Escribir `api/app/routers/consorcio.py`**

```python
from dataclasses import fields

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ct.rules import Config

from .. import admin, models, security
from ..db import get_db

router = APIRouter(tags=["consorcio"])
UMBRALES_VALIDOS = {f.name for f in fields(Config)}


class CambioConsorcio(BaseModel):
    nombre: str | None = None
    direccion: str | None = None
    cuit: str | None = None
    admin_nombre: str | None = None
    admin_cuit: str | None = None
    marca: str | None = None
    umbrales: dict | None = None


@router.get("/consorcio")
def ver(db: Session = Depends(get_db),
        s: dict = Depends(security.requiere("auditor", "consejo", "moderador"))):
    c = db.query(models.Consorcio).first()
    if not c:
        raise HTTPException(404, "Inicializar el consorcio primero (cli.py init)")
    return {"nombre": c.nombre, "direccion": c.direccion, "cuit": c.cuit,
            "admin_nombre": c.admin_nombre, "admin_cuit": c.admin_cuit,
            "marca": c.marca, "umbrales": c.umbrales,
            "umbrales_default": {f.name: getattr(Config(), f.name) for f in fields(Config)}}


@router.put("/consorcio")
def editar(cambio: CambioConsorcio, db: Session = Depends(get_db),
           s: dict = Depends(security.requiere("auditor"))):
    c = db.query(models.Consorcio).first()
    if not c:
        raise HTTPException(404, "Inicializar el consorcio primero (cli.py init)")
    if cambio.umbrales is not None:
        raros = set(cambio.umbrales) - UMBRALES_VALIDOS
        if raros:
            raise HTTPException(422, f"Umbrales desconocidos: {', '.join(sorted(raros))}")
        c.umbrales = cambio.umbrales
    for campo in ("nombre", "direccion", "cuit", "admin_nombre", "admin_cuit", "marca"):
        valor = getattr(cambio, campo)
        if valor is not None:
            setattr(c, campo, valor)
    db.commit()
    return {"ok": True}


@router.get("/unidades")
def unidades(db: Session = Depends(get_db),
             s: dict = Depends(security.requiere("auditor", "consejo"))):
    return [{"uf": u.uf, "piso_depto": u.piso_depto, "tipo": u.tipo,
             "propietario": u.propietario, "tiene_codigo": u.codigo_hash is not None}
            for u in db.query(models.Unidad).order_by(models.Unidad.uf)]


@router.post("/unidades/{uf}/codigo")
def codigo(uf: int, db: Session = Depends(get_db),
           s: dict = Depends(security.requiere("auditor"))):
    try:
        return {"uf": uf, "codigo": admin.generar_codigo(db, uf)}
    except ValueError as e:
        raise HTTPException(404, str(e))
```

- [ ] **Step 4: Escribir `api/app/routers/documentos.py`**

```python
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy.orm import Session

from .. import models, security
from ..db import get_db

router = APIRouter(tags=["documentos"])
MIME = {"html": "text/html", "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "pdf": "application/pdf"}


def _mime(key: str) -> str:
    return MIME.get(key.rsplit(".", 1)[-1].lower(), "application/octet-stream")


def _servir(request: Request, key: str) -> Response:
    url = request.app.state.storage.url_firmada(key)
    if url:
        return Response(status_code=307, headers={"Location": url})
    return Response(request.app.state.storage.leer(key), media_type=_mime(key))


@router.get("/documentos")
def listar(liquidacion_id: int, db: Session = Depends(get_db),
           s: dict = Depends(security.requiere("auditor", "consejo", "moderador"))):
    filas = db.query(models.Documento).filter_by(liquidacion_id=liquidacion_id).all()
    return [{"id": d.id, "gasto_n": d.gasto_n, "tipo": d.tipo, "hash": d.hash,
             "metadatos": d.metadatos} for d in filas]


@router.get("/documentos/{d_id}/contenido")
def contenido(d_id: int, request: Request, db: Session = Depends(get_db),
              s: dict = Depends(security.requiere("auditor", "consejo", "moderador"))):
    d = db.get(models.Documento, d_id)
    if not d:
        raise HTTPException(404, "No existe ese documento")
    return _servir(request, d.archivo_key)


@router.get("/informes/{periodo}/{tipo}")
def informe(periodo: str, tipo: str, request: Request, db: Session = Depends(get_db),
            s: dict = Depends(security.sesion)):
    fila = (db.query(models.Informe).join(models.Liquidacion)
              .filter(models.Liquidacion.periodo == periodo,
                      models.Liquidacion.estado == "publicada",
                      models.Informe.tipo == tipo).first())
    if not fila:
        raise HTTPException(404, "No hay informe publicado para ese período")
    return _servir(request, fila.archivo_key)


@router.get("/mi-unidad")
def mi_unidad(db: Session = Depends(get_db), s: dict = Depends(security.requiere("propietario"))):
    uf = int(s["sub"][3:])
    liq = (db.query(models.Liquidacion).filter_by(estado="publicada")
             .order_by(models.Liquidacion.periodo.desc()).first())
    if not liq:
        raise HTTPException(404, "Todavía no hay ningún informe publicado")
    fila = next((u for u in (liq.datos or {}).get("unidades", []) if u["uf"] == uf), None)
    return {"uf": uf, "periodo": liq.periodo, "estado_cuenta": fila,
            "informes": [f"/informes/{liq.periodo}/html", f"/informes/{liq.periodo}/xlsx"]}
```

- [ ] **Step 5: Incluir los routers en `api/app/main.py`**

```python
from .routers import auth, consorcio, documentos, hallazgos, liquidaciones
# ...
app.include_router(consorcio.router)
app.include_router(documentos.router)
```

- [ ] **Step 6: Verificar que pasa la suite entera (API y motor)**

```bash
cd api && .venv/bin/python -m pytest -q
# Expected: todos en verde
cd ../engine && .venv/bin/python -m pytest -q tests
# Expected: 27 passed, 2 skipped
```

- [ ] **Step 7: Commit**

```bash
git add api/app/routers/consorcio.py api/app/routers/documentos.py api/app/main.py api/tests/test_consorcio_api.py api/tests/test_documentos_api.py
git commit -m "API: configuración del consorcio, documentos con acceso por rol y vista del propietario" -m "Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

### Task 15: Dockerfile, arranque local y documentación

**Files:**
- Create: `api/Dockerfile`, `api/README.md`
- Modify: `docs/ESTADO.md`

- [ ] **Step 1: Escribir `api/Dockerfile`**

```dockerfile
FROM python:3.12-slim
RUN apt-get update && apt-get install -y --no-install-recommends poppler-utils \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /srv
COPY engine/ engine/
COPY api/ api/
RUN pip install --no-cache-dir ./engine ./api
WORKDIR /srv/api
EXPOSE 8080
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]
```

- [ ] **Step 2: Probar el arranque local sin Docker**

```bash
cd api
CT_STORAGE_DIR=/tmp/ct-storage CT_DATABASE_URL=sqlite:///./ct-dev.db \
  .venv/bin/uvicorn app.main:app --port 8080 &
sleep 2 && curl -s localhost:8080/salud   # Expected: {"ok":true}
kill %1 && rm -f ct-dev.db
```

- [ ] **Step 3: Probar la imagen Docker (si Docker está disponible; si no, saltear y queda para el Plan 3)**

```bash
cd .. && docker build -f api/Dockerfile -t ct-api . && \
  docker run --rm -e CT_STORAGE_DIR=/tmp -e CT_DATABASE_URL=sqlite:// -p 8080:8080 -d --name ct-api ct-api && \
  sleep 3 && curl -s localhost:8080/salud && docker rm -f ct-api
# Expected: {"ok":true}
```

- [ ] **Step 4: Escribir `api/README.md`**

```markdown
# API del panel (Consorcio Transparente)

FastAPI + Postgres. Importa el motor (`engine/`) como biblioteca; requiere `pdftotext` (poppler).

## Desarrollo
    python3 -m venv .venv && .venv/bin/pip install -e ../engine -e '.[dev]'
    .venv/bin/python -m pytest -q                # tests (SQLite en memoria, storage en tmp)
    cp .env.example .env                          # completar
    .venv/bin/python cli.py init "Rivadavia 2069" --direccion "Av. Rivadavia 2069, CABA"
    .venv/bin/python cli.py usuario lucas@example.com "Lucas" auditor
    .venv/bin/uvicorn app.main:app --reload --port 8080

## Flujo
1. `POST /liquidaciones` (PDF + período) → procesa en background: cuadre → reglas → gastos → hallazgos.
2. `POST /liquidaciones/{id}/comprobantes` (ZIP de `ct descargar`) → cruce → documentos + hallazgos.
3. Revisar `GET /hallazgos`, cambiar estados, marcar `publicado`.
4. `POST /liquidaciones/{id}/publicar` → informes HTML/Excel en storage; el propietario entra
   con su código (`POST /auth/login-unidad`) y ve `/mi-unidad` e `/informes/{periodo}/{tipo}`.

Regla de oro: si la liquidación no cuadra (`no_cuadra`), no hay publicación posible.
```

- [ ] **Step 5: Actualizar `docs/ESTADO.md`** — agregar al principio de "Qué existe y funciona":

```markdown
- **API del panel** (`api/`): FastAPI + SQLAlchemy sobre Postgres (SQLite en dev). Persiste liquidaciones,
  gastos, documentos y hallazgos con estados (pendiente/preguntado/respondido/descartado/cerrado) e historial;
  auth por roles (auditor/consejo/moderador) y por código de unidad; ingesta con cuadre obligatorio;
  publicación de informes HTML/Excel a storage (R2 o disco). Ver `api/README.md`.
  Spec: `docs/superpowers/specs/2026-09-04-panel-rivadavia-design.md`. Falta: front Next.js (Plan 2) y deploy (Plan 3).
```

Y en "Pendientes inmediatos", reemplazar el punto 1 por el estado real (API hecha; siguen Plan 2 web y Plan 3 deploy).

- [ ] **Step 6: Verificación final completa**

```bash
cd api && .venv/bin/python -m pytest -q && cd ../engine && .venv/bin/python -m pytest -q tests
# Expected: todo en verde (API completa + 27 passed, 2 skipped del motor)
```

- [ ] **Step 7: Commit**

```bash
git add api/Dockerfile api/README.md docs/ESTADO.md
git commit -m "API: Dockerfile, README y actualización del estado del proyecto" -m "Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```
