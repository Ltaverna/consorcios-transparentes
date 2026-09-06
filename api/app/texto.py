"""Extracción de texto plano de los documentos (comprobantes). Módulo neutral: lo usan
el router de documentos, la consulta y la ingesta (embeddings) sin depender entre sí."""
import subprocess
import tempfile

from . import models

# hash del documento → texto extraído. El contenido detrás de un hash es inmutable, así que
# la cache no expira; vive lo que viva el proceso. La usan /documentos/{id}/texto,
# /consulta/comprobantes y el paso de embeddings de la ingesta.
_CACHE_TEXTO: dict[str, str] = {}


def extraer_texto(storage, d: models.Documento) -> str:
    """Texto plano de un documento vía `pdftotext -layout` (poppler). Devuelve "" para todo
    lo que no sea un PDF con capa de texto (imágenes, escaneos, archivos rotos): sin OCR en
    esta etapa, y nunca un error."""
    if d.hash and d.hash in _CACHE_TEXTO:
        return _CACHE_TEXTO[d.hash]
    texto = ""
    try:
        raw = storage.leer(d.archivo_key)
    except OSError:
        raw = b""
    if raw[:5] == b"%PDF-":
        with tempfile.NamedTemporaryFile(suffix=".pdf") as f:
            f.write(raw)
            f.flush()
            try:
                out = subprocess.run(["pdftotext", "-layout", f.name, "-"],
                                     capture_output=True, timeout=10)
                texto = out.stdout.decode("utf-8", "ignore")[:100_000].strip()
            except (subprocess.TimeoutExpired, OSError):
                texto = ""
    if d.hash:
        _CACHE_TEXTO[d.hash] = texto
    return texto
