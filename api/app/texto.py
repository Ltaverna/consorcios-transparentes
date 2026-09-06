"""Extracción de texto plano de los documentos (comprobantes). Módulo neutral: lo usan
el router de documentos, la consulta y la ingesta (embeddings) sin depender entre sí."""
import re
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


# --- fragmento_relevante: heurística calibrada con las facturas reales del consorcio ---
#
# Dónde empieza el detalle del ítem (encabezado de la tabla, una línea):
# - Facturas B/C emitidas por el sitio de ARCA (monotributistas, Laufken, etc.):
#   "Código  Producto / Servicio  Cantidad  U. Medida  Precio Unit. ..." — el OCR de
#   algunos PDFs convierte la "/" en "I" o "|".
# - Sistemas de facturación propios: "CANT.  DETALLE ... PR.UNIT.  TOTAL" (gestionpro)
#   o "DESCRIPCION ... IMPORTE" / "Código  Descripción  Cantidad  P.Unitario  Importe".
_DETALLE_RE = re.compile(
    r"Producto\s*[/I|]\s*Servicio"
    r"|CANT\.?\s+DETALLE"
    r"|DESCRIPCI[OÓ]N\b(?=.*(?:IMPORTE|P\.?\s*UNIT|CANTIDAD))",
    re.IGNORECASE)

# Dónde termina: bloque de totales o pie legal.
_FIN_DETALLE_RE = re.compile(
    r"Subtotal\s*[:$\d]|Importe\s+(?:Total|Otros\s+Tributos)|TOTAL\s+(?:A\s+PAGAR|ARS)"
    r"|Son\s+pesos|R[eé]gimen\s+de\s+Transparencia|IVA\s+Contenido",
    re.IGNORECASE)

# Líneas de boilerplate del encabezado/pie vistas en las facturas reales (ORIGINAL,
# tipo de comprobante, datos fiscales del emisor y del consorcio, CAE, contacto).
_BOILERPLATE_RE = re.compile(
    r"^\s*(?:ORIGINAL|DUPLICADO|TRIPLICADO)\s*$"
    r"|FACTURA|RECIBO|LIQUIDACI[OÓ]N\s+DE\s+SERVICIOS|NOTA\s+DE\s+(?:CR[EÉ]DITO|D[EÉ]BITO)"
    r"|\bCOD\.?\s*:?\s*\d|C[óo]digo\s+\d"
    r"|Punto\s+de\s+Venta|Comp\.?\s*Nro"
    r"|Raz[óo]n\s+Social|Domicilio|Apellido\s+y\s+Nombre"
    r"|Condici[óo]n|CONDICION"
    r"|CUIT|C\.U\.I\.T"
    r"|Ing(?:resos?)?\.?\s*Brut|Ag\.?\s*Percep"
    r"|Fecha\s+de|Per[íi]odo\s+Facturado|Vencimiento|Inicio\s+(?:de\s+)?Actividades"
    r"|^\s*Actividades\s*:"
    r"|\bIVA\b|Monotributo|Consumidor\s+Final|Responsable\s+Inscripto"
    r"|Sres\.?\s*:|Se[ñn]ores|CLIENTE\s*:?"
    r"|\bCAE\b|C\.A\.E\.|Comprobante\s+Autorizado|P[áa]g\.\s*\d"
    r"|www\.|@|Tel\.?\s*[:\d]|generado\s+con\s+sistema"
    r"|R[eé]gimen\s+de\s+Transparencia|Son\s+pesos|Franqueo",
    re.IGNORECASE)

# Residuos del encabezado de la tabla cuando el layout lo parte en varias líneas
# (columnas sueltas, líneas de solo números/puntuación).
_RESIDUO_RE = re.compile(
    r"U\.?\s*Medida|Precio\s+Un|Bon[li]?f|^\s*\d*\s*Subtotal\s*$"
    r"|^[\d\s.,:;|!l$%()'-]+$|^\s*[A-Z]{1,2}-[\d-]+\s*$",
    re.IGNORECASE)


def _compactar(lineas, n: int) -> str:
    """Colapsa espacios múltiples y líneas vacías para que el fragmento sea legible."""
    plano = "\n".join(re.sub(r"\s+", " ", l).strip() for l in lineas if l.strip())
    return plano[:n]


def fragmento_relevante(texto: str, n: int = 300) -> str:
    """Fragmento legible de un comprobante para los resultados de búsqueda: intenta
    empezar en el detalle del ítem (qué se facturó) en vez del boilerplate del
    encabezado. Cascada: tabla de detalle → líneas sin boilerplate → primeros n
    caracteres (nunca vacío si el texto no lo es)."""
    lineas = (texto or "").splitlines()

    # 1) tabla de detalle explícita: de la línea siguiente al encabezado hasta los totales
    for i, linea in enumerate(lineas):
        if _DETALLE_RE.search(linea):
            cuerpo = [l for l in _hasta_totales(lineas[i + 1:])
                      if l.strip() and not _BOILERPLATE_RE.search(l)
                      and not _RESIDUO_RE.search(l)]
            if cuerpo:
                return _compactar(cuerpo, n)
            break

    # 2) sin marcadores: saltear el boilerplate conocido, tomar las primeras sustantivas
    sustantivas = [l for l in lineas
                   if l.strip() and not _BOILERPLATE_RE.search(l) and not _RESIDUO_RE.search(l)]
    if sustantivas:
        return _compactar(sustantivas, n)

    # 3) último recurso: los primeros n caracteres, como antes (pero compactados)
    return _compactar(lineas, n)


def _hasta_totales(lineas):
    for l in lineas:
        if _FIN_DETALLE_RE.search(l):
            return
        yield l
