"""QR de ARCA (ex AFIP) de las facturas electrónicas: datos autoritativos sin OCR.

Toda factura electrónica lleva un QR obligatorio con la URL
`https://www.afip.gob.ar/fe/qr/?p=<base64 de un JSON>` (ver, fecha, cuit, ptoVta, tipoCmp,
nroCmp, importe, moneda, tipoDocRec, nroDocRec, codAut...). Leerlo da CUIT emisor, numeración,
fecha, importe y CUIT receptor con autoridad de ARCA.

Dependencia OPCIONAL (patrón embeddings): `pyzbar` + `Pillow` se importan de forma perezosa;
sin ellos (o sin `libzbar` en el sistema) `leer_qr` devuelve None y el motor sigue como hoy.
`pdftoppm` (poppler, ya requerido) renderiza la primera página de los PDF.
"""
from __future__ import annotations
import base64
import glob
import json
import os
import re
import subprocess
import tempfile
from typing import Optional
from urllib.parse import parse_qs, urlsplit


def _b64_json(p: str) -> Optional[dict]:
    p = p.strip()
    if len(p) % 4:
        p += "=" * (-len(p) % 4)
    for decode in (base64.urlsafe_b64decode, base64.b64decode):
        try:
            data = json.loads(decode(p.encode()))
            return data if isinstance(data, dict) else None
        except Exception:
            continue
    return None


def _fecha_iso(f) -> Optional[str]:
    """ARCA emite '2026-03-25' pero hay generadores que ponen '20260325'."""
    if not isinstance(f, str):
        return None
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", f):
        return f
    if re.fullmatch(r"\d{8}", f):
        return f"{f[:4]}-{f[4:6]}-{f[6:]}"
    return None


def _entero(v) -> Optional[int]:
    try:
        return int(v)
    except (TypeError, ValueError):
        return None


def decodificar_payload(url: str) -> Optional[dict]:
    """URL del QR de ARCA -> dict normalizado, o None si no es un QR de ARCA o el JSON no
    se puede leer. Campos ausentes quedan en None; nunca lanza excepción."""
    try:
        parts = urlsplit(url)
        host = (parts.hostname or "").lower()
        if not (host == "afip.gob.ar" or host.endswith(".afip.gob.ar")):
            return None
        if "/fe/qr" not in parts.path.lower():
            return None
        p = parse_qs(parts.query).get("p", [None])[0]
        if not p:
            return None
        data = _b64_json(p)
        if data is None:
            return None
        cuit = _entero(data.get("cuit"))
        receptor = _entero(data.get("nroDocRec")) if _entero(data.get("tipoDocRec")) == 80 else None
        importe = data.get("importe")
        cae = data.get("codAut")
        return {
            "cuit_emisor": str(cuit) if cuit else None,
            "tipo_cmp": _entero(data.get("tipoCmp")),
            "pto_vta": _entero(data.get("ptoVta")),
            "nro_cmp": _entero(data.get("nroCmp")),
            "fecha": _fecha_iso(data.get("fecha")),
            "importe": float(importe) if isinstance(importe, (int, float)) else None,
            "moneda": data.get("moneda") if isinstance(data.get("moneda"), str) else None,
            "cuit_receptor": str(receptor) if receptor else None,
            "cae": str(cae) if cae is not None else None,
        }
    except Exception:
        return None


def _decodificar_imagen(img) -> Optional[dict]:
    from pyzbar import pyzbar
    for code in pyzbar.decode(img):
        try:
            q = decodificar_payload(code.data.decode("utf-8", errors="replace"))
        except Exception:
            q = None
        if q:
            return q
    return None


def leer_qr(path: str) -> Optional[dict]:
    """Busca el QR de ARCA en un PDF (primera página, vía pdftoppm) o en una imagen.
    Sin pyzbar/Pillow/libzbar, o ante cualquier error, devuelve None."""
    try:
        from pyzbar import pyzbar  # noqa: F401  (verifica libzbar disponible)
        from PIL import Image
    except Exception:
        return None
    try:
        if path.lower().endswith(".pdf"):
            with tempfile.TemporaryDirectory() as td:
                base = os.path.join(td, "pagina")
                subprocess.run(["pdftoppm", "-r", "200", "-f", "1", "-l", "1", "-png", path, base],
                               capture_output=True, timeout=20)
                pngs = sorted(glob.glob(base + "*.png"))
                if not pngs:
                    return None
                with Image.open(pngs[0]) as img:
                    return _decodificar_imagen(img)
        with Image.open(path) as img:
            return _decodificar_imagen(img)
    except Exception:
        return None
