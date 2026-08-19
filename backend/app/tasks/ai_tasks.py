"""AI reply orchestration (Feature 13 + agent media send).

This Celery task is the seam between transport (inbound webhook) and the AI layer.
It is deliberately thin: it loads state, runs the `ai/` pipeline, enforces the
compliance gate + mandatory disclosure, and delegates delivery. It never builds
prompts itself and never talks to a transport directly except via the send task.

Order of operations per inbound turn:
  1. Load tenant + lead + conversation. Bail if the agent is paused (human takeover),
     disabled, or the meeting is already confirmed.
  2. Opt-out check (deterministic) → set do_not_contact, stop. Compliance first.
  3. Debounce → if a newer inbound arrived, skip (the newer task will reply).
  4. Recall memory + media catalogue → build persona/system prompt → run the state machine.
  5. Persist lead state + extracted facts.
  6. Gate the send (outreach_policy). If allowed + auto-send criteria met, apply a
     human-like typing delay and deliver (text or tenant media); otherwise store a DRAFT.
"""

import logging
from datetime import datetime, timezone
from typing import Any, Callable, Optional

from celery import shared_task
from sqlalchemy.orm import Session

from app.ai import persona, pipeline
from app.core.config import settings
from app.core.outreach_policy import OutreachDecision, OutreachKind, gate
from app.core.tenancy import set_tenant
from app.db.session import SessionLocal
from app.messaging.factory import get_provider
from app.models.database import (
    AgentActivity,
    Lead,
    LeadStatus,
    Message as DBMessage,
    MessageRole,
    MessageStatus,
    WANumber,
    Workspace,
)
from app.services import listening as listening_svc
from app.services import media as media_svc
from app.services import memory
from app.services.conversations import ensure_conversation
from app.services.crm import bump_sent_counter, daily_quota_available, log_activity, read_agent_config
from app.services.typing_delay import apply_typing_delay
from app.tasks.whatsapp_tasks import send_whatsapp_media, send_whatsapp_message

logger = logging.getLogger(__name__)


def log_agent_step(db: Session, workspace_id: str, lead_id: str, agent_name: str, status: str, detail: str = "") -> None:
    """Write a live agent-step entry (streamed to the frontend activity feed)."""
    try:
        icon = {"Lead Finder": "🔍", "Lead Qualifier": "📋", "Message Drafter": "✍️", "Message Reviewer": "✅"}.get(agent_name, "🤖")
        db.add(AgentActivity(
            workspace_id=workspace_id,
            lead_id=lead_id or None,
            event_type="agent_step",
            title=f"{icon} {agent_name} — {status}",
            detail=(detail[:1000] if detail else None),
        ))
        db.commit()
    except Exception as e:
        logger.warning("Failed to write agent step log: %s", e)


def _resolve_provider(db: Session, workspace: Workspace):
    """Best-effort MessagingProvider for driving the typing indicator. Prefers a
    connected WANumber; falls back to the tenant's default (wacli) transport."""
    number = (
        db.query(WANumber)
        .filter(WANumber.workspace_id == workspace.id, WANumber.status == "CONNECTED")
        .first()
    )
    if number is not None:
        return get_provider(number)

    class _Shim:
        provider = workspace.default_provider or "wacli"
        workspace_id = str(workspace.id)
        wacli_account = str(workspace.id)
        wacli_store_dir = None
    return get_provider(_Shim())


def _should_escalate(lead: Lead, state: pipeline.ConversationState) -> bool:
    """Use the Anthropic escalation model at high-value moments."""
    if not settings.LLM_ESCALATION_ENABLED:
        return False
    if (lead.intent_label or "").upper() == "HOT" or (lead.score or 0) >= 80:
        return True
    return state in (pipeline.ConversationState.PROPOSE, pipeline.ConversationState.CONFIRM)


def enqueue_agent_outbound(
    *,
    workspace_id: str,
    to: str,
    reply: str,
    media_asset_id: Optional[str],
    decision: OutreachDecision,
    should_auto_send: bool,
    send_text: Optional[Callable[..., Any]] = None,
    send_media: Optional[Callable[..., Any]] = None,
) -> str:
    """Enqueue the outbound send after the gate decision.

    Returns one of: ``sent_media``, ``sent_text``, ``draft``, ``blocked``.
    Pure orchestration — injectable Celery delay callables for unit tests.
    Media is only sent when ``media_asset_id`` is already validated against the
    tenant catalogue AND the gate allows auto-send.
    """
    text_fn = send_text or send_whatsapp_message.delay
    media_fn = send_media or send_whatsapp_media.delay

    if not should_auto_send:
        return "draft" if decision.allowed else "blocked"

    if media_asset_id:
        media_fn(workspace_id, to, media_asset_id, caption=reply)
        return "sent_media"

    text_fn(workspace_id, to, reply)
    return "sent_text"


@shared_task(
    name="ai.generate_reply",
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=120,
    max_retries=2,
)
def generate_ai_reply(
    workspace_id: str,
    lead_id: str,
    auto_send_allowed: bool = False,
    trigger_message_id: str | None = None,
):
    logger.info("Generating AI reply for workspace=%s lead=%s", workspace_id, lead_id)

    db: Session = SessionLocal()
    try:
        # RLS GUC — defence in depth for tenant-scoped reads (memory + media catalogue).
        set_tenant(db, workspace_id)

        workspace = db.query(Workspace).filter(Workspace.id == workspace_id).first()
        lead = db.query(Lead).filter(Lead.id == lead_id).first()
        if not workspace or not lead:
            logger.error("Workspace or lead not found")
            return
        if not workspace.agent_enabled:
            logger.info("Agent disabled for workspace=%s", workspace_id)
            return

        convo = ensure_conversation(db, str(workspace.id), str(lead.id))
        db.commit()

        # ── Human takeover: a person owns this thread; the agent stays silent ──
        if convo.human_takeover:
            logger.info("Human takeover active for lead=%s — agent paused.", lead_id)
            lead.needs_response = False
            db.commit()
            return

        # ── Hard stop: meeting confirmed ──
        if lead.meeting_status == "CONFIRMED":
            logger.info("Meeting already CONFIRMED for lead=%s — agent silenced.", lead_id)
            lead.needs_response = False
            db.commit()
            return

        messages = (
            db.query(DBMessage)
            .filter(DBMessage.lead_id == lead_id)
            .order_by(DBMessage.timestamp.asc())
            .all()
        )
        if not messages:
            return
        latest_msg = messages[-1].content

        # ── Opt-out is honored immediately, before anything else ──
        if pipeline.detect_opt_out(latest_msg):
            lead.do_not_contact = True
            lead.needs_response = False
            convo.status = "ended"
            log_activity(db, str(workspace.id), "opt_out",
                         f"{lead.name} opted out — do_not_contact set", detail=latest_msg, lead_id=str(lead.id))
            log_agent_step(db, workspace_id, lead_id, "Message Reviewer", "Opt-out honored 🛑",
                           "Contact asked to stop. do_not_contact set; agent will not reply.")
            db.commit()
            return

        # ── Debounce: a newer inbound supersedes this task ──
        if trigger_message_id:
            from app.services import debounce
            if not debounce.is_latest_trigger(str(lead.id), trigger_message_id):
                logger.info("Superseded inbound for lead=%s — skipping stale reply.", lead_id)
                return

        config = read_agent_config(workspace)
        user_turn_count = sum(1 for m in messages if m.role == MessageRole.USER)
        prior_agent_msgs = sum(1 for m in messages if m.role == MessageRole.AGENT)

        # Conversation history (last 20 turns keeps the prompt tight)
        history_text = "\n".join(
            f"{'Lead' if m.role == MessageRole.USER else 'You (Sales Agent)'}: {m.content}"
            for m in messages[-20:]
        )
        services_list = config.get("services") or [
            "Web development", "App development", "Custom software development", "Cyber security services",
        ]

        # ── Recall memory + brand media catalogue → build persona/system prompt ──
        # Re-set GUC: set_config(..., is_local=true) clears after each commit above.
        set_tenant(db, workspace_id)
        memory_context = memory.build_memory_context(db, str(workspace.id), str(lead.id), query=latest_msg)
        media_catalogue = media_svc.catalogue_for_agent(db, str(workspace.id))
        state = pipeline.derive_state(lead.meeting_status, user_turn_count, lead.score or 0)
        system_prompt = persona.build_system_prompt(
            workspace, config, memory_context=memory_context, stage=state.value,
        )

        log_agent_step(db, workspace_id, lead_id, "Lead Finder",
                       f"Running (turn {user_turn_count}, {state.value})",
                       f"Analyzing: \"{latest_msg[:120]}\"")

        result = pipeline.run(
            system_prompt=system_prompt,
            brand_name=config.get("brand_name", "AI Agency"),
            services=services_list,
            meeting_cta=config.get("meeting_cta", "wanna hop on a quick google meet?"),
            history_text=history_text,
            latest_msg=latest_msg,
            turn_count=user_turn_count,
            state=state,
            media_catalogue=media_catalogue,
            escalate=_should_escalate(lead, state),
        )

        log_agent_step(db, workspace_id, lead_id, "Lead Qualifier",
                       f"Done — {result.intent_label} (score {result.score}) | "
                       f"meeting={'CONFIRMED ✅' if result.meeting_confirmed else 'YES' if result.meeting_requested else 'NOT YET'}",
                       f"{result.summary}\n→ Next: {result.next_action}")

        # Stop only if confirmed non-lead after enough turns
        if result.intent_label == "NO_ACTION" and not result.is_lead and user_turn_count >= 3:
            lead.intent_label = "NO_ACTION"
            lead.needs_response = False
            log_agent_step(db, workspace_id, lead_id, "Lead Finder", "Stopped — NO_ACTION",
                           f"Confirmed non-lead after {user_turn_count} turns.")
            db.commit()
            return

        # ── Persist extracted memory facts ──
        if result.facts:
            stored = memory.store_facts(db, str(workspace.id), str(lead.id), result.facts)
            if stored:
                log_agent_step(db, workspace_id, lead_id, "Message Drafter", f"Remembered {stored} fact(s)",
                               "; ".join(f.get("fact", "") for f in result.facts)[:400])

        # ── Mandatory AI disclosure on the first agent message of the thread ──
        final_reply = persona.ensure_disclosure(
            result.reply, workspace, is_first_agent_message=(prior_agent_msgs == 0)
        )

        media_note = f" + media={result.media_asset_id}" if result.media_asset_id else ""
        log_agent_step(db, workspace_id, lead_id, "Message Reviewer", "Done ✅",
                       f"Reply: \"{final_reply[:200]}\"{media_note}")

        # ── Persist lead state ──
        lead.intent_label = result.intent_label
        lead.score = result.score
        lead.summary = result.summary
        lead.service_interest = result.service_interest
        lead.requirement_summary = result.summary
        lead.next_action = result.next_action
        lead.needs_response = False

        if result.meeting_confirmed:
            lead.meeting_status = "CONFIRMED"
            lead.status = LeadStatus.IN_PROGRESS
            convo.status = "ended"
            log_agent_step(db, workspace_id, lead_id, "Message Reviewer",
                           "Meeting CONFIRMED 🎉 — agent silenced", "Warm close sent; stopping.")
        elif result.meeting_requested:
            lead.meeting_status = "REQUESTED"
            lead.status = LeadStatus.IN_PROGRESS
        elif result.score >= 70:
            lead.status = LeadStatus.IN_PROGRESS

        # ── Compliance gate — the single authority on whether we may send ──
        decision = gate(workspace, lead, OutreachKind.AGENT_REPLY,
                        window_hours=settings.CUSTOMER_SERVICE_WINDOW_HOURS)

        should_auto_send = (
            decision.allowed
            and bool(config.get("auto_reply_enabled"))
            and bool(config.get("auto_send_matched_leads"))
            and workspace.is_running
            and daily_quota_available(workspace)
            and bool(final_reply)
            and (auto_send_allowed or user_turn_count >= 2)
        )

        import uuid as _uuid
        media_uuid = _uuid.UUID(result.media_asset_id) if result.media_asset_id else None
        agent_msg = DBMessage(
            workspace_id=workspace.id,
            lead_id=lead.id,
            role=MessageRole.AGENT,
            content=final_reply,
            status=MessageStatus.SENT if should_auto_send else MessageStatus.DRAFT,
            media_asset_id=media_uuid,
        )
        db.add(agent_msg)
        db.commit()

        if should_auto_send:
            # Human-like pause + WhatsApp "typing…" before the send.
            try:
                provider = _resolve_provider(db, workspace)
                apply_typing_delay(final_reply, incoming_message=latest_msg,
                                   typing_cb=lambda on: provider.send_typing(lead.jid, on))
            except Exception as exc:
                logger.warning("typing delay/indicator failed: %s", exc)

            outcome = enqueue_agent_outbound(
                workspace_id=str(lead.workspace_id),
                to=lead.jid,
                reply=agent_msg.content,
                media_asset_id=result.media_asset_id,
                decision=decision,
                should_auto_send=True,
            )
            lead.last_contacted_at = datetime.now(timezone.utc)
            lead.last_outbound_at = lead.last_contacted_at
            bump_sent_counter(workspace)
            event = "auto_media_sent" if outcome == "sent_media" else "auto_reply_sent"
            log_activity(db, str(workspace.id), event,
                         f"Auto {'media' if outcome == 'sent_media' else 'reply'} sent to {lead.name} "
                         f"(turn {user_turn_count})",
                         detail=agent_msg.content, lead_id=str(lead.id), group_jid=lead.source_group_jid)
        else:
            reason = "" if decision.allowed else f" [gate: {decision.reason}]"
            log_activity(db, str(workspace.id), "draft_created",
                         f"Draft prepared for {lead.name} (turn {user_turn_count}){reason}",
                         detail=agent_msg.content, lead_id=str(lead.id), group_jid=lead.source_group_jid)

        # Feature 16 — attach auto-reply (or gate block) onto the ListeningLead audit row.
        if (lead.source or "").upper() == "GROUP":
            listening_svc.finalize_reply(
                db,
                str(workspace.id),
                str(lead.id),
                reply_text=agent_msg.content,
                sent=should_auto_send,
                block_reason=None if should_auto_send else (decision.reason if not decision.allowed else "not_auto_sent"),
            )

        db.commit()
        logger.info(
            "AI reply handled for lead=%s turn=%d auto_send=%s media=%s",
            lead_id, user_turn_count, should_auto_send, result.media_asset_id,
        )

    except Exception as exc:
        logger.exception("Error generating AI reply: %s", exc)
        db.rollback()
        raise
    finally:
        db.close()
