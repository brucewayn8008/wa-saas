"""Feature 13 — human-like typing delay (pure calculation + callback wiring)."""

from app.services import typing_delay
from app.core.config import settings


def test_delay_within_bounds():
    for msg in ["ok", "hey there, what's your timeline and budget for this project?", "x" * 500]:
        d = typing_delay.calculate_typing_delay(msg, incoming_message="i need a website")
        assert typing_delay.MIN_DELAY <= d <= settings.TYPING_DELAY_MAX_SECONDS


def test_longer_reply_generally_takes_longer():
    short = typing_delay.calculate_typing_delay("ok")
    long = typing_delay.calculate_typing_delay("x" * 300)
    assert long >= short


def test_apply_typing_delay_drives_callback_without_real_sleep():
    events = []
    slept = []
    typing_delay.apply_typing_delay(
        "hello there",
        incoming_message="hi",
        typing_cb=lambda on: events.append(on),
        sleep=lambda s: slept.append(s),
    )
    # typing turned on then off, and we "slept" without touching the wall clock.
    assert events == [True, False]
    assert sum(slept) > 0
