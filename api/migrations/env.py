"""Entorno de Alembic: toma la URL de la config de la app (CT_DATABASE_URL)."""
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

from app.config import settings
from app.db import Base
from app import models  # noqa: F401  # registra las tablas en Base.metadata

# Objeto Config de Alembic (valores del alembic.ini).
config = context.config

# Guardia: si nadie exportó CT_DATABASE_URL, settings.database_url queda en el
# default "sqlite://" (en memoria).  Correr alembic ahí sería un no-op silencioso
# porque la base desaparece al terminar el proceso.
if settings.database_url == "sqlite://":
    raise SystemExit(
        "CT_DATABASE_URL no está seteada: alembic migraría una base en memoria. "
        "Exportala o usá el .env del contenedor."
    )

# La URL sale de la app, no del .ini: misma fuente de verdad que el arranque.
# El "%" se escapa a "%%" para que configparser no interprete los %-encodings
# de la password como directivas de interpolación (InterpolationSyntaxError).
config.set_main_option("sqlalchemy.url", settings.database_url.replace("%", "%%"))

# Logging del .ini.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Metadata de los modelos, para el autogenerate.
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Modo offline: emite el SQL sin conectarse a la base."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Modo online: se conecta y corre las migraciones (SQLite o Postgres)."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
