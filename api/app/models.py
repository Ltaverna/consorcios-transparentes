"""Tablas del panel. Un solo consorcio (Rivadavia 2069); multi-consorcio = migración futura."""
from datetime import date, datetime, timezone

from sqlalchemy import (JSON, Boolean, Date, DateTime, Float, ForeignKey, Integer,
                        String, Text, UniqueConstraint)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.mutable import MutableDict, MutableList
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import TypeDecorator

from .db import Base

JSONDict = MutableDict.as_mutable(JSON().with_variant(JSONB(), "postgresql"))
JSONList = MutableList.as_mutable(JSON().with_variant(JSONB(), "postgresql"))


class FechaUTC(TypeDecorator):
    """Guarda en UTC y devuelve siempre datetime con tz (SQLite la pierde)."""
    impl = DateTime(timezone=True)
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is not None and value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return value

    def process_result_value(self, value, dialect):
        if value is not None and value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return value


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
    umbrales: Mapped[dict] = mapped_column(JSONDict, default=dict)


class Unidad(Base):
    __tablename__ = "unidades"
    id: Mapped[int] = mapped_column(primary_key=True)
    uf: Mapped[int] = mapped_column(Integer, unique=True)
    piso_depto: Mapped[str] = mapped_column(String(40), default="")
    tipo: Mapped[str] = mapped_column(String(40), default="")
    propietario: Mapped[str] = mapped_column(String(200), default="")
    porcentuales: Mapped[dict] = mapped_column(JSONDict, default=dict)
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
    archivo_key: Mapped[str] = mapped_column(String(500))
    datos: Mapped[dict | None] = mapped_column(JSONDict, default=None)  # Liquidacion.to_dict() completo
    cuadra: Mapped[bool] = mapped_column(Boolean, default=False)
    error: Mapped[str] = mapped_column(Text, default="")
    creado: Mapped[datetime] = mapped_column(FechaUTC(), default=ahora)
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
    pagos: Mapped[list] = mapped_column(JSONList, default=list)
    liquidacion: Mapped[Liquidacion] = relationship(back_populates="gastos")


class Documento(Base):
    __tablename__ = "documentos"
    id: Mapped[int] = mapped_column(primary_key=True)
    liquidacion_id: Mapped[int] = mapped_column(ForeignKey("liquidaciones.id", ondelete="CASCADE"))
    gasto_n: Mapped[int | None] = mapped_column(Integer, default=None)
    tipo: Mapped[str] = mapped_column(String(20), default="otro")  # factura | pago | recibo | imagen | otro
    archivo_key: Mapped[str] = mapped_column(String(500))
    hash: Mapped[str] = mapped_column(String(64), default="")
    metadatos: Mapped[dict] = mapped_column(JSONDict, default=dict)  # Documento.to_dict() del motor


class Hallazgo(Base):
    __tablename__ = "hallazgos"
    __table_args__ = (UniqueConstraint("liquidacion_id", "origen", "clave"),)
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
    refs: Mapped[list] = mapped_column(JSONList, default=list)
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
    ts: Mapped[datetime] = mapped_column(FechaUTC(), default=ahora)


class Informe(Base):
    __tablename__ = "informes"
    __table_args__ = (UniqueConstraint("liquidacion_id", "tipo"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    liquidacion_id: Mapped[int] = mapped_column(ForeignKey("liquidaciones.id", ondelete="CASCADE"))
    tipo: Mapped[str] = mapped_column(String(10))  # html | xlsx
    archivo_key: Mapped[str] = mapped_column(String(500))
    marca: Mapped[str] = mapped_column(String(120), default="")
    publicado_en: Mapped[datetime] = mapped_column(FechaUTC(), default=ahora)
