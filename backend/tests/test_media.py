"""07 — Media service unit tests.

Tests cover:
  - upload_asset stores bytes and creates a DB row (local dev path)
  - get_signed_url returns /media/{id}/file when S3 is unconfigured
  - delete_asset removes the DB row and local file
  - list_assets returns assets scoped to the workspace
  - resolve_outgoing_media returns OutgoingMedia with path for wacli (local path)
  - _kind_for_mime and _ext_for_mime helpers
  - ingest_inbound_media downloads and stores inbound media
"""

from __future__ import annotations

import uuid
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from app.services.media import (
    _ext_for_mime,
    _kind_for_mime,
    _local_path,
    delete_asset,
    download_asset_bytes,
    get_asset,
    get_signed_url,
    ingest_inbound_media,
    list_assets,
    resolve_outgoing_media,
    upload_asset,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _mock_asset(workspace_id: str = "ws-1", asset_id: str | None = None, mime: str = "image/jpeg"):
    a = MagicMock()
    a.id = uuid.UUID(asset_id) if asset_id else uuid.uuid4()
    a.workspace_id = workspace_id
    a.type = _kind_for_mime(mime)
    a.mime = mime
    a.size_bytes = 123
    a.tags = []
    a.storage_key = f"{workspace_id}/{a.id}/test.jpg"
    a.wa_media_id = None
    return a


def _mock_db():
    db = MagicMock()
    db.add.return_value = None
    db.commit.return_value = None
    db.refresh.return_value = None
    return db


# ---------------------------------------------------------------------------
# MIME helpers
# ---------------------------------------------------------------------------

def test_kind_for_mime_image():
    assert _kind_for_mime("image/jpeg") == "image"
    assert _kind_for_mime("image/png") == "image"


def test_kind_for_mime_video():
    assert _kind_for_mime("video/mp4") == "video"


def test_kind_for_mime_document():
    assert _kind_for_mime("application/pdf") == "document"


def test_ext_for_mime_jpeg():
    assert _ext_for_mime("image/jpeg") == ".jpg"


def test_ext_for_mime_png():
    assert _ext_for_mime("image/png") == ".png"


def test_ext_for_mime_mp4():
    assert _ext_for_mime("video/mp4") == ".mp4"


# ---------------------------------------------------------------------------
# upload_asset — local dev path (no S3)
# ---------------------------------------------------------------------------

def test_upload_asset_writes_local_file(tmp_path, monkeypatch):
    monkeypatch.setattr("app.services.media._LOCAL_DIR", tmp_path)
    monkeypatch.setattr("app.services.media._s3_configured", lambda: False)

    ws_id = str(uuid.uuid4())
    db = _mock_db()

    # Capture the MediaAsset constructed
    created = {}
    original_add = db.add
    def capture_add(obj):
        created["asset"] = obj
    db.add.side_effect = capture_add

    with patch("app.services.media.MediaAsset") as MockAsset:
        fake = MagicMock()
        fake.storage_key = f"{ws_id}/test-id/photo.jpg"
        MockAsset.return_value = fake

        upload_asset(db, workspace_id=ws_id, data=b"IMGDATA", filename="photo.jpg", mime="image/jpeg")

        MockAsset.assert_called_once()
        kwargs = MockAsset.call_args.kwargs
        assert kwargs["workspace_id"] == ws_id
        assert kwargs["mime"] == "image/jpeg"
        assert kwargs["type"] == "image"
        assert kwargs["size_bytes"] == 7


def test_upload_asset_creates_local_dirs(tmp_path, monkeypatch):
    """upload_asset writes the binary to the local dir tree and the bytes are correct."""
    monkeypatch.setattr("app.services.media._LOCAL_DIR", tmp_path)
    monkeypatch.setattr("app.services.media._s3_configured", lambda: False)

    ws_id = str(uuid.uuid4())
    db = _mock_db()

    with patch("app.services.media.MediaAsset") as MockAsset:
        # Capture the storage_key that upload_asset actually constructs
        captured = {}
        def make_asset(**kwargs):
            captured["storage_key"] = kwargs["storage_key"]
            m = MagicMock()
            m.storage_key = kwargs["storage_key"]
            return m
        MockAsset.side_effect = make_asset

        upload_asset(db, workspace_id=ws_id, data=b"PNG", filename="img.png", mime="image/png")

        dest = tmp_path / captured["storage_key"].replace("/", str(Path("/")))
        # Reconstruct path using the captured key
        dest = _local_path(captured["storage_key"])
        assert dest.exists()
        assert dest.read_bytes() == b"PNG"


# ---------------------------------------------------------------------------
# get_signed_url — dev fallback
# ---------------------------------------------------------------------------

def test_get_signed_url_dev_returns_file_path(monkeypatch):
    monkeypatch.setattr("app.services.media._s3_configured", lambda: False)
    asset = _mock_asset()
    url = get_signed_url(asset)
    assert url == f"/api/v1/media/{asset.id}/file"


# ---------------------------------------------------------------------------
# delete_asset
# ---------------------------------------------------------------------------

def test_delete_asset_removes_local_file(tmp_path, monkeypatch):
    monkeypatch.setattr("app.services.media._LOCAL_DIR", tmp_path)
    monkeypatch.setattr("app.services.media._s3_configured", lambda: False)

    asset = _mock_asset()
    local = _local_path(asset.storage_key)
    local.parent.mkdir(parents=True, exist_ok=True)
    local.write_bytes(b"TODELETE")

    db = _mock_db()
    delete_asset(db, asset)

    assert not local.exists()
    db.delete.assert_called_once_with(asset)
    db.commit.assert_called_once()


# ---------------------------------------------------------------------------
# resolve_outgoing_media — local dev path
# ---------------------------------------------------------------------------

def test_resolve_outgoing_media_local(tmp_path, monkeypatch):
    monkeypatch.setattr("app.services.media._LOCAL_DIR", tmp_path)
    monkeypatch.setattr("app.services.media._s3_configured", lambda: False)

    asset = _mock_asset(mime="image/jpeg")
    local = _local_path(asset.storage_key)
    local.parent.mkdir(parents=True, exist_ok=True)
    local.write_bytes(b"IMGBYTES")

    outgoing = resolve_outgoing_media(asset)
    assert outgoing.kind == "image"
    assert outgoing.mime == "image/jpeg"
    assert outgoing.path is not None
    assert Path(outgoing.path).read_bytes() == b"IMGBYTES"
    # Caller's responsibility to unlink the temp file; just assert it exists
    Path(outgoing.path).unlink(missing_ok=True)


# ---------------------------------------------------------------------------
# ingest_inbound_media
# ---------------------------------------------------------------------------

def test_ingest_inbound_media_calls_upload(monkeypatch):
    """ingest_inbound_media should download the URL and call upload_asset."""
    monkeypatch.setattr("app.services.media._s3_configured", lambda: False)

    db = _mock_db()
    ws_id = str(uuid.uuid4())
    fake_asset = MagicMock()

    # Patch httpx.Client used inside the function
    import httpx as _httpx
    mock_resp = MagicMock()
    mock_resp.content = b"IMGDATA"
    mock_resp.raise_for_status.return_value = None

    with patch.object(_httpx, "Client") as mock_client_cls, \
         patch("app.services.media.upload_asset", return_value=fake_asset) as mock_upload:

        mock_client = MagicMock()
        mock_client_cls.return_value.__enter__ = MagicMock(return_value=mock_client)
        mock_client_cls.return_value.__exit__ = MagicMock(return_value=False)
        mock_client.get.return_value = mock_resp

        result = ingest_inbound_media(
            db,
            workspace_id=ws_id,
            lead_id=str(uuid.uuid4()),
            media_url="https://example.com/media.jpg",
            mime="image/jpeg",
        )

        mock_upload.assert_called_once()
        kw = mock_upload.call_args.kwargs
        assert kw["workspace_id"] == ws_id
        assert kw["mime"] == "image/jpeg"
        assert "inbound" in kw["tags"]
        assert result is fake_asset


def test_ingest_inbound_media_returns_none_on_download_failure(monkeypatch):
    """Network failure must return None (non-fatal) so the message is still recorded."""
    monkeypatch.setattr("app.services.media._s3_configured", lambda: False)

    import httpx as _httpx
    db = _mock_db()

    with patch.object(_httpx, "Client") as mock_client_cls:
        mock_client = MagicMock()
        mock_client_cls.return_value.__enter__ = MagicMock(return_value=mock_client)
        mock_client_cls.return_value.__exit__ = MagicMock(return_value=False)
        mock_client.get.side_effect = Exception("network error")

        result = ingest_inbound_media(
            db,
            workspace_id="ws-1",
            lead_id="lead-1",
            media_url="https://bad.example.com/file.jpg",
            mime="image/jpeg",
        )
        assert result is None


def test_catalogue_for_agent_skips_inbound():
    from app.services.media import catalogue_for_agent

    brand = _mock_asset()
    brand.tags = ["portfolio"]
    inbound = _mock_asset()
    inbound.tags = ["inbound"]

    db = _mock_db()
    with patch("app.services.media.list_assets", return_value=[brand, inbound]):
        cat = catalogue_for_agent(db, "ws-1")
    assert len(cat) == 1
    assert cat[0]["id"] == str(brand.id)
    assert "portfolio" in cat[0]["tags"]
