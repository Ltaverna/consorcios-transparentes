"""Documentos privados: R2 en producción (URL firmada), disco local en dev y tests."""
import logging
import pathlib

from .config import settings

logger = logging.getLogger(__name__)

MIME = {"html": "text/html", "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "pdf": "application/pdf", "jpg": "image/jpeg", "jpeg": "image/jpeg", "png": "image/png"}


def mime_por_clave(key: str) -> str:
    return MIME.get(key.rsplit(".", 1)[-1].lower(), "application/octet-stream")


class LocalStorage:
    def __init__(self, base: str):
        self.base = pathlib.Path(base)

    def _ruta(self, key: str) -> pathlib.Path:
        p = (self.base / key).resolve()
        if not p.is_relative_to(self.base.resolve()):
            raise ValueError(f"clave fuera del directorio: {key}")
        return p

    def guardar(self, key: str, data: bytes) -> None:
        p = self._ruta(key)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(data)

    def leer(self, key: str) -> bytes:
        return self._ruta(key).read_bytes()

    def existe(self, key: str) -> bool:
        return self._ruta(key).exists()

    def borrar(self, key: str) -> None:
        try:
            self._ruta(key).unlink(missing_ok=True)
        except Exception:
            logger.warning("No se pudo borrar %s del disco local", key, exc_info=True)

    def url_firmada(self, key: str, segundos: int = 900, descarga: bool = False) -> str | None:
        return None  # sin URL directa: la API sirve el archivo por streaming


class R2Storage:
    """Cloudflare R2 vía API S3. Sin tests unitarios: se prueba en el deploy (Plan 3)."""

    def __init__(self):
        import boto3
        self.bucket = settings.r2_bucket
        self.s3 = boto3.client(
            "s3", endpoint_url=settings.r2_endpoint,
            aws_access_key_id=settings.r2_access_key,
            aws_secret_access_key=settings.r2_secret_key,
            region_name="auto",
        )

    def guardar(self, key: str, data: bytes) -> None:
        self.s3.put_object(Bucket=self.bucket, Key=key, Body=data, ContentType=mime_por_clave(key))

    def leer(self, key: str) -> bytes:
        return self.s3.get_object(Bucket=self.bucket, Key=key)["Body"].read()

    def existe(self, key: str) -> bool:
        try:
            self.s3.head_object(Bucket=self.bucket, Key=key)
            return True
        except Exception:
            return False

    def borrar(self, key: str) -> None:
        try:
            self.s3.delete_object(Bucket=self.bucket, Key=key)
        except Exception:
            logger.warning("No se pudo borrar %s de R2", key, exc_info=True)

    def url_firmada(self, key: str, segundos: int = 900, descarga: bool = False) -> str | None:
        params = {"Bucket": self.bucket, "Key": key}
        if descarga:
            params["ResponseContentDisposition"] = "attachment"
        return self.s3.generate_presigned_url(
            "get_object", Params=params, ExpiresIn=segundos)


def storage_por_defecto():
    if settings.storage_dir:
        return LocalStorage(settings.storage_dir)
    if settings.r2_endpoint:
        return R2Storage()
    raise RuntimeError("Configurar CT_STORAGE_DIR (dev) o CT_R2_* (producción)")
