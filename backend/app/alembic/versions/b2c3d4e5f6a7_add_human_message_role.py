"""add 'human' value to messagerole enum (Feature 14 — human takeover)

Manual replies sent by a human operator during takeover are stored with
role='human' so the inbox can distinguish them from AI ('agent') messages.

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-08-08

"""
from typing import Sequence, Union

from alembic import op

revision: str = "b2c3d4e5f6a7"
down_revision: Union[str, Sequence[str], None] = "a1b2c3d4e5f6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # SQLAlchemy stores the enum *name* (USER/AGENT), so the label is 'HUMAN'.
    # Postgres 12+ allows ADD VALUE inside a transaction. Idempotent via IF NOT EXISTS.
    op.execute("ALTER TYPE messagerole ADD VALUE IF NOT EXISTS 'HUMAN'")


def downgrade() -> None:
    # Postgres cannot drop a single enum value without recreating the type; the
    # 'HUMAN' value is harmless if left in place, so downgrade is a no-op.
    pass
