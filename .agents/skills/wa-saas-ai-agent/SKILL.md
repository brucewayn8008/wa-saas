---
name: wa-saas-ai-agent
description: >-
  The AI sales-agent conventions for wa-saas — persona + mandatory disclosure, the
  qualify to nurture to propose to confirm pipeline, memory facts (pgvector),
  debounce and human-like typing delivery, and LLM provider abstraction
  (Gemini default, Anthropic escalation). Use when editing ai/ or the reply
  pipeline, prompts, memory, or conversation state.
---

# wa-saas — AI Sales Agent

`ai/` builds prompts and calls the LLM. It **never sends** and **never touches transport** — it returns a decision; `tasks/` + `messaging/` dispatch it (gated). Keep it pure/testable.

## LLM provider (`ai/provider.py`)
- Gemini is default; Anthropic is escalation. Lazy-load SDKs; wrap calls in try/except with graceful fallback. Keys from env (`GEMINI_API_KEY`, `ANTHROPIC_API_KEY`).
- Prefer structured output; validate before use.

## Persona + disclosure (`ai/persona.py`)
- Builds the tenant persona from `system_prompt` + `agent_config` (services, tone, offer, booking link, business hours).
- **The first message of a new conversation MUST contain the tenant's `disclosure_line`** — this is deterministic, not left to the model. The agent never claims to be a specific real human.

## Pipeline (`ai/pipeline.py`)
State flow: **qualify → nurture → propose-meeting → confirm**.
- Recall `memory_facts` (pgvector semantic recall; **falls back to recency when pgvector is absent** — don't hard-depend on vectors).
- Extract stated facts (service, budget, timeline, preference) → persist as `memory_facts` (tenant-scoped) so replies stay consistent.
- Qualify to HOT/WARM/COLD; after enough signal, propose a meeting / booking link.
- May *propose* a tenant `media_asset_id` from the provided catalogue (validate it belongs to the tenant); actual media send happens in the gated task path.
- Opt-out keywords ("stop") → set `do_not_contact`.

## Human-like delivery
- `services/debounce.py` coalesces multi-message bursts before generating one reply.
- `services/typing_delay.py` adds reading delay + typing indicator + splits into 1–3 short bubbles. Keep it human, not instant.

## Guardrails
- Never send from `ai/`. Never bypass `outreach_policy.gate()` (see `wa-saas-compliance`).
- All reads are tenant-scoped via `tenant_context()` (see `wa-saas-tenancy-rls`).
- Human takeover: if `conversation.human_takeover` is true, the agent does not auto-reply.

## Verify an ai/ change
Deterministic test: first reply in a new thread contains the disclosure line; multi-turn qualifies + remembers a stated fact + proposes a meeting; "stop" sets DNC; provider failure falls back without crashing.
