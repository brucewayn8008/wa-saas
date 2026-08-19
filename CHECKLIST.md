# wa-saas — Build Checklist

Work through these in order. Mark `[x]` when done. Each item is one focused session.

---

## Auth Fix — Clerk Free Plan (no Orgs)

- [x] **A1 — Swap org→tenant for user→tenant in backend**
  - `core/auth.py`: extract `sub` (Clerk user ID) instead of `org_id`
  - `workspaces` table: replace `clerk_org_id` with `clerk_user_id` (migration)
  - `tenant_members` table: simplify — owner is the user, no org switcher needed
  - Remove `require_role` org-RBAC; replace with simple `owner` check per tenant
  - Dev bypass still works (`ENV=dev`)
  - **Verify:** JWT with user `sub` resolves correct tenant; cross-user isolation still holds

- [x] **A2 — Fix frontend auth flow**
  - Remove `<OrganizationSwitcher>` / `<UserButton>` org controls from sidebar
  - Replace with plain Clerk `<UserButton>` (profile/sign-out only)
  - Onboarding: skip "create organization" step — tenant auto-created on first login
  - `NEXT_PUBLIC_AUTH_BYPASS=false`, `NEXT_PUBLIC_USE_MOCKS=true` still while backend wires up
  - **Verify:** sign up → lands on onboarding → tenant auto-provisioned in backend

---

## Phase 1 Completion

- [x] **07 — Media Service (wacli path)**
  - `services/media.py`: upload to S3/R2, signed URLs, `media_assets` CRUD
  - `api/endpoints/media.py`: `POST /media/upload`, `GET /media`, `DELETE /media/:id`
  - Outbound: agent picks relevant asset → `wacli send file` via `WacliProvider.send_media`
  - Inbound: store media received from wacli sync/webhook against conversation
  - **Verify:** upload image → agent sends it via wacli; inbound media stored on conversation

---

## Frontend — Connect to Real Backend

- [ ] **F6 — Flip mocks off + wire onboarding to wacli QR**
  - Set `NEXT_PUBLIC_USE_MOCKS=false` in `.env.local`
  - Onboarding connect-number step: show wacli QR scan UI (not Cloud API Embedded Signup)
  - `GET /onboarding/qr` → poll until `status = CONNECTED`
  - Wire `lib/services.ts` hooks to real `/api/v1/*` endpoints (conversations, leads, dashboard)
  - `NEXT_PUBLIC_API_URL=http://localhost:8000` confirmed in env
  - **Verify:** sign up → onboarding → scan QR → dashboard shows real data

---

## Phase 4 — Lead Sourcing

- [x] **15 — Leads CRM (backend)**
  - `api/endpoints/leads.py`: `GET /leads` (filter: status, intent_label, source, min_score, do_not_contact, search; sort; limit/offset + total), `GET /leads/:id` (detail + memory_facts + conversation thread + consent)
  - `PATCH /leads/:id` (manual status / intent_label / do_not_contact); DNC honored by gate (proven in tests)
  - Logic in `services/crm.py`; sessions via `get_tenant_db`
  - **Verify:** filters + pagination total; cross-tenant 404; PATCH DNC → gate blocks — suite green (90)

- [ ] **15b — Leads CRM (frontend wire-up)**
  - Connect `/leads` page hooks to real API (currently mock)
  - Connect `/leads/[id]` detail page
  - **Verify:** real leads from wacli inbound visible and filterable in UI

- [x] **16 — Listening Inbox (backend, auto-reply)**
  - Group chat messages from wacli sync/webhook → keyword + embedding intent match
  - Create `ListeningLead`; AI reply auto-sent when `outreach_policy.gate()` allows
  - `GET /listening` (processed leads), `DELETE /listening/:id` (soft dismiss)
  - **Verify:** matching group message → auto-send when gated; dismiss hides; suite green

- [x] **16b — Listening Inbox (frontend wire-up)**
  - Connect `/listening` page to real API (read-only feed + dismiss)
  - **Verify:** processed lead appears with automated reply; dismiss removes it

- [ ] **17 — Inbound Capture**
  - QR link / click-to-WhatsApp URL generator per tenant
  - Widget embed snippet (iframe or JS) that routes to tenant's WhatsApp with pre-filled message
  - Inbound from widget records `consent.source = widget` on the lead
  - `GET /capture/link` → returns wa.me link + QR code image
  - **Verify:** widget-initiated chat creates a consented lead with source=widget

---

## Phase 5 — Scale & Reliability

- [ ] **18 — Queues & Pooling**
  - Separate Celery queues: `ai`, `send`, `media`, `beat`
  - PgBouncer for connection pooling
  - Partition `messages` table by `(tenant_id, created_at)`
  - Per-tenant rate buckets in Redis
  - **Verify:** load test (k6) with multiple tenants shows no starvation

- [ ] **19 — Observability**
  - Structured JSON logging with `tenant_id` on every log line
  - Prometheus metrics: webhook latency, reply latency, send success/fail
  - Sentry error tracking (backend + frontend)
  - `/health` endpoint with DB + Redis + wacli status
  - Alert on webhook failure streak / send failure rate
  - **Verify:** metrics visible; forced webhook failure triggers alert

- [ ] **20 — Deploy**
  - Dockerfiles for backend, worker, beat, frontend
  - `docker-compose.yml` for full local stack (postgres+pgvector, redis, backend, worker, frontend)
  - CI/CD: lint → typecheck → test → build → deploy
  - DB backup script + restore runbook
  - **Verify:** `docker compose up` boots clean; restore from backup succeeds

---

## Notes

- Clerk free plan: tenant = Clerk user (`sub`), not org. No org switcher, no RBAC tiers.
- wacli is the active transport. Cloud API stays deferred.
- `NEXT_PUBLIC_USE_MOCKS=true` until F6 is done.
- Every send must pass `outreach_policy.gate()`. No exceptions.
- Never cold-message. Never scrape group members. Always disclose AI.
