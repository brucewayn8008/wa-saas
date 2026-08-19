"""Messaging transport layer.

The ONLY package that talks to WhatsApp (wacli CLI, legacy Go gateway, or deferred Cloud API).
The AI/CRM core never imports a concrete provider — it uses `get_provider(...)`.
"""

from app.messaging.base import MessagingProvider, OutgoingMedia, SendResult
from app.messaging.factory import get_provider

__all__ = ["MessagingProvider", "OutgoingMedia", "SendResult", "get_provider"]
