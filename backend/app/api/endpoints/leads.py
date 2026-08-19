"""Leads CRM API (Feature 15) — list/filter/detail/patch.

Parse + auth + delegate only. Business logic lives in `services/crm.py`.
All queries run inside `get_tenant_db` → `tenant_context()` (RLS GUC).
"""
from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from app.core.auth import AuthContext, get_auth_context, get_tenant_db
from app.models.database import Lead, LeadStatus, MessageRole
from app.services import crm

logger = logging.getLogger(__name__)
router = APIRouter()


# ---------------------------------------------------------------------------
# Response / request models (Pydantic v2)
# ---------------------------------------------------------------------------


class LeadSummaryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    status: str
    intent_label: Optional[str] = None
    score: int = 0
    service_interest: Optional[str] = None
    source: str = "DIRECT"
    last_inbound_at: Optional[str] = None
    meeting_status: str = "NOT_REQUESTED"
    do_not_contact: bool = False
    requirement_summary: Optional[str] = None


class LeadListData(BaseModel):
    items: list[LeadSummaryOut]
    total: int
    limit: int
    offset: int


class MemoryFactOut(BaseModel):
    id: str
    category: Optional[str] = None
    fact: str
    confidence: Optional[int] = None
    source: str = "stated"


class ThreadMessageOut(BaseModel):
    id: str
    direction: Literal["inbound", "outbound"]
    role: str
    content: str
    timestamp: Optional[str] = None
    status: Optional[str] = None


class ConversationOut(BaseModel):
    id: str
    status: str
    human_takeover: bool
    last_inbound_at: Optional[str] = None
    messages: list[ThreadMessageOut] = Field(default_factory=list)


class ConsentOut(BaseModel):
    id: str
    source: str
    granted_at: Optional[str] = None
    revoked_at: Optional[str] = None


class LeadDetailOut(LeadSummaryOut):
    memory_facts: list[MemoryFactOut] = Field(default_factory=list)
    conversation: Optional[ConversationOut] = None
    consent: Optional[ConsentOut] = None


class LeadPatchBody(BaseModel):
    status: Optional[str] = None
    intent_label: Optional[str] = None
    do_not_contact: Optional[bool] = None


class ApiEnvelope(BaseModel):
    success: bool
    data: Any = None
    error: Optional[str] = None


def _iso(dt: Optional[datetime]) -> Optional[str]:
    return dt.isoformat() if dt else None


def _status_value(status: LeadStatus | str) -> str:
    return status.value if isinstance(status, LeadStatus) else str(status)


def _summary(lead: Lead) -> LeadSummaryOut:
    return LeadSummaryOut(
        id=str(lead.id),
        name=lead.name,
        status=_status_value(lead.status),
        intent_label=lead.intent_label,
        score=int(lead.score or 0),
        service_interest=lead.service_interest,
        source=(lead.source or "DIRECT"),
        last_inbound_at=_iso(lead.last_inbound_at),
        meeting_status=lead.meeting_status or "NOT_REQUESTED",
        do_not_contact=bool(lead.do_not_contact),
        requirement_summary=lead.requirement_summary,
    )


def _detail(result: crm.LeadDetailResult) -> LeadDetailOut:
    lead = result.lead
    base = _summary(lead)
    convo_out: Optional[ConversationOut] = None
    if result.conversation is not None:
        convo = result.conversation
        convo_out = ConversationOut(
            id=str(convo.id),
            status=convo.status,
            human_takeover=bool(convo.human_takeover),
            last_inbound_at=_iso(convo.last_inbound_at),
            messages=[
                ThreadMessageOut(
                    id=str(m.id),
                    direction=crm.message_direction(m.role),
                    role=m.role.value if isinstance(m.role, MessageRole) else str(m.role),
                    content=m.content,
                    timestamp=_iso(m.timestamp),
                    status=m.status.value if m.status is not None else None,
                )
                for m in result.messages
            ],
        )
    elif result.messages:
        # Thread exists even if Conversation row is missing (legacy inbound).
        convo_out = ConversationOut(
            id="",
            status="active",
            human_takeover=False,
            last_inbound_at=_iso(lead.last_inbound_at),
            messages=[
                ThreadMessageOut(
                    id=str(m.id),
                    direction=crm.message_direction(m.role),
                    role=m.role.value if isinstance(m.role, MessageRole) else str(m.role),
                    content=m.content,
                    timestamp=_iso(m.timestamp),
                    status=m.status.value if m.status is not None else None,
                )
                for m in result.messages
            ],
        )

    consent_out = None
    if result.consent is not None:
        c = result.consent
        consent_out = ConsentOut(
            id=str(c.id),
            source=c.source,
            granted_at=_iso(c.granted_at),
            revoked_at=_iso(c.revoked_at),
        )

    return LeadDetailOut(
        **base.model_dump(),
        memory_facts=[
            MemoryFactOut(
                id=str(f.id),
                category=f.category,
                fact=f.fact,
                confidence=f.confidence,
                source=f.source or "stated",
            )
            for f in result.memory_facts
        ],
        conversation=convo_out,
        consent=consent_out,
    )


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.get("")
@router.get("/")
def list_leads(
    status: Optional[str] = Query(None),
    intent_label: Optional[str] = Query(None),
    source: Optional[str] = Query(None),
    min_score: Optional[int] = Query(None, ge=0, le=100),
    do_not_contact: Optional[bool] = Query(None),
    search: Optional[str] = Query(None),
    sort: Optional[str] = Query("last_inbound_at"),
    limit: Optional[int] = Query(None, ge=1, le=crm.LEAD_LIST_MAX_LIMIT),
    offset: Optional[int] = Query(0, ge=0),
    ctx: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_tenant_db),
):
    try:
        query = crm.normalize_lead_list_query(
            status=status,
            intent_label=intent_label,
            source=source,
            min_score=min_score,
            do_not_contact=do_not_contact,
            search=search,
            sort=sort,
            limit=limit,
            offset=offset,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    result = crm.list_leads(db, ctx.tenant_id, query)
    data = LeadListData(
        items=[_summary(lead) for lead in result.leads],
        total=result.total,
        limit=result.limit,
        offset=result.offset,
    )
    return ApiEnvelope(success=True, data=data).model_dump()


@router.get("/{lead_id}")
def get_lead(
    lead_id: str,
    ctx: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_tenant_db),
):
    result = crm.get_lead_detail(db, ctx.tenant_id, lead_id)
    if not result:
        raise HTTPException(status_code=404, detail="Lead not found")
    return ApiEnvelope(success=True, data=_detail(result)).model_dump()


@router.patch("/{lead_id}")
def patch_lead(
    lead_id: str,
    body: LeadPatchBody,
    ctx: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_tenant_db),
):
    if body.status is None and body.intent_label is None and body.do_not_contact is None:
        raise HTTPException(status_code=422, detail="no fields to update")
    try:
        lead = crm.update_lead(
            db,
            ctx.tenant_id,
            lead_id,
            status=body.status,
            intent_label=body.intent_label,
            do_not_contact=body.do_not_contact,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")

    # Persist before returning; tenant_context also commits on exit.
    try:
        db.commit()
        db.refresh(lead)
    except Exception:
        logger.exception("[leads/patch] commit failed for lead=%s", lead_id)
        db.rollback()
        raise HTTPException(status_code=500, detail="Update failed")

    return ApiEnvelope(success=True, data=_summary(lead)).model_dump()
