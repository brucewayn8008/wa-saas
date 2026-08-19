"""Ensure memory_facts.embedding exists without requiring pgvector.

Revision ID: f6a7b8c9d0e1
Revises: e5f6a7b8c9d0
Create Date: 2026-08-20
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "f6a7b8c9d0e1"
down_revision: Union[str, None] = "e5f6a7b8c9d0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    conn.execute(sa.text("SAVEPOINT sp_embed_vec"))
    try:
        conn.execute(sa.text("ALTER TABLE memory_facts ADD COLUMN IF NOT EXISTS embedding vector(768)"))
        conn.execute(sa.text("RELEASE SAVEPOINT sp_embed_vec"))
    except Exception:
        conn.execute(sa.text("ROLLBACK TO SAVEPOINT sp_embed_vec"))
        conn.execute(sa.text("ALTER TABLE memory_facts ADD COLUMN IF NOT EXISTS embedding text"))


def downgrade() -> None:
    # Leave embedding in place — dropping could destroy vector data.
    pass
