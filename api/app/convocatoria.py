"""Convocatoria → propuesta de mociones. Extracción multi-formato + normalización del JSON del LLM.
El LLM solo PROPONE; el moderador revisa. No toca el motor de análisis."""
import base64
import html
import os
import re
import subprocess
import tempfile
import zipfile

from .config import settings

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


_TOOL = {
    "name": "registrar_convocatoria",
    "description": "Devuelve el orden del día y las mociones votables extraídas de la convocatoria.",
    "input_schema": {
        "type": "object",
        "properties": {
            "metadatos": {"type": "object", "description": "fecha, hora, lugar, administracion, art2060 si aparecen"},
            "agenda": {"type": "array", "items": {"type": "object", "properties": {
                "n": {"type": "integer"}, "titulo": {"type": "string"},
                "tipo": {"type": "string", "enum": ["procedimental", "informativo", "deliberativo"]}}}},
            "mociones": {"type": "array", "items": {"type": "object", "properties": {
                "titulo": {"type": "string", "description": "moción afirmativa y concreta para votar"}}}},
        },
        "required": ["agenda", "mociones"],
    },
}
_PROMPT = ("Sos asistente de una asamblea de consorcio. De esta convocatoria, extraé el orden del día "
           "(clasificando cada punto como procedimental, informativo o deliberativo) y, por cada punto "
           "deliberativo, una moción afirmativa y concreta para votar. Devolvé todo con la herramienta "
           "registrar_convocatoria. No inventes puntos que no estén.")


def _cliente():
    import anthropic
    return anthropic.Anthropic(api_key=settings.anthropic_api_key)


def _contenido(data: bytes, nombre: str):
    ext = os.path.splitext(nombre)[1].lower()
    if ext == ".pdf":
        b64 = base64.standard_b64encode(data).decode()
        return [{"type": "document", "source": {"type": "base64", "media_type": "application/pdf", "data": b64}},
                {"type": "text", "text": _PROMPT}]
    texto = texto_de_docx(data) if ext == ".docx" else texto_de_doc(data) if ext == ".doc" else texto_de_pdf(data)
    return [{"type": "text", "text": _PROMPT + "\n\n--- CONVOCATORIA ---\n" + texto}]


def proponer_mociones(data: bytes, nombre: str) -> dict:
    msg = _cliente().messages.create(
        model=settings.anthropic_modelo, max_tokens=2000,
        tools=[_TOOL], tool_choice={"type": "tool", "name": "registrar_convocatoria"},
        messages=[{"role": "user", "content": _contenido(data, nombre)}])
    for bloque in msg.content:
        if getattr(bloque, "type", None) == "tool_use":
            return normalizar_propuesta(bloque.input)
    raise ValueError("el modelo no devolvió la herramienta esperada")


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
