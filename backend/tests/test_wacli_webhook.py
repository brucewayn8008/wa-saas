"""Unit tests for wacli inbound webhook (Feature 06)."""

from __future__ import annotations

import json
from unittest.mock import patch
from uuid import uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.messaging.wacli_sig import signature_header, verify_wacli_signature
from app.services.inbound_wacli import IngestResult, _is_group_jid, ingest_wacli_message


SECRET = "test-wacli-secret"


def test_verify_signature_accepts_valid_hmac():
    body = b'{"Chat":"1@s.whatsapp.net","Text":"hi"}'
    header = signature_header(SECRET, body)
    assert verify_wacli_signature(SECRET, body, header) is True


def test_verify_signature_rejects_tampered_body():
    body = b'{"Text":"hi"}'
    header = signature_header(SECRET, body)
    assert verify_wacli_signature(SECRET, b'{"Text":"bye"}', header) is False


def test_verify_signature_rejects_missing():
    assert verify_wacli_signature(SECRET, b"{}", None) is False
    assert verify_wacli_signature("", b"{}", "sha256=abc") is False


def test_is_group_jid():
    assert _is_group_jid("120363@g.us") is True
    assert _is_group_jid("1555@s.whatsapp.net") is False


@pytest.fixture()
def client(monkeypatch):
    monkeypatch.setattr("app.api.endpoints.webhook_wacli.settings.WACLI_WEBHOOK_SECRET", SECRET)
    from app.api.endpoints import webhook_wacli

    app = FastAPI()
    app.include_router(webhook_wacli.router, prefix="/api/v1/webhook")
    return TestClient(app)


def _post(client: TestClient, payload: dict, **query):
    raw = json.dumps(payload).encode("utf-8")
    headers = {"X-Wacli-Signature": signature_header(SECRET, raw)}
    return client.post("/api/v1/webhook/wacli", content=raw, headers=headers, params=query)


def test_webhook_rejects_bad_signature(client):
    raw = b'{"Text":"hi","Chat":"1@s.whatsapp.net"}'
    r = client.post(
        "/api/v1/webhook/wacli",
        content=raw,
        headers={"X-Wacli-Signature": "sha256=deadbeef"},
    )
    assert r.status_code == 401
    assert r.json()["error"] == "invalid_signature"


def test_webhook_rejects_when_secret_missing(monkeypatch):
    monkeypatch.setattr("app.api.endpoints.webhook_wacli.settings.WACLI_WEBHOOK_SECRET", "")
    from app.api.endpoints import webhook_wacli

    app = FastAPI()
    app.include_router(webhook_wacli.router, prefix="/api/v1/webhook")
    c = TestClient(app)
    raw = b"{}"
    r = c.post(
        "/api/v1/webhook/wacli",
        content=raw,
        headers={"X-Wacli-Signature": signature_header(SECRET, raw)},
    )
    assert r.status_code == 503


def test_webhook_ignores_receipt(client):
    with patch("app.api.endpoints.webhook_wacli.ingest_wacli_message") as ingest:
        r = _post(client, {"EventType": "receipt", "Chat": "1@s.whatsapp.net"})
    assert r.status_code == 200
    assert r.json()["status"] == "ignored_receipt"
    ingest.assert_not_called()


def test_webhook_routes_message_to_ingest(client):
    lead = str(uuid4())
    with patch(
        "app.api.endpoints.webhook_wacli.ingest_wacli_message",
        return_value=IngestResult(status="success", lead_id=lead),
    ) as ingest:
        r = _post(
            client,
            {
                "Chat": "15551234567@s.whatsapp.net",
                "ID": "3EB0ABC",
                "SenderJID": "15551234567@s.whatsapp.net",
                "FromMe": False,
                "Text": "hi",
                "ChatName": "Alice",
            },
            account="tenant-a",
        )
    assert r.status_code == 200
    assert r.json() == {"status": "success", "lead_id": lead}
    ingest.assert_called_once()
    assert ingest.call_args.kwargs["account"] == "tenant-a"


def test_webhook_unresolved_tenant_400(client):
    with patch(
        "app.api.endpoints.webhook_wacli.ingest_wacli_message",
        return_value=IngestResult(status="unresolved_tenant"),
    ):
        r = _post(
            client,
            {
                "Chat": "15551234567@s.whatsapp.net",
                "Text": "hi",
                "FromMe": False,
            },
        )
    assert r.status_code == 400


def test_webhook_presence_route(client):
    with patch(
        "app.api.endpoints.webhook_wacli.handle_wacli_presence",
        return_value=IngestResult(status="presence_ok", lead_id="x"),
    ) as presence:
        r = _post(
            client,
            {"EventType": "chat_presence", "Chat": "1@s.whatsapp.net", "State": "composing"},
            account="a",
        )
    assert r.status_code == 200
    assert r.json()["status"] == "presence_ok"
    presence.assert_called_once()


def test_ingest_from_me_ignored():
    result = ingest_wacli_message(
        {"Chat": "1@s.whatsapp.net", "Text": "hi", "FromMe": True}
    )
    assert result.status == "ignored_from_me"


def test_ingest_empty_ignored():
    result = ingest_wacli_message({"Chat": "1@s.whatsapp.net", "Text": "", "FromMe": False})
    assert result.status == "ignored_empty"
