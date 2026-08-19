"""SaaS multi-tenancy: tenant columns, new tables, pgvector, and RLS policies (Feature 02)

Revision ID: a1b2c3d4e5f6
Revises: 6e8e338c61d9
Create Date: 2026-08-06

What this does:
  * Adds Clerk-org + disclosure + default_provider columns to `workspaces` (the tenant).
  * Creates the SaaS tables: tenant_members, wa_numbers, conversations, memory_facts,
    media_assets, message_templates, consent, subscriptions, usage.
  * Enables pgvector and adds memory_facts.embedding vector(768) + HNSW index.
  * Enables + FORCES Row-Level Security on every tenant-scoped table with a
    tenant_isolation policy keyed on current_setting('app.tenant_id').

IMPORTANT: RLS is IGNORED for superusers and roles with BYPASSRLS. The app MUST
connect as a NON-superuser role for isolation to take effect. See
ops/db/create_app_role.sql and set POSTGRES_USER accordingly. `users` is left
un-RLS'd on purpose (cross-tenant auth table; scoped in the app layer).
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, Sequence[str], None] = "6e8e338c61d9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# (table, tenant_column) — every tenant-scoped DATA table gets an isolation policy.
# NOTE: `workspaces` and `tenant_members` are the identity/resolution layer and are
# deliberately NOT RLS-protected: auth must look up the tenant by `clerk_org_id`
# BEFORE it knows the workspace UUID to set `app.tenant_id`. They are guarded at the
# app layer (always resolved by exact id from the verified Clerk token). `users` is
# cross-tenant auth and also stays un-RLS'd.
RLS_TABLES = [
    ("leads", "workspace_id"),
    ("messages", "workspace_id"),
    ("target_groups", "workspace_id"),
    ("agent_activities", "workspace_id"),
    ("whatsapp_sessions", "workspace_id"),
    ("wa_numbers", "workspace_id"),
    ("conversations", "workspace_id"),
    ("memory_facts", "workspace_id"),
    ("media_assets", "workspace_id"),
    ("message_templates", "workspace_id"),
    ("consent", "workspace_id"),
    ("subscriptions", "workspace_id"),
    ("usage", "workspace_id"),
]

UUID = postgresql.UUID(as_uuid=True)


def _uuid_pk():
    return sa.Column("id", UUID, primary_key=True, server_default=sa.text("gen_random_uuid()"))


def _ws_fk(nullable=False, ondelete="CASCADE"):
    return sa.Column("workspace_id", UUID, sa.ForeignKey("workspaces.id", ondelete=ondelete), nullable=nullable)


def upgrade() -> None:
    # gen_random_uuid() needs pgcrypto; pgvector for embeddings (optional — skip if not installed).
    op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto")
    conn = op.get_bind()
    conn.execute(sa.text("SAVEPOINT sp_vector"))
    try:
        conn.execute(sa.text("CREATE EXTENSION IF NOT EXISTS vector"))
        conn.execute(sa.text("RELEASE SAVEPOINT sp_vector"))
    except Exception:
        conn.execute(sa.text("ROLLBACK TO SAVEPOINT sp_vector"))
        # pgvector not installed locally — memory embeddings disabled, everything else works

    # --- tenant columns on workspaces ---
    op.add_column("workspaces", sa.Column("clerk_org_id", sa.String(255), nullable=True))
    op.add_column("workspaces", sa.Column("disclosure_line", sa.Text(), nullable=True,
                                          server_default="You're chatting with an AI assistant."))
    op.add_column("workspaces", sa.Column("default_provider", sa.String(30), nullable=False,
                                          server_default="whatsmeow"))
    op.create_unique_constraint("uq_workspaces_clerk_org", "workspaces", ["clerk_org_id"])

    # --- new tables ---
    op.create_table(
        "tenant_members",
        _uuid_pk(), _ws_fk(),
        sa.Column("clerk_user_id", sa.String(255), nullable=False),
        sa.Column("email", sa.String(255), nullable=True),
        sa.Column("role", sa.String(30), nullable=False, server_default="agent"),
    )
    op.create_index("ix_tenant_members_clerk_user", "tenant_members", ["clerk_user_id"])

    op.create_table(
        "wa_numbers",
        _uuid_pk(), _ws_fk(),
        sa.Column("provider", sa.String(30), nullable=False, server_default="whatsmeow"),
        sa.Column("phone_number_id", sa.String(64), nullable=True),
        sa.Column("waba_id", sa.String(64), nullable=True),
        sa.Column("access_token", sa.Text(), nullable=True),
        sa.Column("messaging_tier", sa.Integer(), nullable=True),
        sa.Column("jid", sa.String(255), nullable=True),
        sa.Column("qr_code", sa.Text(), nullable=True),
        sa.Column("status", sa.String(50), nullable=False, server_default="UNCONFIGURED"),
    )
    op.create_index("ix_wa_numbers_phone_number_id", "wa_numbers", ["phone_number_id"])

    op.create_table(
        "conversations",
        _uuid_pk(), _ws_fk(),
        sa.Column("lead_id", UUID, sa.ForeignKey("leads.id", ondelete="CASCADE"), nullable=False),
        sa.Column("wa_number_id", UUID, sa.ForeignKey("wa_numbers.id", ondelete="SET NULL"), nullable=True),
        sa.Column("status", sa.String(30), nullable=False, server_default="active"),
        sa.Column("human_takeover", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("last_inbound_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )

    op.create_table(
        "memory_facts",
        _uuid_pk(), _ws_fk(),
        sa.Column("lead_id", UUID, sa.ForeignKey("leads.id", ondelete="CASCADE"), nullable=False),
        sa.Column("category", sa.String(50), nullable=True),
        sa.Column("fact", sa.Text(), nullable=False),
        sa.Column("confidence", sa.Integer(), nullable=True),
        sa.Column("source", sa.String(30), nullable=False, server_default="stated"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )
    # embedding column + ANN index — skip gracefully if pgvector isn't installed
    conn2 = op.get_bind()
    conn2.execute(sa.text("SAVEPOINT sp_embedding"))
    try:
        conn2.execute(sa.text("ALTER TABLE memory_facts ADD COLUMN IF NOT EXISTS embedding vector(768)"))
        conn2.execute(sa.text("CREATE INDEX IF NOT EXISTS ix_memory_facts_embedding ON memory_facts USING hnsw (embedding vector_cosine_ops)"))
        conn2.execute(sa.text("RELEASE SAVEPOINT sp_embedding"))
    except Exception:
        conn2.execute(sa.text("ROLLBACK TO SAVEPOINT sp_embedding"))
        # pgvector unavailable; embeddings disabled for this env

    op.create_table(
        "media_assets",
        _uuid_pk(), _ws_fk(),
        sa.Column("type", sa.String(20), nullable=False, server_default="image"),
        sa.Column("storage_key", sa.String(512), nullable=False),
        sa.Column("wa_media_id", sa.String(128), nullable=True),
        sa.Column("mime", sa.String(100), nullable=True),
        sa.Column("size_bytes", sa.Integer(), nullable=True),
        sa.Column("tags", postgresql.ARRAY(sa.String()), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )

    op.create_table(
        "message_templates",
        _uuid_pk(), _ws_fk(),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("wa_template_name", sa.String(255), nullable=True),
        sa.Column("language", sa.String(10), nullable=False, server_default="en"),
        sa.Column("body", sa.Text(), nullable=True),
        sa.Column("status", sa.String(30), nullable=False, server_default="pending"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )

    op.create_table(
        "consent",
        _uuid_pk(), _ws_fk(),
        sa.Column("lead_id", UUID, sa.ForeignKey("leads.id", ondelete="CASCADE"), nullable=False),
        sa.Column("source", sa.String(50), nullable=False),
        sa.Column("granted_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
    )

    op.create_table(
        "subscriptions",
        _uuid_pk(),
        sa.Column("workspace_id", UUID, sa.ForeignKey("workspaces.id", ondelete="CASCADE"), unique=True, nullable=False),
        sa.Column("stripe_customer_id", sa.String(64), nullable=True),
        sa.Column("stripe_subscription_id", sa.String(64), nullable=True),
        sa.Column("plan", sa.String(50), nullable=False, server_default="free"),
        sa.Column("status", sa.String(30), nullable=False, server_default="inactive"),
        sa.Column("current_period_end", sa.DateTime(timezone=True), nullable=True),
        sa.Column("max_numbers", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("monthly_conversation_quota", sa.Integer(), nullable=False, server_default="100"),
        sa.Column("max_seats", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("media_storage_mb", sa.Integer(), nullable=False, server_default="100"),
    )

    op.create_table(
        "usage",
        _uuid_pk(), _ws_fk(),
        sa.Column("period", sa.String(7), nullable=False),
        sa.Column("conversations_used", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("messages_sent", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("media_stored_mb", sa.Integer(), nullable=False, server_default="0"),
    )

    # --- Row-Level Security ---
    for table, col in RLS_TABLES:
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY")
        # NULLIF(...,'') so BOTH an unset GUC and an empty-string GUC fail closed
        # (NULL comparison -> 0 rows) instead of raising a uuid cast error.
        op.execute(
            f"CREATE POLICY tenant_isolation ON {table} "
            f"USING ({col} = NULLIF(current_setting('app.tenant_id', true), '')::uuid) "
            f"WITH CHECK ({col} = NULLIF(current_setting('app.tenant_id', true), '')::uuid)"
        )


def downgrade() -> None:
    for table, _ in RLS_TABLES:
        op.execute(f"DROP POLICY IF EXISTS tenant_isolation ON {table}")
        op.execute(f"ALTER TABLE {table} NO FORCE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY")

    for table in ["usage", "subscriptions", "consent", "message_templates", "media_assets",
                  "memory_facts", "conversations", "wa_numbers", "tenant_members"]:
        op.drop_table(table)

    op.drop_constraint("uq_workspaces_clerk_org", "workspaces", type_="unique")
    op.drop_column("workspaces", "default_provider")
    op.drop_column("workspaces", "disclosure_line")
    op.drop_column("workspaces", "clerk_org_id")
