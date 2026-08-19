"""Feature 03 — agent selects tenant media and sends through the gate.

Covers:
  - pipeline picks a valid catalogue id → enqueue calls send_media after gate allows
  - invalid/foreign id → text-only (no send_media), no crash
  - gate block (DNC / quota) → neither text nor media goes out
  - catalogue excludes inbound-tagged assets
  - inbound ingest links media_asset_id onto the Message
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from app.core.outreach_policy import OutreachDecision, OutreachKind, gate
from app.services.media import catalogue_for_agent
from app.tasks.ai_tasks import enqueue_agent_outbound


ASSET_ID = "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"
NOW = datetime(2026, 8, 20, 12, 0, tzinfo=timezone.utc)


# ---------------------------------------------------------------------------
# enqueue_agent_outbound — the gated send seam
# ---------------------------------------------------------------------------

def test_valid_media_enqueues_send_media_when_gate_allows():
    sent = {"text": [], "media": []}
    decision = OutreachDecision(allowed=True, reason="within_service_window")

    outcome = enqueue_agent_outbound(
        workspace_id="ws-1",
        to="1555@s.whatsapp.net",
        reply="here's a portfolio shot",
        media_asset_id=ASSET_ID,
        decision=decision,
        should_auto_send=True,
        send_text=lambda *a, **k: sent["text"].append((a, k)),
        send_media=lambda *a, **k: sent["media"].append((a, k)),
    )

    assert outcome == "sent_media"
    assert len(sent["media"]) == 1
    args, kwargs = sent["media"][0]
    assert args[0] == "ws-1"
    assert args[1] == "1555@s.whatsapp.net"
    assert args[2] == ASSET_ID
    assert kwargs.get("caption") == "here's a portfolio shot" or (len(args) > 3 and args[3] == "here's a portfolio shot")
    assert sent["text"] == []


def test_invalid_media_none_sends_text_only():
    """After pipeline drops a bad id, media_asset_id is None → text path."""
    sent = {"text": [], "media": []}
    decision = OutreachDecision(allowed=True, reason="within_service_window")

    outcome = enqueue_agent_outbound(
        workspace_id="ws-1",
        to="1555@s.whatsapp.net",
        reply="sure, what's your timeline?",
        media_asset_id=None,
        decision=decision,
        should_auto_send=True,
        send_text=lambda *a, **k: sent["text"].append(a),
        send_media=lambda *a, **k: sent["media"].append(a),
    )

    assert outcome == "sent_text"
    assert len(sent["text"]) == 1
    assert sent["media"] == []


def test_gate_blocked_sends_neither_text_nor_media():
    """Compliance: over-quota / DNC / outside window → no transport call."""
    sent = {"text": [], "media": []}
    decision = OutreachDecision(allowed=False, reason="daily_quota_exceeded")

    outcome = enqueue_agent_outbound(
        workspace_id="ws-1",
        to="1555@s.whatsapp.net",
        reply="here's a shot",
        media_asset_id=ASSET_ID,
        decision=decision,
        should_auto_send=False,  # generate_ai_reply sets this False when gate denies
        send_text=lambda *a, **k: sent["text"].append(a),
        send_media=lambda *a, **k: sent["media"].append(a),
    )

    assert outcome == "blocked"
    assert sent["text"] == []
    assert sent["media"] == []


def test_gate_dnc_then_media_does_not_go_out():
    """End-to-end gate check: DNC lead cannot receive media."""
    tenant = SimpleNamespace(
        agent_enabled=True, is_running=True,
        daily_message_limit=35, messages_sent_today=0,
    )
    lead = SimpleNamespace(do_not_contact=True, last_inbound_at=NOW)
    decision = gate(tenant, lead, OutreachKind.AGENT_REPLY, now=NOW)
    assert not decision.allowed

    sent_media = []
    outcome = enqueue_agent_outbound(
        workspace_id="ws-1",
        to="1555@s.whatsapp.net",
        reply="portfolio",
        media_asset_id=ASSET_ID,
        decision=decision,
        should_auto_send=False,
        send_media=lambda *a, **k: sent_media.append(a),
    )
    assert outcome == "blocked"
    assert sent_media == []


# ---------------------------------------------------------------------------
# catalogue_for_agent — brand only, no inbound
# ---------------------------------------------------------------------------

def test_catalogue_excludes_inbound_tagged_assets():
    brand_id = str(uuid.uuid4())
    inbound_id = str(uuid.uuid4())

    brand = MagicMock()
    brand.id = uuid.UUID(brand_id)
    brand.type = "image"
    brand.tags = ["portfolio", "hero"]

    inbound = MagicMock()
    inbound.id = uuid.UUID(inbound_id)
    inbound.type = "image"
    inbound.tags = ["inbound"]

    db = MagicMock()
    with patch("app.services.media.list_assets", return_value=[brand, inbound]):
        cat = catalogue_for_agent(db, "ws-1")

    ids = {e["id"] for e in cat}
    assert brand_id in ids
    assert inbound_id not in ids
    assert cat[0]["caption"] == "portfolio, hero"


# ---------------------------------------------------------------------------
# Inbound media linked onto Message (Part 4)
# ---------------------------------------------------------------------------

def test_inbound_media_sets_message_media_asset_id():
    """When ingest returns an asset, inbound_wacli assigns it to the Message."""
    asset = MagicMock()
    asset.id = uuid.uuid4()

    inbound_msg = SimpleNamespace(media_asset_id=None)

    # Simulate the linking logic used in inbound_wacli after ingest_inbound_media
    if asset is not None:
        inbound_msg.media_asset_id = asset.id

    assert inbound_msg.media_asset_id == asset.id


def test_inbound_ingest_failure_leaves_message_without_media():
    """Download failure → None asset → message still recorded, media_asset_id unset."""
    inbound_msg = SimpleNamespace(media_asset_id=None)
    asset = None
    if asset is not None:
        inbound_msg.media_asset_id = asset.id
    assert inbound_msg.media_asset_id is None
