"""Feature 12 — LLM provider selection (Gemini default, Anthropic escalation)."""

import pytest

from app.ai import provider as p
from app.core.config import settings


@pytest.fixture
def restore_settings():
    saved = (settings.GEMINI_API_KEY, settings.ANTHROPIC_API_KEY, settings.LLM_ESCALATION_ENABLED)
    yield
    settings.GEMINI_API_KEY, settings.ANTHROPIC_API_KEY, settings.LLM_ESCALATION_ENABLED = saved


def test_default_is_gemini(restore_settings):
    settings.GEMINI_API_KEY = "g"
    settings.ANTHROPIC_API_KEY = "a"
    settings.LLM_ESCALATION_ENABLED = True
    assert p.get_llm(escalate=False).name == "gemini"


def test_escalation_uses_anthropic(restore_settings):
    settings.GEMINI_API_KEY = "g"
    settings.ANTHROPIC_API_KEY = "a"
    settings.LLM_ESCALATION_ENABLED = True
    assert p.get_llm(escalate=True).name == "anthropic"


def test_escalation_disabled_stays_gemini(restore_settings):
    settings.GEMINI_API_KEY = "g"
    settings.ANTHROPIC_API_KEY = "a"
    settings.LLM_ESCALATION_ENABLED = False
    assert p.get_llm(escalate=True).name == "gemini"


def test_escalation_falls_back_when_anthropic_unconfigured(restore_settings):
    settings.GEMINI_API_KEY = "g"
    settings.ANTHROPIC_API_KEY = ""
    settings.LLM_ESCALATION_ENABLED = True
    assert p.get_llm(escalate=True).name == "gemini"


def test_gemini_unconfigured_falls_back_to_anthropic(restore_settings):
    settings.GEMINI_API_KEY = ""
    settings.ANTHROPIC_API_KEY = "a"
    settings.LLM_ESCALATION_ENABLED = True
    assert p.get_llm(escalate=False).name == "anthropic"


def test_llm_response_truthiness():
    assert bool(p.LLMResponse(text="hi", provider="x", model="y")) is True
    assert bool(p.LLMResponse(text="  ", provider="x", model="y")) is False
