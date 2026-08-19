# wa-saas — Task Board

Canonical task list for all phases. Mirror of `context/build-plan.md`, tracked as checkboxes.
Legend: `[ ]` todo · `[~]` in progress · `[x]` done. Update this after every feature and keep `context/progress-tracker.md` in sync.

---

## Phase 0 — Foundation & Safety Rails
- [x] **01 Repo hygiene & config** — `.gitignore`, `.env.example`, `ENV` dev/prod flag, all new secrets in `config.py` from env. _(done)_
- [x] **02 Tenancy foundation** — `tenancy.py` GUC helper; new SaaS tables (wa_numbers, conversations, memory_facts, media_assets, message_templates, consent, subscriptions, usage, tenant_members); Clerk-org columns on `workspaces`; **RLS policies on 15 tables + Alembic migration + app-role SQL. RLS isolation verified live (2 tenants, cross-tenant write blocked, fails closed).** Scope note: `Workspace` kept as the tenant table (`Tenant` alias added) — literal rename deferred as risky cosmetics; isolation delivered. _(done)_
- [x] **03 Compliance gate** — `core/outreach_policy.py` + 9 passing unit tests (do-not-contact, 24h window, cold-block, quota, agent-disabled, template consent basis). _(done)_
- [x] **04 MessagingProvider abstraction** — `messaging/{base,whatsmeow,cloud_api,factory}.py`; whatsmeow wrapped, Cloud API outbound implemented. _(done)_

## Phase 1 — Messaging Layer (wacli first; Cloud API deferred)
> **Decision (now):** Use **[wacli](https://wacli.sh/)** (CLI built on whatsmeow — linked-device QR, `sync --follow`, signed webhooks, `send text`/`send file`) as the **active** transport. WhatsApp Cloud API stays stubbed and is **out of scope until we explicitly pick it back up**.

- [x] **05 wacli provider — outbound** — `messaging/wacli.py` (`send text`/`send file` via CLI `--json`/`--store`); factory default `wacli`; `whatsapp_tasks` routes through provider; onboarding accepts `wacli` + store/account; migration `c3d4e5f6a7b8`; 13 unit tests. _(done)_
- [x] **06 wacli inbound webhook** — `POST /api/v1/webhook/wacli`: HMAC `X-Wacli-Signature`; RLS-safe `resolve_wacli_number`; upsert lead/conversation/message + `wa_message_id` dedup; enqueue `generate_ai_reply`; `ops/run_wacli_sync.sh`; 12 unit tests. _(done)_
- [x] **07 Media service (wacli path)** — `services/media.py` + `/media` API + `whatsapp.send_media` + `test_media.py` (13). _(done library path)_ Gap: agent auto-select in reply pipeline still open; `POST /media/{id}/send` is ungated (flagged in baseline 00).
- [ ] **08 Templates** — **deferred** (Meta-approved templates are a Cloud API concept). Until Cloud API: free-form / opt-in sends only through `outreach_policy` (24h window, consent, rate limits). Revisit when Cloud API is enabled.

### Deferred — WhatsApp Cloud API (do not start yet)
- [ ] **05b Cloud API provider — outbound** — `messaging/cloud_api.py` live WABA creds + send test.
- [ ] **06b Cloud API webhook — inbound** — `/webhook/cloud` signature verify + pipeline.

## Phase 2 — Auth, Tenancy & Billing
- [x] **09 Clerk Organizations auth** — `core/auth.py`: JWKS RS256 verify (no more unverified decode), `o`/`org_*` claim support, org→tenant provisioning, `TenantMember`, `require_role`, `get_tenant_db` (RLS session), dev fallback gated on `ENV!=prod`. 5 unit tests. _(done)_
- [x] **10 Onboarding + WhatsApp connect** — `api/endpoints/onboarding.py`: `/configure`, `/connect-number` (plan-limit gated, RLS), `/go-live` (blocks without disclosure line + a connected number). _(done)_
- [x] **11 Stripe billing** — `services/billing.py` (plan catalog, quota logic, usage metering, lazy Stripe, webhook handler) + `api/endpoints/billing.py` (`GET /billing`, `/checkout`, signature-verified `/webhook`). 4 unit tests. _(done)_

_Backend test suite note superseded — see Phase 3 / baseline 00 (true count **82**)._

## Phase 3 — AI Sales Agent
- [x] **12 LLM provider abstraction + persona/disclosure** — `ai/provider.py` (Gemini default + Anthropic escalation, lazy SDKs, fallback), `ai/persona.py` builds persona + **deterministic** first-message AI disclosure. _(done)_
- [x] **13 Conversation state machine + memory** — `ai/pipeline.py` qualify→nurture→propose→confirm; `services/memory.py` (pgvector recall + Gemini embeddings, graceful fallback), `services/debounce.py`, `services/typing_delay.py`; opt-out keywords set `do_not_contact`; wired through `outreach_policy.gate()` in `tasks/ai_tasks.py`. _(done)_
- [x] **14 Conversations inbox + human takeover** — `api/endpoints/conversations.py`: live threads, manual reply (through the gate), `human_takeover` toggle that pauses the agent; `messagerole` enum gains `human`. _(done)_

_Backend test suite (2026-08-20 · Feature 15): **90 passing** (prior 82 + leads CRM 8)._

## Phase 4 — Compliant Lead Sourcing
- [x] **15 Leads CRM (backend)** — `services/crm.py` list/filter/sort/paginate + detail (facts/thread/consent) + PATCH overrides; `get_tenant_db`; 8 tests in `test_leads_crm.py`. Frontend wire-up still open (prompt 02).
- [x] **16 Listening inbox (auto-reply)** — group intent match → gated auto-send → `/listening` feed + dismiss
- [ ] **17 Inbound capture** — widget / click-to-WhatsApp / QR into the lead pipeline.

## Phase 5 — Scale & Reliability
- [ ] **18 Queues, pooling, partitioning** — Celery queues, PgBouncer, partition `messages`, rate buckets.
- [ ] **19 Observability** — structured logs, metrics, Sentry, health, alerts.
- [ ] **20 Deploy** — Dockerfiles + compose, CI/CD, backups + restore runbook.

---

## Cross-cutting invariants (never violated — see AGENTS.md)
- [ ] Every send passes `outreach_policy.gate()` and a `MessagingProvider`.
- [ ] No send without inbound/opt-in. No group-member scraping. Always disclose AI. No real-person photos.
- [ ] Every tenant query inside `tenant_context()` (RLS).
