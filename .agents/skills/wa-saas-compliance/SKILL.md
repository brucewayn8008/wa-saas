---
name: wa-saas-compliance
description: >-
  The non-negotiable WhatsApp compliance rules for wa-saas, enforced in
  core/outreach_policy.py. Use whenever code sends a WhatsApp message, adds an
  outreach/reply/broadcast path, touches consent/opt-in/do-not-contact, handles
  the 24h window, media sending, or listening/group features. Prevents spam,
  impersonation, and number bans.
---

# wa-saas — Compliance Gate (hard invariants)

This product is legitimate B2B sales automation. It must **never** become spam or impersonation tooling. These are enforced in `core/outreach_policy.py` and must never be weakened.

## The invariants
1. **Every outbound message passes `outreach_policy.gate()` AND goes through a `MessagingProvider`.** There is no other send path — not from `ai/`, not from an endpoint, not a "quick" `httpx` call.
2. **No send without a prior inbound message or a recorded `consent` row.** No cold outreach, ever.
3. **Always inject the tenant's `disclosure_line`** on the first message of a conversation. The agent never claims to be a specific real human.
4. **No scraping of group members** into outreach. Listening auto-detects public intent in groups the tenant belongs to and **auto-replies** only when `outreach_policy.gate()` allows.
5. **Media = the tenant's own approved brand assets only** (from `media_assets`). No real-person photos as a fake persona.
6. **Quotas enforced in the gate.** Over-quota tenants cannot send.
7. **Templates are the only way to message outside the 24h window** — and templates are a Cloud API concept, currently **deferred**. On wacli, outside-24h free-form stays blocked.
8. **Webhooks are signature-verified** before processing (wacli `X-Wacli-Signature`, Stripe, Clerk).

## What the gate checks (`gate(tenant, lead, kind)`)
agent enabled · inbound-or-opt-in basis · 24h customer-service window · do-not-contact list · per-tenant + per-number rate limit · quota. A violation is a **hard block**, surfaced cleanly (log to `agent_activities`), never a crash.

## When you add ANY send path, verify
- [ ] It calls `outreach_policy.gate(...)` and only sends if allowed.
- [ ] It sends via `messaging/factory.get_provider(...)`, not a direct transport call.
- [ ] A new-conversation first message contains the `disclosure_line`.
- [ ] Media sent is a `media_assets` row belonging to this tenant.
- [ ] Opt-out keyword ("stop") sets `do_not_contact` and future sends are blocked.
- [ ] A test proves the block cases (no consent, DNC, over quota, outside 24h) actually block.

## Anti-patterns (reject on sight)
- Calling `WacliProvider`/gateway directly from `ai/` or an endpoint.
- Building a contact list from group membership.
- "Temporarily" bypassing the gate for a demo or a test fixture.
- Hardcoding thresholds — use the constants in `outreach_policy.py` (e.g. `CUSTOMER_SERVICE_WINDOW_HOURS`, `DEFAULT_DAILY_MESSAGE_LIMIT`).

If a task asks you to break one of these, **stop and surface it.**
