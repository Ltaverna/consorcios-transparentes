"""Reglas de detección sobre una liquidación (y opcionalmente la anterior).

Cada regla devuelve cero o más Hallazgos. Los umbrales viven en Config para ajustarlos por consorcio.
Las reglas hablan de hechos documentados; la redacción evita conclusiones acusatorias.
"""
from __future__ import annotations
import re
from dataclasses import dataclass, field, fields, asdict
from datetime import date
from typing import Callable, Optional

from .model import Gasto, Liquidacion

SEV = ("CRÍTICO", "ALTO", "MEDIO", "BAJO")


@dataclass
class Config:
    caja_share_alto: float = 0.40          # % de disponibilidades en efectivo
    efectivo_mes_alto: float = 0.10        # % del gasto del mes pagado en efectivo
    efectivo_linea_alta: float = 300_000   # un pago en efectivo mayor a esto
    dias_factura_pago_max: int = 60
    dias_factura_futura: int = 1           # factura fechada después del pago
    unidades_share_alto: float = 0.20      # obras en unidades privadas / gasto del mes
    sobreprorrateo_min: float = 0.03       # prorrateado / gasto - 1
    meses_deuda_alto: float = 3.0
    concentracion_deuda: float = 0.30      # una unidad con más de X de la deuda total
    bancarios_share_alto: float = 0.012
    admin_variacion_alta: float = 0.05     # honorarios vs mes anterior
    factura_nro_bajo: int = 20             # proveedor con numeración de factura muy baja
    interes_dispersion: float = 0.05       # diferencia entre tasas de interés a deudores
    cobertura_pendientes_min: float = 1.0  # disponibilidades / facturas pendientes
    # --- referencias de mercado (0 = regla apagada; las carga el auditor por paritaria) ---
    sueldo_encargado_ref: float = 0.0      # neto mensual según escala SUTERH vigente
    sueldo_tolerancia: float = 0.10
    honorarios_ref: float = 0.0            # honorarios de administración de referencia (mensual)
    honorarios_tolerancia: float = 0.10
    abono_ascensores_ref: float = 0.0      # tope mensual por rubro de abono
    abono_matafuegos_ref: float = 0.0
    abono_limpieza_ref: float = 0.0
    # --- reglas históricas (serie de meses previos) ---
    salto_puntos_medio: float = 0.25       # exceso sobre la mediana de variaciones del mes
    salto_puntos_alto: float = 0.50
    salto_importe_min: float = 50_000      # gastos chicos no ameritan hallazgo
    concentracion_proveedor: float = 0.25  # share de un proveedor sobre el gasto sin sueldos

    @classmethod
    def desde_dict(cls, d: dict | None) -> "Config":
        conocidos = {f.name for f in fields(cls)}
        return cls(**{k: v for k, v in (d or {}).items() if k in conocidos})


@dataclass
class Hallazgo:
    regla: str
    severidad: str
    area: str
    titulo: str
    evidencia: str
    monto: float = 0.0
    recomendacion: str = ""
    refs: list[str] = field(default_factory=list)   # gastos (n) o unidades (uf) involucrados
    clave: str = ""     # slug estable para identidad entre reprocesos cuando el título trae cifras

    def to_dict(self) -> dict:
        return asdict(self)


Rule = Callable[[Liquidacion, Optional[Liquidacion], Config], list[Hallazgo]]
RULES: list[tuple[str, Rule]] = []


def rule(name: str):
    def deco(fn: Rule):
        RULES.append((name, fn))
        return fn
    return deco


def fmt(v: float) -> str:
    s = f"{abs(v):,.0f}".replace(",", ".")
    return ("-" if v < 0 else "") + "$" + s


def pct(v: float) -> str:
    return f"{v * 100:.1f} %".replace(".", ",")


# ------------------------------------------------------------------ cuadre
@rule("cuadre")
def r_cuadre(liq, prev, cfg):
    bad = [c for c in liq.checks if not c.ok]
    if not bad:
        return []
    ev = "; ".join(f"{c.nombre}: esperado {fmt(c.esperado)}, obtenido {fmt(c.obtenido)}" for c in bad[:6])
    return [Hallazgo("cuadre", "CRÍTICO", "Integridad de la liquidación", f"La liquidación no cuadra en {len(bad)} verificación(es)", ev,
                     sum(abs(c.diff) for c in bad), "Pedir a la administración la liquidación corregida antes de analizar nada más.",
                     clave="cuadre-general")]


# ------------------------------------------------------------------ efectivo
@rule("efectivo")
def r_efectivo(liq, prev, cfg):
    out = []
    caja = next((c for c in liq.cuentas if "CAJA" in c.nombre.upper()), None)
    disp = liq.estado.saldo_cierre
    if caja and disp > 0 and caja.saldo_cierre / disp > cfg.caja_share_alto:
        out.append(Hallazgo("efectivo", "CRÍTICO", "Control interno / caja",
                            f"El {pct(caja.saldo_cierre / disp)} de las disponibilidades está en efectivo",
                            f"Caja cierra con {fmt(caja.saldo_cierre)} sobre disponibilidades de {fmt(disp)}. Ingresos en efectivo del mes: {fmt(caja.ingresos)}. "
                            "La Ley 941 (CABA) exige depositar los fondos en cuenta bancaria del consorcio.",
                            caja.saldo_cierre, "Exigir depósito del efectivo y conciliación de caja contra comprobantes de cobro.",
                            clave="caja-share"))
    ef = [g for g in liq.gastos if g.en_efectivo]
    tot_ef = sum(g.importe for g in ef)
    if liq.suma_gastos and tot_ef / liq.suma_gastos > cfg.efectivo_mes_alto:
        top = sorted(ef, key=lambda g: -g.importe)[:4]
        out.append(Hallazgo("efectivo", "ALTO", "Control interno / caja",
                            f"El {pct(tot_ef / liq.suma_gastos)} del gasto del mes se pagó en efectivo",
                            "Pagos en efectivo: " + "; ".join(f"{g.proveedor} {fmt(g.importe)}" for g in top),
                            tot_ef, "Prohibir pagos en efectivo por encima de un mínimo y exigir recibo oficial del proveedor.", [str(g.n) for g in ef],
                            clave="efectivo-mes"))
    for g in ef:
        if g.importe >= cfg.efectivo_linea_alta and not (liq.suma_gastos and tot_ef / liq.suma_gastos > cfg.efectivo_mes_alto):
            out.append(Hallazgo("efectivo", "ALTO", "Control interno / caja", f"Pago en efectivo de {fmt(g.importe)} a {g.proveedor}",
                                g.concepto[:160], g.importe, "Pedir el recibo oficial del proveedor.", [str(g.n)],
                                clave="efectivo-linea"))
    return out


# ------------------------------------------------------------------ liquidez
@rule("liquidez")
def r_liquidez(liq, prev, cfg):
    out = []
    disp = liq.estado.saldo_cierre
    pend = abs(liq.patrimonial.facturas_pend)
    if pend and disp < pend * cfg.cobertura_pendientes_min:
        out.append(Hallazgo("liquidez", "CRÍTICO" if disp < pend * 0.5 else "ALTO", "Liquidez",
                            "Las disponibilidades no cubren las facturas pendientes",
                            f"Disponibilidades {fmt(disp)} vs. facturas pendientes {fmt(pend)}: déficit de {fmt(pend - disp)}.",
                            disp - pend, "Proyectar el flujo de caja del mes siguiente y definir si hace falta una expensa extraordinaria explícita.",
                            clave="cobertura"))
    if prev and prev.estado.saldo_cierre > 0 and liq.estado.saldo_anterior > 0:
        pass
    if liq.estado.saldo_anterior > 0 and disp < liq.estado.saldo_anterior * 0.25:
        out.append(Hallazgo("liquidez", "ALTO", "Liquidez", f"Las disponibilidades cayeron {pct(1 - disp / liq.estado.saldo_anterior)} en el mes",
                            f"De {fmt(liq.estado.saldo_anterior)} a {fmt(disp)}. Gastos del mes {fmt(liq.estado.egresos)}, cobrado {fmt(liq.estado.ing_termino + liq.estado.ing_adeudadas + liq.estado.ing_intereses + liq.estado.ing_adelantadas)}.",
                            disp - liq.estado.saldo_anterior, "Pedir explicación del consumo de reservas.",
                            clave="caida-disponibilidades"))
    return out


# ------------------------------------------------------------------ obras en unidades privadas
@rule("obras_unidades")
def r_obras(liq, prev, cfg):
    en_unidades = [g for g in liq.gastos if "UNIDADES" in g.categoria.upper() or re.search(r"\b(depto|dpto|departamento|piso \d+|UF \d+)\b", g.concepto, re.I) and re.search(r"serpentina|porcelanato|pintura|piso|baño|cañer", g.concepto, re.I)]
    tot = sum(g.importe for g in en_unidades)
    if liq.suma_gastos and tot / liq.suma_gastos > cfg.unidades_share_alto:
        top = sorted(en_unidades, key=lambda g: -g.importe)[:5]
        return [Hallazgo("obras_unidades", "CRÍTICO", "Obras / contratación",
                         f"El {pct(tot / liq.suma_gastos)} del gasto del mes son trabajos dentro de unidades privadas, liquidados como expensas ordinarias",
                         "; ".join(f"{g.proveedor}: {g.concepto[:90]} ({fmt(g.importe)})" for g in top),
                         tot, "Pedir acta de asamblea que aprueba las obras, presupuestos comparativos, informe técnico que justifique la responsabilidad del consorcio y denuncia al seguro.",
                         [str(g.n) for g in en_unidades], clave="obras-unidades")]
    return []


# ------------------------------------------------------------------ fechas factura / pago
@rule("fechas")
def r_fechas(liq, prev, cfg):
    out = []
    tarde = [g for g in liq.gastos if g.dias_factura_pago is not None and g.dias_factura_pago > cfg.dias_factura_pago_max]
    if tarde:
        out.append(Hallazgo("fechas", "MEDIO", "Pagos atrasados / duplicación",
                            f"{len(tarde)} factura(s) pagadas con más de {cfg.dias_factura_pago_max} días de atraso",
                            "; ".join(f"{g.proveedor} factura {g.factura_nro} del {g.factura_fecha:%d-%m-%Y} pagada el {g.fecha_pago:%d-%m-%Y} ({g.dias_factura_pago} días)" for g in tarde[:6]),
                            sum(g.importe for g in tarde), "Verificar que no se hayan liquidado en meses anteriores (riesgo de doble pago).", [str(g.n) for g in tarde],
                            clave="pago-tardio"))
    antes = [g for g in liq.gastos if g.dias_factura_pago is not None and g.dias_factura_pago < -cfg.dias_factura_futura]
    for g in antes:
        sev = "ALTO" if -g.dias_factura_pago > 7 or g.importe >= 1_000_000 else "MEDIO"
        out.append(Hallazgo("fechas", sev, "Obras / contratación", f"Factura de {g.proveedor} emitida {-g.dias_factura_pago} días después del pago",
                            f"Factura {g.factura_nro} fechada {g.factura_fecha:%d-%m-%Y}; pago del {g.fecha_pago:%d-%m-%Y} por {fmt(g.importe)}.",
                            g.importe, "Exigir factura antes del pago.", [str(g.n)],
                            clave="factura-posterior"))
    # cargas sociales pagadas tarde: F.931 del período N pagado después del mes N+1
    for g in liq.gastos:
        if re.search(r"931", g.concepto) and g.periodo and g.fecha_pago:
            m = re.search(r"([A-Za-z]+)\s*,?\s*(\d{4})", g.periodo)
            if m:
                meses = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"]
                try:
                    mi = meses.index(m.group(1).lower()); y = int(m.group(2))
                    due_month = (mi + 2) % 12 + 1; due_year = y + (1 if mi + 2 >= 12 else 0)
                    if (g.fecha_pago.year, g.fecha_pago.month) >= (due_year, due_month):
                        out.append(Hallazgo("fechas", "MEDIO", "Pagos atrasados / duplicación", f"Cargas sociales (F.931) de {g.periodo} pagadas el {g.fecha_pago:%d-%m-%Y}, fuera de término",
                                            "El F.931 vence el mes siguiente al período; el pago tardío genera intereses resarcitorios.", g.importe, "Pedir el comprobante y verificar si se pagaron intereses.", [str(g.n)],
                                            clave="f931"))
                except ValueError:
                    pass
    return out


# ------------------------------------------------------------------ proveedores nuevos
@rule("proveedor_nuevo")
def r_prov_nuevo(liq, prev, cfg):
    out = []
    for g in liq.gastos:
        if not g.factura_nro:
            continue
        m = re.match(r"^(\d{4,5})-(\d{8})$", g.factura_nro.strip())
        if m and int(m.group(2)) <= cfg.factura_nro_bajo and g.importe >= 200_000:
            out.append(Hallazgo("proveedor_nuevo", "ALTO", "Obras / contratación",
                                f"{g.proveedor} factura con numeración N° {int(m.group(2))}: proveedor casi sin actividad previa, por {fmt(g.importe)}",
                                g.concepto[:160], g.importe, "Verificar inscripción en ARCA, antecedentes y presupuestos comparativos.", [str(g.n)],
                                clave="numeracion-baja"))
    return out


# ------------------------------------------------------------------ prorrateo
@rule("prorrateo")
def r_prorrateo(liq, prev, cfg):
    out = []
    tot_pr = liq.prorrateo_total.get("_total_mes") or sum(v for k, v in liq.prorrateo_total.items() if not k.startswith("_"))
    if tot_pr and liq.suma_gastos and tot_pr / liq.suma_gastos - 1 > cfg.sobreprorrateo_min:
        por_clase = {k: v for k, v in liq.prorrateo_total.items() if not k.startswith("_")}
        diffs = {k: round(v - sum(g.importe for g in liq.gastos if g.columna == k), 2) for k, v in por_clase.items()}
        out.append(Hallazgo("prorrateo", "ALTO", "Prorrateo", f"Se prorratea {fmt(tot_pr - liq.suma_gastos)} más que el gasto del mes sin concepto informado",
                            f"Importe a cobrar {fmt(tot_pr)} vs. gastos {fmt(liq.suma_gastos)}. Diferencia por clase: " + ", ".join(f"{k} {fmt(v)}" for k, v in diffs.items()),
                            tot_pr - liq.suma_gastos, "Exigir que el excedente se identifique como fondo de reserva o expensa extraordinaria con saldo informado.",
                            clave="sobre-prorrateo"))
    if prev:
        # misma obra (mismo proveedor, concepto parecido) en distinta clase
        for g in liq.gastos:
            for h in prev.gastos:
                if g.proveedor == h.proveedor and g.columna != h.columna and g.importe > 500_000 and h.importe > 500_000:
                    out.append(Hallazgo("prorrateo", "ALTO", "Prorrateo", f"{g.proveedor}: prorrateado en clase {g.columna} este mes y en clase {h.columna} el anterior",
                                        f"Este mes {fmt(g.importe)} ({g.concepto[:80]}); mes anterior {fmt(h.importe)} ({h.concepto[:80]}). Cambia quién paga (por ejemplo, cocheras exentas o no).",
                                        g.importe, "Exigir criterio de prorrateo estable por obra.", [str(g.n)],
                                        clave="cambio-clase"))
                    break
    return out


# ------------------------------------------------------------------ morosidad
@rule("morosidad")
def r_morosidad(liq, prev, cfg):
    out = []
    if not liq.unidades:
        return out
    deudores = [u for u in liq.unidades if u.deuda > 0]
    tot = sum(u.deuda for u in deudores)
    if not tot:
        return out
    top = max(deudores, key=lambda u: u.deuda)
    meses = top.deuda / top.total_mes if top.total_mes else 0
    if top.deuda / tot > cfg.concentracion_deuda or meses > cfg.meses_deuda_alto:
        sin_pago = [u for u in deudores if u.pagos == 0]
        out.append(Hallazgo("morosidad", "ALTO", "Morosidad",
                            f"Deuda concentrada: {top.piso_depto} ({top.propietario}) debe {fmt(top.deuda)}, {meses:.1f} meses de expensa, {pct(top.deuda / tot)} de la deuda total".replace(".", ",", 1) if False else
                            f"Deuda concentrada: {top.piso_depto} ({top.propietario}) debe {fmt(top.deuda)}, equivalente a {meses:.1f} meses de expensa y al {pct(top.deuda / tot)} de la deuda total",
                            f"{len(deudores)} unidades deudoras por {fmt(tot)}; {len(sin_pago)} no pagaron nada en el mes: " + ", ".join(u.piso_depto for u in sin_pago[:8]),
                            tot, "Pedir estado de intimaciones y juicios por unidad; iniciar acciones sobre los mayores deudores.", [str(u.uf) for u in deudores],
                            clave="concentracion"))
    # tasas de interés
    tasas = [(u, u.interes / u.deuda) for u in deudores if u.interes > 0 and u.deuda > 0]
    if len(tasas) >= 3:
        vals = [t for _, t in tasas]
        if max(vals) - min(vals) > cfg.interes_dispersion:
            out.append(Hallazgo("morosidad", "MEDIO", "Morosidad", "Criterio de intereses a deudores no uniforme",
                                "Interés del mes sobre la deuda: " + ", ".join(f"{u.piso_depto} {pct(t)}" for u, t in sorted(tasas, key=lambda x: -x[1])[:8]),
                                sum(u.interes for u, _ in tasas), "Solicitar la fórmula de cálculo de intereses y su respaldo en el reglamento.",
                                clave="dispersion-interes"))
    return out


# ------------------------------------------------------------------ costos fijos
@rule("costos")
def r_costos(liq, prev, cfg):
    out = []
    banc = sum(g.importe for g in liq.gastos if "BANCARIO" in g.categoria.upper())
    if liq.suma_gastos and banc / liq.suma_gastos > cfg.bancarios_share_alto:
        out.append(Hallazgo("costos", "MEDIO", "Costos", f"Gastos bancarios de {fmt(banc)} ({pct(banc / liq.suma_gastos)} del gasto del mes)",
                            "Impuesto a débitos y créditos estimado (0,6 % de los movimientos) más comisiones; no se informa el detalle.", banc, "Pedir el resumen bancario y renegociar comisiones.",
                            clave="bancarios"))
    if prev:
        cur = liq.por_proveedor(); ant = prev.por_proveedor()
        subas = []
        for p, v in cur.items():
            if p in ant and ant[p] > 0 and v / ant[p] - 1 > cfg.admin_variacion_alta and "ADMINISTRACION" in " ".join(g.categoria for g in liq.gastos if g.proveedor == p).upper():
                subas.append((p, ant[p], v))
        for p, a, v in subas:
            out.append(Hallazgo("costos", "MEDIO", "Costos", f"Honorarios de administración suben {pct(v / a - 1)} respecto del mes anterior",
                                f"{p}: {fmt(a)} → {fmt(v)}.", v - a, "Pedir la base del aumento (índice o acuerdo de asamblea).",
                                clave=f"honorarios-admin:{p}"))
    return out


# ------------------------------------------------------------------ clasificación
@rule("clasificacion")
def r_clasificacion(liq, prev, cfg):
    out = []
    for g in liq.gastos:
        if "SUELDOS" in g.categoria.upper() and re.search(r"retenci[oó]n sobre factura|SIRE", g.concepto, re.I):
            out.append(Hallazgo("clasificacion", "MEDIO", "Clasificación", f"Retención sobre factura de un proveedor ({fmt(g.importe)}) incluida en 'Sueldos y cargas sociales'",
                                g.concepto[:160], g.importe, "Reclasificar: corresponde al servicio del proveedor retenido.", [str(g.n)],
                                clave="retencion-sobre-factura"))
    cats = [c for c in liq.totales_categoria]
    dup = {c for c in cats if cats.count(c) > 1}
    if len(set(g.categoria for g in liq.gastos)) < len(liq.totales_categoria):
        out.append(Hallazgo("clasificacion", "BAJO", "Clasificación", "Un mismo rubro aparece dos veces en la liquidación", ", ".join(sorted(dup)) or "rubros repetidos", 0, "Unificar rubros.",
                            clave="rubro-repetido"))
    return out


# ------------------------------------------------------------------ legales
@rule("legales")
def r_legales(liq, prev, cfg):
    leg = [g for g in liq.gastos if re.search(r"honorarios.*(carta documento|mediaci|patrocinio|abogad|juicio|denuncia)|carta documento|mediaci[oó]n", g.concepto, re.I)]
    if not leg:
        return []
    return [Hallazgo("legales", "ALTO", "Contingencias legales", f"Gastos legales por {fmt(sum(g.importe for g in leg))} sin explicación del reclamo",
                     "; ".join(f"{g.proveedor}: {g.concepto[:110]} ({fmt(g.importe)})" for g in leg), sum(g.importe for g in leg),
                     "Pedir informe del asesor legal: partes, objeto, estado y contingencia estimada.", [str(g.n) for g in leg])]


# ------------------------------------------------------------------ referencias de mercado
# Rubros de abono: (nombre, regex sobre concepto + proveedor, campo del tope en Config).
ABONOS = [("ascensores", r"ascensor", "abono_ascensores_ref"),
          ("matafuegos", r"matafuego|extinguidor", "abono_matafuegos_ref"),
          ("limpieza", r"limpieza", "abono_limpieza_ref")]


@rule("sueldo_mercado")
def r_sueldo_mercado(liq, prev, cfg):
    if not cfg.sueldo_encargado_ref:
        return []
    # Calibrado sobre Redconar: el neto sale como "Sueldo <nombre> ..." o "SUELDO Y SAC ...";
    # así quedan afuera F.931, FATERYH/SERACARH/SUTERH y las retenciones sobre factura del rubro.
    netos = [g for g in liq.gastos if "SUELDO" in g.categoria.upper() and re.match(r"\s*sueldo\b", g.concepto, re.I)]
    if not netos:
        return []
    total = sum(g.importe for g in netos)
    desvio = total / cfg.sueldo_encargado_ref - 1
    if abs(desvio) <= cfg.sueldo_tolerancia:
        return []
    refs = [str(g.n) for g in netos]
    sac = any(re.search(r"\bSAC\b|aguinaldo", g.concepto, re.I) for g in netos)
    ev = (f"Sueldos netos del mes: {fmt(total)}; referencia de escala cargada por el auditor: "
          f"{fmt(cfg.sueldo_encargado_ref)} (desvío {pct(desvio)})."
          + (" Incluye SAC/aguinaldo: el desvío de junio y diciembre es estructural." if sac else ""))
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


@rule("honorarios_mercado")
def r_honorarios_mercado(liq, prev, cfg):
    if not cfg.honorarios_ref:
        return []
    adm = [g for g in liq.gastos if "ADMINISTRACION" in g.categoria.upper()]
    total = sum(g.importe for g in adm)
    if not adm or total <= cfg.honorarios_ref * (1 + cfg.honorarios_tolerancia):
        return []
    desvio = total / cfg.honorarios_ref - 1
    sev = "ALTO" if total > cfg.honorarios_ref * (1 + 2 * cfg.honorarios_tolerancia) else "MEDIO"
    ev = (f"Gastos de administración del mes: {fmt(total)}; referencia cargada por el auditor: "
          f"{fmt(cfg.honorarios_ref)} (desvío {pct(desvio)}).")
    return [Hallazgo("honorarios_mercado", sev, "Mercado", f"Honorarios de administración {pct(desvio)} sobre la referencia",
                     ev, total - cfg.honorarios_ref,
                     "Pedir la base del honorario: contrato con la administración o acta de asamblea que lo aprueba.",
                     [str(g.n) for g in adm], clave="honorarios-sobre-referencia")]


@rule("abonos_mercado")
def r_abonos_mercado(liq, prev, cfg):
    out = []
    for rubro, patron, campo in ABONOS:
        ref = getattr(cfg, campo)
        if not ref:
            continue
        # Se excluye la categoría de seguros: la póliza integral describe ascensores,
        # matafuegos y limpieza en su cobertura y no es un abono del rubro.
        gs = [g for g in liq.gastos
              if "SEGURO" not in g.categoria.upper() and re.search(patron, g.concepto + " " + g.proveedor, re.I)]
        total = sum(g.importe for g in gs)
        if not gs or total <= ref:
            continue
        ev = (f"Total del rubro {rubro}: {fmt(total)} contra un tope de referencia cargado por el auditor de {fmt(ref)} (desvío {pct(total/ref - 1)}). "
              + "; ".join(f"{g.proveedor}: {g.concepto[:70]} ({fmt(g.importe)})" for g in gs[:4]))
        out.append(Hallazgo("abonos_mercado", "MEDIO", "Mercado", f"Abono de {rubro} por {fmt(total)} sobre el tope de referencia",
                            ev, total - ref,
                            "Pedir presupuestos comparativos del rubro y la última renegociación del abono.",
                            [str(g.n) for g in gs], clave=f"abono-caro:{rubro}"))
    return out


# ------------------------------------------------------------------ API
def evaluar(liq: Liquidacion, prev: Optional[Liquidacion] = None, cfg: Optional[Config] = None) -> list[Hallazgo]:
    cfg = cfg or Config()
    out: list[Hallazgo] = []
    for name, fn in RULES:
        try:
            out.extend(fn(liq, prev, cfg))
        except Exception as e:  # una regla rota no debe tirar el análisis
            out.append(Hallazgo(name, "BAJO", "Motor", f"La regla '{name}' falló: {e}", "", 0, "Revisar la regla.",
                                clave=f"motor-error-{name}"))
    order = {s: i for i, s in enumerate(SEV)}
    out.sort(key=lambda h: (order.get(h.severidad, 9), -abs(h.monto)))
    return out
