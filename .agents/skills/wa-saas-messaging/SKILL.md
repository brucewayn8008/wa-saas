---
name: wa-saas-messaging
description: >-
  WhatsApp transport rules for wa-saas — the MessagingProvider abstraction and the
  wacli CLI (whatsmeow) as the active transport, with Cloud API deferred. Use when
  sending/receiving WhatsApp messages or media, handling the wacli inbound webhook,
  pairing numbers, or touching anything in messaging/ or the webhooks.
---

# wa-saas — Messaging Transport

`messaging/` is the **only** package that talks to WhatsApp. Everything else uses the interface via the factory. `ai/` never sends.

## Provider abstraction
```python
# messaging/base.py
class MessagingProvider(Protocol):
    async def send_text(self, to, text) -> SendResult: ...
    async def send_media(self, to, asset, caption) -> SendResult: ...
    async def send_template(self, to, template, vars) -> SendResult: ...
    async def send_typing(self, to, on) -> None: ...

# resolve per tenant/number — never import a concrete provider elsewhere
provider = messaging.factory.get_provider(tenant, wa_number)
```
Providers: `wacli` (active default), `whatsmeow` (legacy Go gateway), `cloud_api` (**deferred/stub — do not build unless explicitly asked**).

## wacli (active transport)
- Pair once: `wacli auth` (QR). Keep warm + receive: `wacli sync --follow --webhook <url> --webhook-secret <secret>` (see `ops/run_wacli_sync.sh`).
- Send: `WacliProvider` shells out to `wacli send text|file` (`--json`, per-tenant `--account` / `WACLI_STORE_DIR`).
- Wrap subprocess calls in typed try/except → `SendResult(success, error, wa_message_id)`. Never crash the run; log `[messaging/wacli]`.

## Inbound webhook
`POST /api/v1/webhook/wacli` (`api/endpoints/webhook_wacli.py`):
- **Verify `X-Wacli-Signature: sha256=<hmac>` before anything else** (`messaging/wacli_sig.py`, secret `WACLI_WEBHOOK_SECRET`).
- Resolve tenant by linked account (RLS-safe), upsert contact/lead/conversation/message, **dedup on `wa_message_id`**, enqueue `generate_ai_reply` only when not `FromMe`.

## Hard rules
- A send from `messaging/` is still gated: the caller must pass `outreach_policy.gate()` first (see `wa-saas-compliance`).
- No transport calls from `api/endpoints/`, `services/`, `ai/`, or `tasks/` except through a provider.
- Cloud API + Meta templates (`send_template`, 05b/06b/08) are deferred. Keep `cloud_api.py` stubbed; don't block work on Meta review.
- wacli/whatsmeow is a single-number / low-scale profile — not a path to mass outreach.

## Verify a messaging change
Paired store → backend send delivers to a test chat; inbound personal chat creates a lead + fires the reply pipeline through the gate; bad signature is rejected; duplicate `wa_message_id` is ignored.
