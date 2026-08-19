"""Dashboard summary endpoint — returns DashboardData for the SaaS frontend."""
from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.auth import AuthContext, get_auth_context, get_db
from app.models.database import (
    AgentActivity,
    Conversation,
    Lead,
    WANumber,
    Workspace,
)
from app.services import billing

router = APIRouter()


def _wa_status(ws, db: Session) -> str:
    num = db.query(WANumber).filter(WANumber.workspace_id == ws.id).first()
    if num:
        raw = (num.status or "UNCONFIGURED").upper()
        if raw == "CONNECTED":
            return "CONNECTED"
        if raw in ("QR_PENDING", "QR_WAITING"):
            return "QR_PENDING"
        return "UNCONFIGURED"
    session = getattr(ws, "whatsapp_session", None)
    if session:
        raw = (session.status or "UNCONFIGURED").upper()
        if raw in ("CONNECTED", "READY"):
            return "CONNECTED"
        if raw in ("QR_PENDING", "WAITING_FOR_SCAN"):
            return "QR_PENDING"
        if raw == "DISCONNECTED":
            return "LOGGED_OUT"
    return "UNCONFIGURED"


@router.get("")
def get_dashboard(
    ctx: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    ws = db.query(Workspace).filter(Workspace.id == ctx.tenant.id).first()
    if not ws:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Tenant not found")

    leads = db.query(Lead).filter(Lead.workspace_id == ws.id).all()
    conversations = db.query(Conversation).filter(Conversation.workspace_id == ws.id).all()
    activities = (
        db.query(AgentActivity)
        .filter(AgentActivity.workspace_id == ws.id)
        .order_by(AgentActivity.created_at.desc())
        .limit(20)
        .all()
    )

    sub = billing.get_or_create_subscription(db, ws.id)
    usage_rec = billing.get_or_create_usage(db, ws.id)
    db.commit()

    hot_leads = [l for l in leads if (l.score or 0) >= 75]
    meeting_leads = [l for l in leads if l.meeting_status in ("REQUESTED", "READY", "BOOKED")]
    takeover_convos = [c for c in conversations if c.human_takeover]

    activity_items = [
        {
            "id": str(a.id),
            "title": a.title,
            "detail": a.detail or "",
            "eventType": a.event_type,
            "createdAt": (a.created_at or datetime.now(timezone.utc)).isoformat(),
        }
        for a in activities
    ]

    needs_attention = []
    if takeover_convos:
        needs_attention.append({
            "id": "takeover-alert",
            "kind": "takeover",
            "title": f"{len(takeover_convos)} conversation{'s' if len(takeover_convos) > 1 else ''} on human takeover",
            "href": "/conversations",
        })

    return {
        "success": True,
        "data": {
            "companyName": ws.company_name or "My Workspace",
            "agentEnabled": ws.agent_enabled,
            "waStatus": _wa_status(ws, db),
            "usage": {
                "conversationsUsed": usage_rec.conversations_used,
                "conversationsQuota": sub.monthly_conversation_quota,
                "messagesSent": usage_rec.messages_sent,
                "mediaStoredMb": usage_rec.media_stored_mb,
                "mediaQuotaMb": sub.media_storage_mb,
            },
            "stats": {
                "activeConversations": len([c for c in conversations if c.status == "active"]),
                "hotLeads": len(hot_leads),
                "meetingsBookedWeek": len(meeting_leads),
                "messagesSentToday": ws.messages_sent_today,
            },
            "activity": activity_items,
            "needsAttention": needs_attention,
        },
    }
