"""Media service — upload / retrieve / delete tenant brand media assets.

Storage backend: S3-compatible (AWS S3 or Cloudflare R2) when
OBJECT_STORAGE_ENDPOINT + OBJECT_STORAGE_BUCKET + keys are set.
Falls back to local filesystem under /tmp/prepop-media/ for dev.

Every asset is scoped to a tenant (workspace_id). The binary never lives in
Postgres — only the storage_key and metadata do.
"""

from __future__ import annotations

import logging
import mimetypes
import os
import uuid
from pathlib import Path
from typing import Optional

from sqlalchemy.orm import Session

from app.core.config import settings
from app.messaging.base import OutgoingMedia
from app.models.database import MediaAsset

logger = logging.getLogger(__name__)

_LOCAL_DIR = Path("/tmp/prepop-media")

# ---------------------------------------------------------------------------
# Storage backend (lazy initialised)
# ---------------------------------------------------------------------------

def _s3_configured() -> bool:
    return bool(
        settings.OBJECT_STORAGE_ENDPOINT
        and settings.OBJECT_STORAGE_BUCKET
        and settings.OBJECT_STORAGE_KEY
        and settings.OBJECT_STORAGE_SECRET
    )


def _s3_client():
    import boto3  # lazy — only imported when S3 is configured
    return boto3.client(
        "s3",
        endpoint_url=settings.OBJECT_STORAGE_ENDPOINT,
        aws_access_key_id=settings.OBJECT_STORAGE_KEY,
        aws_secret_access_key=settings.OBJECT_STORAGE_SECRET,
        region_name="auto",
    )


def _local_path(storage_key: str) -> Path:
    return _LOCAL_DIR / storage_key.replace("/", os.sep)


# ---------------------------------------------------------------------------
# Core operations
# ---------------------------------------------------------------------------

def upload_asset(
    db: Session,
    *,
    workspace_id: str,
    data: bytes,
    filename: str,
    mime: str,
    tags: Optional[list[str]] = None,
) -> MediaAsset:
    """Store `data` in object storage and persist a `media_assets` row."""
    asset_id = str(uuid.uuid4())
    ext = Path(filename).suffix or _ext_for_mime(mime)
    storage_key = f"{workspace_id}/{asset_id}/{filename}"
    kind = _kind_for_mime(mime)

    if _s3_configured():
        client = _s3_client()
        client.put_object(
            Bucket=settings.OBJECT_STORAGE_BUCKET,
            Key=storage_key,
            Body=data,
            ContentType=mime,
        )
        logger.info("[media] uploaded to S3 key=%s", storage_key)
    else:
        dest = _local_path(storage_key)
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(data)
        logger.info("[media] saved locally path=%s", dest)

    asset = MediaAsset(
        id=uuid.UUID(asset_id),
        workspace_id=workspace_id,
        type=kind,
        storage_key=storage_key,
        mime=mime,
        size_bytes=len(data),
        tags=tags or [],
    )
    db.add(asset)
    db.commit()
    db.refresh(asset)
    return asset


def get_signed_url(asset: MediaAsset, expires: int = 3600) -> str:
    """Return a time-limited URL to download the asset binary."""
    if _s3_configured():
        client = _s3_client()
        return client.generate_presigned_url(
            "get_object",
            Params={"Bucket": settings.OBJECT_STORAGE_BUCKET, "Key": asset.storage_key},
            ExpiresIn=expires,
        )
    # Dev: serve via the /media/{id}/file endpoint (handled in api/endpoints/media.py)
    return f"/api/v1/media/{asset.id}/file"


def download_asset_bytes(asset: MediaAsset) -> bytes:
    """Return raw bytes for the asset — used when wacli needs a local file path."""
    if _s3_configured():
        client = _s3_client()
        resp = client.get_object(
            Bucket=settings.OBJECT_STORAGE_BUCKET,
            Key=asset.storage_key,
        )
        return resp["Body"].read()
    p = _local_path(asset.storage_key)
    if not p.exists():
        raise FileNotFoundError(f"Local media not found: {p}")
    return p.read_bytes()


def delete_asset(db: Session, asset: MediaAsset) -> None:
    """Delete binary from storage and remove the DB row."""
    if _s3_configured():
        try:
            _s3_client().delete_object(
                Bucket=settings.OBJECT_STORAGE_BUCKET,
                Key=asset.storage_key,
            )
        except Exception as exc:
            logger.warning("[media] S3 delete failed for key=%s: %s", asset.storage_key, exc)
    else:
        p = _local_path(asset.storage_key)
        p.unlink(missing_ok=True)

    db.delete(asset)
    db.commit()


def list_assets(db: Session, workspace_id: str) -> list[MediaAsset]:
    return (
        db.query(MediaAsset)
        .filter(MediaAsset.workspace_id == workspace_id)
        .order_by(MediaAsset.created_at.desc())
        .all()
    )


def get_asset(db: Session, workspace_id: str, asset_id: str) -> Optional[MediaAsset]:
    return (
        db.query(MediaAsset)
        .filter(MediaAsset.workspace_id == workspace_id, MediaAsset.id == asset_id)
        .first()
    )


def catalogue_for_agent(db: Session, workspace_id: str) -> list[dict]:
    """Compact brand-asset catalogue for the LLM (metadata only — no binaries).

    Excludes inbound prospect media (tagged ``inbound``). Agent may only propose
    tenant-owned brand assets from this list.
    """
    catalogue: list[dict] = []
    for asset in list_assets(db, workspace_id):
        tags = list(asset.tags or [])
        if "inbound" in tags:
            continue
        caption = ", ".join(tags) if tags else (asset.type or "media")
        catalogue.append({
            "id": str(asset.id),
            "type": asset.type or "image",
            "tags": tags,
            "caption": caption,
        })
    return catalogue


def resolve_outgoing_media(asset: MediaAsset) -> OutgoingMedia:
    """Convert a MediaAsset row into the transport-neutral OutgoingMedia struct.

    For wacli: download bytes to a temp file and return path.
    For Cloud API (deferred): use wa_media_id or signed URL.
    """
    import tempfile

    kind = asset.type or "image"
    mime = asset.mime or "application/octet-stream"

    if _s3_configured():
        # Generate signed URL — WacliProvider will download it to a temp file.
        url = get_signed_url(asset, expires=300)
        return OutgoingMedia(kind=kind, url=url, mime=mime, wa_media_id=asset.wa_media_id)

    # Dev: materialise from local storage to a temp file for wacli send file.
    data = download_asset_bytes(asset)
    suffix = _ext_for_mime(mime)
    fd, tmp_path = tempfile.mkstemp(prefix="prepop-send-", suffix=suffix)
    try:
        os.close(fd)
        Path(tmp_path).write_bytes(data)
    except Exception:
        os.unlink(tmp_path)
        raise
    return OutgoingMedia(kind=kind, path=tmp_path, mime=mime)


# ---------------------------------------------------------------------------
# Inbound media ingestion (from wacli webhook payload)
# ---------------------------------------------------------------------------

def ingest_inbound_media(
    db: Session,
    *,
    workspace_id: str,
    lead_id: str,
    media_url: str,
    mime: str,
    filename: Optional[str] = None,
) -> Optional[MediaAsset]:
    """Download inbound media from wacli webhook URL and store it as an asset.

    Returns None if the download fails (non-fatal — conversation still recorded).
    """
    import httpx

    try:
        with httpx.Client(timeout=30.0, follow_redirects=True) as client:
            resp = client.get(media_url)
            resp.raise_for_status()
            data = resp.content
    except Exception as exc:
        logger.warning("[media] inbound download failed url=%s: %s", media_url, exc)
        return None

    fname = filename or f"inbound-{uuid.uuid4()}{_ext_for_mime(mime)}"
    return upload_asset(
        db,
        workspace_id=workspace_id,
        data=data,
        filename=fname,
        mime=mime,
        tags=["inbound"],
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _kind_for_mime(mime: str) -> str:
    m = (mime or "").lower()
    if m.startswith("image/"):
        return "image"
    if m.startswith("video/"):
        return "video"
    if m.startswith("audio/"):
        return "audio"
    return "document"


def _ext_for_mime(mime: str) -> str:
    ext = mimetypes.guess_extension(mime or "")
    if ext in (None, ".jpe"):
        # Common overrides
        overrides = {
            "image/jpeg": ".jpg",
            "image/png": ".png",
            "image/webp": ".webp",
            "video/mp4": ".mp4",
            "audio/ogg": ".ogg",
            "application/pdf": ".pdf",
        }
        return overrides.get((mime or "").lower(), ".bin")
    return ext
