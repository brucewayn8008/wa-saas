"""Conversations inbox + human takeover (Feature 14).

Endpoints (all tenant-scoped via RLS session; the URL id is a Conversation id):

  GET  /conversations                 → live threads (summaries)
  GET  /conversations/{id}            → one thread with its messages
  POST /conversations/{id}/messages   → manual human reply (through the gate)
  POST /conversations/{id}/takeover   → toggle human_takeover (pause/resume agent)

The reply path is the human-authorized send: it still passes `outreach_policy.gate`
(do-not-contact, 24h window, quota) and is delivered through the send task — there
is no send that bypasses the gate. Taking over pauses the agent so it won't
auto-reply on the next inbound.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.auth import AuthContext, get_auth_context, get_tenant_db
from app.core.config import settings
from app.core.outreach_policy import OutreachKind, gate
from app.models.database import (
    Conversation,
    Lead,
    LeadStatus,
    Message as DBMessage,
    MessageRole,
    MessageStatus,
    Workspace,
)
from app.services.conversations import set_human_takeover
from app.services.crm import bump_sent_counter, daily_quota_available, log_activity
from app.tasks.whatsapp_tasks import send_whatsapp_message

logger = logging.getLogger(__name__)
router = APIRouter()

_ROLE_MAP = {MessageRole.USER: "user", MessageRole.AGENT: "agent", MessageRole.HUMAN: "human"}


def _stage(lead: Lead) -> str:
    """Map lead status/intent onto the frontend LeadStage vocabulary."""
    if lead.status == LeadStatus.CONVERTED:
        return "CONVERTED"
    if lead.status == LeadStatus.FAILED:
        return "FAILED"
    intent = (lead.intent_label or "").upper()
    if intent in ("HOT", "WARM", "COLD"):
        return intent
    return "NEW"


def _within_window(convo: Conversation, lead: Lead) -> bool:
    last = convo.last_inbound_at or lead.last_inbound_at
    if not last:
        return False
    if last.tzinfo is None:
        last = last.replace(tzinfo=timezone.utc)
    hours = settings.CUSTOMER_SERVICE_WINDOW_HOURS
    return (datetime.now(timezone.utc) - last).total_seconds() <= hours * 3600


def _unread_count(db: Session, lead_id) -> int:
    """User messages since the last outbound (agent/human) message."""
    last_out = (
        db.query(DBMessage.timestamp)
        .filter(DBMessage.lead_id == lead_id, DBMessage.role != MessageRole.USER)
        .order_by(DBMessage.timestamp.desc())
        .first()
    )
    q = db.query(DBMessage).filter(DBMessage.lead_id == lead_id, DBMessage.role == MessageRole.USER)
    if last_out:
        q = q.filter(DBMessage.timestamp > last_out[0])
    return q.count()


def _last_message(db: Session, lead_id) -> DBMessage | None:
    return (
        db.query(DBMessage)
        .filter(DBMessage.lead_id == lead_id)
        .order_by(DBMessage.timestamp.desc())
        .first()
    )


def _summary(db: Session, convo: Conversation, lead: Lead) -> dict:
    last = _last_message(db, lead.id)
    updated = (last.timestamp if last else convo.created_at) or datetime.now(timezone.utc)
    return {
        "id": str(convo.id),
        "leadId": str(lead.id),
        "contactName": lead.name,
        "lastMessage": (last.content if last else ""),
        "updatedAt": updated.isoformat(),
        "stage": _stage(lead),
        "unread": _unread_count(db, lead.id),
        "humanTakeover": convo.human_takeover,
        "within24hWindow": _within_window(convo, lead),
        "doNotContact": lead.do_not_contact,
    }


def _load(db: Session, ctx: AuthContext, convo_id: str) -> tuple[Conversation, Lead]:
    convo = (
        db.query(Conversation)
        .filter(Conversation.id == convo_id, Conversation.workspace_id == ctx.tenant.id)
        .first()
    )
    if not convo:
        raise HTTPException(status_code=404, detail="Conversation not found")
    lead = db.query(Lead).filter(Lead.id == convo.lead_id).first()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    return convo, lead


@router.get("")
@router.get("/")
def list_conversations(
    status: str | None = None,
    ctx: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_tenant_db),
):
    q = db.query(Conversation).filter(Conversation.workspace_id == ctx.tenant.id)
    if status:
        q = q.filter(Conversation.status == status)
    convos = q.all()

    leads = {
        l.id: l
        for l in db.query(Lead).filter(Lead.id.in_([c.lead_id for c in convos])).all()
    } if convos else {}

    summaries = [_summary(db, c, leads[c.lead_id]) for c in convos if c.lead_id in leads]
    summaries.sort(key=lambda s: s["updatedAt"], reverse=True)
    return {"data": summaries}


@router.get("/{convo_id}")
def get_conversation(
    convo_id: str,
    ctx: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_tenant_db),
):
    convo, lead = _load(db, ctx, convo_id)
    messages = (
        db.query(DBMessage)
        .filter(DBMessage.lead_id == lead.id)
        .order_by(DBMessage.timestamp.asc())
        .all()
    )
    detail = _summary(db, convo, lead)
    detail["score"] = lead.score or 0
    detail["messages"] = [
        {
            "id": str(m.id),
            "role": _ROLE_MAP.get(m.role, "agent"),
            "text": m.content,
            "timestamp": (m.timestamp or datetime.now(timezone.utc)).isoformat(),
            "status": "sent" if m.status == MessageStatus.SENT else None,
        }
        for m in messages
    ]
    return {"data": detail}


class ReplyBody(BaseModel):
    text: str


@router.post("/{convo_id}/messages")
def send_reply(
    convo_id: str,
    body: ReplyBody,
    ctx: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_tenant_db),
):
    convo, lead = _load(db, ctx, convo_id)
    text = (body.text or "").strip()
    if not text:
        raise HTTPException(status_code=400, detail="Empty message")

    # Mutate the workspace on THIS (RLS) session so the quota counter persists.
    ws = db.query(Workspace).filter(Workspace.id == ctx.tenant.id).first()
    if not ws:
        raise HTTPException(status_code=404, detail="Tenant not found")

    # A human manual reply is still authorized by the compliance gate.
    decision = gate(ws, lead, OutreachKind.HUMAN_APPROVED,
                    window_hours=settings.CUSTOMER_SERVICE_WINDOW_HOURS)
    if not decision.allowed:
        raise HTTPException(status_code=422, detail=f"Blocked by policy: {decision.reason}")
    if not daily_quota_available(ws):
        raise HTTPException(status_code=429, detail="Daily message quota exceeded")

    msg = DBMessage(
        workspace_id=ws.id,
        lead_id=lead.id,
        role=MessageRole.HUMAN,
        content=text,
        status=MessageStatus.SENT,
    )
    db.add(msg)

    # A human stepping in owns the thread — pause the agent to avoid double replies.
    set_human_takeover(db, convo, True)

    now = datetime.now(timezone.utc)
    lead.last_contacted_at = now
    lead.last_outbound_at = now
    lead.needs_response = False
    bump_sent_counter(ws)
    log_activity(db, str(ws.id), "manual_reply_sent",
                 f"Manual reply sent to {lead.name}", detail=text, lead_id=str(lead.id))
    db.commit()

    try:
        send_whatsapp_message.delay(str(ctx.tenant.id), lead.jid, text)
    except Exception as exc:
        logger.error("Failed to enqueue manual send: %s", exc)

    return {"data": {"id": str(msg.id), "humanTakeover": True}, "success": True}


class TakeoverBody(BaseModel):
    enabled: bool


@router.post("/{convo_id}/takeover")
def toggle_takeover(
    convo_id: str,
    body: TakeoverBody,
    ctx: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_tenant_db),
):
    convo, lead = _load(db, ctx, convo_id)
    set_human_takeover(db, convo, body.enabled)
    log_activity(db, str(ctx.tenant.id),
                 "human_takeover_on" if body.enabled else "human_takeover_off",
                 f"Human {'took over' if body.enabled else 'released'} {lead.name}",
                 lead_id=str(lead.id))
    db.commit()
    return {"data": {"id": str(convo.id), "humanTakeover": convo.human_takeover}, "success": True}
