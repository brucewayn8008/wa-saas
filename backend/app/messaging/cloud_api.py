"""WhatsApp Business Cloud API provider — DEFERRED.

Near-term transport is wacli (`messaging/wacli.py`). This provider stays
implemented for a future WABA cutover but is not the default factory path.
"""

from __future__ import annotations

import logging
from typing import Optional

import httpx

from app.core.config import settings
from app.messaging.base import MessagingProvider, OutgoingMedia, SendResult

logger = logging.getLogger(__name__)


class CloudApiProvider(MessagingProvider):
    def __init__(self, phone_number_id: str, access_token: str, api_base: Optional[str] = None, timeout: float = 15.0):
        self.phone_number_id = phone_number_id
        self.access_token = access_token
        self.api_base = (api_base or settings.WHATSAPP_API_BASE).rstrip("/")
        self.timeout = timeout

    @property
    def _url(self) -> str:
        return f"{self.api_base}/{self.phone_number_id}/messages"

    @property
    def _headers(self) -> dict:
        return {"Authorization": f"Bearer {self.access_token}", "Content-Type": "application/json"}

    def _send(self, payload: dict, log_ctx: str) -> SendResult:
        payload = {"messaging_product": "whatsapp", **payload}
        try:
            res = httpx.post(self._url, headers=self._headers, json=payload, timeout=self.timeout)
            res.raise_for_status()
            data = res.json()
            msg_id = (data.get("messages") or [{}])[0].get("id")
            return SendResult(True, wa_message_id=msg_id)
        except httpx.HTTPStatusError as e:
            logger.error("[cloud_api/%s] %s -> %s", log_ctx, e, e.response.text)
            return SendResult(False, error=e.response.text)
        except httpx.HTTPError as e:
            logger.error("[cloud_api/%s] %s", log_ctx, e)
            return SendResult(False, error=str(e))

    def send_text(self, to: str, text: str) -> SendResult:
        return self._send({"to": to, "type": "text", "text": {"body": text}}, "send_text")

    def send_media(self, to: str, media: OutgoingMedia, caption: Optional[str] = None) -> SendResult:
        kind = media.kind if media.kind in ("image", "video") else "image"
        obj: dict = {"caption": caption} if caption else {}
        if media.wa_media_id:
            obj["id"] = media.wa_media_id
        elif media.url:
            obj["link"] = media.url
        else:
            return SendResult(False, error="media_missing_id_and_url")
        return self._send({"to": to, "type": kind, kind: obj}, "send_media")

    def send_template(self, to: str, template: str, language: str, variables: Optional[dict] = None) -> SendResult:
        components = []
        if variables:
            components = [{
                "type": "body",
                "parameters": [{"type": "text", "text": str(v)} for v in variables.values()],
            }]
        payload = {
            "to": to,
            "type": "template",
            "template": {"name": template, "language": {"code": language}, "components": components},
        }
        return self._send(payload, "send_template")

    def send_typing(self, to: str, on: bool = True) -> None:
        # Cloud API has no standalone typing indicator; no-op. Human-like pacing is
        # handled by delivery timing in the send task instead.
        return None
