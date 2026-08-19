---
name: wa-saas-tenancy-rls
description: >-
  Multi-tenant isolation rules for wa-saas — Postgres Row-Level Security keyed on
  the app.tenant_id GUC and the tenant_context() helper. Use whenever writing DB
  queries, endpoints, services, Celery tasks, or migrations that touch
  tenant-scoped data (leads, conversations, messages, media, memory_facts, usage,
  etc.). Prevents cross-tenant data leaks.
---

# wa-saas — Tenancy & RLS

Isolation is a survival feature: one tenant must never read or write another's data. Two layers enforce it — Postgres **RLS** and app-layer scoping. Use both.

## The core rule
**Every tenant-scoped query runs inside `core/tenancy.tenant_context()`** (or the `get_tenant_db` dependency), which sets `SET LOCAL app.tenant_id = '<uuid>'` on the session. Never run a bare tenant query.

```python
from app.core.tenancy import tenant_context

with tenant_context(tenant_id) as db:
    leads = db.query(Lead).filter(...).all()   # RLS also scopes this
```

- RLS policy on each tenant table: `USING (tenant_id = current_setting('app.tenant_id')::uuid)`.
- App-layer `.filter(tenant_id == ...)` too — defense in depth.
- **Fails closed:** no GUC set → no rows. Never "fix" a missing-rows bug by removing the GUC or querying as superuser.

## Where tenant_id comes from
Clerk JWT → `core/auth.py` verifies (JWKS) → extracts `sub` (Clerk **user** id; free plan = user→tenant, not org) → resolves/provisions the `Tenant` (the `workspaces` table; `Tenant` is an alias). Never trust a `tenant_id` sent from the client.

## Gotchas specific to this repo
- **RLS is inert unless** the app connects as a NON-superuser role. Local dev often runs as superuser → RLS silently off. For real isolation use `ops/db/create_app_role.sql` + `POSTGRES_USER=wa_app`.
- `Workspace` is kept as the tenant table (rename deferred as risky cosmetics). Don't rename it as part of feature work.
- **PgBouncer:** `SET LOCAL` must be transaction-scoped; verify the GUC doesn't leak across pooled transactions.
- `/admin` staff role bypasses RLS **explicitly** and is audit-logged — never a general bypass.
- Celery tasks are tenant work too: open `tenant_context()` inside the task; don't pass ORM objects across the task boundary, pass ids.

## New tenant table checklist
- [ ] `tenant_id uuid` FK + index.
- [ ] RLS policy added in the migration (mirror existing tables).
- [ ] All access goes through `tenant_context()`.
- [ ] A test proves tenant A cannot see tenant B's rows (via API and via wrong/absent GUC).
