"""Feature 16 — Listening inbox: intent match, auto-reply audit, dismiss, isolation."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from types import SimpleNamespace

import pytest

from app.core.outreach_policy import OutreachKind, gate
from app.db.session import SessionLocal
from app.models.database import Lead, LeadStatus, ListeningLead, User, Workspace
from app.services import listening as listening_svc
from app.tasks.ai_tasks import enqueue_agent_outbound


NOW = datetime(2026, 8, 20, 12, 0, tzinfo=timezone.utc)


@pytest.fixture
def db():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.rollback()
        session.close()


def _seed_tenant(db, *, label: str) -> Workspace:
    user = User(email=f"listening-{label}-{uuid.uuid4().hex[:10]}@example.com")
    db.add(user)
    db.flush()
    ws = Workspace(
        owner_id=user.id,
        company_name=f"Listen Co {label}",
        business_description="web sites and funnels",
        clerk_org_id=f"user:listening-{label}-{uuid.uuid4().hex[:8]}",
        agent_enabled=True,
        is_running=True,
        disclosure_line="You're chatting with an AI assistant for Listen Co.",
    )
    db.add(ws)
    db.flush()
    return ws


def _add_lead(db, ws: Workspace, *, name: str = "Group Lead") -> Lead:
    lead = Lead(
        workspace_id=ws.id,
        jid=f"{uuid.uuid4().hex[:12]}@s.whatsapp.net",
        name=name,
        status=LeadStatus.NEW,
        source="GROUP",
        source_group_jid="120363@g.us",
        source_group_name="Indie Hackers",
        last_inbound_at=NOW,
        meeting_status="NOT_REQUESTED",
    )
    db.add(lead)
    db.flush()
    return lead


# ── Intent match ────────────────────────────────────────────────────────────


def test_match_intent_keyword_hit():
    m = listening_svc.match_intent(
        "Anyone know a good web developer for a restaurant site?",
        keywords=["website", "developer", "seo"],
        services=["Web development"],
        embed_fn=lambda _t: None,  # force keywords-only
    )
    assert m.matched is True
    assert m.reason == "keyword"


def test_match_intent_semantic_when_keywords_miss():
    # Orthogonal unit vectors → high cosine when identical
    vec = [1.0] + [0.0] * 7

    def embed(text: str):
        return list(vec)

    # Avoid keyword/intent phrases ("need", "looking for", "anyone", …)
    m = listening_svc.match_intent(
        "Our ecommerce storefront conversion rate keeps slipping every month",
        keywords=["zzz-no-hit"],
        services=["Conversion-focused marketing sites"],
        embed_fn=embed,
        semantic_threshold=0.5,
    )
    assert m.matched is True
    assert m.reason == "semantic"
    assert m.score is not None and m.score >= 50


def test_match_intent_no_hit_without_embeddings():
    m = listening_svc.match_intent(
        "What time is the meetup tonight everyone?",
        keywords=["website", "developer"],
        services=["Web development"],
        embed_fn=lambda _t: None,
    )
    assert m.matched is False


# ── Detection → auto-send (gated) ───────────────────────────────────────────


def test_detection_auto_send_when_gate_allows():
    """Matched listening lead + gate allow → enqueue sends (not draft)."""
    tenant = SimpleNamespace(
        agent_enabled=True, is_running=True,
        daily_message_limit=35, messages_sent_today=0,
    )
    lead = SimpleNamespace(do_not_contact=False, last_inbound_at=NOW)
    decision = gate(tenant, lead, OutreachKind.AGENT_REPLY, now=NOW)
    assert decision.allowed

    sent = {"text": [], "media": []}
    outcome = enqueue_agent_outbound(
        workspace_id="ws-1",
        to="1555@s.whatsapp.net",
        reply="Happy to help — you're chatting with an AI assistant.",
        media_asset_id=None,
        decision=decision,
        should_auto_send=True,
        send_text=lambda *a, **k: sent["text"].append(a),
        send_media=lambda *a, **k: sent["media"].append(a),
    )
    assert outcome == "sent_text"
    assert len(sent["text"]) == 1
    assert sent["media"] == []


def test_gate_blocks_listening_auto_send_without_consent_basis():
    tenant = SimpleNamespace(
        agent_enabled=True, is_running=True,
        daily_message_limit=35, messages_sent_today=0,
    )
    lead = SimpleNamespace(do_not_contact=False, last_inbound_at=None)
    decision = gate(tenant, lead, OutreachKind.AGENT_REPLY, now=NOW)
    assert not decision.allowed
    assert decision.reason == "outside_service_window"

    sent = []
    outcome = enqueue_agent_outbound(
        workspace_id="ws-1",
        to="1555@s.whatsapp.net",
        reply="hi",
        media_asset_id=None,
        decision=decision,
        should_auto_send=False,
        send_text=lambda *a, **k: sent.append(a),
    )
    assert outcome == "blocked"
    assert sent == []


# ── Persist / list / dismiss / isolation ─────────────────────────────────────


def test_record_finalize_list_and_dismiss(db):
    ws = _seed_tenant(db, label="A")
    lead = _add_lead(db, ws)

    match = listening_svc.IntentMatch(matched=True, reason="keyword")
    row = listening_svc.record_detection(
        db,
        str(ws.id),
        lead_id=str(lead.id),
        group_jid="120363@g.us",
        group_name="Indie Hackers",
        sender_jid=lead.jid,
        original_message="Anyone know a good web developer?",
        match=match,
    )
    assert row.status == "detected"

    listening_svc.finalize_reply(
        db,
        str(ws.id),
        str(lead.id),
        reply_text="Happy to help with restaurant sites. You're chatting with an AI.",
        sent=True,
    )
    db.flush()

    feed = listening_svc.list_listening(db, str(ws.id))
    assert len(feed) == 1
    assert feed[0].status == "sent"
    assert "AI" in (feed[0].reply_text or "")

    dismissed = listening_svc.dismiss(db, str(ws.id), str(row.id))
    assert dismissed is not None
    assert dismissed.status == "dismissed"
    assert listening_svc.list_listening(db, str(ws.id)) == []


def test_finalize_blocked_stores_reason(db):
    ws = _seed_tenant(db, label="B")
    lead = _add_lead(db, ws, name="Blocked Lead")
    listening_svc.record_detection(
        db,
        str(ws.id),
        lead_id=str(lead.id),
        group_jid="120363@g.us",
        group_name="Founders",
        sender_jid=lead.jid,
        original_message="Need a website rebuild urgently please",
        match=listening_svc.IntentMatch(matched=True, reason="keyword"),
    )
    listening_svc.finalize_reply(
        db,
        str(ws.id),
        str(lead.id),
        reply_text="Would have sent this",
        sent=False,
        block_reason="daily_quota_exceeded",
    )
    feed = listening_svc.list_listening(db, str(ws.id))
    assert len(feed) == 1
    assert feed[0].status == "blocked"
    assert feed[0].block_reason == "daily_quota_exceeded"


def test_cross_tenant_listening_isolation(db):
    ws_a = _seed_tenant(db, label="isoA")
    ws_b = _seed_tenant(db, label="isoB")
    lead_a = _add_lead(db, ws_a, name="A Lead")
    lead_b = _add_lead(db, ws_b, name="B Lead")

    listening_svc.record_detection(
        db, str(ws_a.id), lead_id=str(lead_a.id),
        group_jid="g-a@g.us", group_name="Group A", sender_jid=lead_a.jid,
        original_message="Need a website for my cafe please",
        match=listening_svc.IntentMatch(matched=True, reason="keyword"),
    )
    listening_svc.finalize_reply(
        db, str(ws_a.id), str(lead_a.id), reply_text="A reply", sent=True,
    )
    listening_svc.record_detection(
        db, str(ws_b.id), lead_id=str(lead_b.id),
        group_jid="g-b@g.us", group_name="Group B", sender_jid=lead_b.jid,
        original_message="Looking for a developer this week",
        match=listening_svc.IntentMatch(matched=True, reason="keyword"),
    )
    listening_svc.finalize_reply(
        db, str(ws_b.id), str(lead_b.id), reply_text="B reply", sent=True,
    )

    a_feed = listening_svc.list_listening(db, str(ws_a.id))
    b_feed = listening_svc.list_listening(db, str(ws_b.id))
    assert len(a_feed) == 1 and a_feed[0].reply_text == "A reply"
    assert len(b_feed) == 1 and b_feed[0].reply_text == "B reply"

    # Dismissing A's row must not touch B
    listening_svc.dismiss(db, str(ws_a.id), str(a_feed[0].id))
    assert listening_svc.list_listening(db, str(ws_a.id)) == []
    assert len(listening_svc.list_listening(db, str(ws_b.id))) == 1

    # Wrong-tenant dismiss is a no-op (row not found under that workspace filter)
    missing = listening_svc.dismiss(db, str(ws_a.id), str(b_feed[0].id))
    assert missing is None
    assert db.query(ListeningLead).filter(ListeningLead.id == b_feed[0].id).first().status == "sent"
