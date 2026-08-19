# AGENTS.md

This is **wa-saas** — a multi-tenant, **disclosed** AI WhatsApp sales-agent SaaS. Any AI agent working in this repo must read the context pack in `context/` **before** writing any code, every session.

## Read first, in this order

1. `context/project-overview.md` — what we're building and why, pages, flows, scope.
2. `context/architecture.md` — stack, folder boundaries, DB schema, patterns, **invariants**.
3. `context/code-standards.md` — conventions the agent must never violate.
4. `context/build-plan.md` — the phased feature list. Build one feature fully before the next.
5. `context/progress-tracker.md` — what's done, in progress, next. **Update after every feature.**

`ui-tokens.md`, `ui-rules.md`, `ui-registry.md`, `library-docs.md` are read as needed when touching UI or third-party libraries.

## Non-negotiable boundaries (compliance)

This product is legitimate B2B sales automation. It must **never** become spam or impersonation tooling. These are hard invariants, enforced in code (`app/core/outreach_policy.py`):

- **No message is ever sent to a contact without a prior inbound message or a recorded opt-in.** No cold outreach.
- **No scraping of WhatsApp group members** into outreach lists. Group *listening* auto-detects public intent in groups the tenant already belongs to and **auto-replies to the lead** only when `outreach_policy.gate()` allows (inbound/opt-in basis, 24h window, DNC, quotas). No member scraping.
- **The agent always discloses it is an AI** for the tenant's brand. It never claims to be a specific real human.
- **No real-person photos** as a fake persona. Media is the tenant's own approved brand assets only.
- Every send passes the `outreach_policy` gate (opt-in, 24h window, do-not-contact, rate limits).

If a request conflicts with these, stop and surface it — do not implement it.

## How to run (dev)

See `ops/` scripts and `context/architecture.md` → "How to run". Backend (FastAPI), Celery worker + beat, Next.js frontend, Postgres + Redis, and **wacli** (`auth` + `sync --follow --webhook`) as the near-term WhatsApp transport. Cloud API is deferred — see `TASKS.md` Phase 1.
