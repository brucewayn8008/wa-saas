# Architecture

## Stack

| Layer | Tool | Purpose |
| ----- | ---- | ------- |
| API / backend | FastAPI (Python 3.12) | REST API, webhooks, control plane |
| Async workers | Celery + Redis | AI replies, sends, media, scheduled jobs |
| Messaging (**near-term primary**) | **[wacli](https://wacli.sh/)** CLI (whatsmeow) | Linked-device QR, `sync --follow`, signed webhooks, `send text`/`send file` |
| Messaging (legacy secondary) | Go **whatsmeow** gateway | Existing bridge; prefer wacli going forward |
| Messaging (**deferred**) | WhatsApp Business **Cloud API** | Production WABA path later — not blocking current build |
| Database | PostgreSQL + **pgvector** | System of record, tenant-isolated (RLS), embeddings |
| Cache / queue / limits | Redis | Celery broker, debounce/typing state, rate-limit buckets |
| Object storage | S3 / Cloudflare R2 + CDN | Media (photos/videos), signed URLs |
| Auth | **Clerk (Organizations)** | Multi-tenant auth, orgs = tenants, RBAC |
| Billing | **Stripe** | Subscriptions, usage metering, quotas |
| AI | Gemini (default) / Anthropic (escalation) | Reply generation, qualification, extraction |
| Frontend | Next.js (App Router) + Tailwind | Tenant dashboard |
| Language | Python (backend), Go (gateway), TypeScript (frontend) | Polyglot |

---

## Folder Structure

```
wa-saas/
├── AGENTS.md
├── context/                              → this context pack
├── backend/
│   ├── app/
│   │   ├── main.py                       → FastAPI app entry
│   │   ├── core/
│   │   │   ├── config.py                 → Settings (env-driven)
│   │   │   ├── auth.py                    → Clerk JWT verify → tenant + RBAC
│   │   │   ├── outreach_policy.py         → ★ compliance gate (every send routes here)
│   │   │   ├── celery_app.py              → Celery config + beat schedules
│   │   │   └── tenancy.py                 → tenant context + RLS GUC helpers
│   │   ├── models/
│   │   │   └── database.py                → SQLAlchemy models (tenant-scoped)
│   │   ├── db/
│   │   │   ├── session.py                 → session factory (sets app.tenant_id)
│   │   │   └── init_db.py                 → migrations / RLS bootstrap
│   │   ├── api/endpoints/
│   │   │   ├── webhook_wacli.py           → wacli sync webhook (X-Wacli-Signature)
│   │   │   ├── webhook.py                 → legacy whatsmeow gateway webhook
│   │   │   ├── webhook_cloud.py           → Cloud API webhook (deferred)
│   │   │   ├── conversations.py           → inbox + takeover
│   │   │   ├── leads.py                   → lead CRM
│   │   │   ├── listening.py               → group listening auto-reply inbox
│   │   │   ├── templates.py               → template management
│   │   │   ├── media.py                   → media upload/list
│   │   │   ├── settings.py                → persona/services config
│   │   │   ├── billing.py                 → Stripe checkout + webhook
│   │   │   └── admin.py                   → staff super-admin
│   │   ├── messaging/                     → ★ MessagingProvider abstraction
│   │   │   ├── base.py                    → MessagingProvider interface
│   │   │   ├── wacli.py                   → WacliProvider (CLI subprocess / wrapper)
│   │   │   ├── whatsmeow.py               → WhatsmeowProvider (legacy Go gateway)
│   │   │   ├── cloud_api.py               → CloudApiProvider (deferred / stub)
│   │   │   └── factory.py                 → resolve provider per tenant
│   │   ├── services/
│   │   │   ├── crm.py                     → lead lifecycle, activity logging
│   │   │   ├── media.py                   → object-storage upload/download
│   │   │   ├── billing.py                 → plans, quotas, usage metering
│   │   │   ├── memory.py                  → memory-fact extraction + recall (pgvector)
│   │   │   ├── debounce.py                → coalesce multi-message bursts (ported)
│   │   │   └── typing_delay.py            → human-like delivery timing (ported)
│   │   ├── ai/
│   │   │   ├── provider.py                → LLM provider interface (Gemini/Anthropic)
│   │   │   ├── pipeline.py                → qualify→reply→extract pipeline
│   │   │   └── persona.py                 → persona + mandatory disclosure builder
│   │   └── tasks/
│   │       ├── ai_tasks.py                → generate_ai_reply
│   │       ├── whatsapp_tasks.py          → send via MessagingProvider
│   │       └── followup_tasks.py          → scheduled follow-ups (opt-in only)
│   └── requirements.txt
├── go-gateway/
│   └── main.go                           → whatsmeow bridge (listening/single-number)
├── frontend-next/                        → Next.js dashboard
└── ops/                                  → run scripts, docker-compose (added)
```

---

## System Boundaries

| Folder | Owns |
| ------ | ---- |
| `api/endpoints/` | HTTP only — request parse, auth, delegate. No business logic. |
| `messaging/` | All WhatsApp transport. The only place that invokes wacli / gateway / (later) Cloud API. |
| `services/` | Business logic — CRM, media, billing, memory. No HTTP, no transport calls except via `messaging/`. |
| `ai/` | Prompt building + LLM calls. Never sends messages, never writes transport. |
| `tasks/` | Celery orchestration. Thin — calls services/ai/messaging. |
| `core/` | Config, auth, tenancy, and the **outreach_policy** gate. |
| `models/` | SQLAlchemy models only. |

**The one rule that matters most:** every outbound message passes through `messaging/` **and** is authorized by `core/outreach_policy.py` first. There is no other send path.

---

## Data Flow

### Inbound message (wacli — near-term)

```
Prospect messages tenant number
        ↓
wacli sync --follow --webhook → POST /api/v1/webhook/wacli
        ↓
Verify X-Wacli-Signature (HMAC sha256)
        ↓
Resolve tenant by linked wacli account / wa_numbers row
        ↓
Upsert Contact/Lead + Conversation + store Message (RECEIVED)  [tenant-scoped]
        ↓
Enqueue Celery: generate_ai_reply(tenant_id, lead_id)  (debounced)
        ↓
ai/pipeline: recall memory (pgvector) → persona+disclosure prompt → LLM
        ↓
outreach_policy.gate(...)  → allowed? (inbound conversation + quota + not DNC)
        ↓
tasks/whatsapp_tasks → WacliProvider.send_text / send_media
        ↓
Store Message (SENT) + AgentActivity
```

### Group listening (auto-reply)

```
wacli sync receives a group message the tenant is a member of
        ↓
webhook → intent match (keywords + embedding)  → if signal:
        ↓
create ListeningLead + CRM Lead (source=GROUP)
        ↓
ai/pipeline generates reply (with disclosure) → outreach_policy.gate
        ↓
allowed → MessagingProvider.send to the lead (DM); ListeningLead status=sent
blocked → persist reply + block_reason; ListeningLead status=blocked
        ↓
appears in /listening for review/dismiss (no manual approve step)
```

### Outbound / re-engagement (opt-in)

```
# Near-term (wacli): no Meta templates — gate blocks outside-24h free-form unless
# a future opt-in free-form path is explicitly approved. Prefer wait for Cloud API.

# Deferred (Cloud API):
Template broadcast requested
        ↓
select contacts WHERE consent recorded AND NOT do_not_contact
        ↓
outreach_policy.gate (opt-in + 24h window + rate limit + quota)
        ↓
MessagingProvider.send_template  (approved template only)
```

---

## Database Schema (Postgres + RLS + pgvector)

> Evolves the current `wa-mark-2` schema. **`Workspace` is promoted to `Tenant`** (organization). Every domain table carries `tenant_id` and is protected by Row-Level Security keyed on the `app.tenant_id` session GUC.

### `tenants` (was `workspaces`)

| Column | Type | Notes |
| ------ | ---- | ----- |
| id | uuid | PK |
| clerk_org_id | text | unique — Clerk Organization id |
| company_name | text | |
| business_description | text | |
| system_prompt | text | persona base |
| disclosure_line | text | **mandatory** AI-disclosure text |
| agent_config | jsonb | services, tone, offer, booking link, business hours |
| agent_enabled | bool | |
| default_provider | text | `wacli` \| `whatsmeow` \| `cloud_api` (cloud_api deferred) |
| created_at / updated_at | timestamptz | |

### `tenant_members`

| Column | Type | Notes |
| ------ | ---- | ----- |
| id | uuid | PK |
| tenant_id | uuid | FK tenants |
| clerk_user_id | text | |
| email | text | |
| role | text | `owner` \| `admin` \| `agent` |

### `wa_numbers` (replaces single `whatsapp_sessions`)

| Column | Type | Notes |
| ------ | ---- | ----- |
| id | uuid | PK |
| tenant_id | uuid | FK tenants |
| provider | text | `wacli` \| `whatsmeow` \| `cloud_api` |
| phone_number_id | text | Cloud API — routing key (deferred) |
| waba_id | text | Cloud API (deferred) |
| jid | text | WhatsApp JID (wacli / whatsmeow) |
| wacli_account | text | wacli `--account` name / store key |
| status | text | UNCONFIGURED / QR_PENDING / CONNECTED / LOGGED_OUT |
| qr_code | text | pairing UX helper (wacli auth / legacy gateway) |
| messaging_tier | int | Cloud API tier (deferred) |

### `leads`

Existing `leads` columns kept, plus `tenant_id` (FK) and `consent_id` (FK, nullable). Key fields: `jid`, `name`, `status` (NEW/IN_PROGRESS/CONVERTED/FAILED), `intent_label`, `score`, `service_interest`, `requirement_summary`, `meeting_status`, `source` (DIRECT/GROUP/AD/WIDGET), `do_not_contact`, `last_inbound_at`, `last_outbound_at`.

### `conversations` (new — was implicit)

| Column | Type | Notes |
| ------ | ---- | ----- |
| id | uuid | PK |
| tenant_id | uuid | FK |
| lead_id | uuid | FK leads |
| wa_number_id | uuid | which number |
| status | text | active / paused / ended |
| human_takeover | bool | if true, agent does not auto-reply |
| last_inbound_at | timestamptz | drives 24h-window logic |

### `messages`

Existing columns + `tenant_id`, `conversation_id`, `wa_message_id` (unique, dedup), `media_asset_id` (nullable), `direction` derived from `role`. **Partition candidate** by `(tenant_id, timestamp)`.

### `memory_facts` (new — ported from aisha-agent)

| Column | Type | Notes |
| ------ | ---- | ----- |
| id | uuid | PK |
| tenant_id | uuid | FK |
| lead_id | uuid | FK |
| category | text | service / budget / timeline / preference |
| fact | text | |
| embedding | vector(768) | pgvector — semantic recall |
| confidence | int | 0-100 |
| source | text | inferred / stated |
| is_active | bool | soft delete |

### `media_assets` (new)

| Column | Type | Notes |
| ------ | ---- | ----- |
| id | uuid | PK |
| tenant_id | uuid | FK |
| type | text | image / video |
| storage_key | text | object-storage key (NOT the binary) |
| wa_media_id | text | cached Cloud API media id |
| mime | text | |
| size_bytes | int | |
| tags | text[] | e.g. portfolio, product |

### `message_templates` (new)

| Column | Type | Notes |
| ------ | ---- | ----- |
| id | uuid | PK |
| tenant_id | uuid | FK |
| name | text | |
| wa_template_name | text | approved template name |
| language | text | |
| body | text | preview |
| status | text | pending / approved / rejected |

### `consent` (new)

| Column | Type | Notes |
| ------ | ---- | ----- |
| id | uuid | PK |
| tenant_id | uuid | FK |
| lead_id | uuid | FK |
| source | text | inbound / widget / ad / import(with-proof) |
| granted_at | timestamptz | |
| revoked_at | timestamptz | nullable |

### `subscriptions` + `usage` (new — billing)

`subscriptions`: `tenant_id`, `stripe_customer_id`, `stripe_subscription_id`, `plan`, `status`, `current_period_end`, quota columns (`max_numbers`, `monthly_conversation_quota`, `max_seats`, `media_storage_mb`).
`usage`: `tenant_id`, `period`, `conversations_used`, `messages_sent`, `media_stored_mb`.

### `agent_activities`

Existing + `tenant_id`. Feeds dashboard activity + admin health.

---

## Row-Level Security (RLS)

- Each request resolves `tenant_id` from the Clerk org claim, then sets a Postgres session GUC: `SET LOCAL app.tenant_id = '<uuid>'`.
- Every tenant-scoped table has a policy: `USING (tenant_id = current_setting('app.tenant_id')::uuid)`.
- App-layer queries also filter by `tenant_id` (defense in depth). **Never** run a tenant query without the GUC set.
- `/admin` uses a separate staff role that bypasses RLS explicitly and is audit-logged.

See `core/tenancy.py` for the `tenant_context()` helper that opens a session with the GUC set.

---

## MessagingProvider Pattern

```python
# messaging/base.py
class MessagingProvider(Protocol):
    async def send_text(self, to: str, text: str) -> SendResult: ...
    async def send_media(self, to: str, asset: MediaAsset, caption: str | None) -> SendResult: ...
    async def send_template(self, to: str, template: str, vars: dict) -> SendResult: ...
    async def send_typing(self, to: str, on: bool) -> None: ...

# messaging/factory.py — resolve per tenant/number
def get_provider(tenant: Tenant, number: WANumber) -> MessagingProvider:
    if number.provider == "wacli":
        return WacliProvider(number)
    if number.provider == "cloud_api":
        return CloudApiProvider(number)  # deferred
    return WhatsmeowProvider(number)     # legacy gateway
```

The AI/CRM core never imports a concrete provider — only the interface via the factory.

---

## Authentication

- Provider: **Clerk with Organizations**. One org = one tenant.
- Backend verifies the Clerk JWT (JWKS), extracts `org_id` → resolves `tenant_id`, and role → RBAC.
- `require_role("admin")` dependency guards privileged endpoints.
- The old `x-user-email` dev fallback is **removed** in production (allowed only when `ENV=dev`).
- Protected: all `/api/v1/*` except health, **wacli webhook** (signature-verified), Stripe webhook (signature-verified), Clerk webhook. (Cloud API webhook when deferred work resumes.)

---

## How to Run (dev)

```
# Postgres (with pgvector) + Redis running locally or via docker-compose
ops/run_backend.sh     # FastAPI :8000
ops/run_worker.sh      # Celery worker
ops/run_beat.sh        # Celery beat
ops/run_frontend.sh    # Next.js :3000

# wacli (near-term WhatsApp transport) — install from https://wacli.sh/
wacli auth                           # QR pair once
wacli sync --follow \
  --webhook http://127.0.0.1:8000/api/v1/webhook/wacli \
  --webhook-secret "$WACLI_WEBHOOK_SECRET"

# Optional legacy:
# ops/run_gateway.sh                 # Go whatsmeow gateway :5005
```

Cloud API (deferred) additionally needs a Meta app + test number and a public webhook URL (ngrok in dev).

---

## Invariants

Rules the AI agent must never violate:

- **Every outbound message passes `outreach_policy.gate()` AND goes through a `MessagingProvider`.** There is no other send path.
- **No send without inbound or recorded opt-in.** No cold outreach. Ever.
- **The agent always includes the tenant's `disclosure_line`** at the start of a new conversation. It never claims to be a specific real human.
- **No scraping of group members** into outreach. Listening produces **draft** replies that a human must approve.
- **Media is tenant-owned brand assets only.** No real-person photos used as a fake persona.
- **Every tenant-scoped query runs inside `tenant_context()`** with `app.tenant_id` set — never a bare query.
- `messaging/` is the only package that invokes wacli / gateway / Cloud API. `ai/` never sends.
- wacli (`X-Wacli-Signature`) and Clerk/Stripe webhooks are **always signature-verified** before processing. (Same rule for Cloud API when enabled.)
- Quotas are enforced in the gate — a tenant over quota cannot send.
- Secrets come from env/secret-manager only — never hardcoded, never committed.
- Templates are the **only** way to message outside the 24h customer-service window.
