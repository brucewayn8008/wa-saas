"""Debounce AI replies so rapid multi-bubble WhatsApp bursts coalesce (Feature 13,
ported from aisha-agent).

Each inbound message sets a Redis token for its conversation. A reply task
scheduled with a countdown only proceeds if it still holds the latest token —
older tasks skip silently, so a 3-bubble burst yields one reply, not three.

Also tracks inbound "typing…" presence so the agent waits while the contact is
still composing, like a human would. All Redis errors fail OPEN for delivery
(better to reply than to silently drop) but fail CLOSED for the typing wait
(a Redis blip must not stall replies forever).
"""

from __future__ import annotations

import logging
from typing import Optional

import redis

from app.core.config import settings

logger = logging.getLogger(__name__)

_KEY_PREFIX = "reply_debounce:"
_TYPING_PREFIX = "user_typing:"
_TOKEN_TTL_SECONDS = 180

_client: Optional[redis.Redis] = None


def _redis() -> redis.Redis:
    global _client
    if _client is None:
        _client = redis.Redis.from_url(settings.REDIS_URL, decode_responses=True)
    return _client


def _key(conversation_id: str) -> str:
    return f"{_KEY_PREFIX}{conversation_id}"


def _typing_key(conversation_id: str) -> str:
    return f"{_TYPING_PREFIX}{conversation_id}"


def set_pending_reply(conversation_id: str, trigger_id: str) -> None:
    """Mark ``trigger_id`` as the latest inbound message awaiting a reply."""
    try:
        _redis().set(_key(str(conversation_id)), str(trigger_id), ex=_TOKEN_TTL_SECONDS)
    except Exception as exc:
        logger.warning("debounce set failed for %s: %s", conversation_id, exc)


def is_latest_trigger(conversation_id: str, trigger_id: str) -> bool:
    """True if this task still owns the debounce slot (fail-open on Redis error)."""
    try:
        current = _redis().get(_key(str(conversation_id)))
    except Exception as exc:
        logger.warning("debounce read failed for %s: %s — proceeding", conversation_id, exc)
        return True
    if current is None:
        return True
    return current == str(trigger_id)


def clear_pending_reply(conversation_id: str, trigger_id: Optional[str] = None) -> None:
    """Clear the debounce token after a successful reply."""
    try:
        client = _redis()
        key = _key(str(conversation_id))
        if trigger_id is None:
            client.delete(key)
            return
        if client.get(key) == str(trigger_id):
            client.delete(key)
    except Exception as exc:
        logger.warning("debounce clear failed for %s: %s", conversation_id, exc)


def mark_user_typing(conversation_id: str, ttl_seconds: Optional[float] = None) -> None:
    """Record that the contact is currently (or just was) typing."""
    ttl = ttl_seconds if ttl_seconds is not None else float(getattr(settings, "USER_TYPING_TTL_SECONDS", 12.0) or 12.0)
    try:
        _redis().set(_typing_key(str(conversation_id)), "1", ex=max(1, int(round(ttl))))
    except Exception as exc:
        logger.warning("mark typing failed for %s: %s", conversation_id, exc)


def clear_user_typing(conversation_id: str) -> None:
    try:
        _redis().delete(_typing_key(str(conversation_id)))
    except Exception as exc:
        logger.warning("clear typing failed for %s: %s", conversation_id, exc)


def is_user_typing(conversation_id: str) -> bool:
    """True if the contact's typing flag is still active (fail-closed on error)."""
    try:
        return bool(_redis().get(_typing_key(str(conversation_id))))
    except Exception as exc:
        logger.warning("read typing failed for %s: %s — assuming not typing", conversation_id, exc)
        return False
