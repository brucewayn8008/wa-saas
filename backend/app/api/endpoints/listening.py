"""Listening inbox API (Feature 16) — list processed group leads + soft dismiss.

Parse + auth + delegate only. Business logic lives in `services/listening.py`.
All queries run inside `get_tenant_db` → `tenant_context()` (RLS GUC).
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session

from app.core.auth import AuthContext, get_auth_context, get_tenant_db
from app.models.database import ListeningLead
from app.services import listening as listening_svc

logger = logging.getLogger(__name__)
router = APIRouter()


class ListeningItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    group_name: str
    original_message: str
    match_reason: str
    match_score: Optional[int] = None
    reply_text: Optional[str] = None
    status: str
    block_reason: Optional[str] = None
    created_at: Optional[str] = None
    lead_id: Optional[str] = None


class ApiEnvelope(BaseModel):
    success: bool
    data: Any = None
    error: Optional[str] = None


def _iso(dt: Optional[datetime]) -> Optional[str]:
    return dt.isoformat() if dt else None


def _item(row: ListeningLead) -> ListeningItemOut:
    return ListeningItemOut(
        id=str(row.id),
        group_name=row.group_name,
        original_message=row.original_message,
        match_reason=row.match_reason,
        match_score=row.match_score,
        reply_text=row.reply_text,
        status=row.status,
        block_reason=row.block_reason,
        created_at=_iso(row.created_at),
        lead_id=str(row.lead_id) if row.lead_id else None,
    )


@router.get("")
@router.get("/")
def list_listening(
    ctx: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_tenant_db),
):
    rows = listening_svc.list_listening(db, ctx.tenant_id)
    return ApiEnvelope(success=True, data=[_item(r) for r in rows]).model_dump()


@router.delete("/{listening_id}")
def dismiss_listening(
    listening_id: str,
    ctx: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_tenant_db),
):
    row = listening_svc.dismiss(db, ctx.tenant_id, listening_id)
    if not row:
        raise HTTPException(status_code=404, detail="Listening item not found")
    try:
        db.commit()
    except Exception:
        logger.exception("[listening/dismiss] commit failed id=%s", listening_id)
        db.rollback()
        raise HTTPException(status_code=500, detail="Dismiss failed")
    return ApiEnvelope(success=True, data={"id": str(row.id), "status": row.status}).model_dump()
