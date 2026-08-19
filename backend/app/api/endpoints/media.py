"""Media API — upload / list / delete / serve tenant brand assets.

POST   /media/upload      — multipart file upload
GET    /media             — list all assets for the tenant
GET    /media/{id}        — single asset metadata + signed URL
DELETE /media/{id}        — delete asset (storage + DB row)
GET    /media/{id}/file   — stream binary (dev fallback when no S3)
POST   /media/{id}/send   — send asset to a lead via wacli
"""

from __future__ import annotations

import logging
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from fastapi.responses import Response
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.auth import AuthContext, get_auth_context, get_tenant_db
from app.models.database import Lead
from app.services import media as media_svc

logger = logging.getLogger(__name__)
router = APIRouter()

ALLOWED_MIME_PREFIXES = ("image/", "video/", "audio/")
MAX_UPLOAD_BYTES = 50 * 1024 * 1024  # 50 MB


# ---------------------------------------------------------------------------
# Response schemas
# ---------------------------------------------------------------------------

class AssetOut(BaseModel):
    id: str
    type: str
    mime: Optional[str]
    size_bytes: Optional[int]
    tags: Optional[list[str]]
    url: str                   # signed URL or /media/{id}/file in dev
    created_at: str

    model_config = {"from_attributes": True}


def _asset_out(asset, db: Session, workspace_id: str) -> AssetOut:
    return AssetOut(
        id=str(asset.id),
        type=asset.type,
        mime=asset.mime,
        size_bytes=asset.size_bytes,
        tags=asset.tags or [],
        url=media_svc.get_signed_url(asset),
        created_at=asset.created_at.isoformat(),
    )


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("/upload", response_model=AssetOut, status_code=status.HTTP_201_CREATED)
async def upload_media(
    file: UploadFile = File(...),
    tags: Optional[str] = Form(None),  # comma-separated e.g. "portfolio,hero"
    ctx: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_tenant_db),
):
    """Upload a brand media asset (image or video). Max 50 MB."""
    mime = file.content_type or "application/octet-stream"
    if not any(mime.startswith(p) for p in ALLOWED_MIME_PREFIXES):
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"Unsupported media type: {mime}. Allowed: image/*, video/*, audio/*",
        )

    data = await file.read()
    if len(data) > MAX_UPLOAD_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File exceeds {MAX_UPLOAD_BYTES // (1024*1024)} MB limit",
        )

    tag_list = [t.strip() for t in (tags or "").split(",") if t.strip()]

    asset = media_svc.upload_asset(
        db,
        workspace_id=ctx.tenant_id,
        data=data,
        filename=file.filename or f"upload-{uuid.uuid4()}",
        mime=mime,
        tags=tag_list,
    )
    return _asset_out(asset, db, ctx.tenant_id)


@router.get("", response_model=list[AssetOut])
def list_media(
    ctx: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_tenant_db),
):
    """List all media assets for the tenant, newest first."""
    assets = media_svc.list_assets(db, ctx.tenant_id)
    return [_asset_out(a, db, ctx.tenant_id) for a in assets]


@router.get("/{asset_id}", response_model=AssetOut)
def get_media(
    asset_id: str,
    ctx: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_tenant_db),
):
    asset = media_svc.get_asset(db, ctx.tenant_id, asset_id)
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")
    return _asset_out(asset, db, ctx.tenant_id)


@router.delete("/{asset_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_media(
    asset_id: str,
    ctx: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_tenant_db),
):
    asset = media_svc.get_asset(db, ctx.tenant_id, asset_id)
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")
    media_svc.delete_asset(db, asset)


@router.get("/{asset_id}/file")
def serve_media_file(
    asset_id: str,
    ctx: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_tenant_db),
):
    """Stream the binary for dev environments without S3. In prod, use the signed URL."""
    asset = media_svc.get_asset(db, ctx.tenant_id, asset_id)
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")
    try:
        data = media_svc.download_asset_bytes(asset)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Asset file not found in storage")
    return Response(content=data, media_type=asset.mime or "application/octet-stream")


class SendMediaBody(BaseModel):
    lead_id: str
    caption: Optional[str] = None


@router.post("/{asset_id}/send", status_code=status.HTTP_202_ACCEPTED)
def send_media_to_lead(
    asset_id: str,
    body: SendMediaBody,
    ctx: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_tenant_db),
):
    """Enqueue sending a media asset to a lead via wacli."""
    asset = media_svc.get_asset(db, ctx.tenant_id, asset_id)
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")

    lead = db.query(Lead).filter(
        Lead.workspace_id == ctx.tenant_id,
        Lead.id == body.lead_id,
    ).first()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")

    from app.tasks.whatsapp_tasks import send_whatsapp_media
    send_whatsapp_media.delay(
        workspace_id=ctx.tenant_id,
        to=lead.jid,
        asset_id=asset_id,
        caption=body.caption,
    )
    return {"queued": True, "asset_id": asset_id, "lead_id": body.lead_id}
