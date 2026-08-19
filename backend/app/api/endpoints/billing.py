"""Billing endpoints (Feature 11): plan status, checkout, Stripe webhook."""

import logging

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.auth import AuthContext, get_auth_context, get_db, require_role
from app.services import billing

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("")
async def get_billing(ctx: AuthContext = Depends(get_auth_context), db: Session = Depends(get_db)):
    sub = billing.get_or_create_subscription(db, ctx.tenant.id)
    usage = billing.get_or_create_usage(db, ctx.tenant.id)
    db.commit()
    plan_obj = billing.get_plan(sub.plan)
    renew = sub.current_period_end.strftime("%Y-%m-%d") if sub.current_period_end else "—"
    plan_labels = {"free": "Free", "starter": "Starter", "pro": "Pro", "scale": "Scale"}
    price_labels = {"free": "Free", "starter": "$29/mo", "pro": "$79/mo", "scale": "$199/mo"}
    return {
        "success": True,
        "data": {
            "plan": plan_labels.get(sub.plan, sub.plan.capitalize()),
            "status": sub.status.capitalize(),
            "renewDate": renew,
            "priceLabel": price_labels.get(sub.plan, "—"),
            "usage": {
                "conversationsUsed": usage.conversations_used,
                "conversationsQuota": sub.monthly_conversation_quota,
                "numbersUsed": 1,
                "numbersQuota": sub.max_numbers,
                "seatsUsed": 1,
                "seatsQuota": sub.max_seats,
                "mediaStoredMb": usage.media_stored_mb,
                "mediaQuotaMb": sub.media_storage_mb,
            },
        },
    }


class CheckoutBody(BaseModel):
    plan: str


@router.post("/checkout")
async def checkout(body: CheckoutBody, ctx: AuthContext = Depends(require_role("admin")), db: Session = Depends(get_db)):
    plan = billing.get_plan(body.plan)
    if not plan.stripe_price_id:
        raise HTTPException(status_code=400, detail="This plan is not purchasable (no Stripe price configured)")
    sub = billing.get_or_create_subscription(db, ctx.tenant.id)
    db.commit()
    try:
        session = billing.create_checkout_session(
            customer_id=sub.stripe_customer_id,
            price_id=plan.stripe_price_id,
            success_url="/billing?status=success",
            cancel_url="/billing?status=cancelled",
            workspace_id=str(ctx.tenant.id),
        )
    except Exception as e:  # Stripe/network errors
        logger.error("[billing/checkout] %s", e)
        raise HTTPException(status_code=502, detail="Could not start checkout")
    return {"success": True, "data": {"url": getattr(session, "url", None)}}


@router.post("/webhook")
async def stripe_webhook(request: Request, db: Session = Depends(get_db)):
    payload = await request.body()
    sig = request.headers.get("stripe-signature", "")
    try:
        event = billing.verify_and_parse_event(payload, sig)
    except Exception as e:
        logger.warning("[billing/webhook] signature verification failed: %s", e)
        raise HTTPException(status_code=400, detail="Invalid signature")
    billing.handle_event(db, event)
    return {"received": True}
