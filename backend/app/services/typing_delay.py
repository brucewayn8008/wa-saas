"""Human-like reply timing (Feature 13, ported from aisha-agent).

Real people don't answer instantly — they read, think, then type. This module
computes a human-like delay before an outbound send and can drive the WhatsApp
"typing…" presence during the wait.

It is transport-agnostic: the delay calculation is pure (unit-testable), and the
optional typing indicator is driven through an injected callback so `services/`
never imports a concrete `MessagingProvider`.
"""

from __future__ import annotations

import logging
import random
import time
from typing import Callable, Optional

from app.core.config import settings

logger = logging.getLogger(__name__)

CHARS_PER_SECOND = 10.0
MIN_DELAY = 0.8
THINKING_PAUSE_CHANCE = 0.12
THINKING_PAUSE_RANGE = (0.4, 1.5)
JITTER_FRACTION = 0.15


def _max_delay() -> float:
    return float(getattr(settings, "TYPING_DELAY_MAX_SECONDS", 6.0) or 6.0)


def calculate_typing_delay(message: str, incoming_message: Optional[str] = None) -> float:
    """Human-like delay (seconds) before sending ``message``.

    reading time + typing time proportional to length + jitter + occasional pause,
    clamped to [MIN_DELAY, TYPING_DELAY_MAX_SECONDS].
    """
    if incoming_message:
        reading = min(max(0.3, len(incoming_message) / 24.0), 2.5)
    else:
        reading = random.uniform(0.2, 0.7)

    typing = len(message) / CHARS_PER_SECOND if message else 0.4
    base = reading + typing
    jitter = base * random.uniform(-JITTER_FRACTION, JITTER_FRACTION)

    thinking = random.uniform(*THINKING_PAUSE_RANGE) if random.random() < THINKING_PAUSE_CHANCE else 0.0

    total = base + jitter + thinking
    return round(max(MIN_DELAY, min(total, _max_delay())), 2)


def apply_typing_delay(
    message: str,
    incoming_message: Optional[str] = None,
    *,
    typing_cb: Optional[Callable[[bool], None]] = None,
    sleep: Callable[[float], None] = time.sleep,
) -> float:
    """Sleep for a human-like duration before sending a reply.

    If ``typing_cb`` is given, it's called with ``True`` when composing starts and
    ``False`` when done, so the caller can drive the WhatsApp typing indicator via
    its `MessagingProvider`. Returns the delay applied (useful for logging/tests).
    """
    delay = calculate_typing_delay(message, incoming_message=incoming_message)
    logger.info("typing delay %.2fs for %d-char reply", delay, len(message or ""))

    # brief read pause with no indicator, then "typing…" for the remainder
    reading = min(max(delay * (0.3 if incoming_message else 0.15), 0.2), delay * 0.5)
    composing = max(0.0, delay - reading)

    if reading > 0:
        sleep(reading)
    if typing_cb:
        try:
            typing_cb(True)
        except Exception as exc:  # never let presence failures block a send
            logger.warning("typing_cb(on) failed: %s", exc)
    if composing > 0:
        sleep(composing)
    if typing_cb:
        try:
            typing_cb(False)
        except Exception as exc:
            logger.warning("typing_cb(off) failed: %s", exc)
    return delay
