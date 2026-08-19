# Progress Tracker

Update this file after every completed feature. Any AI agent reading this should immediately know what is done, what is in progress, and what is next.

---

## Current Status

**Phase:** Phase 0–3 COMPLETE · Phase 1 · 07 Media library DONE · **Prompt 03 agent media outbound DONE** · Phase 4 · 15 Leads CRM DONE · **16 Listening inbox (auto-reply) DONE**. Cloud API deferred.
**Last completed:** **16 / 16b Listening inbox** — group intent → gated auto-reply + live `/listening` feed (dismiss only). Suite **111** green; `npm run ci` green.
**Next:** Prompt pack `06` / Phase 4 · 17 Inbound capture, or continue prompt pack order.

**⚠ Deploy note:** RLS is inert unless the app connects as a NON-superuser role — run `ops/db/create_app_role.sql` and set `POSTGRES_USER=wa_app`. The local Postgres lacks the `vector` extension, so a full `alembic upgrade` needs `CREATE EXTENSION vector` available on the target server.

**✅ Local/ops (2026-08-09):** wa-saas is self-contained (`wa-saas/go-gateway` added; `ops/*.sh` repointed off `wa-mark-2`; everything else archived to `old/`). Local dev reuses the `wa_mark2` DB; `create_all` builds SaaS tables on startup (alembic stays at `6e8e338c61d9`, RLS skipped locally). Enum: `HUMAN` added to `messagerole`. `pgvector` absent locally → memory falls back to recency recall.

---

## Progress

### Phase 0 — Foundation & Safety Rails
- [x] 01 Repo hygiene & config
- [x] 02 Tenancy foundation — RLS on 15 tables + migration + app-role; isolation verified live
- [x] 03 Compliance gate (outreach_policy.py) — 9 unit tests passing
- [x] 04 MessagingProvider abstraction

### Phase 1 — Messaging Layer (wacli first)
- [x] 05 wacli provider — outbound
- [x] 06 wacli inbound webhook
- [x] 07 Media service (wacli path) — `services/media.py`, `/media` API, `whatsapp.send_media`, `test_media.py`. **Agent auto-select closed by prompt 03.**
- [ ] 08 Templates — **deferred** until Cloud API
- [ ] 05b/06b Cloud API outbound + webhook — **deferred**

### Phase 2 — Auth, Tenancy & Billing
- [x] 09 Clerk auth — JWKS verify; **user→tenant** (Clerk free plan; A1/A2). Tracker previously said org→tenant — superseded.
- [x] 10 Onboarding + WhatsApp connect — configure / connect-number / go-live
- [x] 11 Stripe billing — plans, quota, usage, webhook, 4 tests

### Phase 3 — AI Sales Agent
- [x] 12 LLM provider abstraction + persona/disclosure — Gemini default + Anthropic escalation, deterministic disclosure
- [x] 13 Conversation state machine + memory — qualify→nurture→propose→confirm, pgvector recall, debounce, typing, opt-out
- [x] 14 Conversations inbox + human takeover — live threads, gated manual reply, pause agent

### Phase 4 — Compliant Lead Sourcing
- [x] 15 Leads CRM (**backend + frontend**) — list/filter/pagination, detail (memory_facts + conversation thread + consent), PATCH status/intent/DNC through `services/crm.py` + `get_tenant_db`. Frontend `/leads` live (mocks gated off for this route).
- [x] 16 Listening inbox (**auto-reply**) — `ListeningLead` + keyword/semantic match; gated auto-send via existing AI pipeline; `GET/DELETE /api/v1/listening`. Frontend `/listening` live read-only feed + dismiss.
- [ ] 17 Inbound capture (widget / click-to-WhatsApp / QR) — **not started**

### Phase 5 — Scale & Reliability
- [ ] 18 Queues, pooling, partitioning — **not started** (single Celery queue; beat schedules exist)
- [ ] 19 Observability — **not started** (`/health` is `{status: ok}` only)
- [ ] 20 Deploy — **not started** (ops scripts exist; full Docker/CI/CD/backup runbook incomplete)

---

## Decisions Made During Build

- Foundation: build on `wa-mark-2` (sales-oriented), NOT `aisha-agent` (romance-deception base). Port only the good conversation engineering from aisha-agent.
- Stack kept polyglot (Python + Go + Next.js). Location: new dir `wa-saas/` seeded from wa-mark-2.
- DB: stay on Postgres; add pgvector, Redis, object storage. No engine switch.
- `Workspace` kept as the tenant table (`Tenant` alias); isolation via Postgres RLS. Literal rename deferred.
- Auth: Clerk **free plan → tenant = Clerk user (`sub`)**, not Organization (A1/A2). No org switcher.
- Excluded (hard boundary): group-member scraping, cold mass DMing, undisclosed impersonation, real-person photos, multi-tenant mass outreach over unofficial WhatsApp Web protocol.
- **Transport (2026-08):** Near-term primary = **wacli** (linked-device CLI). WhatsApp Cloud API deferred. Still every send through `outreach_policy` + `MessagingProvider`.
- **Listening (2026-08-20):** Auto-reply authorized (YOLO). Group intent still never scrapes members; every send still passes `outreach_policy.gate()`. `/listening` is a review/dismiss feed, not an approve queue.

---

## Frontend

**Status:** F0–F5 complete (mock-first dashboard in `frontend-next`). Screens exist; data still mocks by default.

- [x] F0 Design system — tokens in `globals.css`, shadcn-style primitives, AppShell, deps (Query/RHF/Zod/sonner/nuqs)
- [x] F1 Shell & auth — new nav IA, marketing `/`, login/signup, onboarding, legacy redirects
- [x] F2 Mock screens — Dashboard, Conversations (+[id]), Leads (+[id]), Listening, Templates, Media, Settings/Team, Billing, Admin stub
- [x] F3 API layer — `lib/services.ts` + hooks; `NEXT_PUBLIC_USE_MOCKS=true` default (`!== "false"`); `/api/v1/*` paths ready
- [x] F4 Polish — Vitest unit tests, Playwright smoke, `typecheck`/`ci` scripts, `ui-registry.md` updated
- [x] F5 Clerk activated — `clerkMiddleware`, ClerkProvider, `<SignIn>`/`<SignUp>`, `<UserButton>` (org switcher removed per A2). Unauth protected routes → 307 `/login`.

**Mock-only (confirmed 2026-08-20):** `/dashboard`, `/conversations`, `/media`, `/billing`, `/settings` route through hooks → `USE_MOCKS` mock data. **`/leads` and `/listening` are live** (force real API even when `NEXT_PUBLIC_USE_MOCKS=true`). No `.env.local` in repo; defaults keep mocks on elsewhere. Frontend go-live (F6) still open.

**Next frontend:** F6 — flip `NEXT_PUBLIC_USE_MOCKS=false`, wacli-QR onboarding, wire remaining screens to real API.

---

## Notes

- Frontend uses mocks by default (`NEXT_PUBLIC_USE_MOCKS` unset/`true`). Dev auth bypass when Clerk key absent or `NEXT_PUBLIC_AUTH_BYPASS=true`.
- Tracker historically claimed **40** then **65** backend tests; **true count as of 2026-08-20 (prompt 16) is 111**.

---

## Feature 03 — Agent media outbound (2026-08-20)

Shipped:
- `services/media.catalogue_for_agent` — tenant brand assets only (excludes `inbound` tag); compact `{id, type, tags, caption}` for the LLM.
- `ai/pipeline.py` — catalogue in prompt; structured optional `media_asset_id`; invented/foreign ids dropped (text-only, no crash).
- `tasks/ai_tasks.enqueue_agent_outbound` — after `gate()`, sends via `send_whatsapp_media` (caption = reply) or `send_whatsapp_message`; blocked gate → neither path.
- `messages.media_asset_id` column (migration `g7b8c9d0e1f2`); inbound wacli ingest links received media onto the Message.
- Tests: `test_pipeline` media cases + `test_agent_media.py` (valid → send_media; invalid → text; gate block → no send; catalogue filters inbound). Suite **103** green.

**Still open (baseline):** `POST /media/{id}/send` and several MVP approve paths remain ungated — not fixed in this prompt (agent auto-reply path is gated).

## Feature 15 — Leads CRM backend (2026-08-20)

Shipped: `services/crm.py` list/filter/sort/paginate + detail (memory_facts + conversation thread + consent) + PATCH (status / intent_label / do_not_contact → `agent_activities`). Endpoints use `get_tenant_db`. Tests: `tests/test_leads_crm.py` (8). Suite **90** green. Also repaired legacy `memory_facts` table (migrations `e5f6a7b8c9d0`, `f6a7b8c9d0e1`) so SaaS columns match the model.

## Feature 15b — Leads CRM frontend (2026-08-20)

Shipped: `/leads` RSC shell + client `LeadsBoard` (nuqs filters → `GET /api/v1/leads`); `/leads/[id]` detail with memory facts, `ChatBubble` thread, optimistic status/DNC via `PATCH /api/v1/leads/{id}`. `fetchLeads` / `fetchLead` / `patchLead` always hit the live API (mocks gated off for this route). Mapper: `lib/leads-map.ts`. `npm run ci` green (also cleared prior lint blockers on onboarding/landing/relay).

## Feature 16 / 16b — Listening inbox auto-reply (2026-08-20)

Shipped:
- `ListeningLead` model + migration `h8c9d0e1f2a3` + `services/listening.py` (keyword + semantic match, record/finalize/list/dismiss).
- wacli group ingest records a ListeningLead on intent match; `generate_ai_reply` finalizes with sent/blocked after the gate.
- API: `GET /api/v1/listening`, `DELETE /api/v1/listening/{id}` (soft dismiss). No approve endpoint.
- Frontend: `/listening` live feed (auto-replied cards, dismiss only); empty = "Nothing to review"; error → toast. Mocks gated off for this route.
- Compliance docs updated: listening is auto-reply (still gated; still no member scraping).
- Tests: `tests/test_listening.py` (8). Backend suite **111** green; frontend `npm run ci` green.
