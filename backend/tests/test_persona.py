"""Feature 12 — persona + mandatory AI disclosure."""

from dataclasses import dataclass
from typing import Optional

from app.ai import persona


@dataclass
class FakeTenant:
    company_name: str = "Acme"
    disclosure_line: Optional[str] = "You're chatting with an AI assistant for Acme."
    system_prompt: Optional[str] = "Be concise and friendly."
    business_description: str = "We build websites."


def test_disclosure_prepended_on_first_message():
    t = FakeTenant()
    out = persona.ensure_disclosure("hey, what do you need?", t, is_first_agent_message=True)
    assert out.startswith(t.disclosure_line)
    assert "what do you need" in out


def test_disclosure_not_duplicated_if_already_present():
    t = FakeTenant()
    reply = f"{t.disclosure_line} how can i help?"
    out = persona.ensure_disclosure(reply, t, is_first_agent_message=True)
    # The disclosure text appears only once.
    assert out.lower().count("ai assistant") == 1


def test_no_disclosure_on_subsequent_messages():
    t = FakeTenant()
    out = persona.ensure_disclosure("sounds good!", t, is_first_agent_message=False)
    assert out == "sounds good!"


def test_disclosure_falls_back_to_default_when_blank():
    t = FakeTenant(disclosure_line="")
    out = persona.ensure_disclosure("hi", t, is_first_agent_message=True)
    assert persona.DEFAULT_DISCLOSURE in out


def test_needs_disclosure():
    assert persona.needs_disclosure(0) is True
    assert persona.needs_disclosure(3) is False


def test_system_prompt_declares_ai_and_brand():
    t = FakeTenant()
    prompt = persona.build_system_prompt(
        t, {"brand_name": "Acme", "services": ["web dev"]},
        memory_context="- [budget] ~$5k", stage="QUALIFY",
    )
    assert "Acme" in prompt
    assert "AI" in prompt
    assert "never claim to be a specific" in prompt.lower()
    assert "budget" in prompt          # memory injected
    assert "QUALIFY" in prompt         # stage injected
