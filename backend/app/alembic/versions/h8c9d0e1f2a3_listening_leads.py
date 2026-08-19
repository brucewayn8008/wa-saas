"""Create listening_leads table + RLS (Feature 16).

Revision ID: h8c9d0e1f2a3
Revises: g7b8c9d0e1f2
Create Date: 2026-08-20
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID


revision: str = "h8c9d0e1f2a3"
down_revision: Union[str, None] = "g7b8c9d0e1f2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "listening_leads",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "workspace_id",
            UUID(as_uuid=True),
            sa.ForeignKey("workspaces.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "lead_id",
            UUID(as_uuid=True),
            sa.ForeignKey("leads.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("group_jid", sa.String(255), nullable=False),
        sa.Column("group_name", sa.String(255), nullable=False),
        sa.Column("sender_jid", sa.String(255), nullable=False),
        sa.Column("original_message", sa.Text(), nullable=False),
        sa.Column("match_reason", sa.String(30), nullable=False),
        sa.Column("match_score", sa.Integer(), nullable=True),
        sa.Column("reply_text", sa.Text(), nullable=True),
        sa.Column("status", sa.String(30), nullable=False, server_default="detected"),
        sa.Column("block_reason", sa.String(100), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("dismissed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_listening_leads_workspace_id", "listening_leads", ["workspace_id"])
    op.create_index("ix_listening_leads_lead_id", "listening_leads", ["lead_id"])
    op.create_index("ix_listening_leads_status", "listening_leads", ["status"])

    # RLS — same pattern as Feature 02 tenant tables (harmless if role is superuser).
    op.execute("ALTER TABLE listening_leads ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE listening_leads FORCE ROW LEVEL SECURITY")
    op.execute(
        "CREATE POLICY tenant_isolation ON listening_leads "
        "USING (workspace_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid) "
        "WITH CHECK (workspace_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid)"
    )


def downgrade() -> None:
    op.execute("DROP POLICY IF EXISTS tenant_isolation ON listening_leads")
    op.execute("ALTER TABLE listening_leads NO FORCE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE listening_leads DISABLE ROW LEVEL SECURITY")
    op.drop_index("ix_listening_leads_status", table_name="listening_leads")
    op.drop_index("ix_listening_leads_lead_id", table_name="listening_leads")
    op.drop_index("ix_listening_leads_workspace_id", table_name="listening_leads")
    op.drop_table("listening_leads")
