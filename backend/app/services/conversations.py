"""Conversation lifecycle helpers (Features 13 & 14).

A `Conversation` is the durable thread between a tenant number and a lead. It
carries the state that the inbox and the agent both need:
  * `human_takeover` — when true, the agent must NOT auto-reply (a human owns it).
  * `status`         — active | paused | ended.
  * `last_inbound_at`— drives the 24h service-window logic.

All calls assume the session is already tenant-scoped (RLS GUC set) OR the
caller passes the workspace_id explicitly for defense-in-depth filtering.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.orm import Session

from app.models.database import Conversation

logger = logging.getLogger(__name__)


def get_conversation(db: Session, workspace_id: str, lead_id: str) -> Optional[Conversation]:
    return (
        db.query(Conversation)
        .filter(Conversation.workspace_id == workspace_id, Conversation.lead_id == lead_id)
        .first()
    )


def ensure_conversation(
    db: Session,
    workspace_id: str,
    lead_id: str,
    *,
    wa_number_id: Optional[str] = None,
    mark_inbound: bool = False,
) -> Conversation:
    """Get or create the conversation for a (tenant, lead). Optionally stamp an
    inbound. Flushes so the row has an id; commit is the caller's responsibility."""
    convo = get_conversation(db, workspace_id, lead_id)
    if convo is None:
        convo = Conversation(
            workspace_id=workspace_id,
            lead_id=lead_id,
            wa_number_id=wa_number_id,
            status="active",
            human_takeover=False,
        )
        db.add(convo)
        db.flush()
    if wa_number_id and not convo.wa_number_id:
        convo.wa_number_id = wa_number_id
    if mark_inbound:
        convo.last_inbound_at = datetime.now(timezone.utc)
        if convo.status == "ended":
            convo.status = "active"
    return convo


def set_human_takeover(db: Session, convo: Conversation, on: bool) -> Conversation:
    """Toggle human takeover. When on, the agent pauses; the conversation is
    marked paused so the inbox reflects it."""
    convo.human_takeover = bool(on)
    convo.status = "paused" if on else "active"
    return convo
