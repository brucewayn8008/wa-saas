"""LLM provider abstraction (Feature 12).

Two providers behind one interface:
  * Gemini      — the DEFAULT for every reply (fast, cheap).
  * Anthropic   — the ESCALATION path for hot / high-value leads, or a fallback
                  when Gemini returns nothing.

The rest of the app depends only on `LLMProvider` + `get_llm()`, never on a
concrete SDK. SDKs are imported lazily so importing this module (and the tests
that touch prompt-building) does not require either package to be installed.

Providers are transport-agnostic and side-effect free: they take a prompt and
return text. Deciding *whether* to send anything is `outreach_policy`'s job.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Optional, Protocol, runtime_checkable

from app.core.config import settings

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class LLMResponse:
    text: str
    provider: str
    model: str

    def __bool__(self) -> bool:
        return bool(self.text and self.text.strip())


@runtime_checkable
class LLMProvider(Protocol):
    name: str

    def generate(
        self,
        prompt: str,
        *,
        system: Optional[str] = None,
        json_mode: bool = False,
        temperature: float = 0.4,
        max_tokens: int = 512,
    ) -> LLMResponse: ...


# --------------------------------------------------------------------------- #
# Gemini (default)
# --------------------------------------------------------------------------- #

class GeminiProvider:
    name = "gemini"

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        self._api_key = api_key or settings.GEMINI_API_KEY
        self.model = model or settings.GEMINI_MODEL
        self._client = None

    def _get_client(self):
        if self._client is None:
            if not self._api_key:
                raise RuntimeError("GEMINI_API_KEY not set")
            from google import genai  # lazy
            self._client = genai.Client(api_key=self._api_key)
        return self._client

    def generate(
        self,
        prompt: str,
        *,
        system: Optional[str] = None,
        json_mode: bool = False,
        temperature: float = 0.4,
        max_tokens: int = 512,
    ) -> LLMResponse:
        from google.genai import types as genai_types  # lazy

        client = self._get_client()
        config = genai_types.GenerateContentConfig(
            temperature=temperature,
            max_output_tokens=max_tokens,
            system_instruction=system or None,
            response_mime_type="application/json" if json_mode else "text/plain",
        )
        response = client.models.generate_content(
            model=self.model,
            contents=prompt,
            config=config,
        )
        return LLMResponse(text=response.text or "", provider=self.name, model=self.model)


# --------------------------------------------------------------------------- #
# Anthropic (escalation)
# --------------------------------------------------------------------------- #

class AnthropicProvider:
    name = "anthropic"

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        self._api_key = api_key or settings.ANTHROPIC_API_KEY
        self.model = model or settings.ANTHROPIC_MODEL
        self._client = None

    def _get_client(self):
        if self._client is None:
            if not self._api_key:
                raise RuntimeError("ANTHROPIC_API_KEY not set")
            import anthropic  # lazy
            self._client = anthropic.Anthropic(api_key=self._api_key)
        return self._client

    def generate(
        self,
        prompt: str,
        *,
        system: Optional[str] = None,
        json_mode: bool = False,
        temperature: float = 0.4,
        max_tokens: int = 512,
    ) -> LLMResponse:
        client = self._get_client()
        # Anthropic has no dedicated JSON mode; nudge via system to reply with JSON only.
        sys_parts = [p for p in (system, "Respond with valid JSON only." if json_mode else None) if p]
        message = client.messages.create(
            model=self.model,
            max_tokens=max_tokens,
            temperature=temperature,
            system="\n\n".join(sys_parts) if sys_parts else None,
            messages=[{"role": "user", "content": prompt}],
        )
        text = "".join(block.text for block in message.content if getattr(block, "type", None) == "text")
        return LLMResponse(text=text or "", provider=self.name, model=self.model)


# --------------------------------------------------------------------------- #
# Selection
# --------------------------------------------------------------------------- #

def gemini_configured() -> bool:
    return bool(settings.GEMINI_API_KEY)


def anthropic_configured() -> bool:
    return bool(settings.ANTHROPIC_API_KEY)


def get_llm(*, escalate: bool = False) -> LLMProvider:
    """Resolve the provider for this call.

    Default → Gemini. When ``escalate`` is requested (hot lead / high value) and
    escalation is enabled + Anthropic is configured, use Anthropic. If the chosen
    one isn't configured, gracefully fall back to whichever is.
    """
    want_anthropic = escalate and settings.LLM_ESCALATION_ENABLED and anthropic_configured()
    if want_anthropic:
        return AnthropicProvider()
    if gemini_configured():
        return GeminiProvider()
    if anthropic_configured():
        return AnthropicProvider()
    # Nothing configured — return Gemini; the caller handles the RuntimeError at call time.
    return GeminiProvider()


def complete(
    prompt: str,
    *,
    system: Optional[str] = None,
    json_mode: bool = False,
    temperature: float = 0.4,
    max_tokens: int = 512,
    escalate: bool = False,
) -> LLMResponse:
    """Convenience: pick a provider and generate, with a single Anthropic fallback
    if the primary (Gemini) errors or returns empty. Never raises — returns an
    empty LLMResponse on total failure so callers can use their own fallback text.
    """
    primary = get_llm(escalate=escalate)
    try:
        resp = primary.generate(
            prompt, system=system, json_mode=json_mode,
            temperature=temperature, max_tokens=max_tokens,
        )
        if resp:
            return resp
        logger.warning("[llm] %s returned empty text", primary.name)
    except Exception as exc:
        logger.error("[llm] %s failed: %s", primary.name, exc)

    # Fallback to the other provider if available and different.
    if primary.name != "anthropic" and anthropic_configured():
        try:
            return AnthropicProvider().generate(
                prompt, system=system, json_mode=json_mode,
                temperature=temperature, max_tokens=max_tokens,
            )
        except Exception as exc:
            logger.error("[llm] anthropic fallback failed: %s", exc)
    return LLMResponse(text="", provider=primary.name, model=getattr(primary, "model", ""))
