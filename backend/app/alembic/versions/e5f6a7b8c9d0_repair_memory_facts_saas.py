"""Repair memory_facts to SaaS schema (workspace_id + lead_id).

Local/dev DBs may still have the pre-SaaS table shaped around `contact_id`
(from the mark-2 / aisha lineage). `create_all` skips existing tables, so the
SaaS model never landed. Empty legacy tables are replaced; if lead_id already
exists this is a no-op.

Revision ID: e5f6a7b8c9d0
Revises: d4e5f6a7b8c9
Create Date: 2026-08-20
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID


revision: str = "e5f6a7b8c9d0"
down_revision: Union[str, None] = "d4e5f6a7b8c9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _columns(conn, table: str) -> set[str]:
    rows = conn.execute(
        sa.text(
            "SELECT column_name FROM information_schema.columns "
            "WHERE table_schema = 'public' AND table_name = :t"
        ),
        {"t": table},
    )
    return {r[0] for r in rows}


def upgrade() -> None:
    conn = op.get_bind()
    cols = _columns(conn, "memory_facts")
    if not cols:
        # Fresh create — mirror Feature 02 shape (embedding added best-effort).
        op.create_table(
            "memory_facts",
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
                sa.ForeignKey("leads.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column("category", sa.String(50), nullable=True),
            sa.Column("fact", sa.Text(), nullable=False),
            sa.Column("confidence", sa.Integer(), nullable=True),
            sa.Column("source", sa.String(30), nullable=False, server_default="stated"),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        )
    elif "lead_id" in cols and "workspace_id" in cols:
        return
    else:
        # Legacy contact-scoped table (or other drift) — replace.
        op.rename_table("memory_facts", "memory_facts_legacy_contacts")
        op.create_table(
            "memory_facts",
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
                sa.ForeignKey("leads.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column("category", sa.String(50), nullable=True),
            sa.Column("fact", sa.Text(), nullable=False),
            sa.Column("confidence", sa.Integer(), nullable=True),
            sa.Column("source", sa.String(30), nullable=False, server_default="stated"),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        )

    # Optional pgvector embedding — fall back to plain text column so the ORM
    # model (which maps embedding even without pgvector) can INSERT NULLs.
    conn.execute(sa.text("SAVEPOINT sp_mf_embed"))
    try:
        conn.execute(sa.text("ALTER TABLE memory_facts ADD COLUMN IF NOT EXISTS embedding vector(768)"))
        conn.execute(sa.text("RELEASE SAVEPOINT sp_mf_embed"))
    except Exception:
        conn.execute(sa.text("ROLLBACK TO SAVEPOINT sp_mf_embed"))
        conn.execute(sa.text("ALTER TABLE memory_facts ADD COLUMN IF NOT EXISTS embedding text"))

    # RLS policy (same pattern as other tenant tables) — no-op if role/policies absent.
    conn.execute(sa.text("SAVEPOINT sp_mf_rls"))
    try:
        conn.execute(sa.text("ALTER TABLE memory_facts ENABLE ROW LEVEL SECURITY"))
        conn.execute(
            sa.text(
                """
                DO $$
                BEGIN
                  IF NOT EXISTS (
                    SELECT 1 FROM pg_policies
                    WHERE tablename = 'memory_facts' AND policyname = 'tenant_isolation'
                  ) THEN
                    CREATE POLICY tenant_isolation ON memory_facts
                      USING (workspace_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid);
                  END IF;
                END $$;
                """
            )
        )
        conn.execute(sa.text("RELEASE SAVEPOINT sp_mf_rls"))
    except Exception:
        conn.execute(sa.text("ROLLBACK TO SAVEPOINT sp_mf_rls"))


def downgrade() -> None:
    conn = op.get_bind()
    cols = _columns(conn, "memory_facts_legacy_contacts")
    if cols:
        op.drop_table("memory_facts")
        op.rename_table("memory_facts_legacy_contacts", "memory_facts")
