"""Configuración por variables de entorno (prefijo CT_)."""
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "sqlite://"          # en memoria si no se configura
    jwt_secret: str = "solo-para-desarrollo"
    jwt_horas: int = 12
    cookie_segura: bool = False              # True en producción (HTTPS)
    r2_endpoint: str = ""
    r2_access_key: str = ""
    r2_secret_key: str = ""
    r2_bucket: str = "consorcio-transparente"
    storage_dir: str = ""                    # si está seteado, disco local en vez de R2
    cors_origin: str = "http://localhost:3000"

    model_config = {"env_prefix": "CT_", "env_file": ".env"}


settings = Settings()
