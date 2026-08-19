import json
import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Optional
from uuid import UUID

from sqlalchemy import desc, func, nullslast, or_
from sqlalchemy.orm import Session

from app.models.database import (
    AgentActivity,
    Consent,
    Conversation,
    Lead,
    LeadStatus,
    MemoryFact,
    Message,
    MessageRole,
    Workspace,
)

logger = logging.getLogger(__name__)

LEAD_LIST_MAX_LIMIT = 100
LEAD_LIST_DEFAULT_LIMIT = 50
LEAD_DETAIL_MESSAGE_LIMIT = 100

ALLOWED_LEAD_STATUSES = {s.value for s in LeadStatus}
ALLOWED_INTENT_LABELS = {"HOT", "WARM", "COLD"}
ALLOWED_LEAD_SOURCES = {"DIRECT", "GROUP", "AD", "WIDGET"}
ALLOWED_SORTS = {"last_inbound_at", "score"}

DEFAULT_KEYWORDS = [
    "website",
    "web development",
    "developer",
    "dev",
    "landing page",
    "shopify",
    "wordpress",
    "seo",
    "ads",
    "marketing",
    "branding",
    "app",
    "automation",
    "lead generation",
]


def default_agent_config(workspace: Workspace) -> dict[str, Any]:
    return {
        "brand_name": workspace.company_name,
        "business_description": workspace.business_description,
        "services": [
            "Web development",
            "Performance marketing",
            "Funnels and landing pages",
            "Branding and automation",
        ],
        "keywords": DEFAULT_KEYWORDS,
        "auto_reply_enabled": True,
        "auto_send_matched_leads": True,
        "schedule_group_promos": True,
        "promo_interval_hours": 12,
        "followup_hours": 6,
        "daily_message_limit": workspace.daily_message_limit or 35,
        "qualifying_offer": (
            "We help businesses with high-conversion websites, funnels, paid marketing, "
            "branding, and automation. If that is relevant, I can understand the exact need "
            "and we can take it to a short meeting."
        ),
        "meeting_cta": "Let us have a quick meeting to understand the requirement properly.",
        "offer_template": (
            "If anyone here needs web development, landing pages, paid marketing, SEO, branding, "
            "or automation support, I can help scope it clearly and suggest the fastest path."
        ),
    }


def read_agent_config(workspace: Workspace) -> dict[str, Any]:
    base = default_agent_config(workspace)
    raw = workspace.agent_config or "{}"
    try:
        parsed = json.loads(raw)
        if isinstance(parsed, dict):
            base.update(parsed)
    except json.JSONDecodeError:
        pass
    return base


def write_agent_config(workspace: Workspace, payload: dict[str, Any]) -> None:
    workspace.agent_config = json.dumps(payload)
    workspace.daily_message_limit = int(payload.get("daily_message_limit") or workspace.daily_message_limit or 35)


def normalize_text(value: str) -> str:
    return " ".join((value or "").lower().strip().split())


def message_looks_like_need(text: str, keywords: list[str]) -> bool:
    content = normalize_text(text)
    if len(content) < 10:
        return False

    keyword_hit = any(normalize_text(keyword) in content for keyword in keywords if keyword.strip())
    intent_terms = [
        "need",
        "looking for",
        "require",
        "required",
        "recommend",
        "anyone",
        "budget",
        "project",
        "hire",
        "hiring",
        "want",
        "help",
    ]
    intent_hit = any(term in content for term in intent_terms)
    return keyword_hit or intent_hit


def daily_quota_available(workspace: Workspace) -> bool:
    now = datetime.now(timezone.utc)
    if not workspace.last_daily_reset_at or workspace.last_daily_reset_at.date() != now.date():
        workspace.last_daily_reset_at = now
        workspace.messages_sent_today = 0
    return (workspace.messages_sent_today or 0) < (workspace.daily_message_limit or 35)


def bump_sent_counter(workspace: Workspace) -> None:
    daily_quota_available(workspace)
    workspace.messages_sent_today = (workspace.messages_sent_today or 0) + 1


def log_activity(
    db: Session,
    workspace_id: str,
    event_type: str,
    title: str,
    detail: str | None = None,
    lead_id: str | None = None,
    group_jid: str | None = None,
) -> AgentActivity:
    activity = AgentActivity(
        workspace_id=workspace_id,
        lead_id=lead_id,
        group_jid=group_jid,
        event_type=event_type,
        title=title,
        detail=detail,
    )
    db.add(activity)
    return activity


def lead_display_status(lead: Lead) -> str:
    if lead.status.value == "CONVERTED":
        return "converted"
    if lead.status.value == "FAILED":
        return "lost"
    if lead.meeting_status in {"REQUESTED", "READY"}:
        return "needs_link"
    if lead.status.value == "IN_PROGRESS":
        return "in_conversation"
    if lead.last_outbound_at:
        return "contacted"
    return "new"


# ---------------------------------------------------------------------------
# Leads CRM (Feature 15)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class LeadListQuery:
    status: Optional[str] = None
    intent_label: Optional[str] = None
    source: Optional[str] = None
    min_score: Optional[int] = None
    do_not_contact: Optional[bool] = None
    search: Optional[str] = None
    sort: str = "last_inbound_at"
    limit: int = LEAD_LIST_DEFAULT_LIMIT
    offset: int = 0


@dataclass
class LeadListResult:
    leads: list[Lead]
    total: int
    limit: int
    offset: int


@dataclass
class LeadDetailResult:
    lead: Lead
    memory_facts: list[MemoryFact]
    conversation: Optional[Conversation]
    messages: list[Message]
    consent: Optional[Consent]


def _coerce_uuid(value: str | UUID) -> UUID:
    return value if isinstance(value, UUID) else UUID(str(value))


def normalize_lead_list_query(
    *,
    status: Optional[str] = None,
    intent_label: Optional[str] = None,
    source: Optional[str] = None,
    min_score: Optional[int] = None,
    do_not_contact: Optional[bool] = None,
    search: Optional[str] = None,
    sort: Optional[str] = None,
    limit: Optional[int] = None,
    offset: Optional[int] = None,
) -> LeadListQuery:
    """Validate/clamp list params. Raises ValueError for bad enums (endpoint → 422)."""
    status_n = (status or "").strip().upper() or None
    if status_n and status_n not in ALLOWED_LEAD_STATUSES:
        raise ValueError(f"invalid status; expected one of {sorted(ALLOWED_LEAD_STATUSES)}")

    intent_n = (intent_label or "").strip().upper() or None
    if intent_n and intent_n not in ALLOWED_INTENT_LABELS:
        raise ValueError(f"invalid intent_label; expected one of {sorted(ALLOWED_INTENT_LABELS)}")

    source_n = (source or "").strip().upper() or None
    if source_n and source_n not in ALLOWED_LEAD_SOURCES:
        raise ValueError(f"invalid source; expected one of {sorted(ALLOWED_LEAD_SOURCES)}")

    sort_n = (sort or "last_inbound_at").strip().lower()
    if sort_n not in ALLOWED_SORTS:
        raise ValueError(f"invalid sort; expected one of {sorted(ALLOWED_SORTS)}")

    lim = LEAD_LIST_DEFAULT_LIMIT if limit is None else int(limit)
    lim = max(1, min(lim, LEAD_LIST_MAX_LIMIT))
    off = max(0, int(offset or 0))

    return LeadListQuery(
        status=status_n,
        intent_label=intent_n,
        source=source_n,
        min_score=min_score,
        do_not_contact=do_not_contact,
        search=(search or "").strip() or None,
        sort=sort_n,
        limit=lim,
        offset=off,
    )


def _leads_base_query(db: Session, workspace_id: str | UUID):
    """Always scoped to the tenant — defense in depth alongside RLS GUC."""
    return db.query(Lead).filter(Lead.workspace_id == _coerce_uuid(workspace_id))


def list_leads(db: Session, workspace_id: str | UUID, query: LeadListQuery) -> LeadListResult:
    q = _leads_base_query(db, workspace_id)

    if query.status:
        q = q.filter(Lead.status == LeadStatus(query.status))
    if query.intent_label:
        q = q.filter(func.upper(Lead.intent_label) == query.intent_label)
    if query.source:
        q = q.filter(func.upper(Lead.source) == query.source)
    if query.min_score is not None:
        q = q.filter(Lead.score >= int(query.min_score))
    if query.do_not_contact is not None:
        q = q.filter(Lead.do_not_contact.is_(bool(query.do_not_contact)))
    if query.search:
        term = f"%{query.search}%"
        q = q.filter(
            or_(
                Lead.name.ilike(term),
                Lead.requirement_summary.ilike(term),
            )
        )

    total = q.count()

    if query.sort == "score":
        q = q.order_by(nullslast(desc(Lead.score)), desc(Lead.created_at))
    else:
        q = q.order_by(nullslast(desc(Lead.last_inbound_at)), desc(Lead.created_at))

    leads = q.offset(query.offset).limit(query.limit).all()
    return LeadListResult(leads=leads, total=total, limit=query.limit, offset=query.offset)


def get_lead(db: Session, workspace_id: str | UUID, lead_id: str | UUID) -> Optional[Lead]:
    try:
        lid = _coerce_uuid(lead_id)
    except (ValueError, TypeError):
        return None
    return (
        _leads_base_query(db, workspace_id)
        .filter(Lead.id == lid)
        .first()
    )


def get_lead_detail(
    db: Session,
    workspace_id: str | UUID,
    lead_id: str | UUID,
    *,
    message_limit: int = LEAD_DETAIL_MESSAGE_LIMIT,
) -> Optional[LeadDetailResult]:
    lead = get_lead(db, workspace_id, lead_id)
    if not lead:
        return None

    ws = _coerce_uuid(workspace_id)
    facts = (
        db.query(MemoryFact)
        .filter(
            MemoryFact.workspace_id == ws,
            MemoryFact.lead_id == lead.id,
            MemoryFact.is_active.is_(True),
        )
        .order_by(desc(MemoryFact.created_at))
        .all()
    )
    convo = (
        db.query(Conversation)
        .filter(Conversation.workspace_id == ws, Conversation.lead_id == lead.id)
        .order_by(desc(Conversation.created_at))
        .first()
    )
    # Newest-first fetch then reverse → chronological thread for the UI.
    lim = max(1, min(int(message_limit), LEAD_DETAIL_MESSAGE_LIMIT))
    recent = (
        db.query(Message)
        .filter(Message.workspace_id == ws, Message.lead_id == lead.id)
        .order_by(desc(Message.timestamp))
        .limit(lim)
        .all()
    )
    messages = list(reversed(recent))
    consent = (
        db.query(Consent)
        .filter(
            Consent.workspace_id == ws,
            Consent.lead_id == lead.id,
            Consent.revoked_at.is_(None),
        )
        .order_by(desc(Consent.granted_at))
        .first()
    )
    return LeadDetailResult(
        lead=lead,
        memory_facts=facts,
        conversation=convo,
        messages=messages,
        consent=consent,
    )


def message_direction(role: MessageRole | str) -> str:
    raw = role.value if isinstance(role, MessageRole) else str(role)
    return "inbound" if raw == MessageRole.USER.value else "outbound"


def update_lead(
    db: Session,
    workspace_id: str | UUID,
    lead_id: str | UUID,
    *,
    status: Optional[str] = None,
    intent_label: Optional[str] = None,
    do_not_contact: Optional[bool] = None,
) -> Optional[Lead]:
    """Apply manual CRM overrides. Returns None if the lead is not in this tenant."""
    if status is None and intent_label is None and do_not_contact is None:
        raise ValueError("no fields to update")

    status_n = (status or "").strip().upper() or None
    if status_n and status_n not in ALLOWED_LEAD_STATUSES:
        raise ValueError(f"invalid status; expected one of {sorted(ALLOWED_LEAD_STATUSES)}")

    intent_n = (intent_label or "").strip().upper() or None
    if intent_n and intent_n not in ALLOWED_INTENT_LABELS:
        raise ValueError(f"invalid intent_label; expected one of {sorted(ALLOWED_INTENT_LABELS)}")

    lead = get_lead(db, workspace_id, lead_id)
    if not lead:
        return None

    changes: list[str] = []
    if status_n is not None and lead.status != LeadStatus(status_n):
        lead.status = LeadStatus(status_n)
        changes.append(f"status={status_n}")
    if intent_n is not None and (lead.intent_label or "").upper() != intent_n:
        lead.intent_label = intent_n
        changes.append(f"intent_label={intent_n}")
    if do_not_contact is not None and bool(lead.do_not_contact) != bool(do_not_contact):
        lead.do_not_contact = bool(do_not_contact)
        changes.append(f"do_not_contact={bool(do_not_contact)}")

    if changes:
        log_activity(
            db,
            str(workspace_id),
            "lead_override",
            f"Manual override on {lead.name}",
            detail="; ".join(changes),
            lead_id=str(lead.id),
        )
        logger.info("[crm/update_lead] workspace=%s lead=%s %s", workspace_id, lead.id, "; ".join(changes))

    return lead
