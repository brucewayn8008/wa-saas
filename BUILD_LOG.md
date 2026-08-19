# Build Log

Chronological record of what was built, why, and how it was verified. Newest entries at the top.

---

## 2026-08-09 — Repo cleanup + local/ops setup finished

**Repo cleanup:** made `wa-saas` self-contained and archived the rest.
- Copied the Go whatsmeow gateway source into `wa-saas/go-gateway/` (`main.go`, `go.mod`,
  `go.sum`) — wa-saas previously had no gateway of its own and depended on
  `wa-mark-2/go-gateway`. Sessions live in Postgres, so no WhatsApp re-login is lost.
- Repointed `wa-saas/ops/*.sh` from the old `wa-mark-2/backend`, `wa-mark-2/go-gateway`
  and root `frontend-next` to the `wa-saas/*` paths; added `.venv` detection; fixed the
  `start.sh` log dir; removed dead romantic/aisha vars.
- Moved everything non-`wa-saas` into `old/` (aisha-agent, wa-mark-2, root frontend-next,
  _legacy, agent-skills, wa-agent-helper, root ops, ecosystem.config.js, PDFs, screenshots,
  MAC_24X7_RUNBOOK.md, __pycache__). Root now = `wa-saas/` + `old/` + infra.

**Local/ops setup (verified end-to-end):**
- Installed the missing backend deps into `.venv` (`uvicorn`, `email-validator`,
  `google-genai`, `anthropic`, `stripe`); the rest were already present. Toolchain: Go 1.25.5,
  wacli 0.2.0, Postgres + Redis both up.
- DB: local dev reuses the existing **`wa_mark2`** database (per `backend/.env`) to preserve
  the whatsmeow login + data. `init_db`'s `Base.metadata.create_all` (run on startup) created
  the missing SaaS tables (`wa_numbers`, `tenant_members`, `subscriptions`, `usage`,
  `media_assets`, `message_templates`, `consent`). Alembic sits at `6e8e338c61d9`; the
  SaaS-RLS migration is intentionally **not** applied locally (RLS is bypassed as superuser
  anyway) — create_all is the local table strategy.
- **Enum fix:** SQLAlchemy stores the enum *name*, so `messages.role` labels are `USER`/`AGENT`.
  Added `HUMAN` (not `human`) to the `messagerole` type and corrected migration
  `b2c3d4e5f6a7` accordingly. (A stray lowercase `human` label was left behind — harmless/unused.)
- `pgvector` extension is unavailable on this local Postgres (`vector.control` missing);
  `memory.py` degrades to recency recall, so the agent still works locally.

**Verification:**
- `pytest -q` → **65 passed** (Phase 3 suite + the wacli-provider tests, which now collect
  once `httpx`/deps are present).
- `go build` on `wa-saas/go-gateway` → clean 21MB binary.
- Smoke tests via the actual ops scripts: `run_backend.sh` → `GET /health` = `200 {"status":"ok"}`;
  `run_gateway.sh` → Postgres session store init + listening on `:5005`; Celery app loads
  `ai.generate_reply` + `whatsapp.send_message` with the Redis broker reachable. Frontend
  `node_modules` + `.env.local` present.

**How to run locally:** `ops/run_backend.sh`, `ops/run_worker.sh`, `ops/run_beat.sh`,
`ops/run_gateway.sh`, `ops/run_frontend.sh` (or `ops/start.sh` for all). For the wacli inbound
path: `ops/run_wacli_sync.sh` (needs `WACLI_WEBHOOK_SECRET` + an authenticated wacli store).

**Two blockers fixed to make the agent actually reply:**
1. **Gemini model deprecated** — `gemini-2.5-flash-lite` returns 404 ("no longer available to
   new users"). Switched the default to **`gemini-2.5-flash`** (verified live: returns a real
   reply) in `config.py` + `.env` + `.env.example`.
2. **Schema drift on `workspaces`** — the reused `wa_mark2` `workspaces` table predated the SaaS
   columns and `create_all` doesn't alter existing tables. `ALTER TABLE` added `clerk_org_id`
   (+unique idx), `disclosure_line`, `default_provider`. (`leads`/`messages` were already current.)

Verified live: the pipeline produces a qualified reply (WARM/55), extracts memory facts, and
prepends the AI disclosure on the first message. The `wa_mark2` DB has 1 logged-in whatsmeow
device (`919259684359`); its workspace "Aisha Agent" is `agent_enabled=is_running=True`.

---

## 2026-08-09 — Phase 1 · 06 wacli inbound webhook _(done)_

**Goal:** Accept signed wacli `sync --follow` webhooks and feed the existing lead + AI reply pipeline.

### Delivered
- `POST /api/v1/webhook/wacli` (`api/endpoints/webhook_wacli.py`): verify `X-Wacli-Signature: sha256=<hmac>` over raw body; Clerk-unauthenticated.
- `messaging/wacli_sig.py`: HMAC helpers.
- `services/inbound_wacli.py`: tenant resolve → upsert lead/conversation/message → debounce + `generate_ai_reply`; `chat_presence` typing marks; ignore `FromMe` / receipts / unmonitored groups.
- Alembic `d4e5f6a7b8c9`: `messages.wa_message_id` (+ unique per workspace) and `resolve_wacli_number()` SECURITY DEFINER for RLS-safe lookup by `account` / `store` / `workspace_id` / single-tenant fallback.
- Ops: `ops/run_wacli_sync.sh`.
- Tests: `tests/test_wacli_webhook.py` — 12 passed (wacli suite 25).

**Verify:** set `WACLI_WEBHOOK_SECRET`, run `alembic upgrade head`, then `./ops/run_wacli_sync.sh` (optionally `ACCOUNT=` / `WORKSPACE_ID=`). Send a DM to the linked number → lead + debounced AI reply.

**Next:** 07 Media service (wacli path).

---

## 2026-08-09 — Phase 1 · 05 wacli outbound provider _(done)_

**Goal:** Make wacli the default MessagingProvider for outbound sends.

### Delivered
- `app/messaging/wacli.py`: `WacliProvider` wraps `wacli --json send text|file` with `--store`, timeout, JSON id parsing, URL→temp download for media, templates unsupported, typing no-op.
- `factory.py`: default `provider=wacli`; resolve `wacli_store_dir` / `wacli_account` → store path.
- `tasks/whatsapp_tasks.py`: Celery send uses `get_provider` (no longer hard-wired to Go gateway).
- Model + Alembic `c3d4e5f6a7b8`: `wa_numbers.wacli_store_dir` / `wacli_account`; ORM defaults → `wacli`.
- Onboarding `/connect-number` accepts `wacli` (+ store/account); new numbers QR_PENDING until paired.
- Config / `.env.example`: `WACLI_BIN`, `WACLI_STORE_DIR`, `WACLI_TIMEOUT_SECONDS`, `WACLI_WEBHOOK_SECRET`.
- Tests: `tests/test_wacli_provider.py` — 13 passed (suite 53).

**Verify (manual, paired store):** with `wacli auth` + `wacli sync --follow` running, enqueue `send_whatsapp_message` or call `WacliProvider().send_text(to, text)`.

**Next:** 06 _(done — see above)_.

---

## 2026-08-08 — Plan change: wacli replaces Cloud API as near-term transport

**Decision:** Phase 1 messaging will use **[wacli](https://wacli.sh/)** (linked-device CLI on whatsmeow: `auth`, `sync --follow --webhook`, `send text|file`) instead of WhatsApp Cloud API for now. Cloud API + Meta templates remain deferred (TASKS 05b/06b/08).

**Docs updated:** `TASKS.md`, `context/build-plan.md`, `context/progress-tracker.md`, `context/architecture.md`, `context/project-overview.md`, `context/library-docs.md`, `context/code-standards.md`, `AGENTS.md`.

---

## 2026-08-08 — Phase 3: AI Sales Agent (features 12, 13, 14)

**Goal:** Build the disclosed AI sales agent — a provider-agnostic LLM layer, a
qualify→propose→confirm conversation state machine with memory, and a live
conversations inbox with human takeover. Gemini is the default model.

### 12 — LLM provider abstraction + persona/disclosure _(done)_
- `app/ai/provider.py`: `LLMProvider` protocol + `GeminiProvider` (default) and
  `AnthropicProvider` (escalation). SDKs imported **lazily** so importing the module
  needs neither package. `get_llm(escalate=…)` selects Gemini by default and Anthropic
  for hot/high-value moments (gated on `LLM_ESCALATION_ENABLED` + config), with graceful
  fallback either way. `complete()` wraps a call with a single cross-provider fallback and
  never raises (returns empty on total failure so callers use their own fallback text).
- `app/ai/persona.py`: `build_system_prompt()` gives the agent the tenant's brand voice,
  services and offer while asserting it is an AI and must never impersonate a real human.
  `ensure_disclosure()` **deterministically** prepends the tenant `disclosure_line` to the
  first agent message of a thread — disclosure is enforced in code, not left to the model.
- Config: `GEMINI_MODEL`, `GEMINI_EMBED_MODEL`, `ANTHROPIC_MODEL`, `LLM_ESCALATION_ENABLED`.
  Added `anthropic>=0.39.0` to requirements + `.env.example` keys.

### 13 — Conversation state machine + memory _(done)_
- `app/ai/pipeline.py`: `ConversationState` (QUALIFY→NURTURE→PROPOSE→CONFIRM→DONE),
  `derive_state()` recovers state from `lead.meeting_status`+turn+score (no new columns),
  `detect_opt_out()` (standalone-keyword + phrase matching so "stop by tomorrow" is NOT an
  opt-out), and `run()` — one LLM call per turn returning reply + extracted memory facts.
  `run()` takes an injectable `llm_complete` for testability.
- `app/services/memory.py`: Gemini embeddings (`embed_text`), fact persistence with dedup
  (`add_memory_fact`/`store_facts`), and recall (`recall`/`build_memory_context`) using
  pgvector cosine distance when available, degrading to recency when embeddings/pgvector
  are absent — so it works locally without pgvector.
- `app/services/debounce.py` + `typing_delay.py`: ported from aisha-agent. Debounce keyed on
  lead id (coalesces multi-bubble bursts, fails open for delivery / closed for typing wait).
  Typing delay is pure + transport-agnostic (typing indicator via injected callback).
- `app/services/conversations.py`: `ensure_conversation` / `set_human_takeover` helpers.
- `app/tasks/ai_tasks.py` rewritten to orchestrate: human-takeover pause → opt-out (sets
  `do_not_contact`) → debounce → memory recall → persona prompt → pipeline → persist facts →
  **`outreach_policy.gate()`** before any send → typing delay → deliver or store DRAFT.
  Escalates to Anthropic on HOT / score≥80 / PROPOSE / CONFIRM.
- `app/api/endpoints/webhook.py`: stamps a `Conversation` inbound + sets the debounce token
  and schedules the reply with a countdown.

### 14 — Conversations inbox + human takeover _(done)_
- `app/api/endpoints/conversations.py`: `GET /conversations` (summaries), `GET /{id}`
  (thread + messages), `POST /{id}/messages` (manual human reply — still passes the gate as
  `HUMAN_APPROVED`, stores role=`human`, pauses the agent to avoid double replies),
  `POST /{id}/takeover` (toggle pause). Response shapes match the existing frontend contract
  (`ConversationSummary`/`ConversationDetail` in `frontend-next`).
- Models: added `human` to the `MessageRole` enum; migration
  `b2c3d4e5f6a7_add_human_message_role` (idempotent `ALTER TYPE … ADD VALUE IF NOT EXISTS`).

### Verification
- `pytest -q` → **40 passed** (was 18; +6 persona, +7 pipeline, +6 llm-provider, +3 typing).
- `py_compile` clean on every new/changed module. Pure `ai/` + `services/` modules import
  cleanly. Full app import (celery/redis/google SDKs) deferred to the worker venv — those are
  in `requirements.txt` but not this machine's minimal `.venv` (same constraint as prior phases).
- Compliance held: every agent send routes through `outreach_policy.gate()`; the first agent
  message always carries the disclosure line (deterministic, unit-tested); opt-out sets
  `do_not_contact` immediately; human takeover halts auto-replies.

### Notes / decisions
- Gemini is the default reply + embedding model per the user's request; Anthropic is
  escalation-only. Model ids are env-overridable (no hardcoded guesses).
- State machine is columns-free (derived), so no schema churn beyond the `human` enum value.
- Manual reply auto-enables `human_takeover` (a human stepping in owns the thread), matching
  the frontend's optimistic behavior and preventing agent/human double-sends.

---

## 2026-08-07 — Clerk activated on the frontend (real auth, verified at runtime)

**Goal:** user supplied real Clerk keys and asked to turn Clerk on. It was previously scaffolded but bypassed.

**Config:** frontend `.env.local` → `NEXT_PUBLIC_AUTH_BYPASS=false` + publishable/secret keys + `NEXT_PUBLIC_CLERK_SIGN_IN/UP_URL` and fallback-redirect URLs. Backend `.env` → `CLERK_SECRET_KEY` + `CLERK_JWKS_URL=https://wise-snipe-33.clerk.accounts.dev/.well-known/jwks.json` (instance derived from the pk). Added `cryptography==43.0.3` to backend requirements (PyJWKClient needs it for RS256).

**Wiring:**
- Real `clerkMiddleware` in `src/middleware.ts` (was a hand-rolled cookie check) with `createRouteMatcher` protecting app routes; unauthenticated → 307 redirect to `/login?redirect_url=…`. Keeps a passthrough for keyless/bypass dev; kept legacy redirects.
- **Fixed the core mistake:** `<ClerkProvider>` was being mounted inside a *client* component via `require()`, so SSR children couldn't see the context (`useAuth can only be used within <ClerkProvider>` → 500 on every route). Moved ClerkProvider to the **server** root `layout.tsx`; `providers.tsx` now takes `withClerk` and renders the token bridge. Added `export const dynamic = "force-dynamic"`.
- `ClerkApiBridge` registers Clerk `getToken()` into `lib/api.ts` so `/api/v1` calls carry the session JWT (verified by the backend JWKS auth).
- Real `<SignIn/>`/`<SignUp/>` (`clerk-auth-panel.tsx`) on `/login` `/signup`; `<OrganizationSwitcher/>` + `<UserButton/>` (`clerk-org-controls.tsx`) in the sidebar (org → tenant).

**Verification (production build + `next start`):**
- `tsc` clean; `next build` clean (all routes dynamic, Proxy/Middleware present); 6 frontend unit tests pass.
- Runtime probes: `/login` → 200 serving Clerk (`clerk.browser.js`, instance `wise-snipe-33`); `/dashboard` unauth → **307 → /login**; landing → 200; **0 `useAuth` errors** in the server log.

**Note for the user:** Clerk **Organizations** must be enabled in the Clerk dashboard (and an org created) for the switcher + backend `org→tenant` to work — the backend returns 403 "No active organization" without one. The pasted secret key was placed only in git-ignored `.env` files; rotate it since it was shared in chat. Data still uses mocks (`NEXT_PUBLIC_USE_MOCKS=true`) until Phase 1/3/4 endpoints land.

---

## 2026-08-07 — Phase 2: Auth, Onboarding, Billing (features 09, 10, 11)

**Setup:** installed Clerk skills (`npx skills add clerk/skills` → 20 skills at `~/.agents/skills/`, incl. `clerk-orgs`, `clerk-billing`, `clerk-backend-api`) and consulted `clerk-orgs` for the org/role model (`org:admin`/`org:member`, bind `org_id` from the verified token, never from client).

### 09 — Clerk Organizations auth _(done)_
- Rewrote `core/auth.py`. The previous version fell back to **unverified JWT decode** (`get_unverified_claims`) — a critical hole. Now:
  - **JWKS RS256 verification** via `PyJWKClient` (cached per JWKS URL), issuer-derived or `CLERK_JWKS_URL`. Expired/invalid tokens → 401.
  - `extract_org()` supports both the v2 `o` object claim and legacy flat `org_*`, normalizing `org:admin` → `admin`.
  - `provision()` idempotently ensures User + tenant (Workspace by `clerk_org_id`) + `TenantMember`, keeping the local role synced.
  - `require_role(*roles)` RBAC dependency; `get_tenant_db` yields an **RLS-scoped** session via `tenant_context`.
  - Dev fallback (`x-user-email`/`x-org-id`) only when `ENV != prod` and Clerk is unconfigured; in prod, unconfigured auth → 500 (fail-closed).
- **RLS design fix:** moved `workspaces` + `tenant_members` OUT of the RLS table set. Auth must resolve the tenant by `clerk_org_id` *before* it knows the workspace UUID to set `app.tenant_id`; RLS-protecting the resolution tables would deadlock bootstrapping. Data tables (13) stay protected.
- Tests: `tests/test_auth_claims.py` — 5 passing (both token formats, role normalization, no-org).

### 10 — Onboarding + WhatsApp connect _(done)_
- `api/endpoints/onboarding.py`: `/configure` (agent persona/services), `/connect-number` (creates `WANumber`, **gated by plan number-limit**, RLS session), `/go-live`. All admin-only.
- **Compliance guard in code:** `/go-live` refuses to enable the agent without a non-empty `disclosure_line` and at least one connected number.

### 11 — Stripe billing _(done)_
- `services/billing.py`: plan catalog (free/starter/pro/scale), pure quota logic (`has_conversation_quota`, `can_add_number`, `conversation_quota_remaining`), usage metering (`record_message_sent`/`record_conversation`), subscription bootstrap, and Stripe webhook handling. **Stripe imported lazily** so the app/tests don't require the SDK.
- `api/endpoints/billing.py`: `GET /billing` (plan + usage + remaining), `POST /checkout` (admin), `POST /webhook` (**signature-verified**).
- Registered both routers in `api/router.py`. Added `stripe==11.1.0` to requirements.
- Tests: `tests/test_billing.py` — 4 passing.

### Verification
- Built a backend venv (fastapi, sqlalchemy, PyJWT, pgvector, psycopg, pytest) and ran the **full suite: 18 passed** (auth 5 · gate 9 · billing 4).
- `py_compile` clean on all new modules + router.
- Full DB-integration of auth/onboarding couldn't run here (schema needs the `vector` extension, absent locally); the risky logic is covered by unit tests + the earlier live RLS proof.

### Note
- A parallel frontend rebuild (F0–F4, mock-first) is progressing in `frontend-next`; these backend endpoints match its expected `/api/v1/*` contract for when it flips `NEXT_PUBLIC_USE_MOCKS=false`.
- Phase 1 (Cloud API transport) was intentionally skipped per request; still pending and needed before real end-to-end messaging.

---

## 2026-08-07 — Feature 02: multi-tenancy + RLS (Phase 0 complete)

**Goal:** Deliver real tenant isolation and the SaaS data model.

**Key decision — no risky mass-rename.** `Workspace → Tenant` literally would touch **200 references across 15 files** with no runnable app to catch breakage. Since a `Workspace` already *is* the tenant boundary (owned by a user, isolates leads/messages/groups), I delivered the actual requirement — isolation — additively, and added a `Tenant = Workspace` alias for clean new code. The literal rename is deferred as cosmetics.

**What landed:**
- `models/database.py`: 3 tenant columns on `workspaces` (`clerk_org_id`, `disclosure_line`, `default_provider`) + 9 new models: `TenantMember`, `WANumber`, `Conversation`, `MemoryFact` (pgvector, guarded import), `MediaAsset`, `MessageTemplate`, `Consent`, `Subscription`, `Usage`. `Tenant` alias.
- `app/alembic/versions/a1b2c3d4e5f6_saas_multitenancy_rls.py`: adds columns, creates the 9 tables, enables `pgcrypto` + `vector`, adds `memory_facts.embedding vector(768)` + HNSW index, and installs **RLS `tenant_isolation` policies on 15 tenant-scoped tables** keyed on `current_setting('app.tenant_id')`. `users` intentionally left un-RLS'd (cross-tenant auth).
- `ops/db/create_app_role.sql`: creates the **non-superuser `wa_app`** role. Critical because **RLS is ignored for superusers** — isolation is inert until the backend connects as `wa_app`.
- `pgvector==0.3.6` added to `requirements.txt`.

**Verification (live Postgres):**
- Ran the exact policy SQL against a throwaway DB with two tenants as the `wa_app` role:
  - Tenant A context → sees exactly its 2 leads / 1 workspace; Tenant B → its 1 lead. ✅
  - Cross-tenant INSERT under Tenant A → `new row violates row-level security policy`. ✅ (WITH CHECK works)
  - Unset context → 0 rows (fail-closed). ✅
- **Bug caught by testing:** an *empty-string* GUC threw `invalid input syntax for uuid`. Hardened the policy with `NULLIF(current_setting('app.tenant_id', true), '')` so empty **and** unset both fail closed with no error. Re-verified: empty→0, unset→0, valid→1. ✅
- Models + migration `py_compile` clean.

**Couldn't verify here:** full `alembic upgrade head` — this machine's Postgres lacks the `vector` extension (`CREATE EXTENSION vector` would fail). Migration is standard and compile-clean; run on a server with pgvector available.

---

## 2026-08-06 — Phase 0 foundation (features 01, 03, 04; 02 partial)

**Goal:** Lay the safety rails Phase 1 (Cloud API messaging) depends on — config, the compliance gate, tenant context, and the messaging abstraction — without breaking the seeded `wa-mark-2` code.

### 01 — Repo hygiene & config _(done)_
- Extended `backend/app/core/config.py`: added `ENV` (dev/prod) with `IS_PROD`, and settings for Anthropic, Clerk JWKS, WhatsApp Cloud API (base/app-secret/verify-token), Stripe, object storage, and compliance defaults. Fixed the DB URI to honor `POSTGRES_SERVER` (was hardcoded to `127.0.0.1`) and renamed DB to `wa_saas`.
- Added `backend/.env.example` documenting every key (no secrets).
- Root `.gitignore` (added earlier) keeps `.env`, venvs, `node_modules`, sessions, logs, and media out of git.
- **Why:** secrets must come from env only; prod must be able to disable dev auth fallbacks.

### 02 — Tenancy foundation _(partial)_
- Added `backend/app/core/tenancy.py`: `tenant_context(tenant_id)` context manager + `set_tenant()` that sets the Postgres `app.tenant_id` GUC via `set_config()` (parameterized — no SQL interpolation). RLS policies will key on this GUC.
- **Remaining:** rename `Workspace → Tenant`, add `tenant_id` to all domain tables + new tables (`conversations`, `memory_facts`, `media_assets`, `message_templates`, `consent`, `subscriptions`, `usage`, `wa_numbers`, `tenant_members`), write RLS policies, and an Alembic migration. Recommend the `database-schema-designer` skill here.

### 03 — Compliance gate _(done)_
- Added `backend/app/core/outreach_policy.py`: `gate(tenant, lead, kind)` returning an `OutreachDecision`. Enforces do-not-contact, agent-enabled (for auto-replies), daily quota, and the core anti-spam rule — free-form messages only within the WhatsApp 24h service window; otherwise a template is required; templates require a consent basis (prior inbound until the `consent` table lands).
- Duck-typed on `tenant`/`lead` so it's unit-testable without a DB. The current `Workspace`/`Lead` models satisfy it.
- Added `backend/tests/test_outreach_policy.py` — **9 tests, all passing** (`pytest tests/test_outreach_policy.py` → `9 passed`).
- **Why:** this is the single choke point that keeps the product from becoming spam tooling. Every send path must call it.

### 04 — MessagingProvider abstraction _(done)_
- Added `backend/app/messaging/`:
  - `base.py` — `MessagingProvider` Protocol + `SendResult` / `OutgoingMedia` dataclasses.
  - `whatsmeow.py` — `WhatsmeowProvider` wrapping the Go gateway (`/api/send`, `/api/send-image`, `/api/typing`); templates unsupported by design.
  - `cloud_api.py` — `CloudApiProvider` implementing WhatsApp Cloud API outbound (text/media/template) with error handling.
  - `factory.py` — `get_provider(number)` picks the provider per connected number.
- **Why:** the AI/CRM core must not care which transport a message uses; this is the seam that lets Cloud API become primary while whatsmeow stays for listening.

### Verification
- `pytest tests/test_outreach_policy.py -q` → **9 passed**.
- `python3 -m py_compile` on all new modules + `config.py` → clean (no syntax errors). Full import of messaging modules needs the backend venv (httpx, pydantic-settings) — deferred to when deps are installed.

### Notes / decisions
- Kept new providers **synchronous** (httpx sync) to match the existing sync Celery send task; async can be layered later if the API path needs it.
- Nothing existing was modified destructively — all Phase 0 work is additive. The `Workspace`-based code still runs; the gate maps "tenant" onto the current `Workspace`/`Lead` fields.

---

## 2026-08-06 — Project bootstrap

- Created `wa-saas/` seeded from `wa-mark-2/` source (excluded venvs, `node_modules`, Go binary, session artifacts) — ~2 MB.
- Authored the context pack in `wa-saas/context/` (9 files + `designs/`) modeled on the JobPilot format, tailored to the disclosed multi-tenant WhatsApp AI-sales SaaS.
- Added `AGENTS.md` (read-first + hard compliance boundaries), `.gitignore`, and `TASKS.md` (all-phase board).
- Documented the excluded features (group scraping, cold mass DMing, undisclosed impersonation, real-person photos) as hard boundaries.
