import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import get_db
from app.models.database import Lead, Message as DBMessage, MessageRole, TargetGroup, Workspace
from app.services import debounce
from app.services.conversations import ensure_conversation
from app.services.crm import log_activity, message_looks_like_need, read_agent_config
from app.tasks.ai_tasks import generate_ai_reply

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/message")
async def receive_webhook(request: Request, db: Session = Depends(get_db)):
    try:
        payload = await request.json()
    except Exception:
        logger.error("Invalid webhook body")
        return {"error": "invalid_json"}

    logger.info("Received webhook: %s", payload)

    workspace_id = payload.get("workspace_id")
    chat_jid = (payload.get("chat_jid") or "").strip()
    sender_jid = (payload.get("sender_jid") or chat_jid).strip()
    sender_name = (payload.get("sender") or "Unknown").strip() or "Unknown"
    text = (payload.get("text") or "").strip()
    from_me = bool(payload.get("fromMe"))
    is_group = bool(payload.get("is_group"))

    if from_me or not workspace_id or not text:
        return {"status": "ignored"}

    workspace = db.query(Workspace).filter(Workspace.id == workspace_id).first()
    if not workspace:
        return {"error": "workspace_not_found"}

    lead_jid = sender_jid if is_group else chat_jid
    source_group = None
    auto_send_allowed = False

    try:
        if is_group:
            # Only process messages from monitored groups
            source_group = (
                db.query(TargetGroup)
                .filter(
                    TargetGroup.workspace_id == workspace.id,
                    TargetGroup.jid == chat_jid,
                    TargetGroup.is_active.is_(True),
                )
                .first()
            )
            if not source_group:
                return {"status": "ignored_group"}

        # Check if we already know this person (existing lead with prior conversation)
        existing_lead = (
            db.query(Lead)
            .filter(Lead.workspace_id == workspace.id, Lead.jid == lead_jid)
            .first()
        )
        existing_message_count = 0
        if existing_lead:
            existing_message_count = (
                db.query(DBMessage)
                .filter(DBMessage.lead_id == existing_lead.id)
                .count()
            )

        is_ongoing_conversation = existing_message_count > 0

        if is_group:
            config = read_agent_config(workspace)
            # For ongoing conversations: always continue regardless of keywords
            # For new group contacts: only engage if message shows intent/need
            if not is_ongoing_conversation and not message_looks_like_need(text, list(config.get("keywords") or [])):
                log_activity(
                    db,
                    str(workspace.id),
                    "group_message_skipped",
                    f"Skipped low-signal message from new contact in {source_group.name}",
                    detail=text,
                    group_jid=chat_jid,
                )
                db.commit()
                return {"status": "ignored_low_signal"}
            auto_send_allowed = True
        else:
            # Direct messages: always engage (someone DMing us is high intent)
            auto_send_allowed = True

        lead = existing_lead
        if not lead:
            lead = Lead(
                workspace_id=workspace.id,
                jid=lead_jid,
                name=sender_name,
                source="GROUP" if is_group else "DIRECT",
                source_group_jid=chat_jid if is_group else None,
                source_group_name=source_group.name if source_group else None,
            )
            db.add(lead)
            db.flush()

        lead.name = sender_name or lead.name
        lead.last_inbound_at = datetime.now(timezone.utc)
        lead.needs_response = True
        if is_group:
            lead.source = "GROUP"
            lead.source_group_jid = chat_jid
            lead.source_group_name = source_group.name if source_group else lead.source_group_name

        content = text
        if is_group and source_group:
            content = f"[Group: {source_group.name}] {text}"

        inbound_msg = DBMessage(
            workspace_id=workspace.id,
            lead_id=lead.id,
            role=MessageRole.USER,
            content=content,
        )
        db.add(inbound_msg)
        db.flush()

        # Ensure a Conversation exists and stamp the inbound (drives 24h window + inbox).
        ensure_conversation(db, str(workspace.id), str(lead.id), mark_inbound=True)

        event_type = "direct_message_received" if not is_group else ("conversation_continued" if is_ongoing_conversation else "lead_detected")
        log_activity(
            db,
            str(workspace.id),
            event_type,
            f"Message received from {lead.name}" + (" (ongoing)" if is_ongoing_conversation else ""),
            detail=content,
            lead_id=str(lead.id),
            group_jid=chat_jid if is_group else None,
        )
        db.commit()
    except Exception as exc:
        logger.exception("Webhook persistence failed: %s", exc)
        db.rollback()
        return {"error": "db_error"}

    # Debounce: mark this inbound as the latest, then schedule the reply after a
    # short countdown so rapid multi-bubble bursts coalesce into one reply.
    try:
        debounce.set_pending_reply(str(lead.id), str(inbound_msg.id))
        generate_ai_reply.apply_async(
            args=(str(workspace.id), str(lead.id)),
            kwargs={"auto_send_allowed": auto_send_allowed, "trigger_message_id": str(inbound_msg.id)},
            countdown=settings.REPLY_DEBOUNCE_SECONDS,
        )
    except Exception as exc:
        logger.error("Failed to enqueue AI task: %s", exc)

    return {"status": "success", "lead_id": str(lead.id)}
