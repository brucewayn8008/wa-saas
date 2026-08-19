import logging
from datetime import datetime, timedelta, timezone

from celery import shared_task
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.models.database import Lead, Message as DBMessage, MessageRole, MessageStatus, TargetGroup, Workspace
from app.services.crm import bump_sent_counter, daily_quota_available, log_activity, read_agent_config
from app.tasks.whatsapp_tasks import send_whatsapp_message

logger = logging.getLogger(__name__)


@shared_task(name="followup.check_stale_leads")
def check_stale_leads():
    db: Session = SessionLocal()
    try:
        now = datetime.now(timezone.utc)
        leads = db.query(Lead).filter(Lead.meeting_status != "BOOKED", Lead.do_not_contact.is_(False)).all()
        for lead in leads:
            if not lead.last_inbound_at:
                continue
            workspace = db.query(Workspace).filter(Workspace.id == lead.workspace_id).first()
            if not workspace or not workspace.is_running or not workspace.agent_enabled:
                continue
            config = read_agent_config(workspace)
            hours = int(config.get("followup_hours") or 6)
            if lead.last_inbound_at > now - timedelta(hours=hours):
                continue
            existing_draft = (
                db.query(DBMessage)
                .filter(DBMessage.lead_id == lead.id, DBMessage.status == MessageStatus.DRAFT)
                .first()
            )
            if existing_draft:
                continue
            followup_text = "Just checking in. If this requirement is still active, we can align on scope and next steps in a short meeting."
            draft = DBMessage(
                workspace_id=lead.workspace_id,
                lead_id=lead.id,
                role=MessageRole.AGENT,
                content=followup_text,
                status=MessageStatus.DRAFT,
            )
            db.add(draft)
            log_activity(
                db,
                str(lead.workspace_id),
                "followup_draft",
                f"Follow-up drafted for {lead.name}",
                detail=followup_text,
                lead_id=str(lead.id),
                group_jid=lead.source_group_jid,
            )
        db.commit()
    except Exception as exc:
        logger.exception("Followup task failed: %s", exc)
        db.rollback()
    finally:
        db.close()


@shared_task(name="followup.send_group_promos")
def send_group_promos():
    db: Session = SessionLocal()
    try:
        now = datetime.now(timezone.utc)
        workspaces = db.query(Workspace).filter(Workspace.is_running.is_(True), Workspace.agent_enabled.is_(True)).all()
        for workspace in workspaces:
            config = read_agent_config(workspace)
            if not config.get("schedule_group_promos"):
                continue
            interval_hours = int(config.get("promo_interval_hours") or 12)
            offer_template = config.get("offer_template") or config.get("qualifying_offer") or ""
            if not offer_template or not daily_quota_available(workspace):
                continue
            groups = db.query(TargetGroup).filter(TargetGroup.workspace_id == workspace.id, TargetGroup.is_active.is_(True)).all()
            for group in groups:
                if group.last_promo_sent_at and group.last_promo_sent_at > now - timedelta(hours=interval_hours):
                    continue
                payload = group.custom_offer or offer_template
                send_whatsapp_message.delay(str(workspace.id), group.jid, payload)
                group.last_promo_sent_at = now
                bump_sent_counter(workspace)
                log_activity(
                    db,
                    str(workspace.id),
                    "group_promo_sent",
                    f"Scheduled offer posted in {group.name}",
                    detail=payload,
                    group_jid=group.jid,
                )
                if not daily_quota_available(workspace):
                    break
        db.commit()
    except Exception as exc:
        logger.exception("Group promo task failed: %s", exc)
        db.rollback()
    finally:
        db.close()
