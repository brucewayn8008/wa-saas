"""Billing — plans, quota enforcement, usage metering, and Stripe sync (Feature 11).

Plan/quota logic is pure and unit-testable. Stripe is imported lazily inside the
functions that need it, so the rest of the app (and tests) don't require the SDK.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.database import Subscription, Usage

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class Plan:
    key: str
    max_numbers: int
    monthly_conversation_quota: int
    max_seats: int
    media_storage_mb: int
    stripe_price_id: Optional[str] = None


# The plan catalog. stripe_price_id is filled from env/dashboard in real deployments.
PLANS: dict[str, Plan] = {
    "free":    Plan("free",    max_numbers=1,  monthly_conversation_quota=100,    max_seats=1,  media_storage_mb=100),
    "starter": Plan("starter", max_numbers=1,  monthly_conversation_quota=1_000,  max_seats=3,  media_storage_mb=1_000),
    "pro":     Plan("pro",     max_numbers=3,  monthly_conversation_quota=10_000, max_seats=10, media_storage_mb=10_000),
    "scale":   Plan("scale",   max_numbers=10, monthly_conversation_quota=100_000,max_seats=25, media_storage_mb=100_000),
}


def get_plan(name: Optional[str]) -> Plan:
    return PLANS.get((name or "free").lower(), PLANS["free"])


def current_period() -> str:
    now = datetime.now(timezone.utc)
    return f"{now.year:04d}-{now.month:02d}"


# --------------------------------------------------------------------------- #
# Pure quota logic
# --------------------------------------------------------------------------- #

def conversation_quota_remaining(plan: Plan, conversations_used: int) -> int:
    return max(0, plan.monthly_conversation_quota - conversations_used)


def has_conversation_quota(plan: Plan, conversations_used: int) -> bool:
    return conversations_used < plan.monthly_conversation_quota


def can_add_number(plan: Plan, current_numbers: int) -> bool:
    return current_numbers < plan.max_numbers


def apply_plan(subscription: Subscription, plan: Plan) -> None:
    """Copy a plan's limits onto a subscription row."""
    subscription.plan = plan.key
    subscription.max_numbers = plan.max_numbers
    subscription.monthly_conversation_quota = plan.monthly_conversation_quota
    subscription.max_seats = plan.max_seats
    subscription.media_storage_mb = plan.media_storage_mb


# --------------------------------------------------------------------------- #
# DB-backed usage metering
# --------------------------------------------------------------------------- #

def get_or_create_usage(db: Session, workspace_id, period: Optional[str] = None) -> Usage:
    period = period or current_period()
    usage = (
        db.query(Usage)
        .filter(Usage.workspace_id == workspace_id, Usage.period == period)
        .first()
    )
    if not usage:
        usage = Usage(workspace_id=workspace_id, period=period)
        db.add(usage)
        db.flush()
    return usage


def record_message_sent(db: Session, workspace_id) -> None:
    usage = get_or_create_usage(db, workspace_id)
    usage.messages_sent = (usage.messages_sent or 0) + 1


def record_conversation(db: Session, workspace_id) -> None:
    usage = get_or_create_usage(db, workspace_id)
    usage.conversations_used = (usage.conversations_used or 0) + 1


def get_or_create_subscription(db: Session, workspace_id) -> Subscription:
    sub = db.query(Subscription).filter(Subscription.workspace_id == workspace_id).first()
    if not sub:
        sub = Subscription(workspace_id=workspace_id)
        apply_plan(sub, get_plan("free"))
        db.add(sub)
        db.flush()
    return sub


# --------------------------------------------------------------------------- #
# Stripe integration (lazy import)
# --------------------------------------------------------------------------- #

def _stripe():
    import stripe  # lazy: only needed when actually calling Stripe
    stripe.api_key = settings.STRIPE_SECRET_KEY
    return stripe


def create_checkout_session(customer_id: Optional[str], price_id: str, success_url: str, cancel_url: str, workspace_id: str):
    stripe = _stripe()
    return stripe.checkout.Session.create(
        mode="subscription",
        customer=customer_id or None,
        line_items=[{"price": price_id, "quantity": 1}],
        success_url=success_url,
        cancel_url=cancel_url,
        metadata={"workspace_id": workspace_id},
    )


def verify_and_parse_event(payload: bytes, sig_header: str):
    stripe = _stripe()
    return stripe.Webhook.construct_event(payload, sig_header, settings.STRIPE_WEBHOOK_SECRET)


def handle_event(db: Session, event: dict) -> None:
    """Apply a verified Stripe webhook event to the local subscription state."""
    etype = event.get("type", "")
    obj = event.get("data", {}).get("object", {})

    if etype.startswith("customer.subscription."):
        workspace_id = (obj.get("metadata") or {}).get("workspace_id")
        if not workspace_id:
            logger.warning("[billing] subscription event without workspace_id metadata")
            return
        sub = get_or_create_subscription(db, workspace_id)
        sub.stripe_customer_id = obj.get("customer")
        sub.stripe_subscription_id = obj.get("id")
        sub.status = obj.get("status", sub.status)
        # Map the Stripe price/product back to a local plan via metadata or price nickname.
        plan_key = (obj.get("metadata") or {}).get("plan")
        if plan_key:
            apply_plan(sub, get_plan(plan_key))
        if etype == "customer.subscription.deleted":
            sub.status = "canceled"
            apply_plan(sub, get_plan("free"))
        db.commit()
