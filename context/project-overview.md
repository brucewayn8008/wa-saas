# Project Overview

## About the Project

**wa-saas** is a multi-tenant SaaS that gives any small business a **disclosed AI sales agent on WhatsApp**. A tenant connects their WhatsApp number, describes their business and what they sell, and the agent handles inbound conversations 24/7 — qualifying leads, answering questions, sending photos and videos of the product/service, and booking meetings — while clearly identifying itself as an AI assistant for that brand.

The agent never cold-messages strangers. It works on **inbound** interest (people who message the business), **opted-in** contacts (approved templates for re-engagement), and a **human-in-the-loop listening inbox** that surfaces public "anyone know a web dev?"-style asks from groups the tenant genuinely belongs to — the tenant approves each reply before it sends.

Everything is tracked on a dashboard: live conversations, a lead CRM, agent activity, and per-tenant usage against their plan.

---

## The Problem It Solves

Small businesses and freelancers (web-dev sellers, agencies, coaches, local services) lose leads on WhatsApp because they can't reply fast enough, at all hours, in a structured way. Hiring a sales rep is expensive; generic chatbots feel robotic and don't convert.

wa-saas gives them an always-on agent that replies instantly, sounds natural (typing pauses, message bursts, memory of what the lead said), qualifies the lead, shares media, and books the meeting — while staying fully compliant with WhatsApp's rules so their number never gets banned.

---

## Who It's For

- Freelancers and agencies selling a service (e.g. web development) who get leads via WhatsApp.
- Local SMBs (salons, clinics, tutors, real estate) fielding product/service enquiries.
- Anyone running click-to-WhatsApp ads or a "message us on WhatsApp" button who needs the other end answered well.

Each of these is a **tenant** (an organization). The SaaS is designed to serve up to ~1,000 tenants.

---

## Pages

```
/                        → Landing page (marketing)
/login                   → Auth (Clerk — email + OAuth)
/onboarding              → Create org → connect WhatsApp → configure agent → go live
/dashboard               → Overview: stats, agent status, recent activity
/conversations           → Live inbox — all WhatsApp threads, reply/takeover
/conversations/[id]      → Single thread view
/leads                   → Lead CRM — list, stage, score, filters
/leads/[id]              → Single lead detail + conversation + memory facts
/listening               → Human-approve inbox for group intent signals
/templates               → Approved message templates for opt-in re-engagement
/media                   → Tenant's brand media library (photos/videos)
/settings                → Agent persona, services, business hours, disclosure
/settings/team           → Members & roles (owner/admin/agent)
/billing                 → Plan, usage, invoices (Stripe)
/admin                   → Internal super-admin (staff only) — tenants, health
```

---

## Navigation

Left sidebar (app is data-dense — sidebar beats top nav here):

```
Dashboard · Conversations · Leads · Listening · Templates · Media · Settings · Billing
```

Org switcher at the top of the sidebar (Clerk Organizations). `/admin` is not in tenant nav.

---

## Core User Flow

### Onboarding

1. User signs up (Clerk) → creates an **organization** (the tenant).
2. **Connect WhatsApp:**
   - **wacli path (current / near-term):** scan a QR via `wacli auth` to link the tenant's number as a WhatsApp Web device. Inbound via `wacli sync --follow --webhook`; outbound via `wacli send`.
   - **Cloud API path (deferred):** WhatsApp Embedded Signup → tenant WABA / phone number. Preferred later for multi-tenant scale and Meta templates.
3. **Configure the agent:** brand name, what they sell (services), tone, offer, booking link, business hours, and the **AI disclosure line** (mandatory).
4. Toggle the agent live. Dashboard shows connection status.

### Inbound Conversation (the core loop)

- A prospect messages the tenant's WhatsApp number.
- Message is received → contact + conversation created/updated → lead scored.
- The agent (LLM) drafts a reply grounded in the tenant's persona and the conversation memory.
- Human-like delivery: reading delay, typing indicator, 1–3 short bubbles.
- Within an **active inbound conversation**, the agent may **auto-send** (subject to the compliance gate). For outbound-initiated messages it defaults to **draft → human approve → send**.
- Agent qualifies (HOT/WARM/COLD), remembers stated facts (budget, timeline, service wanted), and after enough signal proposes a meeting / booking link.

### Human-in-the-loop Listening

- On groups the tenant is a real member of, the system detects intent signals (keyword + embedding match, e.g. "need a website", "looking for a web dev").
- These surface in `/listening` as **leads with the original public message + a one-tap AI-drafted reply**.
- **A human approves and sends.** No auto-DM, no scraping members, no mass send.

### Opt-in Re-engagement

- **Deferred until Cloud API:** Meta-approved templates. On the wacli path, outside-24h free-form stays blocked by the compliance gate.

### Media

- The agent can send the tenant's **own** approved photos/videos from the media library (e.g. portfolio shots, product pics) when relevant.
- Inbound media from prospects is received and stored against the conversation.

### Billing

- Plans gate connected numbers, monthly conversation quota, media storage, and seats.
- Usage is metered; quotas enforced by the compliance/send gate.

---

## Data Architecture

### Tenant isolation

- Every domain row carries `tenant_id`. Postgres **Row-Level Security** + app-layer scoping guarantee one tenant never reads another's data.

### Conversation memory

- Facts the lead states (service, budget, timeline) are stored as `memory_facts` and injected into the prompt so the agent stays consistent and contextual. Embeddings (pgvector) power semantic recall + intent matching.

### Consent & compliance

- `consent` records (opt-in source + timestamp), a global `do_not_contact` list, and 24h-window tracking gate every outbound message.

---

## Features In Scope

- Landing page, Clerk auth, org-based multi-tenancy (Clerk Organizations).
- Onboarding with WhatsApp connect (**wacli QR** now; Cloud API Embedded Signup later).
- Disclosed AI sales agent: inbound auto-reply within the compliance gate.
- Human-like delivery (debounce, typing delay, message-burst splitting).
- Lead CRM: scoring, stages, filters, memory facts.
- Live conversations inbox with human takeover.
- Media library — send tenant's own photos/videos; receive inbound media.
- Human-in-the-loop listening inbox for group intent signals.
- Opt-in template re-engagement — **deferred** (Cloud API templates).
- Per-tenant persona/services config with mandatory AI disclosure.
- Stripe billing: plans, usage metering, quota enforcement.
- Roles (owner/admin/agent), team management.
- Observability: activity log, health, metrics.
- Super-admin console for staff.

---

## Features Out of Scope (and why)

- **Automated scraping of group members into an outreach list** — spam, WhatsApp ToS violation, ban + legal risk.
- **Automated mass/cold DMing of people who never contacted the tenant** — same.
- **Undisclosed human-impersonation** (agent pretending to be a specific real person) — deception, legal exposure.
- **Reusing the `aisha-agent` romantic persona or its real-person photos** — non-consensual likeness, impersonation/IP liability.
- **Multi-tenant automated outreach over the unofficial WhatsApp Web protocol (wacli/whatsmeow)** — bans at scale; wacli is for single-number / low-scale inbound + human-approved listening until Cloud API.

These are hard boundaries. The compliant replacements (inbound, opt-in templates, human-approved listening) deliver the same business outcome.

---

## Target User Success

A freelancer connects their WhatsApp, describes their web-dev service, and within 15 minutes the agent is answering inbound enquiries, sharing portfolio pics, qualifying leads, and booking calls — without the freelancer touching their phone, and without any risk to their number.

---

## Success Criteria

- A tenant can sign up, connect WhatsApp, configure the agent, and go live in under 15 minutes.
- Inbound messages get a natural, on-brand, disclosed reply within seconds.
- The agent qualifies leads and books meetings with sensible reasoning.
- Media (photos/videos) sends and receives correctly.
- Two tenants are fully isolated — no cross-tenant data access (proven by tests).
- No message is ever sent without inbound/opt-in; the compliance gate is provably enforced.
- Billing plans meter usage and enforce quotas correctly.
- The system stays healthy under load simulating hundreds of tenants.
