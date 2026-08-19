"""Add messages.media_asset_id for inbound/outbound media linkage.

Revision ID: g7b8c9d0e1f2
Revises: f6a7b8c9d0e1
Create Date: 2026-08-20
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID


revision: str = "g7b8c9d0e1f2"
down_revision: Union[str, None] = "f6a7b8c9d0e1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "messages",
        sa.Column("media_asset_id", UUID(as_uuid=True), nullable=True),
    )
    op.create_foreign_key(
        "fk_messages_media_asset_id",
        "messages",
        "media_assets",
        ["media_asset_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint("fk_messages_media_asset_id", "messages", type_="foreignkey")
    op.drop_column("messages", "media_asset_id")
