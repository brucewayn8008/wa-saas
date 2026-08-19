"""MessagingProvider interface — the contract every transport implements.

Providers are transport-only. They do NOT decide whether a message may be sent —
that is the job of `core/outreach_policy.gate()`, which callers must consult first.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Protocol, runtime_checkable


@dataclass(frozen=True)
class SendResult:
    success: bool
    wa_message_id: Optional[str] = None
    error: Optional[str] = None


@dataclass(frozen=True)
class OutgoingMedia:
    """Transport-neutral media reference resolved from a `media_assets` row."""
    kind: str            # "image" | "video" | "audio" | "document"
    url: Optional[str] = None          # signed URL (Cloud API / download-for-wacli)
    path: Optional[str] = None         # local filesystem path (wacli send file)
    wa_media_id: Optional[str] = None  # cached Cloud API media id, if uploaded
    mime: Optional[str] = None


@runtime_checkable
class MessagingProvider(Protocol):
    """All sends for one WhatsApp number go through one provider instance."""

    def send_text(self, to: str, text: str) -> SendResult: ...

    def send_media(self, to: str, media: OutgoingMedia, caption: Optional[str] = None) -> SendResult: ...

    def send_template(self, to: str, template: str, language: str, variables: Optional[dict] = None) -> SendResult: ...

    def send_typing(self, to: str, on: bool = True) -> None: ...
