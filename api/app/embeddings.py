"""Cliente de embeddings OpenAI-compatible, con urllib puro (sin SDK). Sin key queda
deshabilitado y todo devuelve None: la ingesta y la búsqueda degradan, nunca explotan."""
import json
import logging
import urllib.request

from .config import settings

logger = logging.getLogger(__name__)

MAX_CARACTERES = 8000   # tope de texto por documento; sobra para una factura
TIMEOUT_SEGUNDOS = 30


def habilitado() -> bool:
    return bool(settings.embeddings_api_key)


def embeber(textos: list[str]) -> list[list[float]] | None:
    """Embeddings de `textos` en una sola llamada (batch), cada uno truncado a 8000
    caracteres. None si está deshabilitado (sin key) o si la llamada falla, con log:
    quien llama decide qué hacer sin el vector (la ingesta jamás se rompe por esto)."""
    if not habilitado():
        return None
    if not textos:
        return []
    cuerpo = json.dumps({"model": settings.embeddings_modelo,
                         "input": [t[:MAX_CARACTERES] for t in textos]}).encode()
    req = urllib.request.Request(
        settings.embeddings_url.rstrip("/") + "/embeddings", data=cuerpo,
        headers={"Content-Type": "application/json",
                 "Authorization": f"Bearer {settings.embeddings_api_key}"})
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT_SEGUNDOS) as resp:
            data = json.load(resp)
        # la API garantiza `index` por ítem; el orden del array no está garantizado
        vectores = [fila["embedding"] for fila in sorted(data["data"], key=lambda f: f["index"])]
        if len(vectores) != len(textos):
            raise ValueError(f"la API devolvió {len(vectores)} embeddings para {len(textos)} textos")
        return vectores
    except Exception:
        logger.warning("Falló la llamada a la API de embeddings (%s); se sigue sin vectores",
                       settings.embeddings_url, exc_info=True)
        return None
