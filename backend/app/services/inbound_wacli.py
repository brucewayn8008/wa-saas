"""Ingest a wacli webhook message into CRM + enqueue the AI reply (Feature 06)."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Optional
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.tenancy import tenant_context
from app.db.session import SessionLocal
from app.models.database import Lead, Message as DBMessage, MessageRole, TargetGroup, Workspace
from app.services import debounce
from app.services import listening as listening_svc
from app.services.conversations import ensure_conversation
from app.services.crm import log_activity, read_agent_config

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ResolvedNumber:
    id: str
    workspace_id: str


@dataclass(frozen=True)
class IngestResult:
    status: str
    lead_id: Optional[str] = None
    detail: Optional[str] = None


def _is_group_jid(chat: str) -> bool:
    return (chat or "").endswith("@g.us")


def resolve_wacli_number(
    db: Session,
    *,
    account: Optional[str] = None,
    store_dir: Optional[str] = None,
    workspace_id: Optional[str] = None,
) -> Optional[ResolvedNumber]:
    """Map a wacli sync identity onto a WANumber via SECURITY DEFINER (RLS-safe)."""
    ws_uuid = None
    if workspace_id:
        try:
            ws_uuid = UUID(str(workspace_id))
        except (TypeError, ValueError):
            return None

    row = db.execute(
        text(
            "SELECT id, workspace_id FROM public.resolve_wacli_number("
            ":account, :store_dir, :workspace_id)"
        ),
        {
            "account": account or None,
            "store_dir": store_dir or None,
            "workspace_id": ws_uuid,
        },
    ).first()
    if not row:
        return None
    return ResolvedNumber(id=str(row[0]), workspace_id=str(row[1]))


def ingest_wacli_message(
    payload: dict[str, Any],
    *,
    account: Optional[str] = None,
    store_dir: Optional[str] = None,
    workspace_id: Optional[str] = None,
) -> IngestResult:
    """Persist an inbound wacli message and debounce-enqueue the AI reply."""
    event_type = payload.get("EventType") or "message"
    if event_type != "message":
        return IngestResult(status="ignored_event", detail=str(event_type))

    from_me = bool(payload.get("FromMe") if "FromMe" in payload else payload.get("fromMe"))
    if from_me:
        return IngestResult(status="ignored_from_me")

    chat = (payload.get("Chat") or payload.get("chat") or "").strip()
    sender = (
        payload.get("SenderJID")
        or payload.get("Sender")
        or payload.get("sender_jid")
        or chat
    )
    sender = (sender or "").strip()
    text_body = (payload.get("Text") or payload.get("text") or "").strip()
    wa_id = (payload.get("ID") or payload.get("Id") or payload.get("id") or "").strip() or None
    chat_name = (payload.get("ChatName") or payload.get("chat_name") or "").strip() or "Unknown"

    # Allow messages that carry media even if text_body is empty
    media_url = (payload.get("MediaURL") or payload.get("media_url") or "").strip() or None
    media_mime = (payload.get("MimeType") or payload.get("mime_type") or "").strip() or None
    media_filename = (payload.get("FileName") or payload.get("filename") or "").strip() or None

    if not chat or (not text_body and not media_url):
        return IngestResult(status="ignored_empty")

    bootstrap = SessionLocal()
    try:
        number = resolve_wacli_number(
            bootstrap,
            account=account,
            store_dir=store_dir,
            workspace_id=workspace_id,
        )
    finally:
        bootstrap.close()

    if number is None:
        return IngestResult(status="unresolved_tenant")

    is_group = _is_group_jid(chat)
    lead_jid = sender if is_group else chat

    with tenant_context(number.workspace_id) as db:
        workspace = db.query(Workspace).filter(Workspace.id == number.workspace_id).first()
        if not workspace:
            return IngestResult(status="workspace_not_found")

        if wa_id:
            prior = (
                db.query(DBMessage)
                .filter(DBMessage.workspace_id == workspace.id, DBMessage.wa_message_id == wa_id)
                .first()
            )
            if prior:
                return IngestResult(status="duplicate", lead_id=str(prior.lead_id))

        source_group = None
        auto_send_allowed = False

        if is_group:
            source_group = (
                db.query(TargetGroup)
                .filter(
                    TargetGroup.workspace_id == workspace.id,
                    TargetGroup.jid == chat,
                    TargetGroup.is_active.is_(True),
                )
                .first()
            )
            if not source_group:
                return IngestResult(status="ignored_group")

        existing_lead = (
            db.query(Lead)
            .filter(Lead.workspace_id == workspace.id, Lead.jid == lead_jid)
            .first()
        )
        existing_message_count = 0
        if existing_lead:
            existing_message_count = (
                db.query(DBMessage).filter(DBMessage.lead_id == existing_lead.id).count()
            )
        is_ongoing = existing_message_count > 0

        intent_match = None
        if is_group:
            config = read_agent_config(workspace)
            intent_match = listening_svc.match_intent(
                text_body,
                keywords=list(config.get("keywords") or []),
                services=list(config.get("services") or []),
            )
            if not is_ongoing and not intent_match.matched:
                log_activity(
                    db,
                    str(workspace.id),
                    "group_message_skipped",
                    f"Skipped low-signal message from new contact in {source_group.name}",
                    detail=text_body,
                    group_jid=chat,
                )
                return IngestResult(status="ignored_low_signal")
            auto_send_allowed = True
        else:
            auto_send_allowed = True

        lead = existing_lead
        if not lead:
            lead = Lead(
                workspace_id=workspace.id,
                jid=lead_jid,
                name=chat_name if not is_group else (chat_name or "Unknown"),
                source="GROUP" if is_group else "DIRECT",
                source_group_jid=chat if is_group else None,
                source_group_name=source_group.name if source_group else None,
            )
            db.add(lead)
            db.flush()

        if not is_group and chat_name and chat_name != "Unknown":
            lead.name = chat_name
        lead.last_inbound_at = datetime.now(timezone.utc)
        lead.needs_response = True
        if is_group and source_group:
            lead.source = "GROUP"
            lead.source_group_jid = chat
            lead.source_group_name = source_group.name

        content = text_body
        if is_group and source_group:
            content = f"[Group: {source_group.name}] {text_body}"

        inbound_msg = DBMessage(
            workspace_id=workspace.id,
            lead_id=lead.id,
            role=MessageRole.USER,
            content=content or "[media]",
            wa_message_id=wa_id,
        )
        db.add(inbound_msg)
        db.flush()

        # Feature 16 — audit row for group intent (auto-reply finalized in generate_ai_reply).
        if is_group and source_group and intent_match and intent_match.matched and not is_ongoing:
            listening_svc.record_detection(
                db,
                str(workspace.id),
                lead_id=str(lead.id),
                group_jid=chat,
                group_name=source_group.name,
                sender_jid=lead_jid,
                original_message=text_body,
                match=intent_match,
            )

        # Store inbound media against the conversation (best-effort — non-fatal if it fails)
        if media_url and media_mime:
            try:
                from app.services.media import ingest_inbound_media
                asset = ingest_inbound_media(
                    db,
                    workspace_id=str(workspace.id),
                    lead_id=str(lead.id),
                    media_url=media_url,
                    mime=media_mime,
                    filename=media_filename or None,
                )
                if asset is not None:
                    inbound_msg.media_asset_id = asset.id
                    db.flush()
            except Exception as exc:
                logger.warning("[inbound] inbound media ingest failed: %s", exc)

        ensure_conversation(
            db,
            str(workspace.id),
            str(lead.id),
            wa_number_id=number.id,
            mark_inbound=True,
        )

        event = (
            "direct_message_received"
            if not is_group
            else ("conversation_continued" if is_ongoing else "lead_detected")
        )
        log_activity(
            db,
            str(workspace.id),
            event,
            f"Message received from {lead.name}" + (" (ongoing)" if is_ongoing else ""),
            detail=content,
            lead_id=str(lead.id),
            group_jid=chat if is_group else None,
        )
        lead_id = str(lead.id)
        workspace_id_str = str(workspace.id)
        inbound_id = str(inbound_msg.id)

    try:
        from app.tasks.ai_tasks import generate_ai_reply

        debounce.set_pending_reply(lead_id, inbound_id)
        generate_ai_reply.apply_async(
            args=(workspace_id_str, lead_id),
            kwargs={"auto_send_allowed": auto_send_allowed, "trigger_message_id": inbound_id},
            countdown=settings.REPLY_DEBOUNCE_SECONDS,
        )
    except Exception as exc:
        logger.error("Failed to enqueue AI task: %s", exc)
        return IngestResult(status="enqueued_failed", lead_id=lead_id, detail=str(exc))

    return IngestResult(status="success", lead_id=lead_id)


def handle_wacli_presence(
    payload: dict[str, Any],
    *,
    account: Optional[str] = None,
    store_dir: Optional[str] = None,
    workspace_id: Optional[str] = None,
) -> IngestResult:
    """Mark typing presence for debounce wait."""
    state = (payload.get("State") or payload.get("state") or "").lower()
    chat = (payload.get("Chat") or payload.get("chat") or "").strip()
    if not chat or _is_group_jid(chat):
        return IngestResult(status="ignored_presence")

    bootstrap = SessionLocal()
    try:
        number = resolve_wacli_number(
            bootstrap,
            account=account,
            store_dir=store_dir,
            workspace_id=workspace_id,
        )
    finally:
        bootstrap.close()

    if number is None:
        return IngestResult(status="unresolved_tenant")

    with tenant_context(number.workspace_id) as db:
        lead = (
            db.query(Lead)
            .filter(Lead.workspace_id == number.workspace_id, Lead.jid == chat)
            .first()
        )
        if not lead:
            return IngestResult(status="ignored_unknown_lead")
        lead_id = str(lead.id)

    if state in ("composing", "recording"):
        debounce.mark_user_typing(lead_id)
    else:
        debounce.clear_user_typing(lead_id)
    return IngestResult(status="presence_ok", lead_id=lead_id)
