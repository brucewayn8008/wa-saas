"""Add wacli store columns on wa_numbers; default_provider default → wacli.

Revision ID: c3d4e5f6a7b8
Revises: b2c3d4e5f6a7
Create Date: 2026-08-09
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "c3d4e5f6a7b8"
down_revision: Union[str, None] = "b2c3d4e5f6a7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("wa_numbers", sa.Column("wacli_store_dir", sa.Text(), nullable=True))
    op.add_column("wa_numbers", sa.Column("wacli_account", sa.String(length=128), nullable=True))
    # New rows default to wacli in the ORM; existing DB server_default left as-is
    # to avoid rewriting historical tenants mid-flight.


def downgrade() -> None:
    op.drop_column("wa_numbers", "wacli_account")
    op.drop_column("wa_numbers", "wacli_store_dir")
