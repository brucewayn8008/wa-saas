"""Group listening — intent match, audit rows, auto-reply finalize, dismiss (Feature 16).

Listening only reads messages from groups the tenant already belongs to (TargetGroup).
It never scrapes members. Matched signals create a ListeningLead; the AI reply is
generated via the normal pipeline and auto-sent only when outreach_policy.gate allows.
"""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Literal, Optional, Sequence
from uuid import UUID

from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.models.database import ListeningLead
from app.services.crm import message_looks_like_need, normalize_text

logger = logging.getLogger(__name__)

MatchReason = Literal["keyword", "semantic"]
ListeningStatus = Literal["detected", "sent", "blocked", "dismissed"]

# Cosine similarity floor for semantic matches (services blob vs group message).
SEMANTIC_THRESHOLD = 0.72

FEED_STATUSES = ("sent", "blocked", "detected")


@dataclass(frozen=True)
class IntentMatch:
    matched: bool
    reason: Optional[MatchReason] = None
    score: Optional[int] = None  # 0–100 for semantic; None for keyword


def _cosine(a: Sequence[float], b: Sequence[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)


def match_intent(
    text: str,
    *,
    keywords: list[str],
    services: list[str] | None = None,
    embed_fn=None,
    semantic_threshold: float = SEMANTIC_THRESHOLD,
) -> IntentMatch:
    """Keyword rules first; optional embedding similarity against tenant services.

    When embeddings are unavailable the semantic path is skipped (keywords-only).
    """
    content = normalize_text(text)
    if len(content) < 10:
        return IntentMatch(matched=False)

    if message_looks_like_need(text, list(keywords or [])):
        return IntentMatch(matched=True, reason="keyword")

    services = [s for s in (services or []) if (s or "").strip()]
    if not services:
        return IntentMatch(matched=False)

    fn = embed_fn
    if fn is None:
        try:
            from app.services.memory import embed_text as fn
        except Exception:
            return IntentMatch(matched=False)

    try:
        msg_vec = fn(text)
        svc_blob = " ".join(services)
        svc_vec = fn(svc_blob) if msg_vec is not None else None
    except Exception as exc:
        logger.warning("[listening/match_intent] embed failed: %s", exc)
        return IntentMatch(matched=False)

    if msg_vec is None or svc_vec is None:
        return IntentMatch(matched=False)

    sim = _cosine(msg_vec, svc_vec)
    score = int(round(sim * 100))
    if sim >= semantic_threshold:
        return IntentMatch(matched=True, reason="semantic", score=score)
    return IntentMatch(matched=False, reason="semantic", score=score)


def record_detection(
    db: Session,
    workspace_id: str,
    *,
    lead_id: str | None,
    group_jid: str,
    group_name: str,
    sender_jid: str,
    original_message: str,
    match: IntentMatch,
) -> ListeningLead:
    """Persist a matched group signal before/while the AI reply runs."""
    row = ListeningLead(
        workspace_id=workspace_id,
        lead_id=UUID(str(lead_id)) if lead_id else None,
        group_jid=group_jid,
        group_name=group_name or "Group",
        sender_jid=sender_jid,
        original_message=original_message,
        match_reason=match.reason or "keyword",
        match_score=match.score,
        status="detected",
    )
    db.add(row)
    db.flush()
    return row


def finalize_reply(
    db: Session,
    workspace_id: str,
    lead_id: str,
    *,
    reply_text: str,
    sent: bool,
    block_reason: str | None = None,
) -> Optional[ListeningLead]:
    """Attach the automated reply to the newest open ListeningLead for this lead."""
    row = (
        db.query(ListeningLead)
        .filter(
            ListeningLead.workspace_id == workspace_id,
            ListeningLead.lead_id == lead_id,
            ListeningLead.status == "detected",
        )
        .order_by(desc(ListeningLead.created_at))
        .first()
    )
    if not row:
        return None

    row.reply_text = reply_text
    if sent:
        row.status = "sent"
        row.block_reason = None
    else:
        row.status = "blocked"
        row.block_reason = block_reason or "not_sent"
    db.flush()
    return row


def list_listening(
    db: Session,
    workspace_id: str,
    *,
    limit: int = 50,
    offset: int = 0,
) -> list[ListeningLead]:
    """Processed (non-dismissed) listening items for the tenant feed."""
    limit = max(1, min(int(limit or 50), 100))
    offset = max(0, int(offset or 0))
    return (
        db.query(ListeningLead)
        .filter(
            ListeningLead.workspace_id == workspace_id,
            ListeningLead.status.in_(FEED_STATUSES),
        )
        .order_by(desc(ListeningLead.created_at))
        .offset(offset)
        .limit(limit)
        .all()
    )


def dismiss(db: Session, workspace_id: str, listening_id: str) -> Optional[ListeningLead]:
    """Soft-dismiss — hide from the feed without deleting the audit row."""
    row = (
        db.query(ListeningLead)
        .filter(
            ListeningLead.workspace_id == workspace_id,
            ListeningLead.id == listening_id,
        )
        .first()
    )
    if not row:
        return None
    if row.status == "dismissed":
        return row
    row.status = "dismissed"
    row.dismissed_at = datetime.now(timezone.utc)
    db.flush()
    return row
