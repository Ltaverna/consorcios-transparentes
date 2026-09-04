"""Parser de liquidaciones de expensas emitidas por Redconar (formato 'Mis Expensas' de CABA).

Entrada: texto con layout preservado (pdftotext -layout). Soporta las dos plantillas vistas:
- 2024: encabezados en mayúsculas, "Monto:", "TOTAL <pct>$<importe>" por rubro, clases A y B.
- 2025/2026: "Rubros-Concepto", "Importe:", "Total <rubro> <pct> $<importe>", clases A, B y D, "Total de gastos".

Regla de oro: nada se da por bueno si los totales no cuadran; los checks quedan en Liquidacion.checks.
"""
from __future__ import annotations
import itertools
import re
import subprocess
from datetime import date
from typing import Optional

from .model import (Check, Cuenta, Deudor, EstadoFinanciero, Gasto, Liquidacion, MesEvolucion, Pago, Patrimonial, Unidad)

AMT = r"-?\$?\s?-?\d{1,3}(?:,\d{3})*\.\d{2}"
RE_AMT = re.compile(AMT)
RE_DATE = re.compile(r"\b(\d{2})-(\d{2})-(\d{4})\b")
MESES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"]


def pdf_to_text(path: str) -> str:
    return subprocess.run(["pdftotext", "-layout", path, "-"], capture_output=True, text=True, check=True).stdout


def num(s: str) -> float:
    s = s.replace("$", "").replace(" ", "")
    neg = s.startswith("-") or s.endswith("-")
    s = s.strip("-").replace(",", "")
    v = float(s)
    return -v if neg else v


def dt(s: Optional[str]) -> Optional[date]:
    if not s:
        return None
    m = RE_DATE.search(s)
    if not m:
        return None
    d, mo, y = map(int, m.groups())
    try:
        return date(y, mo, d)
    except ValueError:
        return None


def _clean_lines(text: str) -> list[str]:
    out = []
    for ln in text.splitlines():
        if "Ante cualquier duda podés llamar al 147" in ln or "Facebook/BAConsumidor" in ln or "Powered by TCPDF" in ln:
            continue
        out.append(ln.rstrip("\n"))
    return out


# ------------------------------------------------------------------ encabezado
def _header(lines: list[str], liq: Liquidacion) -> None:
    head = "\n".join(lines[:60])
    m = re.search(r"MIS EXPENSAS.*?\n\s*([A-Za-zÁÉÍÓÚáéíóú]+)\s+(\d{4})", head)
    if m:
        liq.periodo = f"{m.group(1).capitalize()} {m.group(2)}"
    m = re.search(r"1° Venc:\s*(\d{2}-\d{2}-\d{4})", head)
    liq.venc1 = dt(m.group(1)) if m else None
    m = re.search(r"2° Venc:\s*(\d{2}-\d{2}-\d{4})", head)
    liq.venc2 = dt(m.group(1)) if m else None
    m = re.search(r"Nombre:\s*(.+?)\s{2,}Domicilio:\s*(.+)", head)
    if m:
        liq.administracion = m.group(1).strip()
        liq.consorcio = m.group(2).strip()
    cuits = re.findall(r"CUIT:\s*(\d{2}-\d{8}-\d)", head)
    if len(cuits) >= 2:
        liq.cuit_consorcio, liq.cuit_administracion = cuits[0], cuits[1]
    elif cuits:
        liq.cuit_consorcio = cuits[0]


# ------------------------------------------------------------------ gastos
RE_CAT = re.compile(r"^\s*(\d{1,2})\s+([A-ZÁÉÍÓÚÑ][A-ZÁÉÍÓÚÑ .,/&-]+?)\s*$")
RE_ITEM_TAIL = re.compile(r"(" + AMT + r")\s+(-?\d+\.\d{2})\s*%?\s*(\$\s*-?[\d,]+\.\d{2})\s*$")
RE_TOTAL_NEW = re.compile(r"^\s*Total\s+(?!de gastos)(.+?)\s+(-?\d+\.\d{2})%\s+(\$?\s*-?[\d,]+\.\d{2})\s*$", re.I)
RE_TOTAL_OLD = re.compile(r"^\s*TOTAL\s+(-?\d+\.\d{2})\s*(\$\s*-?[\d,]+\.\d{2})\s*$")
RE_TOTAL_GASTOS = re.compile(r"^\s*Total de gastos\s+(.*)$")
RE_PAGO = re.compile(r"PAGO\s+Fecha:\s*(\d{2}-\d{2}-\d{4})", re.I)
RE_PAGO_PARTS = re.compile(r"(?:Importe|Monto):\s*(\$\s*-?[\d,]+\.\d{2})\s*-?\s*Caja:\s*([A-Z]+)\s*-?\s*Forma:\s*([A-Za-zé ]+?)(?=\s+(?:Importe|Monto):|\s*$)", re.I)
RE_FACT = re.compile(r"FACTURA\s+Fecha:\s*(\d{2}-\d{2}-\d{4})\s+Nro:\s*(\S+)\s+Importe:\s*(\$\s*-?[\d,]+\.\d{2})", re.I)
RE_PERIODO = re.compile(r"Per[ií]odo:\s*([A-Za-z]+,?\s*\d{4}|\d{1,2},\s*\d{4})")


def _column_positions(lines: list[str], start: int) -> dict[str, int]:
    """Busca la línea de encabezado de columnas (A B D) más cercana hacia atrás y devuelve la posición de cada letra."""
    for i in range(start, max(0, start - 80), -1):
        ln = lines[i]
        if "Rubros-Concepto" in ln or "RUBROS- CONCEPTO" in ln or "GASTO A" in ln:
            pos = {}
            for m in re.finditer(r"(?:GASTO\s+)?\b([ABD])\b", ln):
                # ignorar la 'A' de 'GASTO A' repetida: usar posición de la letra
                pos[m.group(1)] = m.end() - 1
            if pos:
                return pos
    return {"A": 0}


def _nearest_col(x: int, cols: dict[str, int]) -> str:
    return min(cols.items(), key=lambda kv: abs(kv[1] - x))[0]


def _parse_gastos(lines: list[str], liq: Liquidacion) -> None:
    # límites de la sección
    start = next((i for i, l in enumerate(lines) if "REMUNERACIONES AL PERSONAL" in l), None)
    end = next((i for i, l in enumerate(lines) if "RESUMEN DE GASTOS" in l or "EVOLUCI" in l.upper() and "COBRANZAS" in l.upper()), len(lines))
    if start is None:
        liq.avisos.append("No se encontró la sección de gastos")
        return
    cat = None
    cur: Optional[dict] = None
    items: list[dict] = []
    cols = {"A": 0}
    n = 0
    next_cat = 1

    def close():
        nonlocal cur
        if cur:
            items.append(cur)
            cur = None

    for i in range(start, end):
        ln = lines[i]
        s = ln.strip()
        if not s:
            continue
        if "Rubros-Concepto" in ln or "RUBROS- CONCEPTO" in ln or "GASTO A" in ln:
            cols = _column_positions(lines, i) or cols
            continue
        if s.startswith("expensas ordina") or s.startswith("EXPENSAS ORDINA") or s.startswith("(Conf. Art") or s.startswith("GASTOS DEL PER") or s.startswith("REMUNERACIONES"):
            continue
        mc = RE_CAT.match(ln)
        if mc and not RE_AMT.search(ln) and int(mc.group(1)) == next_cat and not s.endswith('-'):
            close()
            cat = mc.group(2).strip()
            next_cat += 1
            continue
        mt = RE_TOTAL_NEW.match(ln) or RE_TOTAL_OLD.match(ln)
        if mt and cat:
            close()
            amt = num(mt.groups()[-1])
            liq.totales_categoria[cat] = round(liq.totales_categoria.get(cat, 0.0) + amt, 2)
            continue
        mg = RE_TOTAL_GASTOS.match(ln)
        if mg:
            close()
            nums = [num(x) for x in RE_AMT.findall(mg.group(1)) if "%" not in x]
            if nums:
                liq.total_gastos = nums[-1]
                letters = sorted(cols, key=lambda k: cols[k])
                for k, v in zip(letters, nums[:-1]):
                    liq.totales_columna[k] = v
            continue
        mtail = RE_ITEM_TAIL.search(ln)
        if mtail and cat and not RE_PAGO.search(ln) and not RE_FACT.search(ln):
            close()
            n += 1
            col_amt, pct, total = mtail.group(1), mtail.group(2), mtail.group(3)
            x = mtail.start(1)
            colname = _nearest_col(x, cols)
            head = ln[: mtail.start()].strip()
            cur = dict(n=n, categoria=cat, head=head, body=[], columna=colname, importe=num(total), pct=float(pct), col_amt=num(col_amt))
            continue
        if cur is not None:
            cur["body"].append(s)
    close()

    for it in items:
        text = it["head"] + " " + " ".join(it["body"])
        text = re.sub(r"\s+", " ", text)
        prov, _, concepto = it["head"].partition(" - ")
        if not concepto:
            prov, concepto = it["head"], ""
        # nombres de organismos con guion interno (ARCA - AGENCIA DE ...): si la primera parte es una sigla corta, tomar más
        if len(prov.strip()) <= 5 and concepto and concepto.split(" - ")[0].isupper():
            prov = prov.strip() + " - " + concepto.split(" - ")[0].strip(); concepto = " - ".join(concepto.split(" - ")[1:])
        prov = prov.strip().rstrip("-").strip()
        body = " ".join(it["body"])
        # facturas
        mf = RE_FACT.search(re.sub(r"\s+", " ", body))
        # pagos
        pagos = []
        flat = re.sub(r"\s+", " ", body)
        for mp in RE_PAGO.finditer(flat):
            seg = flat[mp.end(): mp.end() + 400]
            nxt = RE_PAGO.search(seg)
            if nxt:
                seg = seg[: nxt.start()]
            parts = RE_PAGO_PARTS.findall(seg)
            if parts:
                for imp, caja, forma in parts:
                    pagos.append(Pago(fecha=dt(mp.group(1)), importe=num(imp), caja=caja.strip(), forma=forma.strip()))
            else:
                mi = re.search(r"(?:Importe|Monto):\s*(\$\s*-?[\d,]+\.\d{2})", seg)
                pagos.append(Pago(fecha=dt(mp.group(1)), importe=num(mi.group(1)) if mi else it["importe"]))
        # concepto sin las líneas técnicas
        concepto_full = re.sub(r"\s+", " ", concepto + " " + body)
        concepto_full = re.split(r"\s*(?:FACTURA Fecha:|PAGO Fecha:)", concepto_full)[0].strip(" -")
        mper = RE_PERIODO.search(concepto_full)
        liq.gastos.append(Gasto(
            n=it["n"], categoria=it["categoria"], proveedor=prov.strip(), concepto=concepto_full, columna=it["columna"], importe=it["importe"], pct_inc=it["pct"],
            factura_fecha=dt(mf.group(1)) if mf else None, factura_nro=mf.group(2) if mf else None, factura_importe=num(mf.group(3)) if mf else None,
            periodo=mper.group(1) if mper else None, pagos=pagos,
        ))


# ------------------------------------------------------------------ deudores
def _parse_deudores(lines: list[str], liq: Liquidacion) -> None:
    start = next((i for i, l in enumerate(lines) if "PROPIETARIOS CON SALDO DEUDOR" in l), None)
    if start is None:
        return
    for ln in lines[start + 1: start + 200]:
        m = re.match(r"^\s*(\d{1,3})\s+(\S+)\s+(.+?)\s+(\$\s*-?[\d,]+\.\d{2})\s*$", ln)
        if m:
            liq.deudores.append(Deudor(uf=int(m.group(1)), piso_depto=m.group(2), propietario=m.group(3).strip().rstrip(","), deuda=num(m.group(4))))
            continue
        mt = re.match(r"^\s*(?:Total|TOTAL DEUDA)\s+(\$\s*-?[\d,]+\.\d{2})\s*$", ln, re.I)
        if mt:
            liq.total_deudores = num(mt.group(1))
            break


# ------------------------------------------------------------------ estado financiero / cuentas / patrimonial
def _grab(lines: list[str], label: str, start: int, end: int) -> Optional[float]:
    for ln in lines[start:end]:
        if ln.strip().lower().startswith(label.lower()):
            amts = RE_AMT.findall(ln)
            if amts:
                return num(amts[-1])
    return None


def _parse_estado(lines: list[str], liq: Liquidacion) -> None:
    i0 = next((i for i, l in enumerate(lines) if "ESTADO FINANCIERO" in l and "COMPOSICI" not in l.upper()), None)
    i1 = next((i for i, l in enumerate(lines) if "COMPOSICI" in l.upper() and "ESTADO FINANCIERO" in l.upper()), None)
    i2 = next((i for i, l in enumerate(lines) if "ESTADO PATRIMONIAL" in l), None)
    i3 = next((i for i, l in enumerate(lines) if "CREDITOS/DEBITOS" in l.upper() or "DETALLE DE PROVEEDORES" in l), len(lines))
    if i0 is not None and i1 is not None:
        e = liq.estado
        g = lambda lab: _grab(lines, lab, i0, i1) or 0.0
        e.saldo_anterior = g("SALDO ANTERIOR"); e.ing_termino = g("Ingresos por pago de expensas en término"); e.ing_adeudadas = g("Ingresos por pago de expensas adeudadas")
        e.ing_intereses = g("Ingresos por pago de intereses"); e.ing_adelantadas = g("Ingresos por expensas adelantadas"); e.otros_ingresos = g("Otros ingresos")
        e.egresos = abs(g("Egresos por gastos del mes")); e.saldo_cierre = g("Saldo al cierre")
    if i1 is not None and i2 is not None:
        name = None; blk: dict = {}
        for ln in lines[i1 + 1: i2]:
            s = ln.strip()
            mname = re.match(r"^\$\s*-\s*(.+?)\s*-?\s*$", s)
            if mname and not RE_AMT.search(s):
                if name:
                    liq.cuentas.append(Cuenta(name, blk.get("saldo_ant", 0), blk.get("ingresos", 0), abs(blk.get("egresos", 0)), blk.get("saldo_cierre", 0)))
                name = mname.group(1).strip(" -"); blk = {}
                continue
            amts = RE_AMT.findall(s)
            if not amts or not name:
                continue
            v = num(amts[-1]); low = s.lower()
            if low.startswith("saldo anterior"): blk["saldo_ant"] = v
            elif low.startswith("ingresos por expensas") or low.startswith("otros ingresos"): blk["ingresos"] = blk.get("ingresos", 0) + v
            elif low.startswith("egresos por gastos") or low.startswith("otros egresos"): blk["egresos"] = blk.get("egresos", 0) + abs(v)
            elif low.startswith("saldo al cierre"): blk["saldo_cierre"] = v
        if name:
            liq.cuentas.append(Cuenta(name, blk.get("saldo_ant", 0), blk.get("ingresos", 0), abs(blk.get("egresos", 0)), blk.get("saldo_cierre", 0)))
    if i2 is not None:
        p = liq.patrimonial
        g = lambda lab: _grab(lines, lab, i2, i3) or 0.0
        p.disponibilidades = g("SALDO DE DISPONIBILIDADES"); p.a_cobrar = g("Expensas y otros conceptos a cobrar"); p.devengados_pend = g("Gastos devengados")
        p.facturas_pend = g("Facturas pendientes"); p.total = g("Total")


# ------------------------------------------------------------------ evolución
def _parse_evolucion(lines: list[str], liq: Liquidacion) -> None:
    i0 = next((i for i, l in enumerate(lines) if "COBRANZAS Y GASTOS" in l.upper()), None)
    if i0 is None:
        return
    meses = None; rows: dict[str, list[float]] = {}
    for ln in lines[i0 + 1: i0 + 12]:
        if meses is None and re.search(r"[A-Za-z]+ \d{4}\s+[A-Za-z]+ \d{4}", ln):
            meses = re.findall(r"([A-Za-zÁÉÍÓÚáéíóú]+ \d{4})", ln)
            continue
        for key, lab in (("a_cobrar", "Importe a cobrar"), ("gastos", "Gastos del mes"), ("cobrado", "Expensas cobradas")):
            if ln.strip().startswith(lab):
                rows[key] = [num(x) for x in RE_AMT.findall(ln)]
    if meses and len(rows) == 3:
        for i, m in enumerate(meses):
            try:
                liq.evolucion.append(MesEvolucion(m, rows["a_cobrar"][i], rows["gastos"][i], rows["cobrado"][i]))
            except IndexError:
                pass


# ------------------------------------------------------------------ estado de cuentas
RE_ROW = re.compile(r"^\s*(\d{1,3})\s+(LOC-?|PB-[A-Z]|\d{1,2}-[A-Z]|UC-\d{1,2})\s+(.+?)\s+(\$ .*?)\s+\1\s*$")
RE_TOK = re.compile(r"\$ (-?[\d,]+\.\d{2})|(\d+\.\d{2})%")


def _class_positions(lines: list[str], row_idx: int) -> dict[str, int]:
    """Posiciones (columna de caracteres) de las letras de clase (A, B, D) en el encabezado previo a la fila."""
    for i in range(row_idx, max(0, row_idx - 12), -1):
        ln = lines[i]
        found = {m.group(1): m.start() for m in re.finditer(r"(?<![A-Za-z])([ABD])(?![A-Za-z])", ln)}
        if found and not RE_AMT.search(ln) and "Uf" not in ln:
            # puede haber letras repartidas en 2 líneas: combinar con la anterior
            prev = lines[i - 1] if i > 0 else ""
            for m in re.finditer(r"(?<![A-Za-z])([ABD])(?![A-Za-z])", prev):
                found.setdefault(m.group(1), m.start())
            return found
    return {}


def _class_names(n: int, hdr: list[str]) -> list[str]:
    """Las clases van de izquierda a derecha en orden alfabético. Con 3 clases, si el encabezado menciona D es A, B, D."""
    if n >= 4:
        return ["A", "B", "C", "D"][:n]
    if n == 3:
        return ["A", "B", "D"] if ("D" in hdr or not hdr) else ["A", "B", "C"]
    return ["A", "B"][:max(n, 1)]


def _parse_unidades(lines: list[str], liq: Liquidacion) -> None:
    raw_rows: list[dict] = []
    classes_hdr: list[str] = []
    in_section = False
    for idx, ln in enumerate(lines):
        if "ESTADO DE CUENTAS Y PRORRATEO" in ln:
            in_section = True
            if not classes_hdr:
                pos = _class_positions(lines[idx: idx + 12], 11) if idx + 12 <= len(lines) else {}
                classes_hdr = sorted(pos, key=lambda k: pos[k])
            continue
        if not in_section:
            continue
        m = RE_ROW.match(ln)
        if not m:
            mt = re.match(r"^\s*Total\s+(\$ .*)$", ln)
            if mt and raw_rows and not liq.prorrateo_total:
                toks = list(RE_TOK.finditer(mt.group(1)))
                pairs = []
                i = 0
                while i < len(toks):
                    if toks[i].group(2) is not None and i + 1 < len(toks) and toks[i + 1].group(1) is not None:
                        pairs.append(num(toks[i + 1].group(1))); i += 2
                    else:
                        i += 1
                classes = _class_names(len(pairs), classes_hdr)
                for c, v in zip(classes, pairs):
                    liq.prorrateo_total[c] = v
                amts = [num(t.group(1)) for t in toks if t.group(1) is not None]
                liq.prorrateo_total["_a_pagar"] = amts[-1]
                liq.prorrateo_total["_total_mes"] = amts[-4] if len(amts) >= 4 else 0.0
                liq.prorrateo_total["_gpart"] = amts[-3] if len(amts) >= 4 else 0.0
                liq.prorrateo_total["_pagos"] = amts[1] if len(amts) > 1 else 0.0
                liq.prorrateo_total["_deuda"] = amts[3] if len(amts) > 3 else 0.0
                liq.prorrateo_total["_interes"] = amts[4] if len(amts) > 4 else 0.0
            continue
        uf, pd_, prop, rest = m.groups()
        seq = []
        for t in RE_TOK.finditer(rest):
            seq.append(("$", num(t.group(1))) if t.group(1) is not None else ("%", float(t.group(2))))
        if not seq or seq[0][0] != "$":
            continue
        first_pct = next((i for i, t in enumerate(seq) if t[0] == "%"), None)
        if first_pct is None:
            liq.avisos.append(f"Fila UF {uf}: sin porcentuales"); continue
        M = [t[1] for t in seq[1:first_pct]]
        tail = seq[first_pct:]
        pairs = []; i = 0
        while i < len(tail) and tail[i][0] == "%" and i + 1 < len(tail) and tail[i + 1][0] == "$":
            pairs.append((tail[i][1], tail[i + 1][1])); i += 2
        rest_amts = [t[1] for t in tail[i:]]
        gpart = 0.0
        if len(rest_amts) == 4:
            total, gpart, red, apagar = rest_amts
        elif len(rest_amts) == 3:
            total, red, apagar = rest_amts
        elif len(rest_amts) == 2:
            total, apagar = rest_amts; red = 0.0
        else:
            liq.avisos.append(f"Fila UF {uf}: no se pudo interpretar la cola de importes ({len(rest_amts)} valores)"); continue
        raw_rows.append(dict(uf=int(uf), pd=pd_, prop=prop.strip(), saldo=seq[0][1], M=M, pairs=pairs, total=total, red=red, apagar=apagar, gpart=gpart))

    if not raw_rows and any("ESTADO DE CUENTAS Y PRORRATEO" in l for l in lines):
        liq.avisos.append("Estado de cuentas: plantilla 2024 (sin signo $) todavía no soportada")
    class_tot = {k: v for k, v in liq.prorrateo_total.items() if not k.startswith("_")}
    classes = sorted(class_tot) or _class_names(max((len(r['pairs']) for r in raw_rows), default=1), classes_hdr)
    for r in raw_rows:
        # asignar cada par (pct, importe) a la clase cuyo total × pct se acerque más al importe, respetando el orden
        expensas: dict[str, float] = {}; pcts: dict[str, float] = {}
        avail = list(classes)
        for pct, amt in r["pairs"]:
            if class_tot and len(avail) > 1:
                best = min(avail, key=lambda c: abs(class_tot[c] * pct / 100.0 - amt))
            else:
                best = avail[0] if avail else "A"
            expensas[best] = amt; pcts[best] = pct
            if best in avail:
                # las clases van de izquierda a derecha: descartar las anteriores a la elegida
                avail = avail[avail.index(best) + 1:]
        if abs(sum(expensas.values()) - r["total"]) > 0.05:
            liq.avisos.append(f"Fila UF {r['uf']}: las clases no suman el total del mes")
        sol = None
        for pos in itertools.combinations(range(4), len(r["M"])):
            v = [0.0] * 4
            for p, val in zip(pos, r["M"]):
                v[p] = val
            pagos, cred, deuda, inte = v
            if abs(r["saldo"] - pagos + cred - deuda) < 0.02 and abs(r["total"] + r["gpart"] + deuda + inte + r["red"] - r["apagar"]) < 0.02:
                sol = v; break
        if sol is None:
            liq.avisos.append(f"Fila UF {r['uf']}: no cierra la identidad saldo/pagos/deuda"); sol = (r["M"] + [0, 0, 0, 0])[:4]
        pagos, cred, deuda, inte = sol
        tipo = "Cochera" if r["pd"].startswith("UC") else ("Local" if r["pd"].startswith("LOC") else "Departamento")
        liq.unidades.append(Unidad(r["uf"], r["pd"], r["prop"], tipo, r["saldo"], pagos, cred, deuda, inte, expensas, pcts, r["total"], r["red"], r["apagar"], r["gpart"]))


# ------------------------------------------------------------------ checks
def _check(liq: Liquidacion, nombre: str, esperado: Optional[float], obtenido: Optional[float], tol: float = 0.05, detalle: str = "") -> None:
    if esperado is None or obtenido is None:
        return
    liq.checks.append(Check(nombre, abs(esperado - obtenido) <= tol, round(esperado, 2), round(obtenido, 2), detalle))


def _checks(liq: Liquidacion) -> None:
    if liq.total_gastos is not None:
        _check(liq, "Suma de líneas = total de gastos", liq.total_gastos, liq.suma_gastos)
    for cat, tot in liq.totales_categoria.items():
        _check(liq, f"Rubro {cat}", tot, liq.por_categoria().get(cat, 0.0))
    if liq.totales_categoria and liq.total_gastos is None:
        _check(liq, "Suma de rubros = suma de líneas", round(sum(liq.totales_categoria.values()), 2), liq.suma_gastos)
    for col, tot in liq.totales_columna.items():
        _check(liq, f"Columna {col}", tot, round(sum(g.importe for g in liq.gastos if g.columna == col), 2))
    e = liq.estado
    if e.saldo_cierre:
        _check(liq, "Estado financiero: saldo anterior + ingresos - egresos = cierre", e.saldo_cierre,
               round(e.saldo_anterior + e.ing_termino + e.ing_adeudadas + e.ing_intereses + e.ing_adelantadas + e.otros_ingresos - e.egresos, 2))
        if liq.total_gastos is not None:
            _check(liq, "Egresos del estado financiero = total de gastos", liq.total_gastos, e.egresos)
    for c in liq.cuentas:
        _check(liq, f"Cuenta {c.nombre}: saldo anterior + ingresos - egresos = cierre", c.saldo_cierre, round(c.saldo_ant + c.ingresos - c.egresos, 2))
    if liq.cuentas and e.saldo_cierre:
        _check(liq, "Suma de cuentas = disponibilidades", e.saldo_cierre, round(sum(c.saldo_cierre for c in liq.cuentas), 2))
    if liq.total_deudores is not None:
        _check(liq, "Deudores: suma = total", liq.total_deudores, round(sum(d.deuda for d in liq.deudores), 2))
    if liq.unidades and liq.prorrateo_total:
        _check(liq, "Estado de cuentas: suma de 'a pagar' = total", liq.prorrateo_total.get("_a_pagar"), round(sum(u.a_pagar for u in liq.unidades), 2))
        _check(liq, "Estado de cuentas: suma de deuda = total", liq.prorrateo_total.get("_deuda"), round(sum(u.deuda for u in liq.unidades), 2))
        _check(liq, "Estado de cuentas: suma de pagos = total", liq.prorrateo_total.get("_pagos"), round(sum(u.pagos for u in liq.unidades), 2))
        for c, v in liq.prorrateo_total.items():
            if not c.startswith("_"):
                _check(liq, f"Prorrateo clase {c}: suma de unidades = total", v, round(sum(u.expensas.get(c, 0.0) for u in liq.unidades), 2))
        if liq.patrimonial.a_cobrar:
            _check(liq, "A cobrar (patrimonial) = total a pagar de unidades", liq.patrimonial.a_cobrar, liq.prorrateo_total.get("_a_pagar"))
        if e.saldo_cierre:
            cobr = e.ing_termino + e.ing_adeudadas + e.ing_intereses + e.ing_adelantadas
            _check(liq, "Expensas cobradas (estado financiero) = pagos de unidades", round(cobr, 2), liq.prorrateo_total.get("_pagos"))


# ------------------------------------------------------------------ API
def parse_text(text: str) -> Liquidacion:
    lines = _clean_lines(text)
    liq = Liquidacion(sistema="redconar", periodo="")
    _header(lines, liq)
    _parse_gastos(lines, liq)
    _parse_deudores(lines, liq)
    _parse_estado(lines, liq)
    _parse_evolucion(lines, liq)
    _parse_unidades(lines, liq)
    _checks(liq)
    return liq


def parse_pdf(path: str) -> Liquidacion:
    return parse_text(pdf_to_text(path))
