"""Feature 11 — plan/quota logic must gate correctly (pure, no Stripe SDK needed)."""

from app.services.billing import (
    Plan,
    apply_plan,
    can_add_number,
    conversation_quota_remaining,
    get_plan,
    has_conversation_quota,
)


def test_get_plan_defaults_to_free():
    assert get_plan(None).key == "free"
    assert get_plan("nonexistent").key == "free"
    assert get_plan("PRO").key == "pro"  # case-insensitive


def test_conversation_quota():
    pro = get_plan("pro")
    assert has_conversation_quota(pro, 9_999) is True
    assert has_conversation_quota(pro, 10_000) is False
    assert conversation_quota_remaining(pro, 9_990) == 10


def test_can_add_number_respects_plan():
    free = get_plan("free")
    assert can_add_number(free, 0) is True
    assert can_add_number(free, 1) is False
    assert can_add_number(get_plan("pro"), 2) is True


def test_apply_plan_copies_limits():
    class Sub:
        plan = "free"
        max_numbers = 0
        monthly_conversation_quota = 0
        max_seats = 0
        media_storage_mb = 0

    s = Sub()
    apply_plan(s, get_plan("scale"))
    assert s.plan == "scale"
    assert s.max_numbers == 10
    assert s.monthly_conversation_quota == 100_000
    assert s.max_seats == 25
