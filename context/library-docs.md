# Library Docs

Usage patterns for the third-party services this project depends on. These are canonical snippets — follow them; do not improvise alternative shapes. Always confirm current API details against official docs before implementing (APIs drift from training data).

---

## wacli (near-term primary transport)

Docs: https://wacli.sh/ · https://github.com/openclaw/wacli  
CLI built on whatsmeow. Pairs as a linked WhatsApp Web device, syncs to local SQLite, exposes scriptable send/search and signed webhooks. **Not affiliated with Meta.** Use for single-number / low-scale inbound sales automation; not for multi-tenant mass outreach.

### Install & pair

```bash
# macOS example — see https://wacli.sh/quickstart.html for current install
brew install openclaw/tap/wacli
wacli auth                    # QR → WhatsApp → Linked devices
wacli sync --follow           # keep store warm
```

### Send (used by `messaging/wacli.py`)

```bash
wacli send text --to +15551234567 --message "hello"
wacli send file --to +15551234567 --file ./pic.jpg --caption "portfolio"
# Prefer --json for machine parsing when wrapping from Python
```

While `sync --follow` is running, sends for the same store are delegated to that process (store lock). Respect that in ops.

### Inbound webhook (used by `/api/v1/webhook/wacli`)

```bash
wacli sync --follow \
  --webhook "https://api.example.com/api/v1/webhook/wacli" \
  --webhook-secret "$WACLI_WEBHOOK_SECRET" \
  --webhook-events message,receipt,chat_presence
```

- Verify header `X-Wacli-Signature: sha256=<hmac_hex>` over the **raw** body with `WACLI_WEBHOOK_SECRET`.
- Default event is a message payload (no `EventType` field), e.g.:

```json
{
  "Chat": "15551234567@s.whatsapp.net",
  "ID": "3EB0…",
  "SenderJID": "15551234567@s.whatsapp.net",
  "Timestamp": "2026-07-25T10:00:00Z",
  "FromMe": false,
  "Text": "hi",
  "ChatName": "Alice"
}
```

- Receipt / typing use `EventType: "receipt"` | `"chat_presence"`.
- Env: `WACLI_BIN` (path to binary), `WACLI_STORE_DIR`, `WACLI_WEBHOOK_SECRET`, optional per-tenant `--account`.

### Templates

wacli has **no** Meta-approved template send. Outside the 24h window, keep free-form blocked via `outreach_policy` until Cloud API is enabled.

---

## WhatsApp Business Cloud API (deferred)

> Parked. Do not implement live WABA wiring until Phase 1 wacli path is shipping. Stub remains in `messaging/cloud_api.py`.

Base: `https://graph.facebook.com/v21.0/{PHONE_NUMBER_ID}/messages`. Auth: `Authorization: Bearer <system-user-access-token>` per tenant WABA.

### Send text

```python
# messaging/cloud_api.py
async def send_text(self, to: str, text: str) -> SendResult:
    r = await self._client.post(
        f"{self.base}/{self.phone_number_id}/messages",
        headers={"Authorization": f"Bearer {self.token}"},
        json={
            "messaging_product": "whatsapp",
            "to": to,
            "type": "text",
            "text": {"body": text},
        },
    )
    return self._parse(r)
```

### Send media (image/video) — by uploaded media id

```python
json={
  "messaging_product": "whatsapp",
  "to": to,
  "type": "image",                     # or "video"
  "image": {"id": wa_media_id, "caption": caption or ""},
}
```

Upload first (`POST /{PHONE_NUMBER_ID}/media`, multipart) → cache the returned `id` in `media_assets.wa_media_id`.

### Send template (only outside the 24h window / opt-in)

```python
json={
  "messaging_product": "whatsapp",
  "to": to,
  "type": "template",
  "template": {
    "name": template_name,
    "language": {"code": lang},        # e.g. "en"
    "components": [...],               # body vars
  },
}
```

### Inbound webhook — verify signature (mandatory)

```python
# api/endpoints/webhook_cloud.py
import hmac, hashlib

def verify(app_secret: str, raw_body: bytes, header_sig: str) -> bool:
    expected = "sha256=" + hmac.new(app_secret.encode(), raw_body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, header_sig)
```

- GET challenge: echo `hub.challenge` when `hub.verify_token == WHATSAPP_VERIFY_TOKEN`.
- POST: verify `X-Hub-Signature-256` against **raw** body, then resolve tenant by `value.metadata.phone_number_id`.
- The **24-hour customer service window**: free-form messages allowed only within 24h of the user's last inbound. Otherwise a template is required. Enforced in `outreach_policy`.

---

## whatsmeow gateway (secondary — listening / single number)

The Go gateway (`go-gateway/main.go`) exposes HTTP: `GET /api/session/start?tenant=...`, `POST /api/send`, `POST /api/send-image`, `GET /api/groups`. `WhatsmeowProvider` wraps these. Used only for a tenant's own number, listening + human-approved replies. **Never** used for multi-tenant automated outreach.

---

## LLM provider (Gemini default, Anthropic escalation)

Abstract behind `ai/provider.py`. Structured JSON output; validate with Pydantic.

### Gemini

```python
from google import genai
client = genai.Client(api_key=settings.GEMINI_API_KEY)
resp = client.models.generate_content(
    model="gemini-2.5-flash",
    contents=prompt,
    config={"response_mime_type": "application/json"},
)
```

### Anthropic (for complex/hot leads) — with prompt caching

```python
from anthropic import Anthropic
client = Anthropic(api_key=settings.ANTHROPIC_API_KEY)
msg = client.messages.create(
    model="claude-sonnet-4-6",
    max_tokens=1024,
    system=[{
        "type": "text",
        "text": persona_and_disclosure,          # stable → cache it
        "cache_control": {"type": "ephemeral"},
    }],
    messages=conversation_turns,
)
```

Cache the stable persona/system block so repeated turns hit the cache. The reply pipeline always injects the tenant `disclosure_line` and the recalled `memory_facts`.

---

## Clerk (auth + Organizations)

```ts
// frontend — org-aware
import { ClerkProvider, OrganizationSwitcher } from "@clerk/nextjs";
```

```python
# backend — verify JWT (JWKS), extract org → tenant
# core/auth.py
claims = verify_jwt(token, jwks_url=settings.CLERK_JWKS_URL)
clerk_org_id = claims["org_id"]      # → resolve tenants.clerk_org_id
role = claims["org_role"]            # → owner/admin/agent
```

Never trust a client-supplied tenant id — always derive from the verified session. Handle Clerk webhooks (org created / membership changed) to sync `tenants` + `tenant_members`.

---

## Stripe (billing)

```python
import stripe
stripe.api_key = settings.STRIPE_SECRET_KEY

# Checkout for a plan
session = stripe.checkout.Session.create(
    mode="subscription",
    customer=tenant.stripe_customer_id,
    line_items=[{"price": price_id, "quantity": 1}],
    success_url=..., cancel_url=...,
)
```

- Verify webhook signature with `STRIPE_WEBHOOK_SECRET` (`stripe.Webhook.construct_event`).
- On `customer.subscription.*` → update `subscriptions` (plan + quota columns).
- Metered usage: increment `usage` from the send gate; enforce quota in `outreach_policy`.

---

## pgvector (memory + intent matching)

```sql
CREATE EXTENSION IF NOT EXISTS vector;
ALTER TABLE memory_facts ADD COLUMN embedding vector(768);
CREATE INDEX ON memory_facts USING hnsw (embedding vector_cosine_ops);
```

```python
# recall: nearest facts for this lead, tenant-scoped (inside tenant_context)
SELECT fact FROM memory_facts
WHERE lead_id = :lead_id AND is_active
ORDER BY embedding <=> :query_embedding
LIMIT 8;
```

Listening intent match: embed the incoming group message, compare against the tenant's service/intent embeddings; threshold → surface as a listening draft.

---

## Object storage (media — S3 / Cloudflare R2)

```python
# services/media.py — boto3 S3-compatible
import boto3
s3 = boto3.client("s3", endpoint_url=settings.OBJECT_STORAGE_ENDPOINT, ...)
s3.upload_fileobj(fileobj, bucket, key)                       # store binary
url = s3.generate_presigned_url("get_object",                # signed read
      Params={"Bucket": bucket, "Key": key}, ExpiresIn=3600)
```

Binaries **never** go in Postgres — only `storage_key` + metadata in `media_assets`.

---

## Celery (async)

```python
@celery_app.task(bind=True, autoretry_for=(httpx.HTTPError,),
                 retry_backoff=True, max_retries=3)
def generate_ai_reply(self, tenant_id, lead_id): ...
```

Separate queues: `ai`, `send`, `media`, `beat`. Every task runs inside `tenant_context(tenant_id)` before touching tenant data.
