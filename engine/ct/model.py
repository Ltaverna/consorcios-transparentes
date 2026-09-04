"""Modelo de datos de una liquidación de expensas (independiente del sistema que la emitió)."""
from __future__ import annotations
from dataclasses import dataclass, field, asdict
from datetime import date
from typing import Optional


@dataclass
class Pago:
    fecha: Optional[date]
    importe: float
    caja: str = ""          # BANCO / CAJA
    forma: str = ""         # Transferencia / Débito automático / Efectivo


@dataclass
class Gasto:
    n: int
    categoria: str
    proveedor: str
    concepto: str
    columna: str            # clase de prorrateo: A, B, D ...
    importe: float
    pct_inc: Optional[float] = None
    factura_fecha: Optional[date] = None
    factura_nro: Optional[str] = None
    factura_importe: Optional[float] = None
    periodo: Optional[str] = None
    pagos: list[Pago] = field(default_factory=list)

    @property
    def fecha_pago(self) -> Optional[date]:
        fs = [p.fecha for p in self.pagos if p.fecha]
        return max(fs) if fs else None

    @property
    def en_efectivo(self) -> bool:
        return any(p.caja.upper() == "CAJA" or p.forma.lower().startswith("efectivo") for p in self.pagos)

    @property
    def dias_factura_pago(self) -> Optional[int]:
        if self.factura_fecha and self.fecha_pago:
            return (self.fecha_pago - self.factura_fecha).days
        return None


@dataclass
class Unidad:
    uf: int
    piso_depto: str
    propietario: str
    tipo: str
    saldo_ant: float
    pagos: float
    cred_deb: float
    deuda: float
    interes: float
    expensas: dict[str, float]      # clase -> importe del mes
    pcts: dict[str, float]          # clase -> porcentual (%)
    total_mes: float
    redondeo: float
    a_pagar: float
    gastos_part: float = 0.0


@dataclass
class Deudor:
    uf: int
    piso_depto: str
    propietario: str
    deuda: float


@dataclass
class Cuenta:
    nombre: str
    saldo_ant: float
    ingresos: float
    egresos: float
    saldo_cierre: float


@dataclass
class EstadoFinanciero:
    saldo_anterior: float = 0.0
    ing_termino: float = 0.0
    ing_adeudadas: float = 0.0
    ing_intereses: float = 0.0
    ing_adelantadas: float = 0.0
    otros_ingresos: float = 0.0
    egresos: float = 0.0
    saldo_cierre: float = 0.0


@dataclass
class Patrimonial:
    disponibilidades: float = 0.0
    a_cobrar: float = 0.0
    devengados_pend: float = 0.0
    facturas_pend: float = 0.0
    total: float = 0.0


@dataclass
class MesEvolucion:
    mes: str
    a_cobrar: float
    gastos: float
    cobrado: float


@dataclass
class Check:
    nombre: str
    ok: bool
    esperado: float
    obtenido: float
    detalle: str = ""

    @property
    def diff(self) -> float:
        return round(self.obtenido - self.esperado, 2)


@dataclass
class Liquidacion:
    sistema: str
    periodo: str                     # "Agosto 2026"
    consorcio: str = ""
    cuit_consorcio: str = ""
    administracion: str = ""
    cuit_administracion: str = ""
    venc1: Optional[date] = None
    venc2: Optional[date] = None
    gastos: list[Gasto] = field(default_factory=list)
    totales_categoria: dict[str, float] = field(default_factory=dict)
    totales_columna: dict[str, float] = field(default_factory=dict)
    total_gastos: Optional[float] = None
    deudores: list[Deudor] = field(default_factory=list)
    total_deudores: Optional[float] = None
    estado: EstadoFinanciero = field(default_factory=EstadoFinanciero)
    cuentas: list[Cuenta] = field(default_factory=list)
    patrimonial: Patrimonial = field(default_factory=Patrimonial)
    unidades: list[Unidad] = field(default_factory=list)
    prorrateo_total: dict[str, float] = field(default_factory=dict)   # clase -> total prorrateado
    evolucion: list[MesEvolucion] = field(default_factory=list)
    checks: list[Check] = field(default_factory=list)
    avisos: list[str] = field(default_factory=list)

    # ---- helpers
    @property
    def suma_gastos(self) -> float:
        return round(sum(g.importe for g in self.gastos), 2)

    def por_categoria(self) -> dict[str, float]:
        out: dict[str, float] = {}
        for g in self.gastos:
            out[g.categoria] = round(out.get(g.categoria, 0.0) + g.importe, 2)
        return out

    def por_proveedor(self) -> dict[str, float]:
        out: dict[str, float] = {}
        for g in self.gastos:
            out[g.proveedor] = round(out.get(g.proveedor, 0.0) + g.importe, 2)
        return dict(sorted(out.items(), key=lambda kv: -kv[1]))

    @property
    def cuadra(self) -> bool:
        return all(c.ok for c in self.checks)

    def to_dict(self) -> dict:
        d = asdict(self)
        # fechas a ISO
        def fix(o):
            if isinstance(o, dict):
                return {k: fix(v) for k, v in o.items()}
            if isinstance(o, list):
                return [fix(v) for v in o]
            if isinstance(o, date):
                return o.isoformat()
            return o
        return fix(d)
