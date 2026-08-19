"""Feature 03 verification — the compliance gate must block every non-compliant send."""

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Optional

from app.core.outreach_policy import OutreachKind, gate


@dataclass
class FakeTenant:
    agent_enabled: bool = True
    is_running: bool = True
    daily_message_limit: int = 35
    messages_sent_today: int = 0


@dataclass
class FakeLead:
    do_not_contact: bool = False
    last_inbound_at: Optional[datetime] = None


NOW = datetime(2026, 8, 6, 12, 0, tzinfo=timezone.utc)


def test_do_not_contact_always_blocks():
    d = gate(FakeTenant(), FakeLead(do_not_contact=True, last_inbound_at=NOW), OutreachKind.AGENT_REPLY, now=NOW)
    assert not d and d.reason == "do_not_contact"


def test_agent_reply_within_window_allowed():
    lead = FakeLead(last_inbound_at=NOW - timedelta(hours=2))
    d = gate(FakeTenant(), lead, OutreachKind.AGENT_REPLY, now=NOW)
    assert d and d.reason == "within_service_window"


def test_agent_reply_outside_window_blocked_requires_template():
    lead = FakeLead(last_inbound_at=NOW - timedelta(hours=30))
    d = gate(FakeTenant(), lead, OutreachKind.AGENT_REPLY, now=NOW)
    assert not d and d.requires_template and d.reason == "outside_service_window"


def test_no_inbound_is_cold_and_blocked():
    d = gate(FakeTenant(), FakeLead(last_inbound_at=None), OutreachKind.AGENT_REPLY, now=NOW)
    assert not d and d.reason == "outside_service_window"


def test_agent_disabled_blocks_agent_reply():
    lead = FakeLead(last_inbound_at=NOW)
    d = gate(FakeTenant(agent_enabled=False), lead, OutreachKind.AGENT_REPLY, now=NOW)
    assert not d and d.reason == "agent_disabled"


def test_quota_exceeded_blocks():
    lead = FakeLead(last_inbound_at=NOW)
    t = FakeTenant(messages_sent_today=35, daily_message_limit=35)
    d = gate(t, lead, OutreachKind.AGENT_REPLY, now=NOW)
    assert not d and d.reason == "daily_quota_exceeded"


def test_template_requires_consent_basis():
    d = gate(FakeTenant(), FakeLead(last_inbound_at=None), OutreachKind.TEMPLATE, now=NOW)
    assert not d and d.reason == "no_consent_basis"


def test_template_ok_with_prior_inbound():
    lead = FakeLead(last_inbound_at=NOW - timedelta(days=10))
    d = gate(FakeTenant(), lead, OutreachKind.TEMPLATE, now=NOW)
    assert d and d.requires_template and d.reason == "template_ok"


def test_human_approved_still_respects_window():
    lead = FakeLead(last_inbound_at=NOW - timedelta(hours=1))
    d = gate(FakeTenant(agent_enabled=False), lead, OutreachKind.HUMAN_APPROVED, now=NOW)
    assert d  # human-approved bypasses the agent-enabled check, still within window
