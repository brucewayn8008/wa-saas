"""Unit tests for the wacli MessagingProvider (Feature 05)."""

from __future__ import annotations

import json
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from app.messaging.base import OutgoingMedia
from app.messaging.factory import get_provider
from app.messaging.wacli import (
    WacliProvider,
    _normalize_recipient,
    _parse_message_id,
    resolve_store_dir,
)


def test_factory_defaults_to_wacli():
    provider = get_provider(SimpleNamespace())
    assert isinstance(provider, WacliProvider)


def test_factory_resolves_wacli_with_store():
    provider = get_provider(
        SimpleNamespace(provider="wacli", wacli_store_dir="/tmp/wacli-tenant-a")
    )
    assert isinstance(provider, WacliProvider)
    assert provider.store_dir == "/tmp/wacli-tenant-a"


def test_factory_resolves_account_subdir(monkeypatch):
    monkeypatch.setattr("app.messaging.wacli.settings.WACLI_STORE_DIR", "/data/wacli")
    provider = get_provider(SimpleNamespace(provider="wacli", wacli_account="tenant-1"))
    assert provider.store_dir == "/data/wacli/accounts/tenant-1"


def test_normalize_recipient_jid_and_phone():
    assert _normalize_recipient("15551234567@s.whatsapp.net") == "15551234567@s.whatsapp.net"
    assert _normalize_recipient("+1 (555) 123-4567") == "+15551234567"


def test_parse_message_id_variants():
    assert _parse_message_id(json.dumps({"id": "ABC123"})) == "ABC123"
    assert _parse_message_id(json.dumps({"ID": "XYZ"})) == "XYZ"
    assert _parse_message_id(json.dumps({"message": {"id": "NEST"}})) == "NEST"
    assert _parse_message_id("not-json") is None


def test_send_text_builds_cli_and_parses_json():
    provider = WacliProvider(store_dir="/tmp/store", binary="wacli", timeout=30)
    fake = MagicMock()
    fake.returncode = 0
    fake.stdout = json.dumps({"sent": True, "id": "3EB0DEAD"})
    fake.stderr = ""

    with patch("app.messaging.wacli.subprocess.run", return_value=fake) as run:
        result = provider.send_text("+15551234567", "hello from tests")

    assert result.success is True
    assert result.wa_message_id == "3EB0DEAD"
    cmd = run.call_args.args[0]
    assert cmd[:2] == ["wacli", "--json"]
    assert "--store" in cmd and "/tmp/store" in cmd
    assert "send" in cmd and "text" in cmd
    assert "--to" in cmd and "+15551234567" in cmd
    assert "--message" in cmd and "hello from tests" in cmd


def test_send_text_failure_from_exit_code():
    provider = WacliProvider(binary="wacli")
    fake = MagicMock()
    fake.returncode = 1
    fake.stdout = ""
    fake.stderr = "not authenticated"

    with patch("app.messaging.wacli.subprocess.run", return_value=fake):
        result = provider.send_text("15551234567", "hi")

    assert result.success is False
    assert "not authenticated" in (result.error or "")


def test_send_text_missing_args():
    provider = WacliProvider()
    assert provider.send_text("", "hi").success is False
    assert provider.send_text("1555", "").success is False


def test_send_media_uses_local_path():
    provider = WacliProvider(binary="wacli")
    fake = MagicMock()
    fake.returncode = 0
    fake.stdout = json.dumps({"sent": True, "id": "MEDIA1"})
    fake.stderr = ""

    with patch("app.messaging.wacli.subprocess.run", return_value=fake) as run:
        result = provider.send_media(
            "15551234567",
            OutgoingMedia(kind="image", path="/tmp/pic.jpg", mime="image/jpeg"),
            caption="portfolio",
        )

    assert result.success is True
    assert result.wa_message_id == "MEDIA1"
    cmd = run.call_args.args[0]
    assert "send" in cmd and "file" in cmd
    assert "--file" in cmd and "/tmp/pic.jpg" in cmd
    assert "--caption" in cmd and "portfolio" in cmd
    assert "--as" in cmd and "image" in cmd


def test_send_template_unsupported():
    result = WacliProvider().send_template("1555", "hello_world", "en", {})
    assert result.success is False
    assert result.error == "templates_unsupported_on_wacli"


def test_send_typing_is_noop():
    WacliProvider().send_typing("1555", on=True)  # must not raise


def test_binary_not_found():
    provider = WacliProvider(binary="wacli-does-not-exist-xyz")
    with patch("app.messaging.wacli.subprocess.run", side_effect=FileNotFoundError()):
        result = provider.send_text("1555", "hi")
    assert result.success is False
    assert "wacli_binary_not_found" in (result.error or "")


def test_resolve_store_dir_priority(monkeypatch):
    monkeypatch.setattr("app.messaging.wacli.settings.WACLI_STORE_DIR", "/global")
    assert resolve_store_dir(store_dir="/explicit") == "/explicit"
    assert resolve_store_dir(account="abc") == "/global/accounts/abc"
    assert resolve_store_dir() == "/global"
