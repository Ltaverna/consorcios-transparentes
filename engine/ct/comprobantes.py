"""Cruce de comprobantes: factura ↔ pago ↔ línea de la liquidación.

Entrada: un manifiesto con, por cada gasto, la lista de adjuntos (archivos PDF) y la liquidación parseada.
Cada adjunto se lee (pdftotext) y se clasifica: factura, comprobante de pago (transferencia), recibo/otro, o imagen sin texto.
Salida: documentos interpretados + hallazgos (pagos a terceros, facturas a nombre de otro, duplicados, faltantes, importes que no coinciden).
"""
from __future__ import annotations
import hashlib
import json
import os
import re
import subprocess
from dataclasses import dataclass, field, asdict
from datetime import date
from typing import Optional

from .model import Gasto, Liquidacion
from .rules import Hallazgo, fmt

RE_CUIT = re.compile(r"\b(\d{2})[- ]?(\d{8})[- ]?(\d)\b")
RE_FECHA = re.compile(r"\b(\d{2})/(\d{2})/(\d{4})\b")
RE_MONEY = re.compile(r"\$\s?(-?\d{1,3}(?:\.\d{3})*(?:,\d{2})|-?\d+,\d{2})")


def _num_ar(s: str) -> float:
    return float(s.replace(".", "").replace(",", "."))


def _cuit(m) -> str:
    return "".join(m.groups())


def cuit_valido(c: str) -> bool:
    """Dígito verificador (módulo 11) y sin secuencias de relleno."""
    if not re.fullmatch(r"\d{11}", c) or c[2:10] in ("00000000", "99999999"):
        return False
    pesos = [5, 4, 3, 2, 7, 6, 5, 4, 3, 2]
    r = 11 - sum(int(d) * w for d, w in zip(c[:10], pesos)) % 11
    dv = {11: 0, 10: 9}.get(r, r)
    return dv == int(c[10])


@dataclass
class Documento:
    archivo: str
    gasto_n: Optional[int]
    tipo: str = "otro"                  # factura | pago | recibo | imagen | otro
    texto_len: int = 0
    hash: str = ""
    # factura
    emisor: Optional[str] = None
    emisor_cuit: Optional[str] = None
    receptor: Optional[str] = None
    receptor_cuit: Optional[str] = None
    receptor_condicion: Optional[str] = None
    factura_tipo: Optional[str] = None
    factura_nro: Optional[str] = None
    fecha: Optional[date] = None
    importe: Optional[float] = None
    # pago
    destinatario: Optional[str] = None
    destinatario_cuit: Optional[str] = None
    pagador_cuit: Optional[str] = None
    operacion: Optional[str] = None
    motivo: Optional[str] = None
    notas: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        d = asdict(self)
        if self.fecha:
            d["fecha"] = self.fecha.isoformat()
        return d


def leer_texto(path: str) -> str:
    try:
        return subprocess.run(["pdftotext", "-layout", path, "-"], capture_output=True, text=True, timeout=60).stdout
    except Exception:
        return ""


def _fecha(s: str) -> Optional[date]:
    m = RE_FECHA.search(s)
    if not m:
        return None
    d, mo, y = map(int, m.groups())
    try:
        return date(y, mo, d)
    except ValueError:
        return None


def _tokens(nombre: str) -> set[str]:
    return {w[:5] for w in re.findall(r"[a-záéíóúñ]{4,}", nombre.lower())}


def nombre_vinculado(texto: str, nombres: dict[str, str]) -> Optional[tuple[str, str]]:
    """Devuelve (nombre, rol) si el texto contiene al menos dos tokens (prefijo de 5 letras) de un nombre de empleado o propietario."""
    low = texto.lower()
    words = {w[:5] for w in re.findall(r"[a-záéíóúñ]{4,}", low)}
    for nombre, rol in nombres.items():
        toks = _tokens(nombre)
        if len(toks) >= 2 and len(toks & words) >= 2:
            return nombre, rol
    return None


def interpretar(path: str, gasto_n: Optional[int], cuit_consorcio: str) -> Documento:
    doc = Documento(archivo=os.path.basename(path), gasto_n=gasto_n)
    try:
        doc.hash = hashlib.sha1(open(path, "rb").read()).hexdigest()[:12]
    except OSError:
        pass
    t = leer_texto(path)
    doc.texto_len = len(t.strip())
    if doc.texto_len < 40:
        doc.tipo = "imagen"
        doc.notas.append("Sin texto: es una imagen o un recibo manuscrito; requiere revisión visual.")
        return doc
    flat = re.sub(r"[ \t]+", " ", t)
    cons = cuit_consorcio.replace("-", "")
    # ---- comprobantes de pago (Office Banking / Galicia / MercadoPago)
    if re.search(r"Datos del destinatario|Detalle de movimiento|Detalle de la operaci[oó]n|Identificador de la operaci[oó]n|Trf Inmed|N[uú]mero de comprobante\s*\n\s*\d{6,}", flat, re.I) and not re.search(r"\bCAE\b|Comp\.? ?Nro", flat):
        doc.tipo = "pago"
        m = re.search(r"Datos del destinatario[\s\S]{0,300}?(\d{11})\s+([^\n]{3,60})", flat)
        if m:
            doc.destinatario_cuit, doc.destinatario = m.group(1), m.group(2).strip()
        else:
            m = re.search(r"Datos del destinatario\s*\n\s*(?:Nombre|Raz[oó]n Social)\s+(?:CUIL|CUIT)\s*\n\s*(.+?)\s{2,}(\d{11})", flat)
            if m:
                doc.destinatario, doc.destinatario_cuit = m.group(1).strip(), m.group(2)
            else:
                m = re.search(r"Leyendas adicionales\s*\n\s*(.+?)\s*\n\s*(\d{11})", flat)
                if m:
                    doc.destinatario, doc.destinatario_cuit = m.group(1).strip(), m.group(2)
        mp = re.search(r"Datos del pagador[\s\S]{0,200}?(\d{11})", flat)
        doc.pagador_cuit = mp.group(1) if mp else (cons if cons in flat.replace("-", "") else None)
        mo = re.search(r"(?:Identificador de la operaci[oó]n|N[uú]mero de operaci[oó]n|Número de comprobante)\s*:?\s*\n?\s*([A-Za-z0-9]{6,})", flat)
        doc.operacion = mo.group(1) if mo else None
        mm = re.search(r"Motivo\s+Tipo de transferencia\s*\n\s*(.+?)\s{2,}(.+)", flat)
        doc.motivo = (mm.group(1).strip() + " / " + mm.group(2).strip()) if mm else None
        doc.fecha = _fecha(flat)
        am = RE_MONEY.findall(flat)
        doc.importe = max((_num_ar(a) for a in am), default=None)
        if re.search(r"Cr[eé]dito", flat) and not re.search(r"D[eé]bito", flat):
            doc.notas.append("Es un CRÉDITO (dinero que entra al consorcio), no un pago.")
        return doc
    # ---- facturas
    if re.search(r"FACTURA|Factura|Comp\. ?Nro|CAE", flat):
        doc.tipo = "factura"
        # CUITs: con guiones, o sin guiones pero precedidos por la palabra CUIT/CUIL (evita CBU, números de cliente, etc.)
        cuits = []
        for m in RE_CUIT.finditer(flat):
            raw = m.group(0)
            ctx = flat[max(0, m.start() - 14): m.start()]
            if ("-" in raw or re.search(r"CUI[TL]", ctx, re.I)) and cuit_valido(_cuit(m)):
                cuits.append(_cuit(m))
        mt = re.search(r"\b([ABCM])\s*\n?\s*(?:FACTURA|Factura)|FACTURA\s*\n?\s*([ABC])\b|COD\.\s*0?(\d{2,3})", flat)
        cod = mt.group(3) if mt and mt.group(3) else None
        doc.factura_tipo = (mt.group(1) or mt.group(2)) if mt and (mt.group(1) or mt.group(2)) else {"001": "A", "006": "B", "011": "C"}.get(cod or "", None)
        mn = re.search(r"(?:Comp\.?\s*Nro:?|N[°º]:?|Nro\.?:?)\s*(\d{4,5}-\d{6,8})", flat)
        doc.factura_nro = mn.group(1) if mn else None
        me = re.search(r"Raz[oó]n Social:\s*(.+?)\s{2,}", flat)
        # emisor: primer CUIT; receptor: CUIT del consorcio si aparece, o segundo CUIT
        doc.emisor_cuit = cuits[0] if cuits else None
        rest = [c for c in cuits[1:]]
        if cons and cons in cuits:
            doc.receptor_cuit = cons
            if doc.emisor_cuit == cons:
                doc.emisor_cuit = rest[0] if rest else None   # solo aparece el CUIT del consorcio: emisor desconocido
        elif rest:
            doc.receptor_cuit = rest[0]
        # nombres
        mr = re.search(r"(?:Apellido y Nombre / Raz[oó]n Social|Cliente):\s*(.+?)\s{2,}", flat) or re.search(r"\n\s*Raz[oó]n social:\s*(.+?)\s*\n", flat, re.I)
        doc.receptor = mr.group(1).strip() if mr else None
        if doc.receptor and (len(doc.receptor) > 60 or "$" in doc.receptor or re.search(r"\d{4}", doc.receptor)):
            doc.receptor = None
        if me and (doc.receptor is None or me.group(1).strip() != doc.receptor):
            doc.emisor = me.group(1).strip()
        if doc.receptor is None and doc.receptor_cuit == cons:
            doc.receptor = "CONSORCIO"
        mc = re.search(r"Condici[oó]n (?:frente al )?(?:de )?IVA:\s*([A-Za-z ]+)", flat)
        # la condición del receptor suele ser la segunda aparición
        mcs = re.findall(r"Condici[oó]n (?:frente al )?(?:de )?IVA:\s*([A-Za-z ]+?)\s{2,}", flat)
        doc.receptor_condicion = (mcs[1] if len(mcs) > 1 else (mcs[0] if mcs else None))
        fe = re.search(r"Fecha(?: de Emisi[oó]n)?:\s*(\d{2}/\d{2}/\d{4})", flat)
        doc.fecha = _fecha(fe.group(1)) if fe else _fecha(flat)
        mi = re.search(r"Importe Total:?\s*\$?\s*([\d\.]+,\d{2})", flat) or re.search(r"TOTAL[^\n]*?([\d\.]+,\d{2})\s*$", flat, re.M)
        doc.importe = _num_ar(mi.group(1)) if mi else None
        if re.search(r"consumidor final", flat, re.I) and doc.receptor_cuit != cons:
            doc.notas.append("Factura a consumidor final que no es el consorcio.")
        if re.search(r"INACTIVA EN LOS PADRONES", flat, re.I):
            doc.notas.append("Leyenda de ARCA: CUIT del receptor inactiva o no inscripta en la condición seleccionada.")
        doc.notas.append("__texto__:" + flat[:3000])
        return doc
    # ---- recibos u otros con texto
    if re.search(r"RECIB[IÍ]|Recibo", flat, re.I):
        doc.tipo = "recibo"
        am = RE_MONEY.findall(flat)
        doc.importe = max((_num_ar(a) for a in am), default=None)
        return doc
    doc.tipo = "otro"
    return doc


# ------------------------------------------------------------------ manifiesto
@dataclass
class ItemManifiesto:
    fecha: Optional[date]
    proveedor: str
    importe: float
    factura_nro: Optional[str]
    adjuntos: list[str]      # rutas
    fuente: dict = field(default_factory=dict)


def cargar_manifiesto_redconar(path_json: str, carpeta: str, mes: Optional[str] = None) -> list[ItemManifiesto]:
    """Convierte el manifiesto generado por la descarga del portal de Redconar (una fila por adjunto) a items por gasto."""
    rows = json.load(open(path_json, encoding="utf-8"))
    if mes:
        rows = [r for r in rows if r.get("mes", "").startswith(mes)]
    by = {}
    for r in rows:
        key = (r["mes"], r["n"])
        it = by.setdefault(key, dict(fecha=r["fecha"], proveedor=r["proveedor"], valor=r.get("valor", ""), factura=r.get("factura"), files=[]))
        if r.get("archivo"):
            p = os.path.join(carpeta, r["mes"], r["archivo"])
            it["files"].append(p)
    out = []
    for (mes_, n), it in sorted(by.items()):
        imp = float(re.sub(r"[^\d.]", "", it["valor"].replace(",", ""))) if it["valor"] else 0.0
        d, m, y = (it["fecha"].split("-") + ["", "", ""])[:3]
        f = date(int(y), int(m), int(d)) if y else None
        out.append(ItemManifiesto(f, it["proveedor"], imp, it["factura"] or None, it["files"], dict(mes=mes_, n=n)))
    return out


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
        cercanos = [d for d in pagos_docs
                    if d.fecha and abs((d.fecha - p.fecha).days) <= DIAS_TOLERANCIA_PAGO]
        if cercanos:
            montos = ", ".join(fmt(d.importe) for d in cercanos if d.importe is not None) or "sin importe legible"
            evidencia = f"Hay comprobantes de esa fecha, pero no cubren el pago declarado: {montos}."
        else:
            fechas = ", ".join(sorted({str(d.fecha) for d in pagos_docs if d.fecha})) or "sin fecha legible"
            evidencia = f"Los comprobantes de pago adjuntos son de otras fechas: {fechas}."
        out.append(Hallazgo(
            "comprobantes", "ALTO", "Control de pagos",
            f"{g.proveedor}: la transferencia declarada el {p.fecha} por {fmt(p.importe)} no está respaldada por los comprobantes adjuntos",
            evidencia,
            p.importe, "Pedir el comprobante de esa transferencia.",
            [str(g.n)], clave=f"pago-sin-comp|{p.fecha.isoformat()}"))
    return out


def _cerca(a: float, b: float) -> bool:
    return abs(a - b) <= max(1.0, 0.02 * max(abs(a), abs(b)))


RE_MONTO_TEXTO = re.compile(r"\d{1,3}(?:\.\d{3})+,\d{2}|\d{1,3}(?:,\d{3})+\.\d{2}")


def _montos_del_concepto(texto: str) -> list[float]:
    """Montos escritos en el concepto de la liquidación ('$3.166.031,55' o '255,132.48'):
    si la propia liquidación declara el total de la factura, no hay nada oculto."""
    out = []
    for m in RE_MONTO_TEXTO.findall(texto or ""):
        if m.count(",") == 1 and m.rfind(",") > m.rfind("."):
            out.append(float(m.replace(".", "").replace(",", ".")))
        else:
            out.append(float(m.replace(",", "")))
    return out


def chequear_importe_factura(g: Gasto, facts: list[Documento], total_proveedor_mes: float) -> list[Hallazgo]:
    """El importe leído de las facturas adjuntas tiene que cerrar contra algo: el gasto, el
    total facturado según la liquidación (caso cuotas) o el total del proveedor en el mes
    (una factura que cubre varias líneas). Si nada cierra, hay que mirarlo."""
    importes = [f.importe for f in facts if f.importe]
    if not importes:
        return []
    suma = round(sum(importes), 2)
    objetivos = [g.importe, total_proveedor_mes] + ([g.factura_importe] if g.factura_importe else [])
    objetivos += _montos_del_concepto(g.concepto)
    if any(_cerca(x, obj) for x in importes + [suma] for obj in objetivos):
        return []
    return [Hallazgo(
        "comprobantes", "MEDIO", "Respaldo documental",
        f"{g.proveedor}: las facturas adjuntas suman {fmt(suma)} pero el gasto es {fmt(g.importe)}",
        f"Importes de las facturas adjuntas: {', '.join(fmt(x) for x in importes)}."
        + (f" Total facturado según la liquidación: {fmt(g.factura_importe)}." if g.factura_importe else ""),
        abs(suma - g.importe), "Cotejar las facturas con el gasto liquidado.",
        [str(g.n)], clave="imp-fact")]


# ------------------------------------------------------------------ cruce
def _same_entity(a: Optional[str], b: Optional[str]) -> bool:
    if not a or not b:
        return False
    return a.replace("-", "") == b.replace("-", "")


def _norm(s: str) -> str:
    return re.sub(r"[^a-z0-9]", "", s.lower())


def cruzar(liq: Liquidacion, items: list[ItemManifiesto], carpeta: Optional[str] = None) -> tuple[list[Documento], list[Hallazgo]]:
    docs: list[Documento] = []
    hs: list[Hallazgo] = []
    cons = liq.cuit_consorcio.replace("-", "")
    nombres: dict[str, str] = {}
    for g in liq.gastos:
        if "SUELDO" in g.categoria.upper():
            m = re.search(r"Sueldo(?: y SAC)?\.?\s+([A-ZÁÉÍÓÚa-záéíóú ]{5,40}?)\s*-", g.proveedor + " - " + g.concepto)
            if m:
                nombres[m.group(1).strip()] = "empleado"
    for u in liq.unidades:
        nombres[u.propietario] = f"propietario de {u.piso_depto}"
    seen_hash: dict[str, list[int]] = {}
    seen_op: dict[str, list[int]] = {}
    por_gasto: dict[int, list[Documento]] = {}
    matched: set[int] = set()
    inciertos: list[int] = []
    for it in items:
        g, certero = _match_gasto(it, liq)
        gn = g.n if g else None
        if g:
            matched.add(g.n)
        if g and not certero:
            inciertos.append(g.n)
        if not it.adjuntos:
            if g:
                hs.append(Hallazgo("comprobantes", "MEDIO", "Respaldo documental", f"Gasto sin ningún comprobante adjunto: {g.proveedor} {fmt(g.importe)}", g.concepto[:140], g.importe, "Pedir la factura y el comprobante de pago.", [str(g.n)]))
            continue
        for p in it.adjuntos:
            d = interpretar(p, gn, liq.cuit_consorcio)
            if g and not certero:
                d.notas.append("Atribución incierta: varios gastos del mes comparten este importe.")
            docs.append(d)
            por_gasto.setdefault(gn or -1, []).append(d)
            if d.hash:
                seen_hash.setdefault(d.hash, []).append(gn or -1)
            if d.tipo == "pago" and d.operacion:
                seen_op.setdefault(d.operacion, []).append(gn or -1)
    # gastos de la liquidación sin item en el manifiesto
    for g in liq.gastos:
        if g.n not in matched:
            hs.append(Hallazgo("comprobantes", "MEDIO", "Respaldo documental", f"Gasto sin comprobantes en el portal: {g.proveedor} {fmt(g.importe)}", g.concepto[:140], g.importe, "Pedir la factura y el comprobante de pago.", [str(g.n)]))
    # por gasto: factura vs pago vs liquidación
    for gn, ds in por_gasto.items():
        g = next((x for x in liq.gastos if x.n == gn), None)
        if not g:
            continue
        facts = [d for d in ds if d.tipo == "factura"]
        pagos = [d for d in ds if d.tipo == "pago" and not any("CRÉDITO" in n for n in d.notas)]
        imgs = [d for d in ds if d.tipo == "imagen"]
        creditos = [d for d in ds if d.tipo == "pago" and any("CRÉDITO" in n for n in d.notas)]
        ref = [str(gn)]
        # factura a nombre de otro
        for f in facts:
            txt = next((n[9:] for n in f.notas if n.startswith("__texto__:")), "")
            vinc = nombre_vinculado(txt, nombres) if (f.receptor_cuit != cons) else None
            if vinc and (not f.receptor_cuit or f.receptor_cuit != cons):
                hs.append(Hallazgo("comprobantes", "CRÍTICO", "Gasto ajeno al consorcio", f"La factura de {g.proveedor} está a nombre de {vinc[0].title()} ({vinc[1]}), no del consorcio",
                                   f"{f.archivo}: el nombre figura como titular o cliente. Importe {fmt(g.importe)}.", g.importe, "Verificar quién contrató el servicio y por qué lo paga el consorcio.", ref))
            elif f.receptor_cuit and cons and f.receptor_cuit != cons and f.receptor_cuit != f.emisor_cuit:
                hs.append(Hallazgo("comprobantes", "CRÍTICO", "Respaldo documental", f"Factura de {g.proveedor} emitida a un tercero, no al consorcio",
                                   f"Receptor: {f.receptor or '?'} (CUIT {f.receptor_cuit}); emisor CUIT {f.emisor_cuit}; {f.archivo}.", g.importe, "Exigir factura a nombre del consorcio y explicar quién compró.", ref))
            elif f.receptor_cuit is None and f.receptor and "CONSORCIO" not in f.receptor.upper() and not vinc:
                hs.append(Hallazgo("comprobantes", "ALTO", "Respaldo documental", f"Factura de {g.proveedor} a nombre de '{f.receptor}'", f"No figura el CUIT del consorcio; {f.archivo}.", g.importe, "Verificar a quién se facturó.", ref))
            for n in f.notas:
                if n.startswith("Leyenda de ARCA"):
                    hs.append(Hallazgo("comprobantes", "BAJO", "Calidad de datos", f"Factura de {g.proveedor} con leyenda de ARCA sobre la CUIT del consorcio", n, 0, "Verificar la situación fiscal del consorcio.", ref))
        # pago a un tercero distinto del emisor
        emisores = {f.emisor_cuit for f in facts if f.emisor_cuit}
        for p in pagos:
            if p.destinatario_cuit and emisores and p.destinatario_cuit not in emisores:
                hs.append(Hallazgo("comprobantes", "CRÍTICO", "Pagos a terceros", f"El pago de {g.proveedor} ({fmt(p.importe or g.importe)}) fue a {p.destinatario or 'otro'} (CUIT {p.destinatario_cuit}), que no es el emisor de la factura",
                                   f"Factura emitida por CUIT {', '.join(sorted(emisores))}; transferencia {p.operacion or ''} del {p.fecha or ''} a CUIT {p.destinatario_cuit}. {p.archivo}.", p.importe or g.importe, "Exigir que los pagos vayan a la cuenta del emisor o una autorización escrita.", ref))
            if p.importe and abs(p.importe - g.importe) > 1 and not any(abs(p.importe - x.importe) < 1 for x in g.pagos):
                mismo_prov = round(sum(x.importe for x in liq.gastos if x.proveedor == g.proveedor and x.fecha_pago == g.fecha_pago), 2)
                if p.importe > g.importe * 1.02 and abs(p.importe - mismo_prov) > 1:
                    hs.append(Hallazgo("comprobantes", "ALTO", "Control de pagos", f"Transferencia por {fmt(p.importe)} para un gasto de {fmt(g.importe)} ({g.proveedor})",
                                       f"{p.archivo}: destinatario {p.destinatario or '?'} CUIT {p.destinatario_cuit or '?'}, fecha {p.fecha or '?'}. Se pagó de más.", p.importe - g.importe, "Aclarar la diferencia y exigir la devolución.", ref))
                elif p.importe < g.importe * 0.98 and "SUELDO" in g.categoria.upper() and len(pagos) == 1:
                    hs.append(Hallazgo("comprobantes", "MEDIO", "Personal", f"Sueldo neto de {fmt(g.importe)} pero se transfirieron {fmt(p.importe)}: diferencia de {fmt(g.importe - p.importe)} no informada",
                                       f"{p.archivo}: posible adelanto o descuento no reflejado en la liquidación.", g.importe - p.importe, "Pedir el detalle de adelantos y descuentos.", ref))
            if p.motivo and re.search(r"haberes", p.motivo, re.I) and "SUELDO" not in g.categoria.upper():
                hs.append(Hallazgo("comprobantes", "ALTO", "Gasto ajeno al consorcio", f"{g.proveedor}: el pago se hizo como 'acreditamiento de haberes' a {p.destinatario or '?'}",
                                   f"El gasto no es un sueldo; {p.archivo}.", g.importe, "Verificar si el servicio está contratado a nombre de un empleado.", ref))
        for c in creditos:
            hs.append(Hallazgo("comprobantes", "ALTO", "Control de pagos", f"Devolución de {fmt(c.importe or 0)} recibida de {c.destinatario or g.proveedor}", f"Crédito del {c.fecha or '?'} adjunto al gasto {g.proveedor} {fmt(g.importe)}: indica un pago en exceso previo. {c.archivo}.", c.importe or 0, "Registrar el error y la devolución en la liquidación.", ref))
        hs.extend(chequear_pagos_declarados(g, pagos))
        total_prov = round(sum(x.importe for x in liq.gastos if x.proveedor == g.proveedor), 2)
        hs.extend(chequear_importe_factura(g, facts, total_prov))
        # sin factura / sin pago
        if not facts and not imgs and g.factura_nro:
            hs.append(Hallazgo("comprobantes", "MEDIO", "Respaldo documental", f"{g.proveedor}: la liquidación cita la factura {g.factura_nro} pero no está adjunta", "", g.importe, "Pedir la factura.", ref))
        deb_auto = any(re.search(r"d[eé]bito", x.forma, re.I) for x in g.pagos)
        if not pagos and not imgs and not creditos and g.importe > 50_000 and not g.en_efectivo and not deb_auto:
            hs.append(Hallazgo("comprobantes", "MEDIO", "Respaldo documental", f"{g.proveedor}: sin comprobante de pago adjunto ({fmt(g.importe)})", "", g.importe, "Pedir el comprobante de la transferencia.", ref))
        if g.en_efectivo and g.importe > 300_000:
            hs.append(Hallazgo("comprobantes", "CRÍTICO", "Control interno / caja", f"{g.proveedor}: {fmt(g.importe)} en efectivo" + (" con recibo sin texto (manuscrito o imagen)" if imgs else ""), g.concepto[:120], g.importe, "Exigir recibo oficial del proveedor.", ref))
        # fechas: pago anterior a la factura según los documentos
        for f in facts:
            for p in pagos:
                if f.fecha and p.fecha and p.fecha < f.fecha:
                    hs.append(Hallazgo("comprobantes", "ALTO", "Obras / contratación", f"{g.proveedor}: transferencia del {p.fecha} anterior a la factura del {f.fecha}", f"{p.archivo} / {f.archivo}", g.importe, "Exigir factura antes del pago.", ref))
    # duplicados
    for h, gns in seen_hash.items():
        u = sorted(set(x for x in gns if x > 0))
        if len(u) > 1:
            names = [next((x.proveedor for x in liq.gastos if x.n == n), str(n)) for n in u]
            suma = round(sum(x.importe for x in liq.gastos if x.n in u), 2)
            d0 = next((d for d in docs if d.hash == h), None)
            if d0 and d0.importe and abs(d0.importe - suma) < 1:
                hs.append(Hallazgo("comprobantes", "BAJO", "Respaldo documental", f"Una sola transferencia de {fmt(d0.importe)} paga {len(u)} gastos ({', '.join(names)})", f"La suma coincide. {d0.archivo}.", 0, "Correcto, solo para tener en cuenta.", [str(n) for n in u]))
            else:
                hs.append(Hallazgo("comprobantes", "ALTO", "Respaldo documental", f"El mismo archivo está adjunto a {len(u)} gastos distintos", f"Gastos: {', '.join(names)}.", 0, "Verificar si es un solo pago contado más de una vez.", [str(n) for n in u]))
    for op, gns in seen_op.items():
        u = sorted(set(x for x in gns if x > 0))
        if len(u) > 1:
            names = [next((x.proveedor for x in liq.gastos if x.n == n), str(n)) for n in u]
            suma = round(sum(x.importe for x in liq.gastos if x.n in u), 2)
            d0 = next((d for d in docs if d.operacion == op), None)
            if not (d0 and d0.importe and abs(d0.importe - suma) < 1):
                hs.append(Hallazgo("comprobantes", "ALTO", "Respaldo documental", f"La transferencia {op} respalda {len(u)} gastos distintos", f"Gastos: {', '.join(names)}.", 0, "Un comprobante por pago; verificar que no se cobre dos veces.", [str(n) for n in u]))
    if inciertos:
        u = sorted(set(inciertos))
        names = [next((x.proveedor for x in liq.gastos if x.n == n), str(n)) for n in u]
        hs.append(Hallazgo("comprobantes", "BAJO", "Calidad de datos",
                           f"{len(u)} gasto(s) con comprobantes atribuidos con incertidumbre",
                           f"Varios gastos del mes comparten importe; se atribuyó al primero. Gastos: {', '.join(names)}.",
                           0, "Verificar a mano a qué gasto corresponde cada comprobante.",
                           [str(n) for n in u], clave="atribucion-incierta"))
    for d in docs:
        d.notas = [n for n in d.notas if not n.startswith("__texto__:")]
    # dedupe
    out = []; seen = set()
    for h in hs:
        k = (h.titulo, tuple(h.refs))
        if k not in seen:
            seen.add(k); out.append(h)
    order = {"CRÍTICO": 0, "ALTO": 1, "MEDIO": 2, "BAJO": 3}
    out.sort(key=lambda h: (order.get(h.severidad, 9), -abs(h.monto)))
    return docs, out
