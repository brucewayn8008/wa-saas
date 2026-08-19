"""Feature 06: messages.wa_message_id + RLS-safe wacli tenant resolve.

Revision ID: d4e5f6a7b8c9
Revises: c3d4e5f6a7b8
Create Date: 2026-08-09
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "d4e5f6a7b8c9"
down_revision: Union[str, None] = "c3d4e5f6a7b8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("messages", sa.Column("wa_message_id", sa.String(length=128), nullable=True))
    op.create_index("ix_messages_wa_message_id", "messages", ["wa_message_id"])
    op.create_index(
        "uq_messages_workspace_wa_message_id",
        "messages",
        ["workspace_id", "wa_message_id"],
        unique=True,
        postgresql_where=sa.text("wa_message_id IS NOT NULL"),
    )

    # Cross-tenant lookup for inbound webhooks (wa_numbers is RLS-forced).
    op.execute(
        """
        CREATE OR REPLACE FUNCTION public.resolve_wacli_number(
            p_account text DEFAULT NULL,
            p_store_dir text DEFAULT NULL,
            p_workspace_id uuid DEFAULT NULL
        )
        RETURNS TABLE (id uuid, workspace_id uuid)
        LANGUAGE plpgsql
        SECURITY DEFINER
        SET search_path = public
        AS $$
        BEGIN
          IF p_workspace_id IS NOT NULL THEN
            RETURN QUERY
              SELECT n.id, n.workspace_id
              FROM wa_numbers n
              WHERE n.provider = 'wacli' AND n.workspace_id = p_workspace_id
              ORDER BY CASE WHEN n.status IN ('CONNECTED', 'connected') THEN 0 ELSE 1 END
              LIMIT 1;
            RETURN;
          END IF;

          IF p_account IS NOT NULL AND btrim(p_account) <> '' THEN
            RETURN QUERY
              SELECT n.id, n.workspace_id
              FROM wa_numbers n
              WHERE n.provider = 'wacli' AND n.wacli_account = p_account
              LIMIT 1;
            IF FOUND THEN
              RETURN;
            END IF;
          END IF;

          IF p_store_dir IS NOT NULL AND btrim(p_store_dir) <> '' THEN
            RETURN QUERY
              SELECT n.id, n.workspace_id
              FROM wa_numbers n
              WHERE n.provider = 'wacli' AND n.wacli_store_dir = p_store_dir
              LIMIT 1;
            IF FOUND THEN
              RETURN;
            END IF;
          END IF;

          IF (SELECT count(*) FROM wa_numbers WHERE provider = 'wacli') = 1 THEN
            RETURN QUERY
              SELECT n.id, n.workspace_id
              FROM wa_numbers n
              WHERE n.provider = 'wacli'
              LIMIT 1;
          END IF;
        END;
        $$;
        """
    )
    op.execute("REVOKE ALL ON FUNCTION public.resolve_wacli_number(text, text, uuid) FROM PUBLIC")
    op.execute("GRANT EXECUTE ON FUNCTION public.resolve_wacli_number(text, text, uuid) TO PUBLIC")


def downgrade() -> None:
    op.execute("DROP FUNCTION IF EXISTS public.resolve_wacli_number(text, text, uuid)")
    op.drop_index("uq_messages_workspace_wa_message_id", table_name="messages")
    op.drop_index("ix_messages_wa_message_id", table_name="messages")
    op.drop_column("messages", "wa_message_id")
