"""Feature 15 — Leads CRM: filters, pagination, tenant isolation, DNC → gate."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest

from app.core.outreach_policy import OutreachKind, gate
from app.db.session import SessionLocal
from app.models.database import (
    Consent,
    Conversation,
    Lead,
    LeadStatus,
    MemoryFact,
    Message,
    MessageRole,
    MessageStatus,
    User,
    Workspace,
)
from app.services import crm


NOW = datetime(2026, 8, 20, 12, 0, tzinfo=timezone.utc)


@pytest.fixture
def db():
    """Session that rolls back so tests never leave fixtures in wa_mark2."""
    session = SessionLocal()
    try:
        yield session
    finally:
        session.rollback()
        session.close()


def _seed_tenant(db, *, label: str) -> Workspace:
    user = User(email=f"leads-crm-{label}-{uuid.uuid4().hex[:10]}@example.com")
    db.add(user)
    db.flush()
    ws = Workspace(
        owner_id=user.id,
        company_name=f"Tenant {label}",
        business_description="test",
        clerk_org_id=f"user:leads-crm-{label}-{uuid.uuid4().hex[:8]}",
        agent_enabled=True,
        is_running=True,
    )
    db.add(ws)
    db.flush()
    return ws


def _add_lead(
    db,
    ws: Workspace,
    *,
    name: str,
    status: LeadStatus = LeadStatus.NEW,
    intent: str | None = None,
    score: int | None = None,
    source: str = "DIRECT",
    dnc: bool = False,
    requirement: str | None = None,
    inbound_at: datetime | None = None,
) -> Lead:
    lead = Lead(
        workspace_id=ws.id,
        jid=f"{uuid.uuid4().hex[:12]}@s.whatsapp.net",
        name=name,
        status=status,
        intent_label=intent,
        score=score,
        source=source,
        do_not_contact=dnc,
        requirement_summary=requirement,
        last_inbound_at=inbound_at,
        meeting_status="NOT_REQUESTED",
    )
    db.add(lead)
    db.flush()
    return lead


# ── normalize / validation ───────────────────────────────────────────────────


def test_normalize_clamps_limit_and_rejects_bad_status():
    q = crm.normalize_lead_list_query(limit=500, offset=-3)
    assert q.limit == crm.LEAD_LIST_MAX_LIMIT
    assert q.offset == 0
    with pytest.raises(ValueError, match="invalid status"):
        crm.normalize_lead_list_query(status="WARM")  # WARM is intent, not status


def test_normalize_accepts_filters():
    q = crm.normalize_lead_list_query(
        status="in_progress",
        intent_label="hot",
        source="widget",
        min_score=70,
        do_not_contact=False,
        search=" website ",
        sort="score",
        limit=10,
        offset=5,
    )
    assert q.status == "IN_PROGRESS"
    assert q.intent_label == "HOT"
    assert q.source == "WIDGET"
    assert q.min_score == 70
    assert q.do_not_contact is False
    assert q.search == "website"
    assert q.sort == "score"
    assert (q.limit, q.offset) == (10, 5)


# ── list filters + pagination ────────────────────────────────────────────────


def test_list_filters_and_pagination_total(db):
    ws = _seed_tenant(db, label="A")
    _add_lead(
        db, ws, name="Alice Hot", status=LeadStatus.IN_PROGRESS, intent="HOT",
        score=90, source="DIRECT", inbound_at=NOW - timedelta(hours=1),
        requirement="Need a website rebuild",
    )
    _add_lead(
        db, ws, name="Bob Warm", status=LeadStatus.NEW, intent="WARM",
        score=55, source="GROUP", inbound_at=NOW - timedelta(hours=2),
    )
    _add_lead(
        db, ws, name="Cara Cold", status=LeadStatus.NEW, intent="COLD",
        score=20, source="AD", inbound_at=NOW - timedelta(days=1), dnc=True,
    )

    hot = crm.list_leads(
        db, ws.id, crm.normalize_lead_list_query(intent_label="HOT"),
    )
    assert hot.total == 1
    assert hot.leads[0].name == "Alice Hot"

    dnc = crm.list_leads(
        db, ws.id, crm.normalize_lead_list_query(do_not_contact=True),
    )
    assert dnc.total == 1 and dnc.leads[0].name == "Cara Cold"

    search = crm.list_leads(
        db, ws.id, crm.normalize_lead_list_query(search="website"),
    )
    assert search.total == 1 and search.leads[0].name == "Alice Hot"

    by_score = crm.list_leads(
        db, ws.id, crm.normalize_lead_list_query(sort="score", limit=2, offset=0),
    )
    assert by_score.total == 3
    assert by_score.limit == 2
    assert [l.name for l in by_score.leads] == ["Alice Hot", "Bob Warm"]

    page2 = crm.list_leads(
        db, ws.id, crm.normalize_lead_list_query(sort="score", limit=2, offset=2),
    )
    assert page2.total == 3
    assert [l.name for l in page2.leads] == ["Cara Cold"]

    status_f = crm.list_leads(
        db, ws.id, crm.normalize_lead_list_query(status="IN_PROGRESS", min_score=80),
    )
    assert status_f.total == 1


# ── tenant isolation (app-layer + tenant-scoped query) ───────────────────────


def test_cross_tenant_lead_invisible(db):
    ws_a = _seed_tenant(db, label="isoA")
    ws_b = _seed_tenant(db, label="isoB")
    lead_b = _add_lead(db, ws_b, name="Secret B", intent="HOT", score=99, inbound_at=NOW)

    listed = crm.list_leads(db, ws_a.id, crm.normalize_lead_list_query())
    assert listed.total == 0
    assert all(str(l.workspace_id) != str(ws_b.id) for l in listed.leads)

    assert crm.get_lead(db, ws_a.id, lead_b.id) is None
    assert crm.get_lead_detail(db, ws_a.id, lead_b.id) is None

    # Own-tenant still sees it.
    assert crm.get_lead(db, ws_b.id, lead_b.id) is not None


# ── detail: facts + thread + consent ─────────────────────────────────────────


def test_get_lead_detail_includes_facts_thread_consent(db):
    ws = _seed_tenant(db, label="detail")
    lead = _add_lead(
        db, ws, name="Dana", intent="HOT", score=88,
        inbound_at=NOW - timedelta(minutes=30), requirement="Shopify store",
    )
    db.add(
        MemoryFact(
            workspace_id=ws.id,
            lead_id=lead.id,
            category="budget",
            fact="Budget around 2k",
            confidence=90,
            source="stated",
            is_active=True,
        )
    )
    db.add(
        MemoryFact(
            workspace_id=ws.id,
            lead_id=lead.id,
            category="timeline",
            fact="old inactive",
            is_active=False,
        )
    )
    convo = Conversation(workspace_id=ws.id, lead_id=lead.id, status="active")
    db.add(convo)
    db.flush()
    db.add_all(
        [
            Message(
                workspace_id=ws.id,
                lead_id=lead.id,
                role=MessageRole.USER,
                status=MessageStatus.RECEIVED,
                content="hi",
                timestamp=NOW - timedelta(minutes=20),
            ),
            Message(
                workspace_id=ws.id,
                lead_id=lead.id,
                role=MessageRole.AGENT,
                status=MessageStatus.SENT,
                content="hello from agent",
                timestamp=NOW - timedelta(minutes=19),
            ),
        ]
    )
    db.add(
        Consent(
            workspace_id=ws.id,
            lead_id=lead.id,
            source="inbound",
            granted_at=NOW - timedelta(hours=1),
        )
    )
    db.flush()

    detail = crm.get_lead_detail(db, ws.id, lead.id)
    assert detail is not None
    assert detail.lead.name == "Dana"
    assert len(detail.memory_facts) == 1
    assert detail.memory_facts[0].fact == "Budget around 2k"
    assert detail.conversation is not None
    assert len(detail.messages) == 2
    assert crm.message_direction(detail.messages[0].role) == "inbound"
    assert crm.message_direction(detail.messages[1].role) == "outbound"
    assert detail.consent is not None
    assert detail.consent.source == "inbound"


# ── PATCH DNC → gate blocks ─────────────────────────────────────────────────


def test_patch_dnc_then_gate_blocks(db):
    ws = _seed_tenant(db, label="dnc")
    ws.agent_enabled = True
    ws.is_running = True
    lead = _add_lead(
        db, ws, name="Eve", intent="HOT", score=80,
        inbound_at=NOW - timedelta(hours=1),
    )
    assert gate(ws, lead, OutreachKind.AGENT_REPLY, now=NOW)

    updated = crm.update_lead(db, ws.id, lead.id, do_not_contact=True)
    assert updated is not None
    assert updated.do_not_contact is True
    db.flush()

    decision = gate(ws, lead, OutreachKind.AGENT_REPLY, now=NOW)
    assert not decision and decision.reason == "do_not_contact"

    # Activity logged
    from app.models.database import AgentActivity

    act = (
        db.query(AgentActivity)
        .filter(AgentActivity.lead_id == lead.id, AgentActivity.event_type == "lead_override")
        .first()
    )
    assert act is not None
    assert "do_not_contact=True" in (act.detail or "")


def test_update_rejects_empty_and_bad_intent(db):
    ws = _seed_tenant(db, label="bad")
    lead = _add_lead(db, ws, name="Finn", inbound_at=NOW)
    with pytest.raises(ValueError, match="no fields"):
        crm.update_lead(db, ws.id, lead.id)
    with pytest.raises(ValueError, match="invalid intent"):
        crm.update_lead(db, ws.id, lead.id, intent_label="SUPERHOT")


def test_gate_blocks_dnc_simple_namespace():
    """Prompt verify: DNC lead is blocked from sends (gate reads the flag)."""
    tenant = SimpleNamespace(agent_enabled=True, is_running=True, daily_message_limit=35, messages_sent_today=0)
    lead = SimpleNamespace(do_not_contact=True, last_inbound_at=NOW)
    d = gate(tenant, lead, OutreachKind.HUMAN_APPROVED, now=NOW)
    assert not d and d.reason == "do_not_contact"
