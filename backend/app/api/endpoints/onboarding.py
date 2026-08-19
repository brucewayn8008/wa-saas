"""Onboarding (Feature 10): configure the agent, connect a WhatsApp number, go live.

All writes are admin-only and tenant-scoped. Number creation runs on an RLS
session and is gated by the tenant's plan number-limit.
"""

import logging
from typing import Optional

import httpx
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.auth import AuthContext, get_auth_context, get_db, get_tenant_db, require_role
from app.core.config import settings
from app.models.database import WANumber, WhatsAppSession, Workspace
from app.services import billing

logger = logging.getLogger(__name__)
router = APIRouter()


class ConfigureBody(BaseModel):
    company_name: Optional[str] = None
    business_description: Optional[str] = None
    system_prompt: Optional[str] = None
    disclosure_line: Optional[str] = None
    agent_config: Optional[str] = None  # JSON string (services, tone, offer, hours)


@router.post("/configure")
async def configure(
    body: ConfigureBody,
    ctx: AuthContext = Depends(require_role("admin")),
    db: Session = Depends(get_tenant_db),
):
    ws = db.query(Workspace).filter(Workspace.id == ctx.tenant.id).first()
    if not ws:
        raise HTTPException(status_code=404, detail="Tenant not found")
    for field in ("company_name", "business_description", "system_prompt", "disclosure_line", "agent_config"):
        value = getattr(body, field)
        if value is not None:
            setattr(ws, field, value)
    db.commit()
    return {"success": True, "data": {"id": str(ws.id), "company_name": ws.company_name}}


class ConnectNumberBody(BaseModel):
    provider: str = "wacli"  # "wacli" | "whatsmeow" | "cloud_api" (deferred)
    phone_number_id: Optional[str] = None
    waba_id: Optional[str] = None
    access_token: Optional[str] = None
    jid: Optional[str] = None
    wacli_store_dir: Optional[str] = None
    wacli_account: Optional[str] = None


@router.post("/connect-number")
async def connect_number(
    body: ConnectNumberBody,
    ctx: AuthContext = Depends(require_role("admin")),
    db: Session = Depends(get_tenant_db),
):
    if body.provider not in ("wacli", "whatsmeow", "cloud_api"):
        raise HTTPException(status_code=400, detail="provider must be wacli, whatsmeow, or cloud_api")
    if body.provider == "cloud_api" and not (body.phone_number_id and body.access_token):
        raise HTTPException(status_code=400, detail="cloud_api requires phone_number_id and access_token")

    sub = billing.get_or_create_subscription(db, ctx.tenant.id)
    current = db.query(WANumber).filter(WANumber.workspace_id == ctx.tenant.id).count()
    if not billing.can_add_number(billing.get_plan(sub.plan), current):
        raise HTTPException(status_code=402, detail="Number limit reached for your plan")

    # wacli / whatsmeow need pairing before CONNECTED; cloud_api can mark connected with creds.
    if body.provider == "cloud_api":
        status = "CONNECTED"
    else:
        status = "QR_PENDING"

    num = WANumber(
        workspace_id=ctx.tenant.id,
        provider=body.provider,
        phone_number_id=body.phone_number_id,
        waba_id=body.waba_id,
        access_token=body.access_token,
        jid=body.jid,
        wacli_store_dir=body.wacli_store_dir,
        wacli_account=body.wacli_account or (str(ctx.tenant.id) if body.provider == "wacli" else None),
        status=status,
    )
    db.add(num)
    # keep the tenant default provider in step with the first connected number
    ws = db.query(Workspace).filter(Workspace.id == ctx.tenant.id).first()
    if ws:
        ws.default_provider = body.provider
    db.commit()
    db.refresh(num)
    return {"success": True, "data": {"id": str(num.id), "provider": num.provider, "status": num.status}}


@router.post("/go-live")
async def go_live(
    ctx: AuthContext = Depends(require_role("admin")),
    db: Session = Depends(get_tenant_db),
):
    ws = db.query(Workspace).filter(Workspace.id == ctx.tenant.id).first()
    if not ws:
        raise HTTPException(status_code=404, detail="Tenant not found")
    # Compliance guard: the agent may not go live without an AI disclosure line.
    if not (ws.disclosure_line and ws.disclosure_line.strip()):
        raise HTTPException(status_code=400, detail="Set an AI disclosure line before going live")
    if db.query(WANumber).filter(WANumber.workspace_id == ctx.tenant.id).count() == 0:
        raise HTTPException(status_code=400, detail="Connect a WhatsApp number before going live")
    ws.agent_enabled = True
    ws.is_running = True
    db.commit()
    return {"success": True, "data": {"agent_enabled": True}}


@router.get("/qr")
async def get_qr_status(
    ctx: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    """Poll for wacli QR code and connection status.

    Returns:
      status — UNCONFIGURED | QR_PENDING | CONNECTED | LOGGED_OUT
      qr     — base64/string QR payload when status is QR_PENDING, else null
    """
    num = (
        db.query(WANumber)
        .filter(WANumber.workspace_id == ctx.tenant.id)
        .order_by(WANumber.id)
        .first()
    )

    if not num:
        # Auto-provision a wacli number and kick the gateway
        num = WANumber(
            workspace_id=ctx.tenant.id,
            provider="wacli",
            wacli_account=str(ctx.tenant.id),
            status="QR_PENDING",
        )
        db.add(num)
        ws = db.query(Workspace).filter(Workspace.id == ctx.tenant.id).first()
        if ws:
            ws.default_provider = "wacli"
        db.commit()
        db.refresh(num)
        # Fire-and-forget: ask the gateway to start a QR session
        _kick_gateway(str(ctx.tenant.id))

    raw = (num.status or "UNCONFIGURED").upper()

    # Also check the legacy WhatsAppSession table — the Go gateway writes QR there.
    legacy_session = (
        db.query(WhatsAppSession)
        .filter(WhatsAppSession.workspace_id == ctx.tenant.id)
        .first()
    )
    legacy_raw = (legacy_session.status if legacy_session else "UNCONFIGURED").upper()
    legacy_qr = legacy_session.qr_code if legacy_session else None

    # Merge: prefer the WANumber status unless the legacy session is more advanced.
    if legacy_raw in ("CONNECTED", "READY"):
        status = "CONNECTED"
        # Sync WANumber so future polls are consistent
        num.status = "CONNECTED"
        db.commit()
    elif legacy_raw in ("QR_PENDING", "WAITING_FOR_SCAN") or raw in ("QR_PENDING", "QR_WAITING"):
        status = "QR_PENDING"
        qr_value = legacy_qr or num.qr_code
        if not qr_value:
            _kick_gateway(str(ctx.tenant.id))
    elif raw == "CONNECTED":
        status = "CONNECTED"
    else:
        status = "QR_PENDING"  # Keep showing spinner — gateway is starting
        qr_value = None
        _kick_gateway(str(ctx.tenant.id))

    qr_value = (legacy_qr or num.qr_code) if status == "QR_PENDING" else None

    return {
        "success": True,
        "data": {
            "status": status,
            "qr": qr_value,
        },
    }


def _kick_gateway(workspace_id: str) -> None:
    """Non-blocking call to start a wacli session on the gateway."""
    try:
        httpx.get(
            f"{settings.GO_GATEWAY_URL}/api/session/start",
            params={"workspace_id": workspace_id},
            timeout=5.0,
        )
    except Exception as exc:
        logger.warning("Gateway kick failed (non-fatal): %s", exc)
