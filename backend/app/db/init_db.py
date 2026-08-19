import logging
from sqlalchemy import text
from sqlalchemy.orm import Session
from app.models.database import Workspace, WhatsAppSession

logger = logging.getLogger(__name__)


def _ensure_schema_extensions(db: Session) -> None:
    statements = [
        "ALTER TABLE workspaces ADD COLUMN IF NOT EXISTS agent_config TEXT NOT NULL DEFAULT '{}'",
        "ALTER TABLE workspaces ADD COLUMN IF NOT EXISTS is_running BOOLEAN NOT NULL DEFAULT FALSE",
        "ALTER TABLE workspaces ADD COLUMN IF NOT EXISTS daily_message_limit INTEGER NOT NULL DEFAULT 35",
        "ALTER TABLE workspaces ADD COLUMN IF NOT EXISTS messages_sent_today INTEGER NOT NULL DEFAULT 0",
        "ALTER TABLE workspaces ADD COLUMN IF NOT EXISTS last_daily_reset_at TIMESTAMPTZ",
        "ALTER TABLE leads ADD COLUMN IF NOT EXISTS source VARCHAR(50) NOT NULL DEFAULT 'DIRECT'",
        "ALTER TABLE leads ADD COLUMN IF NOT EXISTS source_group_jid VARCHAR(255)",
        "ALTER TABLE leads ADD COLUMN IF NOT EXISTS source_group_name VARCHAR(255)",
        "ALTER TABLE leads ADD COLUMN IF NOT EXISTS service_interest VARCHAR(255)",
        "ALTER TABLE leads ADD COLUMN IF NOT EXISTS requirement_summary TEXT",
        "ALTER TABLE leads ADD COLUMN IF NOT EXISTS meeting_status VARCHAR(50) NOT NULL DEFAULT 'NOT_REQUESTED'",
        "ALTER TABLE leads ADD COLUMN IF NOT EXISTS meeting_notes TEXT",
        "ALTER TABLE leads ADD COLUMN IF NOT EXISTS next_action TEXT",
        "ALTER TABLE leads ADD COLUMN IF NOT EXISTS last_inbound_at TIMESTAMPTZ",
        "ALTER TABLE leads ADD COLUMN IF NOT EXISTS last_outbound_at TIMESTAMPTZ",
        "ALTER TABLE leads ADD COLUMN IF NOT EXISTS do_not_contact BOOLEAN NOT NULL DEFAULT FALSE",
        "ALTER TABLE leads ADD COLUMN IF NOT EXISTS needs_response BOOLEAN NOT NULL DEFAULT FALSE",
        "ALTER TABLE target_groups ADD COLUMN IF NOT EXISTS custom_offer TEXT",
        "ALTER TABLE target_groups ADD COLUMN IF NOT EXISTS last_promo_sent_at TIMESTAMPTZ",
        """
        CREATE TABLE IF NOT EXISTS agent_activities (
            id UUID PRIMARY KEY,
            workspace_id UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
            lead_id UUID NULL REFERENCES leads(id) ON DELETE SET NULL,
            group_jid VARCHAR(255),
            event_type VARCHAR(100) NOT NULL,
            title VARCHAR(255) NOT NULL,
            detail TEXT,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS listening_leads (
            id UUID PRIMARY KEY,
            workspace_id UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
            lead_id UUID NULL REFERENCES leads(id) ON DELETE SET NULL,
            group_jid VARCHAR(255) NOT NULL,
            group_name VARCHAR(255) NOT NULL,
            sender_jid VARCHAR(255) NOT NULL,
            original_message TEXT NOT NULL,
            match_reason VARCHAR(30) NOT NULL,
            match_score INTEGER,
            reply_text TEXT,
            status VARCHAR(30) NOT NULL DEFAULT 'detected',
            block_reason VARCHAR(100),
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            dismissed_at TIMESTAMPTZ
        )
        """,
    ]
    for statement in statements:
        db.execute(text(statement))
    db.commit()

def init_db(db: Session) -> None:
    # Tables should be created with Alembic migrations
    # But if you are using it without Alembic for now, you can uncomment base.metadata.create_all
    from app.models.database import Base
    from app.db.session import engine
    Base.metadata.create_all(bind=engine)
    _ensure_schema_extensions(db)
    
    unconfigured = db.query(Workspace).filter(~Workspace.whatsapp_session.has()).all()
    for workspace in unconfigured:
        db.add(WhatsAppSession(workspace_id=workspace.id, status="UNCONFIGURED"))
    if unconfigured:
        db.commit()
        logger.info("Created WhatsApp session rows for %s workspace(s)", len(unconfigured))
