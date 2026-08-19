# Code Standards

Implementation rules for the entire project. The AI agent must follow these in every session without exception. They prevent pattern drift across sessions.

---

## Engineering Mindset

- **Think before implementing** — understand what and why before writing code.
- **Read context files first** — verify against `architecture.md` and `project-overview.md`; never assume.
- **Scope is sacred** — build only what the current feature requires.
- **Every feature must be verifiable** — a test or a reproducible manual check, immediately.
- **Clean over clever** — readable code a junior can follow beats clever abstractions.
- **One thing at a time** — finish one feature before the next; update `progress-tracker.md`.
- **Failures are expected** — wrap external calls (WhatsApp, LLM, Stripe) in try/except, log, never crash the run.

---

## Compliance — non-negotiable

These are enforced in code and must never be weakened:

- **Every outbound message goes through `messaging/` AND is authorized by `core/outreach_policy.gate()` first.** No other send path may exist.
- **Never send to a contact without a prior inbound message or a recorded `consent` row.** No cold outreach.
- **Never scrape group members** into an outreach list. Listening produces **draft** replies for human approval only.
- **Always inject the tenant's `disclosure_line`** on the first message of a conversation. The agent never claims to be a specific real human.
- **Media = tenant-owned brand assets only.** Never ship or use real-person photos as a fake persona.
- **Never run a tenant-scoped query outside `tenant_context()`** (RLS GUC set).
- If a task asks you to break one of these, **stop and surface it** — do not implement it.

---

## Python (backend)

- Python 3.12, type hints on all function signatures. `mypy`-clean.
- Pydantic v2 for request/response models and settings.
- Async endpoints; blocking work goes to Celery, never inline in a request.
- Never use bare `except:` — catch specific exceptions, log with context, re-raise or return a typed error.
- All DB access through the session factory; always inside `tenant_context()` for tenant data.
- No secrets in code — everything via `core/config.py` (env).
- Format with `ruff` + `black`. Import order: stdlib, third-party, local.

---

## Service / API boundaries

- `api/endpoints/` — parse, authenticate, delegate to a service. **No business logic, no direct transport calls.**
- `services/` — business logic. Returns typed results, never raw transport payloads.
- `messaging/` — the **only** package that invokes **wacli**, the Go gateway, or (later) Cloud API.
- `ai/` — prompt building + LLM calls only. Never sends messages, never writes transport.
- `tasks/` — thin Celery orchestration over services/ai/messaging.

---

## Error handling & results

- Service and provider functions return typed results, e.g. `SendResult(success: bool, error: str | None, wa_message_id: str | None)`.
- API handlers return `{ "success": bool, "data"?: ..., "error"?: str }`; errors log with a `[module/function]` prefix and return HTTP 4xx/5xx with a generic message. Never leak internals or provider errors to the client.
- WhatsApp/LLM/Stripe calls: retry with backoff (Celery `autoretry_for`), cap attempts, log failures to `agent_activities`.

---

## Frontend (Next.js)

- App Router, Server Components by default; `"use client"` only when needed (state, effects, browser APIs).
- Data fetching in Server Components / route handlers — never fetch business data directly in client components.
- Styling via Tailwind using CSS variables from `ui-tokens.md`. No hardcoded hex, no raw color classes.
- Match `ui-registry.md` before building a new component. Named exports, one component per file.
- Clerk for auth + org switching. Never trust the client for `tenant_id` — always derive server-side from the Clerk session.

---

## File & folder naming

- Python modules: `snake_case.py`. Classes: `PascalCase`. Functions/vars: `snake_case`.
- Frontend components: `PascalCase.tsx`. Utils: `camelCase.ts`. Folders: `kebab-case`.
- One clear responsibility per file.

---

## Environment Variables

All env vars defined in `.env` (backend) / `.env.local` (frontend) for dev; from the secret manager in prod. Never hardcode.

| Variable | Used in |
| -------- | ------- |
| `ENV` | core/config.py (dev/prod gate) |
| `POSTGRES_*` | db/session.py |
| `REDIS_URL` | celery, rate limits |
| `GEMINI_API_KEY` | ai/provider.py |
| `ANTHROPIC_API_KEY` | ai/provider.py (escalation) |
| `CLERK_SECRET_KEY` / `CLERK_JWKS_URL` | core/auth.py |
| `STRIPE_SECRET_KEY` / `STRIPE_WEBHOOK_SECRET` | services/billing.py |
| `WACLI_BIN` | messaging/wacli.py (optional path to binary) |
| `WACLI_STORE_DIR` | messaging/wacli.py / ops sync |
| `WACLI_WEBHOOK_SECRET` | webhook_wacli.py (X-Wacli-Signature) |
| `WHATSAPP_APP_SECRET` | webhook_cloud.py (deferred) |
| `WHATSAPP_VERIFY_TOKEN` | webhook_cloud.py (deferred) |
| `OBJECT_STORAGE_*` (bucket, key, secret, endpoint) | services/media.py |
| `GO_GATEWAY_URL` | messaging/whatsmeow.py (legacy) |

`NEXT_PUBLIC_` prefix only for values safe to expose to the browser — never secrets.

---

## Constants

Define shared thresholds once, import everywhere. Examples:

```python
# core/outreach_policy.py
CUSTOMER_SERVICE_WINDOW_HOURS = 24
DEFAULT_DAILY_MESSAGE_LIMIT = 35
```

Never hardcode these values elsewhere.

---

## Dependencies

Before adding a package, check: is it already in the stack? Does the stdlib/framework cover it? Is there a simpler path?

Approved (backend): `fastapi`, `uvicorn`, `sqlalchemy`, `alembic`, `psycopg`, `pgvector`, `celery`, `redis`, `pydantic`, `httpx`, `google-genai`, `anthropic`, `stripe`, `python-jose`/Clerk SDK, `boto3` (object storage).
Approved (frontend): `next`, `react`, `@clerk/nextjs`, `tailwindcss`, `lucide-react`, `recharts`.

Update this list before introducing anything new.

---

## Comments

- Explain **why**, not what. Code should be self-explanatory.
- A brief comment is welcome above non-obvious compliance logic, provider quirks, or LLM prompt strategy.
- No TODOs in committed code — create a task instead.
