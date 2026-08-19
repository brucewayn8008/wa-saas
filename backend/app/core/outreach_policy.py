"""Compliance gate — the single authority on whether an outbound WhatsApp message
is allowed to be sent.

EVERY outbound send path (agent auto-reply, human-approved reply, opt-in template)
MUST call `gate(...)` and honor its decision. There is no compliant send that
bypasses this module. See AGENTS.md / context/code-standards.md.

Rules enforced:
  1. Do-not-contact           -> always deny.
  2. Consent / inbound basis  -> no cold outreach. A free-form message requires a
                                 prior inbound within the 24h customer-service window;
                                 otherwise a pre-approved template is required.
  3. Agent enabled/running    -> agent auto-replies only when the tenant's agent is on.
  4. Rate limit / quota       -> per-tenant daily message cap.

The gate is deliberately dependency-light: it operates on duck-typed `lead` and
`tenant` objects (the current `Lead` / `Workspace` models satisfy it), so it is
unit-testable without a database.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Optional, Protocol


class OutreachKind(str, Enum):
    AGENT_REPLY = "agent_reply"        # autonomous agent reply inside a live conversation
    HUMAN_APPROVED = "human_approved"  # a human clicked "approve & send" (listening/manual)
    TEMPLATE = "template"              # opt-in re-engagement via an approved template


@dataclass(frozen=True)
class OutreachDecision:
    allowed: bool
    reason: str
    requires_template: bool = False

    def __bool__(self) -> bool:  # allow `if gate(...):`
        return self.allowed


class _LeadLike(Protocol):
    do_not_contact: bool
    last_inbound_at: Optional[datetime]


class _TenantLike(Protocol):
    agent_enabled: bool
    is_running: bool
    daily_message_limit: int
    messages_sent_today: int


def _aware(dt: Optional[datetime]) -> Optional[datetime]:
    if dt is None:
        return None
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def within_service_window(last_inbound_at: Optional[datetime], window_hours: int, now: datetime) -> bool:
    """True if the contact messaged us within the WhatsApp 24h customer-service window."""
    last = _aware(last_inbound_at)
    if last is None:
        return False
    return now - last <= timedelta(hours=window_hours)


def gate(
    tenant: _TenantLike,
    lead: _LeadLike,
    kind: OutreachKind,
    *,
    window_hours: int = 24,
    now: Optional[datetime] = None,
) -> OutreachDecision:
    """Authorize an outbound message. Returns an OutreachDecision (falsy if blocked)."""
    now = now or datetime.now(timezone.utc)

    # 1. Do-not-contact is absolute.
    if getattr(lead, "do_not_contact", False):
        return OutreachDecision(False, "do_not_contact")

    # 3. Agent must be enabled+running for autonomous replies (human-approved bypasses this).
    if kind == OutreachKind.AGENT_REPLY:
        if not getattr(tenant, "agent_enabled", False) or not getattr(tenant, "is_running", False):
            return OutreachDecision(False, "agent_disabled")

    # 4. Quota / rate limit.
    limit = getattr(tenant, "daily_message_limit", 0) or 0
    sent = getattr(tenant, "messages_sent_today", 0) or 0
    if limit and sent >= limit:
        return OutreachDecision(False, "daily_quota_exceeded")

    # 2. Consent / inbound basis — the core anti-spam rule.
    if kind == OutreachKind.TEMPLATE:
        # Templates are the only way to reach outside the window, but still require a
        # consent basis. Until the `consent` table lands (Feature 08/17), we require a
        # prior inbound as the minimum proof-of-relationship. TODO: check consent row.
        if _aware(lead.last_inbound_at) is None:
            return OutreachDecision(False, "no_consent_basis")
        return OutreachDecision(True, "template_ok", requires_template=True)

    # Free-form (agent reply or human-approved) must be inside the 24h window.
    if within_service_window(lead.last_inbound_at, window_hours, now):
        return OutreachDecision(True, "within_service_window")

    # Outside the window: free-form is not allowed — must use a template instead.
    return OutreachDecision(False, "outside_service_window", requires_template=True)
