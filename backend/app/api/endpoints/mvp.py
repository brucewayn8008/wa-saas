import asyncio
import json
from datetime import datetime, timezone
from typing import Any, AsyncGenerator
from uuid import UUID

import httpx
from fastapi import APIRouter, Body, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.auth import get_current_user
from app.core.config import settings
from app.core.celery_app import celery_app
from app.db.session import SessionLocal
from app.models.database import (
    AgentActivity,
    Lead,
    LeadStatus,
    Message,
    MessageRole,
    MessageStatus,
    TargetGroup,
    User,
    WhatsAppSession,
    Workspace,
)
from app.services.crm import (
    bump_sent_counter,
    daily_quota_available,
    lead_display_status,
    log_activity,
    read_agent_config,
    write_agent_config,
)
from app.tasks.whatsapp_tasks import send_whatsapp_message

router = APIRouter()


def _db() -> Session:
    return SessionLocal()


def _ensure_workspace(db: Session, current_user: User) -> Workspace:
    workspace = (
        db.query(Workspace)
        .filter(Workspace.owner_id == current_user.id)
        .order_by(Workspace.created_at.asc())
        .first()
    )
    if workspace:
        if not workspace.whatsapp_session:
            db.add(WhatsAppSession(workspace_id=workspace.id, status="UNCONFIGURED"))
            db.commit()
            db.refresh(workspace)
        return workspace

    workspace = Workspace(
        owner_id=current_user.id,
        company_name="Lead Operations",
        business_description="We deliver web development, marketing, branding, and automation services.",
        system_prompt=(
            "You are a serious but warm sales operator. Qualify the lead, understand needs, "
            "ask smart follow-up questions, and move strong opportunities toward a meeting."
        ),
        agent_enabled=False,
        is_running=False,
    )
    db.add(workspace)
    db.commit()
    db.refresh(workspace)
    db.add(WhatsAppSession(workspace_id=workspace.id, status="UNCONFIGURED"))
    db.commit()
    db.refresh(workspace)
    return workspace


def _lead_payload(lead: Lead) -> dict[str, Any]:
    latest = max(lead.messages, key=lambda m: m.timestamp or datetime.now(timezone.utc)) if lead.messages else None
    return {
        "id": str(lead.id),
        "sender": lead.name,
        "jid": lead.jid,
        "message": latest.content if latest else "",
        "found_at": (lead.created_at or datetime.now(timezone.utc)).isoformat(),
        "status": lead_display_status(lead),
        "intent_label": lead.intent_label,
        "score": lead.score or 0,
        "summary": lead.summary,
        "assigned_to_id": str(lead.assigned_to_id) if lead.assigned_to_id else None,
        "group_name": lead.source_group_name or "Direct Message",
        "source": lead.source,
        "service_interest": lead.service_interest,
        "requirement_summary": lead.requirement_summary,
        "meeting_status": lead.meeting_status,
        "next_action": lead.next_action,
        "do_not_contact": lead.do_not_contact,
        "last_inbound_at": lead.last_inbound_at.isoformat() if lead.last_inbound_at else None,
        "last_outbound_at": lead.last_outbound_at.isoformat() if lead.last_outbound_at else None,
    }


def _activity_payload(activity: AgentActivity) -> dict[str, Any]:
    return {
        "id": str(activity.id),
        "event_type": activity.event_type,
        "title": activity.title,
        "detail": activity.detail,
        "group_jid": activity.group_jid,
        "created_at": activity.created_at.isoformat() if activity.created_at else None,
    }


def _session_payload(session: WhatsAppSession | None) -> dict[str, Any]:
    status = (session.status if session else "UNCONFIGURED").upper()
    if status in {"CONNECTED", "READY"}:
        mapped = "connected"
    elif status in {"QR_PENDING", "WAITING_FOR_SCAN"}:
        mapped = "waiting_for_scan"
    else:
        mapped = "disconnected"
    return {
        "status": mapped,
        "raw_status": status,
        "qr": session.qr_code if session and mapped == "waiting_for_scan" else None,
        "updated_at": session.last_updated.isoformat() if session and session.last_updated else None,
    }


def _start_gateway_session(workspace_id: str) -> tuple[bool, str | None]:
    try:
        resp = httpx.get(
            f"{settings.GO_GATEWAY_URL}/api/session/start",
            params={"workspace_id": workspace_id},
            timeout=12.0,
        )
        resp.raise_for_status()
        return True, None
    except Exception as exc:
        return False, str(exc)


def _fetch_gateway_groups(workspace_id: str) -> tuple[list[dict[str, Any]], str | None]:
    try:
        resp = httpx.get(
            f"{settings.GO_GATEWAY_URL}/api/groups",
            params={"workspace_id": workspace_id},
            timeout=20.0,
        )
        if resp.status_code == 503:
            _start_gateway_session(workspace_id)
            resp = httpx.get(
                f"{settings.GO_GATEWAY_URL}/api/groups",
                params={"workspace_id": workspace_id},
                timeout=20.0,
            )
        resp.raise_for_status()
        payload = resp.json()
        groups = payload.get("groups") if isinstance(payload, dict) else []
        return groups if isinstance(groups, list) else [], None
    except Exception as exc:
        return [], str(exc)


@router.get("/dashboard")
def dashboard(current_user: User = Depends(get_current_user)):
    db = _db()
    try:
        workspace = _ensure_workspace(db, current_user)
        config = read_agent_config(workspace)
        leads = (
            db.query(Lead)
            .filter(Lead.workspace_id == workspace.id)
            .order_by(Lead.created_at.desc())
            .all()
        )
        activities = (
            db.query(AgentActivity)
            .filter(AgentActivity.workspace_id == workspace.id)
            .order_by(AgentActivity.created_at.desc())
            .limit(30)
            .all()
        )
        active_groups = (
            db.query(TargetGroup)
            .filter(TargetGroup.workspace_id == workspace.id, TargetGroup.is_active.is_(True))
            .count()
        )
        return {
            "ok": True,
            "workspace": {
                "id": str(workspace.id),
                "company_name": workspace.company_name,
                "agent_enabled": workspace.agent_enabled,
                "is_running": workspace.is_running,
                "messages_sent_today": workspace.messages_sent_today,
                "daily_message_limit": workspace.daily_message_limit,
                "session": _session_payload(workspace.whatsapp_session),
            },
            "stats": {
                "total_leads": len(leads),
                "hot_leads": len([lead for lead in leads if (lead.score or 0) >= 75]),
                "warm_leads": len([lead for lead in leads if 45 <= (lead.score or 0) < 75]),
                "meeting_leads": len([lead for lead in leads if lead.meeting_status in {"REQUESTED", "READY", "BOOKED"}]),
                "converted_leads": len([lead for lead in leads if lead.status == LeadStatus.CONVERTED]),
                "active_groups": active_groups,
            },
            "config": config,
            "logs": [_activity_payload(item) for item in activities],
        }
    finally:
        db.close()


@router.get("/leads")
def get_leads(current_user: User = Depends(get_current_user)):
    db = _db()
    try:
        workspace = _ensure_workspace(db, current_user)
        leads = (
            db.query(Lead)
            .filter(Lead.workspace_id == workspace.id)
            .order_by(Lead.created_at.desc())
            .all()
        )
        return {"ok": True, "leads": [_lead_payload(lead) for lead in leads]}
    finally:
        db.close()


@router.get("/leads/{lead_id}/conversation")
def lead_conversation(lead_id: UUID, current_user: User = Depends(get_current_user)):
    db = _db()
    try:
        workspace = _ensure_workspace(db, current_user)
        lead = db.query(Lead).filter(Lead.id == lead_id, Lead.workspace_id == workspace.id).first()
        if not lead:
            raise HTTPException(status_code=404, detail="Lead not found")
        messages = (
            db.query(Message)
            .filter(Message.lead_id == lead.id)
            .order_by(Message.timestamp.asc())
            .all()
        )
        data = _lead_payload(lead)
        data["conversation"] = [
            {
                "id": str(msg.id),
                "role": msg.role.value,
                "text": msg.content,
                "status": msg.status.value.upper(),
                "timestamp": (msg.timestamp or datetime.now(timezone.utc)).isoformat(),
                "manual": msg.role == MessageRole.AGENT and msg.status == MessageStatus.SENT,
            }
            for msg in messages
        ]
        return {"ok": True, "lead": data}
    finally:
        db.close()


class AssignRequest(BaseModel):
    assigned_to_id: str | None = None


@router.patch("/leads/{lead_id}/assign")
def assign_lead(lead_id: UUID, payload: AssignRequest, current_user: User = Depends(get_current_user)):
    db = _db()
    try:
        workspace = _ensure_workspace(db, current_user)
        lead = db.query(Lead).filter(Lead.id == lead_id, Lead.workspace_id == workspace.id).first()
        if not lead:
            raise HTTPException(status_code=404, detail="Lead not found")
        lead.assigned_to_id = UUID(payload.assigned_to_id) if payload.assigned_to_id else None
        db.commit()
        return {"ok": True}
    finally:
        db.close()


class LeadUpdateRequest(BaseModel):
    meeting_status: str | None = None
    do_not_contact: bool | None = None
    next_action: str | None = None


@router.patch("/leads/{lead_id}")
def update_lead(lead_id: UUID, payload: LeadUpdateRequest, current_user: User = Depends(get_current_user)):
    db = _db()
    try:
        workspace = _ensure_workspace(db, current_user)
        lead = db.query(Lead).filter(Lead.id == lead_id, Lead.workspace_id == workspace.id).first()
        if not lead:
            raise HTTPException(status_code=404, detail="Lead not found")
        if payload.meeting_status is not None:
            lead.meeting_status = payload.meeting_status
        if payload.do_not_contact is not None:
            lead.do_not_contact = payload.do_not_contact
        if payload.next_action is not None:
            lead.next_action = payload.next_action
        log_activity(db, str(workspace.id), "lead_updated", f"Lead updated: {lead.name}", lead.next_action or lead.meeting_status, str(lead.id), lead.source_group_jid)
        db.commit()
        return {"ok": True}
    finally:
        db.close()


class ManualMessageRequest(BaseModel):
    message: str = Field(min_length=1)


@router.post("/leads/{lead_id}/send_manual")
def send_manual(lead_id: UUID, payload: ManualMessageRequest, current_user: User = Depends(get_current_user)):
    db = _db()
    try:
        workspace = _ensure_workspace(db, current_user)
        lead = db.query(Lead).filter(Lead.id == lead_id, Lead.workspace_id == workspace.id).first()
        if not lead:
            raise HTTPException(status_code=404, detail="Lead not found")
        if not daily_quota_available(workspace):
            raise HTTPException(status_code=400, detail="Daily message limit reached")
        content = payload.message.strip()
        message = Message(
            lead_id=lead.id,
            workspace_id=lead.workspace_id,
            role=MessageRole.AGENT,
            status=MessageStatus.SENT,
            content=content,
        )
        lead.status = LeadStatus.IN_PROGRESS
        lead.last_contacted_at = datetime.now(timezone.utc)
        lead.last_outbound_at = lead.last_contacted_at
        db.add(message)
        bump_sent_counter(workspace)
        log_activity(db, str(workspace.id), "manual_message_sent", f"Manual message sent to {lead.name}", content, str(lead.id), lead.source_group_jid)
        db.commit()
        send_whatsapp_message.delay(str(lead.workspace_id), lead.jid, content)
        return {"ok": True}
    finally:
        db.close()


@router.post("/leads/{lead_id}/convert")
def convert_lead(lead_id: UUID, current_user: User = Depends(get_current_user)):
    db = _db()
    try:
        workspace = _ensure_workspace(db, current_user)
        lead = db.query(Lead).filter(Lead.id == lead_id, Lead.workspace_id == workspace.id).first()
        if not lead:
            raise HTTPException(status_code=404, detail="Lead not found")
        lead.status = LeadStatus.CONVERTED
        lead.meeting_status = "BOOKED"
        log_activity(db, str(workspace.id), "lead_converted", f"Lead converted: {lead.name}", lead.summary, str(lead.id), lead.source_group_jid)
        db.commit()
        return {"ok": True}
    finally:
        db.close()


@router.post("/leads/{lead_id}/followup")
def add_followup(lead_id: UUID, current_user: User = Depends(get_current_user)):
    db = _db()
    try:
        workspace = _ensure_workspace(db, current_user)
        lead = db.query(Lead).filter(Lead.id == lead_id, Lead.workspace_id == workspace.id).first()
        if not lead:
            raise HTTPException(status_code=404, detail="Lead not found")
        draft = Message(
            lead_id=lead.id,
            workspace_id=lead.workspace_id,
            role=MessageRole.AGENT,
            status=MessageStatus.DRAFT,
            content="Quick follow-up. If this requirement is still active, we can align on scope and move it to a short meeting.",
        )
        db.add(draft)
        log_activity(db, str(workspace.id), "followup_draft", f"Follow-up drafted for {lead.name}", draft.content, str(lead.id), lead.source_group_jid)
        db.commit()
        return {"ok": True}
    finally:
        db.close()


@router.delete("/leads/{lead_id}")
def delete_lead(lead_id: UUID, current_user: User = Depends(get_current_user)):
    db = _db()
    try:
        workspace = _ensure_workspace(db, current_user)
        lead = db.query(Lead).filter(Lead.id == lead_id, Lead.workspace_id == workspace.id).first()
        if not lead:
            raise HTTPException(status_code=404, detail="Lead not found")
        log_activity(db, str(workspace.id), "lead_deleted", f"Lead deleted: {lead.name}", lead.summary, str(lead.id), lead.source_group_jid)
        db.delete(lead)
        db.commit()
        return {"ok": True}
    finally:
        db.close()


class ApproveRequest(BaseModel):
    content: str | None = None


@router.patch("/messages/{message_id}/approve")
def approve_draft(message_id: UUID, payload: ApproveRequest, current_user: User = Depends(get_current_user)):
    db = _db()
    try:
        workspace = _ensure_workspace(db, current_user)
        message = (
            db.query(Message)
            .filter(Message.id == message_id, Message.workspace_id == workspace.id)
            .first()
        )
        if not message:
            raise HTTPException(status_code=404, detail="Message not found")
        if message.status != MessageStatus.DRAFT:
            raise HTTPException(status_code=400, detail="Only DRAFT can be approved")
        if not daily_quota_available(workspace):
            raise HTTPException(status_code=400, detail="Daily message limit reached")
        if payload.content:
            message.content = payload.content.strip()
        message.status = MessageStatus.SENT
        lead = db.query(Lead).filter(Lead.id == message.lead_id).first()
        if lead:
            lead.status = LeadStatus.IN_PROGRESS
            lead.last_contacted_at = datetime.now(timezone.utc)
            lead.last_outbound_at = lead.last_contacted_at
        bump_sent_counter(workspace)
        log_activity(db, str(workspace.id), "draft_approved", f"Draft approved for {lead.name if lead else 'lead'}", message.content, str(lead.id) if lead else None, lead.source_group_jid if lead else None)
        db.commit()
        if lead:
            send_whatsapp_message.delay(str(lead.workspace_id), lead.jid, message.content)
        return {"ok": True}
    finally:
        db.close()


@router.get("/users")
def get_users(current_user: User = Depends(get_current_user)):
    db = _db()
    try:
        _ensure_workspace(db, current_user)
        users = db.query(User).order_by(User.created_at.asc()).all()
        return [{"id": str(user.id), "email": user.email} for user in users]
    finally:
        db.close()


@router.get("/auth")
def auth_status(current_user: User = Depends(get_current_user)):
    db = _db()
    try:
        workspace = _ensure_workspace(db, current_user)
        return {"ok": True, "data": _session_payload(workspace.whatsapp_session)}
    finally:
        db.close()


@router.post("/auth/connect")
def auth_connect(current_user: User = Depends(get_current_user)):
    db = _db()
    try:
        workspace = _ensure_workspace(db, current_user)
        session = workspace.whatsapp_session
        session.status = "QR_PENDING"
        log_activity(db, str(workspace.id), "whatsapp_connect_requested", "WhatsApp connect requested", "Session start requested from dashboard")
        db.commit()
        ok, error = _start_gateway_session(str(workspace.id))
        if not ok:
            raise HTTPException(status_code=502, detail=error or "Failed to start gateway session")
        return {"ok": True, "data": _session_payload(session)}
    finally:
        db.close()


@router.post("/auth/logout")
def auth_logout(current_user: User = Depends(get_current_user)):
    db = _db()
    try:
        workspace = _ensure_workspace(db, current_user)
        workspace.agent_enabled = False
        workspace.is_running = False
        if workspace.whatsapp_session:
            workspace.whatsapp_session.status = "DISCONNECTED"
            workspace.whatsapp_session.qr_code = None
        log_activity(db, str(workspace.id), "whatsapp_disconnected", "WhatsApp disconnected", "Agent and WhatsApp session paused from dashboard")
        db.commit()
        return {"ok": True}
    finally:
        db.close()


@router.get("/agent/status")
def agent_status(current_user: User = Depends(get_current_user)):
    db = _db()
    try:
        workspace = _ensure_workspace(db, current_user)
        active_groups = db.query(TargetGroup).filter(TargetGroup.workspace_id == workspace.id, TargetGroup.is_active.is_(True)).count()
        return {
            "running": workspace.is_running,
            "is_running": workspace.is_running,
            "active_groups": active_groups,
            "messages_sent": workspace.messages_sent_today,
            "daily_limit": workspace.daily_message_limit,
        }
    finally:
        db.close()


@router.post("/agent/start")
def agent_start(current_user: User = Depends(get_current_user)):
    db = _db()
    try:
        workspace = _ensure_workspace(db, current_user)
        workspace.agent_enabled = True
        workspace.is_running = True
        log_activity(db, str(workspace.id), "agent_started", "Agent started", "24x7 monitoring enabled and logs are live")
        db.commit()
        return {"ok": True, "running": True}
    finally:
        db.close()


@router.post("/agent/stop")
def agent_stop(current_user: User = Depends(get_current_user)):
    db = _db()
    try:
        workspace = _ensure_workspace(db, current_user)
        workspace.is_running = False
        log_activity(db, str(workspace.id), "agent_stopped", "Agent stopped", "Monitoring paused")
        db.commit()
        return {"ok": True, "running": False}
    finally:
        db.close()


@router.get("/agent/logs")
def agent_logs(current_user: User = Depends(get_current_user)):
    db = _db()
    try:
        workspace = _ensure_workspace(db, current_user)
        logs = (
            db.query(AgentActivity)
            .filter(AgentActivity.workspace_id == workspace.id)
            .order_by(AgentActivity.created_at.desc())
            .limit(50)
            .all()
        )
        return {"ok": True, "logs": [_activity_payload(item) for item in logs]}
    finally:
        db.close()


@router.get("/groups/target")
def get_target_groups(current_user: User = Depends(get_current_user)):
    db = _db()
    try:
        workspace = _ensure_workspace(db, current_user)
        groups = (
            db.query(TargetGroup)
            .filter(TargetGroup.workspace_id == workspace.id)
            .order_by(TargetGroup.name.asc())
            .all()
        )
        return {
            "ok": True,
            "groups": [
                {
                    "jid": group.jid,
                    "name": group.name,
                    "enabled": group.is_active,
                    "custom_offer": group.custom_offer,
                    "last_promo_sent_at": group.last_promo_sent_at.isoformat() if group.last_promo_sent_at else None,
                }
                for group in groups
            ],
        }
    finally:
        db.close()


@router.get("/groups/discovered")
def get_discovered_groups(current_user: User = Depends(get_current_user)):
    db = _db()
    try:
        workspace = _ensure_workspace(db, current_user)
        groups, error = _fetch_gateway_groups(str(workspace.id))
        if error:
            raise HTTPException(status_code=503, detail=error)

        configured = {
            group.jid: group
            for group in db.query(TargetGroup).filter(TargetGroup.workspace_id == workspace.id).all()
        }
        response = []
        for item in groups:
            jid = str(item.get("jid") or "").strip()
            if not jid:
                continue
            existing = configured.get(jid)
            response.append(
                {
                    "jid": jid,
                    "name": item.get("name") or jid,
                    "topic": item.get("topic") or "",
                    "participant_count": int(item.get("participant_count") or 0),
                    "is_monitored": existing is not None,
                    "enabled": existing.is_active if existing else False,
                }
            )
        log_activity(
            db,
            str(workspace.id),
            "groups_refreshed",
            "WhatsApp groups refreshed",
            f"Fetched {len(response)} joined groups from WhatsApp",
        )
        db.commit()
        return {"ok": True, "groups": response}
    finally:
        db.close()


@router.get("/groups")
def get_groups(current_user: User = Depends(get_current_user)):
    return get_target_groups(current_user)


class GroupRequest(BaseModel):
    jid: str
    name: str
    custom_offer: str | None = None


@router.post("/groups/add")
def add_group(payload: GroupRequest, current_user: User = Depends(get_current_user)):
    db = _db()
    try:
        workspace = _ensure_workspace(db, current_user)
        existing = (
            db.query(TargetGroup)
            .filter(TargetGroup.workspace_id == workspace.id, TargetGroup.jid == payload.jid.strip())
            .first()
        )
        if existing:
            existing.name = payload.name.strip()
            if payload.custom_offer is not None:
                existing.custom_offer = payload.custom_offer.strip() or None
            existing.is_active = True
        else:
            db.add(
                TargetGroup(
                    workspace_id=workspace.id,
                    jid=payload.jid.strip(),
                    name=payload.name.strip(),
                    custom_offer=payload.custom_offer.strip() if payload.custom_offer else None,
                )
            )
        log_activity(db, str(workspace.id), "group_added", f"Group added: {payload.name.strip()}", payload.jid.strip(), group_jid=payload.jid.strip())
        db.commit()
        return {"ok": True}
    finally:
        db.close()


@router.post("/groups/target/{jid}/toggle")
def toggle_group(jid: str, current_user: User = Depends(get_current_user)):
    db = _db()
    try:
        workspace = _ensure_workspace(db, current_user)
        group = db.query(TargetGroup).filter(TargetGroup.workspace_id == workspace.id, TargetGroup.jid == jid).first()
        if not group:
            raise HTTPException(status_code=404, detail="Group not found")
        group.is_active = not group.is_active
        log_activity(
            db,
            str(workspace.id),
            "group_toggled",
            f"Group {'enabled' if group.is_active else 'paused'}: {group.name}",
            group.jid,
            group_jid=group.jid,
        )
        db.commit()
        return {"ok": True, "enabled": group.is_active}
    finally:
        db.close()


@router.get("/settings")
def get_settings(current_user: User = Depends(get_current_user)):
    db = _db()
    try:
        workspace = _ensure_workspace(db, current_user)
        config = read_agent_config(workspace)
        return {
            "ok": True,
            "settings": {
                "brand_name": config["brand_name"],
                "business_description": config["business_description"],
                "system_prompt": workspace.system_prompt or "",
                "services": config.get("services") or [],
                "keywords": config.get("keywords") or [],
                "auto_reply_enabled": bool(config.get("auto_reply_enabled")),
                "auto_send_matched_leads": bool(config.get("auto_send_matched_leads")),
                "schedule_group_promos": bool(config.get("schedule_group_promos")),
                "promo_interval_hours": int(config.get("promo_interval_hours") or 12),
                "followup_hours": int(config.get("followup_hours") or 6),
                "daily_message_limit": int(config.get("daily_message_limit") or workspace.daily_message_limit or 35),
                "meeting_cta": config.get("meeting_cta"),
                "offer_template": config.get("offer_template"),
                "qualifying_offer": config.get("qualifying_offer"),
            },
        }
    finally:
        db.close()


class SettingsRequest(BaseModel):
    brand_name: str
    business_description: str
    system_prompt: str = ""
    services: list[str] = []
    keywords: list[str] = []
    auto_reply_enabled: bool = True
    auto_send_matched_leads: bool = True
    schedule_group_promos: bool = True
    promo_interval_hours: int = 12
    followup_hours: int = 6
    daily_message_limit: int = 35
    meeting_cta: str
    offer_template: str
    qualifying_offer: str


@router.post("/settings")
def save_settings(payload: SettingsRequest, current_user: User = Depends(get_current_user)):
    db = _db()
    try:
        workspace = _ensure_workspace(db, current_user)
        config = {
            "brand_name": payload.brand_name.strip(),
            "business_description": payload.business_description.strip(),
            "services": [item.strip() for item in payload.services if item.strip()],
            "keywords": [item.strip() for item in payload.keywords if item.strip()],
            "auto_reply_enabled": payload.auto_reply_enabled,
            "auto_send_matched_leads": payload.auto_send_matched_leads,
            "schedule_group_promos": payload.schedule_group_promos,
            "promo_interval_hours": max(payload.promo_interval_hours, 1),
            "followup_hours": max(payload.followup_hours, 1),
            "daily_message_limit": max(payload.daily_message_limit, 1),
            "meeting_cta": payload.meeting_cta.strip(),
            "offer_template": payload.offer_template.strip(),
            "qualifying_offer": payload.qualifying_offer.strip(),
        }
        workspace.company_name = config["brand_name"]
        workspace.business_description = config["business_description"]
        if payload.system_prompt is not None:
            workspace.system_prompt = payload.system_prompt.strip()
        write_agent_config(workspace, config)
        db.commit()
        return {"ok": True}
    finally:
        db.close()


@router.post("/admin/reset")
def reset_workspace_data(current_user: User = Depends(get_current_user)):
    db = _db()
    try:
        workspace = _ensure_workspace(db, current_user)
        db.query(Message).filter(Message.workspace_id == workspace.id).delete(synchronize_session=False)
        db.query(Lead).filter(Lead.workspace_id == workspace.id).delete(synchronize_session=False)
        db.query(TargetGroup).filter(TargetGroup.workspace_id == workspace.id).delete(synchronize_session=False)
        db.query(AgentActivity).filter(AgentActivity.workspace_id == workspace.id).delete(synchronize_session=False)
        workspace.messages_sent_today = 0
        workspace.is_running = False
        db.commit()
        return {"ok": True}
    finally:
        db.close()


@router.get("/system-logs")
def get_system_logs(service: str, current_user: User = Depends(get_current_user)):
    import os
    from collections import deque
    
    allowed_services = {
        "backend": "backend.log",
        "gateway": "gateway.log",
        "worker": "worker.log",
        "beat": "beat.log",
        "frontend": "frontend.log",
    }
    
    if service not in allowed_services:
        raise HTTPException(status_code=400, detail="Invalid service log name")
        
    filename = allowed_services[service]
    log_path = os.path.join("/Users/garvsanwariya/bounty/whatsapp_agent", filename)
    
    if not os.path.exists(log_path):
        return {"ok": True, "logs": f"Log file for {service} ({filename}) does not exist yet."}
        
    try:
        with open(log_path, "r", encoding="utf-8", errors="ignore") as f:
            lines = deque(f, 200)
            return {"ok": True, "logs": "".join(lines)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to read logs: {str(e)}")


@router.post("/outreach/trigger")
def trigger_outreach(current_user: User = Depends(get_current_user)):
    db = _db()
    try:
        workspace = _ensure_workspace(db, current_user)
        config = read_agent_config(workspace)
        offer_template = config.get("offer_template") or config.get("qualifying_offer") or ""
        
        if not offer_template:
            raise HTTPException(status_code=400, detail="No offer template or qualification message configured.")
            
        groups = db.query(TargetGroup).filter(TargetGroup.workspace_id == workspace.id, TargetGroup.is_active.is_(True)).all()
        if not groups:
            return {"ok": True, "message": "No active monitored groups found to send outreach to."}
            
        sent_count = 0
        from app.tasks.whatsapp_tasks import send_whatsapp_message
        from datetime import datetime, timezone
        from app.services.crm import bump_sent_counter
        
        now = datetime.now(timezone.utc)
        for group in groups:
            payload = group.custom_offer or offer_template
            send_whatsapp_message.delay(str(workspace.id), group.jid, payload)
            
            group.last_promo_sent_at = now
            bump_sent_counter(workspace)
            log_activity(
                db,
                str(workspace.id),
                "group_promo_sent",
                f"Manual test offer posted in {group.name}",
                detail=payload,
                group_jid=group.jid,
            )
            sent_count += 1
            
        db.commit()
        return {"ok": True, "message": f"Successfully triggered outreach to {sent_count} active group(s)."}
    finally:
        db.close()


@router.get("/agent-logs")
async def stream_agent_logs(request: Request, email: str = "demo@local.dev"):
    """
    SSE endpoint that streams live agent activity logs to the frontend.
    Polls the agent_activities table every 2 seconds and pushes new entries.
    Uses email query param for EventSource compatibility (no custom headers).
    """
    # Resolve workspace from email (dev-mode friendly)
    db = _db()
    try:
        user = db.query(User).filter(User.email == email).first()
        if not user:
            user = User(email=email)
            db.add(user)
            db.commit()
            db.refresh(user)
        workspace = _ensure_workspace(db, user)
        workspace_id = workspace.id
    finally:
        db.close()

    async def event_generator() -> AsyncGenerator[str, None]:
        last_seen_id = None

        # Bootstrap: send the last 20 existing logs so the panel isn't empty on open
        db_init = _db()
        try:
            existing = (
                db_init.query(AgentActivity)
                .filter(AgentActivity.workspace_id == workspace_id)
                .order_by(AgentActivity.created_at.desc())
                .limit(20)
                .all()
            )
            existing.reverse()
            for entry in existing:
                last_seen_id = entry.id
                payload = json.dumps({
                    "id": str(entry.id),
                    "title": entry.title,
                    "detail": entry.detail or "",
                    "event_type": entry.event_type,
                    "ts": entry.created_at.isoformat() if entry.created_at else "",
                })
                yield f"data: {payload}\n\n"
        finally:
            db_init.close()

        # Stream new entries as they come in
        while True:
            if await request.is_disconnected():
                break

            db_poll = _db()
            try:
                query = (
                    db_poll.query(AgentActivity)
                    .filter(AgentActivity.workspace_id == workspace_id)
                    .order_by(AgentActivity.created_at.asc())
                )
                if last_seen_id:
                    # Fetch entries newer than last seen using created_at of last_seen_id
                    last_entry = db_poll.query(AgentActivity).filter(AgentActivity.id == last_seen_id).first()
                    if last_entry:
                        query = query.filter(AgentActivity.created_at > last_entry.created_at)

                new_entries = query.limit(50).all()
                for entry in new_entries:
                    last_seen_id = entry.id
                    payload = json.dumps({
                        "id": str(entry.id),
                        "title": entry.title,
                        "detail": entry.detail or "",
                        "event_type": entry.event_type,
                        "ts": entry.created_at.isoformat() if entry.created_at else "",
                    })
                    yield f"data: {payload}\n\n"
            finally:
                db_poll.close()

            await asyncio.sleep(2)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )
