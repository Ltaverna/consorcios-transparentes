"""Configuración por variables de entorno (prefijo CT_)."""
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "sqlite://"          # en memoria si no se configura
    jwt_secret: str = "solo-para-desarrollo"
    jwt_horas: int = 12
    cookie_segura: bool = False              # True en producción (HTTPS)
    cookie_dominio: str = ""                 # vacío = cookie host-only (dev); en prod, dominio compartido
    r2_endpoint: str = ""
    r2_access_key: str = ""
    r2_secret_key: str = ""
    r2_bucket: str = "consorcio-transparente"
    storage_dir: str = ""                    # si está seteado, disco local en vez de R2
    cors_origin: str = "http://localhost:3000"
    max_liq_mb: int = 30                     # tope de subida de una liquidación (PDF o texto)
    max_zip_mb: int = 100                    # tope de subida del ZIP de comprobantes
    confiar_proxy: bool = False              # True detrás de cloudflared: usa CF-Connecting-IP para el rate limit

    model_config = {"env_prefix": "CT_", "env_file": ".env"}


settings = Settings()
