"""Conversation state machine (Feature 13 + media selection).

One LLM call per inbound turn drives a simple sales state machine:

    QUALIFY  → understand the need (early turns, ask discovery questions)
    NURTURE  → interest established, keep it warm, deepen qualification
    PROPOSE  → suggest a quick meeting (the single closing ask)
    CONFIRM  → a meeting was proposed; detect yes/no
    DONE     → meeting confirmed; the agent goes quiet

The state is derived from the lead's `meeting_status` + turn count, so it is
recoverable from the DB with no extra columns. The call also extracts memory
facts and returns them for `services/memory` to persist.

Optional media: when a tenant media catalogue is provided, the model may propose
one `media_asset_id` from that list. Invented ids are dropped (text-only reply).
This module never sends — delivery + the compliance gate live in `tasks/`.
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Optional

from app.ai import provider as llm

logger = logging.getLogger(__name__)


class ConversationState(str, Enum):
    QUALIFY = "QUALIFY"
    NURTURE = "NURTURE"
    PROPOSE = "PROPOSE"
    CONFIRM = "CONFIRM"
    DONE = "DONE"


# Opt-out is honored immediately and deterministically — never left to the model.
# "stop"/"cancel"/etc. are treated as standalone keywords (SMS/WhatsApp convention)
# so "stop by tomorrow" is NOT an opt-out; unambiguous phrases match anywhere.
_OPT_OUT_STANDALONE = {
    "stop", "unsubscribe", "cancel", "quit", "end",
    "opt out", "optout", "opt-out", "remove me", "no more messages",
}
_OPT_OUT_PHRASES = [
    r"\bunsubscribe\b",
    r"\bopt[\s-]?out\b",
    r"\bstop (?:messaging|texting|contacting|sending|msg)",
    r"\b(?:don'?t|do not|please don'?t|please stop) (?:contact|message|text|msg)(?:ing)? me\b",
    r"\bleave me alone\b",
    r"\bno more (?:messages|texts|msgs)\b",
    r"\b(?:remove|take) me off\b",
    r"\bremove me from\b",
]
_OPT_OUT_RE = re.compile("|".join(_OPT_OUT_PHRASES), re.IGNORECASE)


def detect_opt_out(text: str) -> bool:
    """True if the contact clearly asked to stop being contacted."""
    normalized = " ".join((text or "").lower().split()).strip(" .!?")
    if normalized in _OPT_OUT_STANDALONE:
        return True
    return bool(_OPT_OUT_RE.search(text or ""))


def derive_state(meeting_status: Optional[str], turn_count: int, score: int = 0) -> ConversationState:
    """Current state from persisted lead fields (no extra columns needed)."""
    status = (meeting_status or "NOT_REQUESTED").upper()
    if status == "CONFIRMED":
        return ConversationState.DONE
    if status in ("REQUESTED", "READY"):
        return ConversationState.CONFIRM
    if turn_count <= 2:
        return ConversationState.QUALIFY
    if score >= 70:
        return ConversationState.PROPOSE
    return ConversationState.NURTURE


@dataclass
class PipelineResult:
    is_lead: bool = True
    intent_label: str = "WARM"
    score: int = 50
    summary: str = ""
    service_interest: Optional[str] = None
    meeting_requested: bool = False
    meeting_confirmed: bool = False
    next_action: str = "Continue conversation"
    reply: str = ""
    facts: list[dict[str, Any]] = field(default_factory=list)
    state: ConversationState = ConversationState.QUALIFY
    opt_out: bool = False
    # Tenant brand asset chosen from the provided catalogue (validated); None = text only.
    media_asset_id: Optional[str] = None


# --------------------------------------------------------------------------- #
# JSON parsing (robust to markdown fences / prose)
# --------------------------------------------------------------------------- #

def parse_json_response(res: str) -> dict:
    res_clean = (res or "").strip()
    if not res_clean:
        return {}
    if res_clean.startswith("```"):
        nl = res_clean.find("\n")
        if nl != -1:
            res_clean = res_clean[nl:].strip()
        if res_clean.endswith("```"):
            res_clean = res_clean[:-3].strip()
    start, end = res_clean.find("{"), res_clean.rfind("}")
    if start != -1 and end > start:
        try:
            return json.loads(res_clean[start:end + 1])
        except Exception:
            pass
    try:
        return json.loads(res_clean)
    except Exception:
        return {}


def _as_bool(v: Any) -> bool:
    if isinstance(v, str):
        return v.strip().lower() in ("true", "yes", "1")
    return bool(v)


def format_media_catalogue(catalogue: list[dict[str, Any]]) -> str:
    """Human-readable catalogue block for the LLM prompt (ids only — no binaries)."""
    if not catalogue:
        return "(no media available — leave media_asset_id null)"
    lines: list[str] = []
    for entry in catalogue:
        tags = entry.get("tags") or []
        tags_str = ", ".join(str(t) for t in tags) if tags else "untagged"
        caption = (entry.get("caption") or tags_str or entry.get("type") or "media")
        lines.append(
            f"- id={entry.get('id')} type={entry.get('type', 'image')} "
            f"tags=[{tags_str}] caption=\"{caption}\""
        )
    return "\n".join(lines)


def validate_media_asset_id(
    raw: Any,
    catalogue: list[dict[str, Any]],
) -> Optional[str]:
    """Keep only ids present in the tenant catalogue; invented/foreign ids → None.

    Never raises — a bad selection must not fail the whole reply.
    """
    if raw is None:
        return None
    sid = str(raw).strip()
    if not sid or sid.lower() in ("null", "none", ""):
        return None
    allowed = {str(e.get("id")) for e in catalogue if e.get("id")}
    if sid in allowed:
        return sid
    logger.warning("[pipeline] dropping media_asset_id not in catalogue: %s", sid)
    return None


# --------------------------------------------------------------------------- #
# Prompt building
# --------------------------------------------------------------------------- #

def _build_user_prompt(
    *,
    brand_name: str,
    services: list[str],
    meeting_cta: str,
    history_text: str,
    turn_count: int,
    state: ConversationState,
    media_catalogue: list[dict[str, Any]],
) -> str:
    services_str = ", ".join(services) if services else "our services"
    media_block = format_media_catalogue(media_catalogue)
    media_hint = (
        "When a photo/video from the MEDIA CATALOGUE would help (portfolio, product, "
        "example), set media_asset_id to that entry's id. Otherwise null. "
        "ONLY use an id from the catalogue — never invent one. The reply text is also "
        "used as the media caption when sending."
        if media_catalogue else
        "No media available — always set media_asset_id to null."
    )

    if state == ConversationState.CONFIRM:
        return f"""\
A quick meeting has already been proposed to this lead for {brand_name}.

=== CONVERSATION HISTORY ===
{history_text}

=== MEDIA CATALOGUE (tenant brand assets only) ===
{media_block}

=== TASK ===
Read the lead's latest reply and decide whether they CONFIRMED the meeting
(yes/sure/sounds good/ok/let's do it) or REJECTED/ignored it.

If CONFIRMED: set meeting_confirmed=true and write ONE short warm close
(e.g. "perfect, talk soon!"). Ask nothing further.
If NOT: set meeting_confirmed=false and reply warmly, low-pressure. Don't push again.
{media_hint}

Reply rules: max 1 short sentence, casual lowercase, no bullet points / bold / em-dashes / [placeholders].

Respond ONLY with this JSON:
{{"is_lead": true, "intent_label": "HOT", "score": 90, "summary": "...",
  "service_interest": "...", "meeting_requested": true, "meeting_confirmed": true,
  "next_action": "none", "reply": "perfect, talk soon!", "facts": [],
  "media_asset_id": null}}"""

    early_note = (
        f"IMPORTANT: turn {turn_count} — early. Don't classify NO_ACTION unless clearly spam/"
        "job-seeker/competitor. Engage warmly."
        if turn_count <= 3 else ""
    )
    close_hint = (
        f'This lead looks ready — casually suggest a meeting: "{meeting_cta}". That IS the final ask; '
        "do not ask another question after proposing."
        if state == ConversationState.PROPOSE else
        "Ask one natural discovery question (use next_action as a guide). Do not propose a meeting yet."
    )

    return f"""\
You are the AI sales assistant for {brand_name}, offering: {services_str}.
Conversation stage: {state.value}. {early_note}

=== CONVERSATION HISTORY (turn {turn_count}) ===
{history_text}

=== MEDIA CATALOGUE (tenant brand assets only) ===
{media_block}

=== TASK ===
Analyze the conversation and generate the next reply in ONE JSON response.

Analysis:
1. is_lead=true for anyone who might need our services; false only for obvious spam/job-seekers.
2. intent_label: HOT (ready), WARM (interested), COLD (vague), NO_ACTION (not a lead).
3. score: 0-100. Under turn 3, keep 40-60 unless clearly hot/cold.
4. meeting_requested=true only if they explicitly asked for a call OR are clearly ready after 3+ turns.
5. next_action: the single most useful discovery question to ask next.
6. facts: extract any NEW concrete facts the lead stated — service wanted, budget, timeline,
   preferences. Each fact: {{"fact": "...", "category": "service|budget|timeline|preference",
   "confidence": 0-100, "source": "stated"}}. Empty list if nothing new.
7. media_asset_id: {media_hint}

Reply:
- Sound like a real human texting on WhatsApp. Lowercase, casual, max 1-2 short sentences.
- {close_hint}
- Never repeat what was already said. Respond to what they just said.
- No bullet points, bold, em-dashes, or [placeholders].

Respond ONLY with this JSON structure:
{{"is_lead": true, "intent_label": "WARM", "score": 55, "summary": "brief need summary",
  "service_interest": "web development", "meeting_requested": false, "meeting_confirmed": false,
  "next_action": "what to ask next", "reply": "your message", "facts": [],
  "media_asset_id": null}}"""


# --------------------------------------------------------------------------- #
# Run
# --------------------------------------------------------------------------- #

def run(
    *,
    system_prompt: str,
    brand_name: str,
    services: list[str],
    meeting_cta: str,
    history_text: str,
    latest_msg: str,
    turn_count: int,
    state: ConversationState,
    media_catalogue: Optional[list[dict[str, Any]]] = None,
    escalate: bool = False,
    llm_complete: Optional[Callable[..., llm.LLMResponse]] = None,
) -> PipelineResult:
    """Run one turn of the state machine. ``llm_complete`` is injectable for tests;
    it defaults to `ai.provider.complete`.

    ``media_catalogue`` is a tenant-scoped list of ``{id, type, tags, caption}``.
    Proposed ``media_asset_id`` values outside that list are dropped.
    """
    catalogue = list(media_catalogue or [])
    complete = llm_complete or llm.complete
    user_prompt = _build_user_prompt(
        brand_name=brand_name,
        services=services,
        meeting_cta=meeting_cta,
        history_text=history_text,
        turn_count=turn_count,
        state=state,
        media_catalogue=catalogue,
    )

    resp = complete(
        user_prompt,
        system=system_prompt,
        json_mode=True,
        temperature=0.4,
        max_tokens=700,
        escalate=escalate,
    )
    data = parse_json_response(resp.text if resp else "")

    if not data:
        logger.warning("[pipeline] empty/invalid LLM response — using fallback")
        return PipelineResult(
            summary=(latest_msg or "")[:100],
            next_action="Ask about their project",
            reply="sounds interesting! what kind of project are you working on?",
            state=state,
        )

    facts = data.get("facts")
    if not isinstance(facts, list):
        facts = []

    result = PipelineResult(
        is_lead=_as_bool(data.get("is_lead", True)),
        intent_label=(data.get("intent_label") or "WARM").upper(),
        score=int(data.get("score") or 50),
        summary=(data.get("summary") or "").strip(),
        service_interest=(data.get("service_interest") or "").strip() or None,
        meeting_requested=_as_bool(data.get("meeting_requested")),
        meeting_confirmed=_as_bool(data.get("meeting_confirmed")),
        next_action=(data.get("next_action") or "Continue conversation").strip() or "Continue conversation",
        reply=(data.get("reply") or "").strip(),
        facts=[f for f in facts if isinstance(f, dict) and (f.get("fact") or "").strip()],
        state=state,
        media_asset_id=validate_media_asset_id(data.get("media_asset_id"), catalogue),
    )
    if not result.reply:
        result.reply = "got it! what kind of project are you thinking about?"
    return result
