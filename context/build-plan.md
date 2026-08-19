# Build Plan

## Core Principle

Each feature is built and made **verifiable** before the next. UI features are built with mock data first, verified visually, then wired to real logic. Backend features ship with a test that proves them. No invisible phases. **The compliance gate and tenant isolation are built early and are never bypassed for convenience.**

Features map to the phases in the approved roadmap (`/Users/garvsanwariya/.claude/plans/...`). Update `progress-tracker.md` after every feature.

---

## Phase 0 — Foundation & Safety Rails

### 01 Repo hygiene & config
- `.gitignore` in place; no `.env`, venv, node_modules, session files, or `.playwright-mcp/` committed.
- Rotate any secrets already exposed in git history.
- `core/config.py` reads all secrets from env; add `ENV` (dev/prod) flag.
- **Verify:** `git status` clean of artifacts; app boots reading env only.

### 02 Tenancy foundation (Tenant model + RLS)
- Promote `Workspace` → `Tenant`; add `tenant_id` to every domain table.
- `core/tenancy.py` `tenant_context()` sets `app.tenant_id` GUC per session.
- RLS policies on all tenant tables; Alembic migration.
- **Verify:** RLS test — session for tenant A cannot read tenant B rows.

### 03 Compliance gate (`outreach_policy.py`)
- Central `gate(tenant, lead, kind)` enforcing: inbound-or-opt-in, 24h window, do-not-contact, per-tenant + per-number rate limit, quota.
- Every send path calls it. Feature flag: hard-block on violation.
- **Verify:** unit tests for each rule (no opt-in → blocked; over quota → blocked; DNC → blocked; outside 24h without template → blocked).

### 04 MessagingProvider abstraction
- `messaging/base.py` interface + `factory.py`.
- Refactor existing send (currently hard-wired to `localhost:5005/api/send`) behind `WhatsmeowProvider`.
- **Verify:** existing whatsmeow send still works through the interface.

---

## Phase 1 — Messaging Layer (**wacli first**; Cloud API deferred)

> **Near-term transport:** [wacli](https://wacli.sh/) — scriptable WhatsApp CLI on whatsmeow. Pair with `wacli auth` (QR), keep warm with `wacli sync --follow`, send with `wacli send text|file`, inbound via `--webhook` + `X-Wacli-Signature`.  
> **Deferred:** WhatsApp Business Cloud API (Embedded Signup, Graph send, Meta templates). Keep `messaging/cloud_api.py` stubbed; do not block product progress on Meta app review.

### 05 wacli provider — outbound
- Add `messaging/wacli.py` implementing `MessagingProvider`: `send_text` → `wacli send text --to … --message …`; `send_media` → `wacli send file`; typing best-effort / no-op if unsupported.
- Factory resolves `provider == "wacli"` (default for new numbers). Support `--account` / `WACLI_STORE_DIR` per tenant from `wa_numbers` / config.
- Every send still passes `outreach_policy.gate()` first.
- **Verify:** from a paired store, backend send path delivers a text to a test chat.

### 06 wacli inbound webhook _(done)_
- `POST /api/v1/webhook/wacli`: verify `X-Wacli-Signature: sha256=<hmac>`; parse message payload (`Chat`, `ID`, `SenderJID`, `Text`, `FromMe`, …); resolve tenant by linked account; upsert contact/lead/conversation/message; enqueue `generate_ai_reply` when not `FromMe`.
- Ops script: `ops/run_wacli_sync.sh` (`wacli sync --follow --webhook … --webhook-secret`).
- **Verify:** inbound personal chat creates lead + fires reply pipeline through the gate.

### 07 Media service (photos/videos) — wacli path
- `services/media.py`: upload to object storage, signed URLs, `media_assets` + `/media` API.
- Outbound: download/prepare file → `wacli send file`. Inbound: store when sync/webhook exposes media.
- **Verify:** upload an image, agent sends it via wacli; inbound media lands on the conversation when available.

### 08 Templates — deferred until Cloud API
- Meta-approved templates are **not** available on the wacli/whatsmeow path.
- Until then: no template broadcast feature; outside-24h messaging stays blocked by the gate unless a recorded opt-in path is explicitly designed for free-form (prefer wait for Cloud API).
- When Cloud API returns: `message_templates` CRUD + `send_template` as originally planned.

### Deferred Cloud API (05b / 06b)
- Outbound Graph API + inbound `X-Hub-Signature-256` webhook — implement only when we switch primary transport back to Meta.

---

## Phase 2 — Auth, Tenancy & Billing

### 09 Clerk Organizations auth
- `core/auth.py`: strict JWT (JWKS), org→tenant resolution, `require_role`. Remove prod dev-fallback.
- **Verify:** requests without valid org JWT are rejected; role guard works.

### 10 Onboarding + WhatsApp connect
- `/onboarding`: create org → connect WhatsApp (**wacli QR / linked device** as the primary path now; Cloud API Embedded Signup deferred) → configure agent → go live.
- **Verify:** a new org can pair a number via wacli and flip the agent on.

### 11 Stripe billing
- `services/billing.py`: plans, checkout, webhook → `subscriptions`; quota columns.
- Usage metering from the gate → `usage`.
- **Verify (test mode):** subscribe → quota set → exceeding quota blocks sends.

---

## Phase 3 — AI Sales Agent

### 12 LLM provider abstraction + persona/disclosure
- `ai/provider.py` (Gemini default, Anthropic escalation), `ai/persona.py` builds persona + **mandatory disclosure**.
- **Verify:** first reply in a new thread contains the disclosure line.

### 13 Conversation state machine + memory
- `ai/pipeline.py`: qualify → nurture → propose-meeting → confirm; port `memory_facts` (pgvector recall) + debounce + typing delay.
- Opt-out keywords ("stop") set do_not_contact.
- **Verify:** multi-turn thread qualifies, remembers a stated fact, proposes a meeting, honors "stop".

### 14 Conversations inbox + human takeover
- `/conversations`: live threads, reply manually, toggle `human_takeover` (agent pauses).
- **Verify:** takeover stops auto-replies; manual send works through the gate.

---

## Phase 4 — Compliant Lead Sourcing

### 15 Leads CRM
- `/leads` + `/leads/[id]`: list, filter by stage/score/source, detail with memory facts + conversation.
- **Verify:** inbound leads appear, scored, filterable.

### 16 Listening inbox (human-approve)
- Group intent via wacli sync (group chats in store / webhook) → intent match (keywords + embedding) → `ListeningLead` with **auto-reply** (gated) surfaced in `/listening` for review/dismiss.
- Human edits/approves → gate → send via wacli. No auto-DM, no member scraping.
- **Verify:** a matching group message surfaces a draft; approving sends; nothing sends without approval.

### 17 Inbound capture (widget / click-to-WhatsApp / QR)
- Landing widget + link generator that route into the same lead pipeline with recorded consent source.
- **Verify:** widget-initiated chat creates a consented lead.

---

## Phase 5 — Scale & Reliability

### 18 Queues, pooling, partitioning
- Separate Celery queues (`ai`, `send`, `media`, `beat`); PgBouncer; partition `messages`; per-tenant rate buckets in Redis.
- **Verify:** load test (k6/Locust) with N tenants shows no cross-tenant starvation.

### 19 Observability
- Structured logging with `tenant_id`, Prometheus metrics, Sentry, health checks, alerts on webhook/send failures.
- **Verify:** metrics + traces visible; a forced webhook failure alerts.

### 20 Deploy
- Dockerfiles + compose (dev), CI/CD (lint/test/migrate/deploy), backups + restore runbook.
- **Verify:** clean deploy from scratch; restore from backup succeeds.

---

## Feature Count

| Phase | Features |
| ----- | -------- |
| Phase 0 — Foundation | 4 |
| Phase 1 — Messaging (wacli; Cloud API deferred) | 4 active + deferred Cloud API |
| Phase 2 — Auth & Billing | 3 |
| Phase 3 — AI Agent | 3 |
| Phase 4 — Lead Sourcing | 3 |
| Phase 5 — Scale | 3 |
| **Total** | **20** |
