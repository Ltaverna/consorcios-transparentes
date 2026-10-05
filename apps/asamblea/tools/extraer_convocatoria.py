#!/usr/bin/env python3
"""Extrae el texto de una convocatoria de asamblea en .pdf, .doc o .docx.

Normaliza cualquiera de los tres formatos a texto plano, eligiendo la herramienta por extensión:
  .pdf  -> pdftotext -layout (poppler); fallback a pypdf si no está
  .docx -> zipfile + XML (stdlib, sin dependencias)
  .doc  -> libreoffice --headless --convert-to txt

Uso:
    python extraer_convocatoria.py "ruta/Convocatoria.pdf"        # imprime el texto
Sirve para el flujo asistido (pasar el texto a un LLM que arma las mociones) y como base de la
futura función self-service de la app. No depende de red.
"""
import html
import os
import re
import subprocess
import sys
import tempfile
import zipfile


def de_pdf(ruta: str) -> str:
    try:
        r = subprocess.run(["pdftotext", "-layout", ruta, "-"],
                           capture_output=True, text=True, timeout=120)
        if r.returncode == 0 and r.stdout.strip():
            return r.stdout
    except FileNotFoundError:
        pass
    try:  # fallback sin poppler
        import pypdf
        return "\n".join((p.extract_text() or "") for p in pypdf.PdfReader(ruta).pages)
    except Exception as e:
        raise SystemExit(f"no pude leer el PDF ({e}); instalá poppler-utils (pdftotext) o pypdf")


def de_docx(ruta: str) -> str:
    with zipfile.ZipFile(ruta) as z:
        xml = z.read("word/document.xml").decode("utf-8", "ignore")
    xml = re.sub(r"</w:p>", "\n", xml)
    xml = re.sub(r"<w:tab[^>]*/>", "\t", xml)
    return html.unescape(re.sub(r"<[^>]+>", "", xml))


def de_doc(ruta: str) -> str:
    with tempfile.TemporaryDirectory() as d:
        subprocess.run(["libreoffice", "--headless", "--convert-to", "txt:Text", "--outdir", d, ruta],
                       capture_output=True, timeout=180)
        base = os.path.splitext(os.path.basename(ruta))[0] + ".txt"
        salida = os.path.join(d, base)
        if not os.path.exists(salida):
            raise SystemExit("libreoffice no generó el .txt; ¿está instalado?")
        with open(salida, encoding="utf-8", errors="ignore") as f:
            return f.read()


def extraer(ruta: str) -> str:
    ext = os.path.splitext(ruta)[1].lower()
    if ext == ".pdf":
        return de_pdf(ruta)
    if ext == ".docx":
        return de_docx(ruta)
    if ext == ".doc":
        return de_doc(ruta)
    raise SystemExit(f"formato no soportado: {ext!r} (usá .pdf, .doc o .docx)")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("uso: python extraer_convocatoria.py <archivo .pdf|.doc|.docx>")
    print(extraer(sys.argv[1]))
