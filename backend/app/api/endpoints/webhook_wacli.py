"""wacli sync inbound webhook (Feature 06).

Unauthenticated at the Clerk layer — authenticity is HMAC via X-Wacli-Signature.
Tenant identity comes from query/header account hints (or single-tenant fallback).
"""

from __future__ import annotations

import json
import logging
from typing import Optional

from fastapi import APIRouter, Header, Query, Request
from fastapi.responses import JSONResponse

from app.core.config import settings
from app.messaging.wacli_sig import verify_wacli_signature
from app.services.inbound_wacli import handle_wacli_presence, ingest_wacli_message

router = APIRouter()
logger = logging.getLogger(__name__)


def _tenant_hints(
    *,
    account: Optional[str],
    store: Optional[str],
    workspace_id: Optional[str],
    x_wacli_account: Optional[str],
) -> dict:
    return {
        "account": account or x_wacli_account,
        "store_dir": store,
        "workspace_id": workspace_id,
    }


@router.post("/wacli")
async def wacli_webhook(
    request: Request,
    account: Optional[str] = Query(None, description="wacli --account / wacli_account"),
    store: Optional[str] = Query(None, description="wacli --store path"),
    workspace_id: Optional[str] = Query(None, description="tenant workspace UUID"),
    x_wacli_signature: Optional[str] = Header(None, alias="X-Wacli-Signature"),
    x_wacli_account: Optional[str] = Header(None, alias="X-Wacli-Account"),
):
    raw = await request.body()
    secret = (settings.WACLI_WEBHOOK_SECRET or "").strip()
    if not secret:
        logger.error("WACLI_WEBHOOK_SECRET is not configured")
        return JSONResponse({"error": "webhook_not_configured"}, status_code=503)

    if not verify_wacli_signature(secret, raw, x_wacli_signature):
        logger.warning("wacli webhook signature mismatch")
        return JSONResponse({"error": "invalid_signature"}, status_code=401)

    try:
        payload = json.loads(raw.decode("utf-8") or "{}")
    except Exception:
        return JSONResponse({"error": "invalid_json"}, status_code=400)

    if not isinstance(payload, dict):
        return JSONResponse({"error": "invalid_json"}, status_code=400)

    hints = _tenant_hints(
        account=account,
        store=store,
        workspace_id=workspace_id,
        x_wacli_account=x_wacli_account,
    )
    event_type = payload.get("EventType") or "message"
    logger.info(
        "wacli webhook event=%s chat=%s account=%s",
        event_type,
        payload.get("Chat") or payload.get("chat"),
        hints.get("account"),
    )

    if event_type == "chat_presence":
        result = handle_wacli_presence(payload, **hints)
        return {"status": result.status, "lead_id": result.lead_id}

    if event_type == "receipt":
        return {"status": "ignored_receipt"}

    result = ingest_wacli_message(payload, **hints)
    body = {"status": result.status, "lead_id": result.lead_id}
    if result.detail:
        body["detail"] = result.detail

    if result.status == "unresolved_tenant":
        return JSONResponse(body, status_code=400)
    if result.status == "workspace_not_found":
        return JSONResponse(body, status_code=404)
    return body
