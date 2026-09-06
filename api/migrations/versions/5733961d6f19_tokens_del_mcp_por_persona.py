"""tokens del MCP por persona

Tabla `mcp_tokens`: un token de acceso al MCP por persona, revocable
individualmente (`activo=false`). Se guarda solo el sha256 en hex, indexado:
el token es de alta entropía, alcanza para lookup directo. `creado` se emite
como sa.DateTime(timezone=True), el tipo real de FechaUTC (mismo criterio que
el esquema inicial). Tabla simple: no necesita guard por dialecto.

Revision ID: 5733961d6f19
Revises: a413127a14eb
Create Date: 2026-09-06 14:07:40.309836

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '5733961d6f19'
down_revision: Union[str, Sequence[str], None] = 'a413127a14eb'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table('mcp_tokens',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('nombre', sa.String(length=120), nullable=False),
    sa.Column('token_sha256', sa.String(length=64), nullable=False),
    sa.Column('activo', sa.Boolean(), nullable=False),
    sa.Column('creado', sa.DateTime(timezone=True), nullable=False),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('nombre')
    )
    op.create_index(op.f('ix_mcp_tokens_token_sha256'), 'mcp_tokens', ['token_sha256'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_mcp_tokens_token_sha256'), table_name='mcp_tokens')
    op.drop_table('mcp_tokens')
