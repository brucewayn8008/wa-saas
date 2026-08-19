"""whatsmeow provider — wraps the Go gateway HTTP API.

Used for a tenant's OWN number for listening + human-approved replies only.
Never used for multi-tenant automated outreach (see AGENTS.md).
"""

from __future__ import annotations

import logging
from typing import Optional

import httpx

from app.core.config import settings
from app.messaging.base import MessagingProvider, OutgoingMedia, SendResult

logger = logging.getLogger(__name__)


class WhatsmeowProvider(MessagingProvider):
    def __init__(self, workspace_id: str, gateway_url: Optional[str] = None, timeout: float = 15.0):
        self.workspace_id = str(workspace_id)
        self.gateway_url = (gateway_url or settings.GO_GATEWAY_URL).rstrip("/")
        self.timeout = timeout

    def _post(self, path: str, payload: dict) -> httpx.Response:
        res = httpx.post(f"{self.gateway_url}{path}", json=payload, timeout=self.timeout)
        res.raise_for_status()
        return res

    def send_text(self, to: str, text: str) -> SendResult:
        try:
            res = self._post("/api/send", {"workspace_id": self.workspace_id, "to": to, "text": text})
            return SendResult(True, wa_message_id=(res.json() or {}).get("id"))
        except httpx.HTTPError as e:
            logger.error("[whatsmeow/send_text] %s", e)
            return SendResult(False, error=str(e))

    def send_media(self, to: str, media: OutgoingMedia, caption: Optional[str] = None) -> SendResult:
        try:
            res = self._post(
                "/api/send-image",
                {"workspace_id": self.workspace_id, "to": to, "url": media.url, "caption": caption or ""},
            )
            return SendResult(True, wa_message_id=(res.json() or {}).get("id"))
        except httpx.HTTPError as e:
            logger.error("[whatsmeow/send_media] %s", e)
            return SendResult(False, error=str(e))

    def send_template(self, to: str, template: str, language: str, variables: Optional[dict] = None) -> SendResult:
        # Templates are a Cloud API concept; the unofficial protocol has no equivalent.
        return SendResult(False, error="templates_unsupported_on_whatsmeow")

    def send_typing(self, to: str, on: bool = True) -> None:
        try:
            self._post("/api/typing", {"workspace_id": self.workspace_id, "to": to, "state": "on" if on else "off"})
        except httpx.HTTPError as e:
            logger.warning("[whatsmeow/send_typing] %s", e)
