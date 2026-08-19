---
name: wa-saas-overview
description: >-
  Orientation and working rules for the wa-saas repo (multi-tenant, disclosed AI
  WhatsApp sales-agent SaaS). Use at the start of any task in this repo, when
  deciding where code belongs, or when unsure which convention applies. Points to
  the context pack and the compliance/tenancy/messaging/ai skills.
---

# wa-saas — Orientation

**wa-saas** is a multi-tenant SaaS giving small businesses a *disclosed* AI sales agent on WhatsApp. Stack: FastAPI (Python 3.12) + Celery/Redis + Postgres/pgvector (RLS) + Next.js + Clerk + Stripe + Gemini/Anthropic. Transport is **wacli** (Cloud API deferred).

## Read first, every session
1. `AGENTS.md` (repo root) — the non-negotiable boundaries.
2. `context/project-overview.md`, `context/architecture.md`, `context/code-standards.md`.
3. `context/progress-tracker.md` — what's done / next. **Update it after every feature.**

Never assume the state — grep the code and reconcile against `progress-tracker.md`.

## Where code goes (folder boundaries — enforce these)
| Folder | Owns | Never |
| --- | --- | --- |
| `api/endpoints/` | parse + auth + delegate to a service | business logic, transport calls |
| `services/` | business logic, typed results | HTTP, raw transport payloads |
| `messaging/` | the ONLY place that calls wacli / gateway / Cloud API | business logic |
| `ai/` | prompt building + LLM calls | sending messages, writing transport |
| `tasks/` | thin Celery orchestration | fat logic |
| `core/` | config, auth, tenancy, `outreach_policy` gate | — |
| `models/` | SQLAlchemy models only | — |

## The rules that matter most (see the dedicated skills)
- **Compliance:** every send passes `core/outreach_policy.gate()` + a `MessagingProvider`. No cold outreach, always disclose AI, no group-member scraping, tenant-owned media only. → `wa-saas-compliance`
- **Tenancy:** every tenant-scoped query runs inside `tenant_context()` (RLS GUC). → `wa-saas-tenancy-rls`
- **Transport:** wacli is active; Cloud API is stubbed/deferred. → `wa-saas-messaging`
- **AI agent:** persona + mandatory disclosure, qualify→nurture→propose→confirm, memory + debounce + typing. → `wa-saas-ai-agent`
- **Auth:** Clerk free plan → tenant = Clerk **user** (`sub`), not org. → the `clerk` skill.

## How to work (Definition of Done)
Feature works · compliance invariants provably intact · a test/repro added and the suite green (`cd backend && pytest`; `cd frontend-next && npm run ci`) · `progress-tracker.md`/`TASKS.md`/`CHECKLIST.md` updated · no secrets committed · no new lint/type errors.

If a request conflicts with the compliance boundaries, **stop and surface it — do not implement it.**
