"""embedding en documentos (pgvector)

Columna `embedding` nullable en `documentos` para la búsqueda semántica.
El tipo depende del dialecto (mismo criterio que VectorDual en app.models):
en Postgres `vector(1536)` de pgvector (y la extensión, que la imagen
pgvector/pgvector:pg16 trae disponible); en SQLite, JSON. NULL = documento
sin embedding (imagen/escaneo, embeddings deshabilitados o falla de la API).

Revision ID: a413127a14eb
Revises: 866ed55c8961
Create Date: 2026-09-06 12:14:29.270254

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from pgvector.sqlalchemy import Vector

# revision identifiers, used by Alembic.
revision: str = 'a413127a14eb'
down_revision: Union[str, Sequence[str], None] = '866ed55c8961'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    if op.get_bind().dialect.name == "postgresql":
        op.execute("CREATE EXTENSION IF NOT EXISTS vector")
        op.add_column("documentos", sa.Column("embedding", Vector(1536), nullable=True))
    else:
        op.add_column("documentos", sa.Column("embedding", sa.JSON(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("documentos", "embedding")
    # La extensión no se dropea: puede estar en uso por otra cosa y es inocua.
