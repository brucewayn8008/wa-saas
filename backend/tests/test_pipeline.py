"""Feature 13 — conversation state machine: opt-out, state derivation, run()."""

import json

from app.ai import pipeline
from app.ai.pipeline import ConversationState as CS
from app.ai.provider import LLMResponse


# --- opt-out -------------------------------------------------------------- #

def test_detect_opt_out_positive():
    for msg in ["stop", "STOP", "please unsubscribe", "stop messaging me", "leave me alone", "remove me"]:
        assert pipeline.detect_opt_out(msg) is True, msg


def test_detect_opt_out_negative():
    for msg in ["can you stop by tomorrow?", "non-stop energy", "i want a website"]:
        assert pipeline.detect_opt_out(msg) is False, msg


# --- state derivation ----------------------------------------------------- #

def test_derive_state_progression():
    assert pipeline.derive_state("NOT_REQUESTED", 1, 40) == CS.QUALIFY
    assert pipeline.derive_state("NOT_REQUESTED", 5, 50) == CS.NURTURE
    assert pipeline.derive_state("NOT_REQUESTED", 5, 80) == CS.PROPOSE
    assert pipeline.derive_state("REQUESTED", 6, 90) == CS.CONFIRM
    assert pipeline.derive_state("CONFIRMED", 8, 95) == CS.DONE


# --- json parsing --------------------------------------------------------- #

def test_parse_json_handles_fences_and_prose():
    fenced = "```json\n{\"reply\": \"hi\"}\n```"
    assert pipeline.parse_json_response(fenced)["reply"] == "hi"
    prose = 'sure! {"reply": "ok"} done'
    assert pipeline.parse_json_response(prose)["reply"] == "ok"
    assert pipeline.parse_json_response("not json") == {}


# --- run() with a stub LLM ------------------------------------------------ #

def _stub(payload: dict):
    def _complete(prompt, **kwargs):
        return LLMResponse(text=json.dumps(payload), provider="stub", model="stub")
    return _complete


def test_run_parses_result_and_facts():
    result = pipeline.run(
        system_prompt="sys",
        brand_name="Acme",
        services=["web dev"],
        meeting_cta="quick call?",
        history_text="Lead: i need a website",
        latest_msg="i need a website",
        turn_count=1,
        state=CS.QUALIFY,
        llm_complete=_stub({
            "is_lead": True, "intent_label": "warm", "score": 55,
            "summary": "wants a site", "service_interest": "web development",
            "meeting_requested": False, "meeting_confirmed": False,
            "next_action": "ask budget", "reply": "cool, what's the budget?",
            "facts": [{"fact": "wants a restaurant site", "category": "service"}],
        }),
    )
    assert result.intent_label == "WARM"       # normalized upper
    assert result.score == 55
    assert result.reply == "cool, what's the budget?"
    assert result.facts and result.facts[0]["category"] == "service"


def test_run_fallback_on_empty_llm():
    result = pipeline.run(
        system_prompt="sys", brand_name="Acme", services=[], meeting_cta="call?",
        history_text="", latest_msg="hello", turn_count=1, state=CS.QUALIFY,
        llm_complete=lambda *a, **k: LLMResponse(text="", provider="stub", model="stub"),
    )
    assert result.reply  # non-empty fallback so the agent never sends nothing


def test_run_confirm_state_detects_meeting():
    result = pipeline.run(
        system_prompt="sys", brand_name="Acme", services=["web dev"], meeting_cta="call?",
        history_text="You: quick call?\nLead: yes sounds good", latest_msg="yes sounds good",
        turn_count=6, state=CS.CONFIRM,
        llm_complete=_stub({
            "is_lead": True, "intent_label": "HOT", "score": 90, "summary": "confirmed",
            "meeting_requested": True, "meeting_confirmed": True, "next_action": "none",
            "reply": "perfect, talk soon!", "facts": [],
        }),
    )
    assert result.meeting_confirmed is True


# --- media catalogue selection -------------------------------------------- #

_ASSET = "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"
_CATALOGUE = [
    {"id": _ASSET, "type": "image", "tags": ["portfolio"], "caption": "portfolio"},
]


def test_validate_media_keeps_catalogue_id():
    assert pipeline.validate_media_asset_id(_ASSET, _CATALOGUE) == _ASSET


def test_validate_media_drops_foreign_or_invented_id():
    assert pipeline.validate_media_asset_id("ffffffff-0000-0000-0000-000000000000", _CATALOGUE) is None
    assert pipeline.validate_media_asset_id("not-a-real-id", _CATALOGUE) is None
    assert pipeline.validate_media_asset_id(None, _CATALOGUE) is None
    assert pipeline.validate_media_asset_id("null", _CATALOGUE) is None


def test_run_keeps_valid_media_asset_id():
    result = pipeline.run(
        system_prompt="sys", brand_name="Acme", services=["web dev"], meeting_cta="call?",
        history_text="Lead: show me your work", latest_msg="show me your work",
        turn_count=2, state=CS.QUALIFY, media_catalogue=_CATALOGUE,
        llm_complete=_stub({
            "is_lead": True, "intent_label": "WARM", "score": 60, "summary": "wants samples",
            "meeting_requested": False, "meeting_confirmed": False,
            "next_action": "ask budget", "reply": "here's a recent project",
            "facts": [], "media_asset_id": _ASSET,
        }),
    )
    assert result.media_asset_id == _ASSET
    assert result.reply == "here's a recent project"


def test_run_drops_invalid_media_and_still_replies():
    """Invented media id must not crash the turn — text-only reply."""
    result = pipeline.run(
        system_prompt="sys", brand_name="Acme", services=["web dev"], meeting_cta="call?",
        history_text="Lead: show me your work", latest_msg="show me your work",
        turn_count=2, state=CS.QUALIFY, media_catalogue=_CATALOGUE,
        llm_complete=_stub({
            "is_lead": True, "intent_label": "WARM", "score": 55, "summary": "wants samples",
            "meeting_requested": False, "meeting_confirmed": False,
            "next_action": "ask budget", "reply": "sure, what's your timeline?",
            "facts": [], "media_asset_id": "deadbeef-dead-beef-dead-beefdeadbeef",
        }),
    )
    assert result.media_asset_id is None
    assert result.reply == "sure, what's your timeline?"


def test_format_media_catalogue_empty():
    text = pipeline.format_media_catalogue([])
    assert "no media" in text.lower()
