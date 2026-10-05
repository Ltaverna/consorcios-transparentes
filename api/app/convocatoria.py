"""Convocatoria → propuesta de mociones. Extracción multi-formato + normalización del JSON del LLM.
El LLM solo PROPONE; el moderador revisa. No toca el motor de análisis."""
import html
import os
import re
import subprocess
import tempfile
import zipfile

OPCIONES_DEF = ["A favor", "En contra", "Abstención"]
REGLAS = {"abs", "pres", "2/3"}


def texto_de_docx(data: bytes) -> str:
    with tempfile.NamedTemporaryFile(suffix=".docx", delete=False) as f:
        f.write(data); ruta = f.name
    try:
        with zipfile.ZipFile(ruta) as z:
            xml = z.read("word/document.xml").decode("utf-8", "ignore")
        xml = re.sub(r"</w:p>", "\n", xml)
        xml = re.sub(r"<w:tab[^>]*/>", "\t", xml)
        return html.unescape(re.sub(r"<[^>]+>", "", xml))
    finally:
        os.unlink(ruta)


def texto_de_doc(data: bytes) -> str:
    with tempfile.TemporaryDirectory() as d:
        ruta = os.path.join(d, "conv.doc")
        with open(ruta, "wb") as f:
            f.write(data)
        subprocess.run(["libreoffice", "--headless", "--convert-to", "txt:Text", "--outdir", d, ruta],
                       capture_output=True, timeout=180)
        salida = os.path.join(d, "conv.txt")
        if not os.path.exists(salida):
            raise ValueError("no se pudo convertir el .doc (¿LibreOffice instalado?)")
        with open(salida, encoding="utf-8", errors="ignore") as f:
            return f.read()


def texto_de_pdf(data: bytes) -> str:
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
        f.write(data); ruta = f.name
    try:
        r = subprocess.run(["pdftotext", "-layout", ruta, "-"], capture_output=True, text=True, timeout=120)
        return r.stdout
    finally:
        os.unlink(ruta)


def normalizar_propuesta(crudo: dict) -> dict:
    """Valida y completa el JSON del LLM: defaults de opciones/regla, descarta mociones sin título."""
    crudo = crudo or {}
    mociones = []
    for m in (crudo.get("mociones") or []):
        titulo = (m.get("titulo") or "").strip()
        if not titulo:
            continue
        regla = m.get("regla") if m.get("regla") in REGLAS else "abs"
        opciones = m.get("opciones") if isinstance(m.get("opciones"), list) and m.get("opciones") else OPCIONES_DEF
        mociones.append({"titulo": titulo, "opciones": opciones, "regla": regla})
    agenda = [{"n": a.get("n"), "titulo": (a.get("titulo") or "").strip(), "tipo": a.get("tipo") or ""}
              for a in (crudo.get("agenda") or []) if (a.get("titulo") or "").strip()]
    return {"metadatos": crudo.get("metadatos") or {}, "agenda": agenda, "mociones": mociones}
