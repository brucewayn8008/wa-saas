"""Settings endpoints — agent config, team members, agent toggle.

GET  /settings           → AgentSettings
PUT  /settings           → save and return AgentSettings
GET  /settings/team      → list tenant members
POST /settings/agent     → toggle agent enabled/disabled
"""
from __future__ import annotations

import json

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.auth import AuthContext, get_auth_context, get_db, require_role
from app.models.database import TenantMember, Workspace
from app.services.crm import read_agent_config, write_agent_config

router = APIRouter()


def _settings_out(ws: Workspace) -> dict:
    config = read_agent_config(ws)
    return {
        "brandName": ws.company_name or config.get("brand_name", ""),
        "businessDescription": ws.business_description or config.get("business_description", ""),
        "services": config.get("services", []),
        "tone": config.get("tone", "friendly_professional"),
        "offer": config.get("qualifying_offer", ""),
        "bookingLink": config.get("meeting_cta", ""),
        "businessHours": config.get("business_hours", ""),
        "disclosureLine": ws.disclosure_line or "",
        "agentEnabled": ws.agent_enabled,
    }


class AgentSettingsBody(BaseModel):
    brandName: str
    businessDescription: str
    services: list[str] = []
    tone: str = "friendly_professional"
    offer: str = ""
    bookingLink: str = ""
    businessHours: str = ""
    disclosureLine: str = ""
    agentEnabled: bool = False


class AgentToggleBody(BaseModel):
    enabled: bool


@router.get("")
def get_settings(
    ctx: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    ws = db.query(Workspace).filter(Workspace.id == ctx.tenant.id).first()
    if not ws:
        raise HTTPException(status_code=404, detail="Tenant not found")
    return {"success": True, "data": _settings_out(ws)}


@router.put("")
def save_settings(
    body: AgentSettingsBody,
    ctx: AuthContext = Depends(require_role("admin")),
    db: Session = Depends(get_db),
):
    ws = db.query(Workspace).filter(Workspace.id == ctx.tenant.id).first()
    if not ws:
        raise HTTPException(status_code=404, detail="Tenant not found")

    ws.company_name = body.brandName.strip()
    ws.business_description = body.businessDescription.strip()
    ws.disclosure_line = body.disclosureLine.strip()
    ws.agent_enabled = body.agentEnabled

    existing = read_agent_config(ws)
    existing.update({
        "brand_name": body.brandName.strip(),
        "business_description": body.businessDescription.strip(),
        "services": [s.strip() for s in body.services if s.strip()],
        "tone": body.tone,
        "qualifying_offer": body.offer.strip(),
        "meeting_cta": body.bookingLink.strip(),
        "business_hours": body.businessHours.strip(),
    })
    write_agent_config(ws, existing)
    db.commit()
    db.refresh(ws)
    return {"success": True, "data": _settings_out(ws)}


@router.get("/team")
def list_team(
    ctx: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    members = (
        db.query(TenantMember)
        .filter(TenantMember.workspace_id == ctx.tenant.id)
        .all()
    )
    return {
        "success": True,
        "data": [
            {
                "id": str(m.id),
                "name": m.email.split("@")[0] if m.email else m.clerk_user_id,
                "email": m.email or "",
                "role": m.role,
            }
            for m in members
        ],
    }


@router.post("/agent")
def toggle_agent(
    body: AgentToggleBody,
    ctx: AuthContext = Depends(require_role("admin")),
    db: Session = Depends(get_db),
):
    ws = db.query(Workspace).filter(Workspace.id == ctx.tenant.id).first()
    if not ws:
        raise HTTPException(status_code=404, detail="Tenant not found")
    ws.agent_enabled = body.enabled
    db.commit()
    return {"success": True, "data": {"agentEnabled": ws.agent_enabled}}
