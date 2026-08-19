"""Persona + mandatory AI disclosure (Feature 12).

Two responsibilities:

1. Build the system prompt that gives the agent the tenant's brand voice, offer
   and services — while making it explicit that it is an AI for that brand and
   must NEVER claim to be a specific real human (hard compliance boundary).

2. Guarantee the AI-disclosure line appears in the FIRST agent message of every
   thread. This is enforced deterministically in `ensure_disclosure()` — we do
   not rely on the model obeying an instruction, because disclosure is a legal /
   policy requirement, not a stylistic preference.
"""

from __future__ import annotations

from typing import Any, Optional

DEFAULT_DISCLOSURE = "You're chatting with an AI assistant."


def disclosure_line(tenant) -> str:
    """The tenant's mandatory AI-disclosure text (never empty)."""
    line = (getattr(tenant, "disclosure_line", None) or "").strip()
    return line or DEFAULT_DISCLOSURE


def needs_disclosure(prior_agent_message_count: int) -> bool:
    """Disclosure is required on the first agent message of a thread."""
    return (prior_agent_message_count or 0) == 0


def _contains_disclosure(text: str, line: str) -> bool:
    """Loose containment check — tolerant of casing/punctuation so we don't
    double-disclose if the model already included it."""
    def norm(s: str) -> str:
        return "".join(c for c in s.lower() if c.isalnum() or c.isspace()).strip()

    t, l = norm(text), norm(line)
    if not l:
        return True
    # Match on the disclosure line or its distinctive "ai assistant" core.
    return l in t or ("ai assistant" in l and "ai assistant" in t)


def ensure_disclosure(reply: str, tenant, is_first_agent_message: bool) -> str:
    """Prepend the disclosure line to the first agent message if it isn't already
    present. No-op for subsequent messages."""
    reply = (reply or "").strip()
    if not is_first_agent_message:
        return reply
    line = disclosure_line(tenant)
    if _contains_disclosure(reply, line):
        return reply
    if not reply:
        return line
    return f"{line}\n\n{reply}"


def build_system_prompt(
    tenant,
    config: dict[str, Any],
    *,
    memory_context: str = "",
    stage: Optional[str] = None,
) -> str:
    """Assemble the system instruction for a reply.

    `config` is the parsed `agent_config` (see services/crm.read_agent_config).
    `memory_context` is recalled facts about this lead (services/memory).
    `stage` is the current conversation state (services/conversation_state).
    """
    brand = config.get("brand_name") or getattr(tenant, "company_name", "our team")
    services = config.get("services") or []
    services_str = ", ".join(services) if services else "our services"
    offer = config.get("qualifying_offer") or getattr(tenant, "business_description", "") or ""
    base_persona = (getattr(tenant, "system_prompt", None) or "").strip()

    parts: list[str] = []
    parts.append(
        f"You are the AI sales assistant for {brand}. "
        f"You are an AI — never claim to be a specific named human, never pretend to be a real person, "
        f"and never deny being an AI if asked. Represent {brand} honestly and helpfully."
    )
    parts.append(f"Services offered: {services_str}.")
    if offer:
        parts.append(f"What we help with: {offer}")
    if base_persona:
        parts.append(f"Brand voice / persona notes:\n{base_persona}")
    if stage:
        parts.append(f"Current conversation stage: {stage}.")
    if memory_context:
        parts.append(
            "What you already know about this lead (do not re-ask what's answered here):\n"
            f"{memory_context}"
        )
    parts.append(
        "Style: sound like a real human texting on WhatsApp — warm, lowercase, 1-2 short sentences. "
        "No corporate tone, no bullet points, no bold, no em-dashes, no [placeholders]. "
        "Never claim to be a specific real person."
    )
    return "\n\n".join(parts)
