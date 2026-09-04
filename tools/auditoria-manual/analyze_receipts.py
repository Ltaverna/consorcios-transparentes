import os
HERE = os.path.dirname(os.path.abspath(__file__))
DATOS = os.path.join(HERE, "datos") + "/"
PRIVADO = os.environ.get("CT_PRIVADO", os.path.expanduser("~/consorcio-transparente-privado")) + "/"
import json, re, os, subprocess, glob
from collections import defaultdict

SC = DATOS
ROOT = PRIVADO + "Comprobantes Rivadavia 2069/"
CONS_CUIT = "33600391459"
manifest = json.load(open(SC + "manifest.json"))

def text_of(path):
    try:
        t = subprocess.run(["pdftotext", "-layout", path, "-"], capture_output=True, text=True, timeout=60).stdout
    except Exception as e:
        return ""
    if len(t.strip()) < 40:  # scanned image: try OCR if available
        try:
            subprocess.run(["pdftoppm", "-r", "200", "-png", "-f", "1", "-l", "2", path, SC + "ocr_tmp"], capture_output=True, timeout=120)
            out = ""
            for img in sorted(glob.glob(SC + "ocr_tmp*.png")):
                r = subprocess.run(["tesseract", img, "-", "-l", "spa+eng"], capture_output=True, text=True, timeout=120)
                out += r.stdout
                os.remove(img)
            if out.strip(): t = out + "\n[OCR]"
        except Exception:
            pass
    return t

def cuits(t):
    return [re.sub(r"\D", "", c) for c in re.findall(r"\b\d{2}[- ]?\d{8}[- ]?\d\b", t)]

def money(t):
    vals = []
    for m in re.findall(r"\$?\s?(\d{1,3}(?:[.,]\d{3})+(?:[.,]\d{2})|\d+[.,]\d{2})", t):
        s = m
        if re.search(r"[.,]\d{2}$", s):
            dec = s[-3]; s = s.replace("." if dec == "," else ",", "").replace(dec, ".")
        try: vals.append(float(s))
        except: pass
    return vals

def parse(t, kind):
    d = {}
    d["cuits"] = sorted(set(cuits(t)))
    d["a_nombre_consorcio"] = CONS_CUIT in d["cuits"] or bool(re.search(r"CONSORCIO", t, re.I))
    m = re.search(r"FACTURA\s*([ABCM])\b|\bFactura\s*\n?\s*([ABC])\b|^\s*([ABC])\s*$", t, re.M)
    lt = re.search(r"\b(?:Cod\.?\s*0?(\d{1,3}))", t)
    d["tipo"] = (m.group(1) or m.group(2) or m.group(3)) if m else None
    d["cod"] = lt.group(1) if lt else None
    cae = re.search(r"CAE[^0-9]{0,20}(\d{14})", t); d["cae"] = cae.group(1) if cae else None
    fe = re.findall(r"\b(\d{2}[/-]\d{2}[/-]\d{4})\b", t); d["fechas"] = fe[:6]
    d["consumidor_final"] = bool(re.search(r"consumidor\s+final", t, re.I))
    d["mercadopago"] = bool(re.search(r"mercado\s*pago", t, re.I))
    d["efectivo"] = bool(re.search(r"\befectivo\b|contado", t, re.I))
    rs = re.search(r"Raz[oó]n social:?\s*([^\n]{3,60})", t, re.I); d["razon_social_cliente"] = rs.group(1).strip() if rs else None
    dest = re.search(r"Datos del destinatario[\s\S]{0,200}?(\d{11})\s+([^\n]{3,60})", t)
    d["destinatario"] = (dest.group(1), dest.group(2).strip()) if dest else None
    pag = re.search(r"Datos del pagador[\s\S]{0,200}?(\d{11})\s+([^\n]{3,60})", t)
    d["pagador"] = (pag.group(1), pag.group(2).strip()) if pag else None
    mv = money(t); d["max_importe"] = max(mv) if mv else None
    d["ocr"] = "[OCR]" in t
    d["chars"] = len(t)
    return d

rows = []
for m in manifest:
    if not m.get("archivo"): rows.append(dict(m, parsed=None)); continue
    path = os.path.join(ROOT, m["mes"], m["archivo"])
    if not os.path.exists(path): rows.append(dict(m, parsed={"missing": True})); continue
    t = text_of(path)
    p = parse(t, m["src"])
    p["texto"] = t[:1500]
    rows.append(dict(m, parsed=p))
json.dump(rows, open(SC + "receipts_parsed.json", "w"), ensure_ascii=False, indent=1)

# ---- Report
def val(s):
    return float(re.sub(r"[^\d.]", "", s.replace(",", ""))) if s else None
print("archivos:", sum(1 for r in rows if r.get("archivo")), "| sin texto:", sum(1 for r in rows if r.get("parsed") and r["parsed"].get("chars", 0) < 40))
print("\n== FACTURAS NO EMITIDAS AL CONSORCIO / CONSUMIDOR FINAL ==")
for r in rows:
    p = r.get("parsed")
    if not p or p.get("missing"): continue
    isfact = re.search(r"\bFC\b|Factura|F C", r["nombre"], re.I) and not re.search(r"pago|recibo|pag\b|vep", r["nombre"], re.I)
    if isfact and (p["consumidor_final"] or (p["chars"] > 200 and not p["a_nombre_consorcio"])):
        print(f"- {r['mes'][:7]} {r['fecha']} {r['proveedor'][:30]:30} {r['valor']:>16} | {r['nombre'][:40]} | consumidor final={p['consumidor_final']} cliente={p['razon_social_cliente']} cuits={p['cuits'][:4]}")
print("\n== TRANSFERENCIAS: DESTINATARIO ==")
for r in rows:
    p = r.get("parsed")
    if p and p.get("destinatario"):
        print(f"- {r['mes'][:7]} {r['fecha']} {r['proveedor'][:30]:30} {r['valor']:>16} -> {p['destinatario'][0]} {p['destinatario'][1][:40]}")
print("\n== SIN ADJUNTOS ==")
for r in rows:
    if r["nombre"] == "(sin adjuntos)": print(f"- {r['mes'][:7]} {r['fecha']} {r['proveedor'][:35]:35} {r['valor']:>16} {r.get('desc','')[:50]}")
print("\n== SOLO PAGO SIN FACTURA / SOLO FACTURA SIN PAGO ==")
grp = defaultdict(list)
for r in rows:
    if r.get("archivo"): grp[(r["mes"], r["n"])].append(r)
for k, items in sorted(grp.items()):
    names = " | ".join(i["nombre"] for i in items)
    has_pago = bool(re.search(r"pago|pag\b|recibo|vep", names, re.I)); has_fact = bool(re.search(r"\bFC\b|F C|factura|\.pdf|_", names, re.I))
    if not has_pago or not has_fact:
        i = items[0]; print(f"- {i['mes'][:7]} {i['fecha']} {i['proveedor'][:30]:30} {i['valor']:>16} | {'sin comprobante de pago' if not has_pago else 'sin factura'} | {names[:80]}")
