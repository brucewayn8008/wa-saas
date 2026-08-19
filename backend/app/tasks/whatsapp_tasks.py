"""Outbound WhatsApp send tasks — always via MessagingProvider (wacli near-term)."""

from __future__ import annotations

import logging
from types import SimpleNamespace

from celery import shared_task

from app.core.config import settings
from app.db.session import SessionLocal
from app.messaging.factory import get_provider
from app.models.database import WANumber, Workspace

logger = logging.getLogger(__name__)


def _provider_for_workspace(workspace_id: str):
    db = SessionLocal()
    try:
        number = (
            db.query(WANumber)
            .filter(WANumber.workspace_id == workspace_id, WANumber.status == "CONNECTED")
            .order_by(WANumber.id.asc())
            .first()
        )
        if number is not None:
            return get_provider(number)

        ws = db.query(Workspace).filter(Workspace.id == workspace_id).first()
        provider_name = (ws.default_provider if ws else None) or "wacli"
        return get_provider(
            SimpleNamespace(
                provider=provider_name,
                workspace_id=str(workspace_id),
                wacli_account=str(workspace_id),
                wacli_store_dir=None,
            )
        )
    finally:
        db.close()


@shared_task(
    name="whatsapp.send_message",
    autoretry_for=(RuntimeError,),
    retry_backoff=True,
    retry_backoff_max=60,
    max_retries=3,
)
def send_whatsapp_message(workspace_id: str, to: str, text: str):
    """
    Dispatch a text message for a workspace through the configured MessagingProvider.
    Near-term default is wacli (`WacliProvider`). Callers must have already passed
    `outreach_policy.gate()` — this task does not re-check policy.
    """
    logger.info("Dispatching message via MessagingProvider for WS %s to %s", workspace_id, to)
    provider = _provider_for_workspace(workspace_id)
    result = provider.send_text(to, text)
    if not result.success:
        # Raise so Celery can retry transient CLI/network failures.
        raise RuntimeError(result.error or "wacli_send_failed")
    logger.info(
        "Message sent successfully wa_message_id=%s provider=%s",
        result.wa_message_id,
        type(provider).__name__,
    )
    return {"success": True, "wa_message_id": result.wa_message_id}


@shared_task(
    name="whatsapp.send_media",
    autoretry_for=(RuntimeError,),
    retry_backoff=True,
    retry_backoff_max=60,
    max_retries=3,
)
def send_whatsapp_media(workspace_id: str, to: str, asset_id: str, caption: str | None = None):
    """Send a MediaAsset to a lead via the configured MessagingProvider.

    Downloads/resolves the asset into an OutgoingMedia struct then calls
    provider.send_media(). Callers must have already passed outreach_policy.gate().
    """
    from app.core.tenancy import tenant_context
    from app.services.media import get_asset, resolve_outgoing_media

    with tenant_context(workspace_id) as db:
        asset = get_asset(db, workspace_id, asset_id)
        if not asset:
            logger.error("[send_media] asset %s not found for workspace %s", asset_id, workspace_id)
            return {"success": False, "error": "asset_not_found"}
        outgoing = resolve_outgoing_media(asset)

    provider = _provider_for_workspace(workspace_id)
    result = provider.send_media(to, outgoing, caption)

    # Clean up temp file materialised for wacli (path only, no URL)
    if outgoing.path and not outgoing.url:
        import os
        try:
            os.unlink(outgoing.path)
        except OSError:
            pass

    if not result.success:
        raise RuntimeError(result.error or "send_media_failed")

    logger.info("[send_media] sent asset=%s wa_id=%s", asset_id, result.wa_message_id)
    return {"success": True, "wa_message_id": result.wa_message_id}


# Keep settings import referenced so ENV overrides are loaded with the worker.
_ = settings.WACLI_BIN
