# UI Registry

Living document. Updated after every component is built. Read this before building any new component — match existing patterns exactly before inventing new ones.

---

## How to Use

Before building any component:

1. Check if a similar component already exists here.
2. If yes — match its exact classes and props.
3. If no — build it following `ui-rules.md` and `ui-tokens.md`, then add it here.

After building a component, add: name, file path, purpose, and the exact token classes used.

---

## Layout

| Component | Path | Purpose | Token classes |
| --------- | ---- | ------- | ------------- |
| `AppShell` | `components/layout/app-shell.tsx` | Sidebar + header + content max 1280 | `bg-[var(--bg)]`, `border-[var(--border)]`, `bg-[var(--surface)]` |
| `Sidebar` | `components/layout/sidebar.tsx` | Primary nav + org label | Active: `bg-[var(--brand)] text-[var(--brand-fg)]`; idle: `text-[var(--fg-muted)] hover:bg-[var(--surface-2)]` |
| `MobileNav` | `components/layout/sidebar.tsx` | Horizontal nav &lt; lg | Same brand active styles |
| `PageHeader` | `components/layout/page-header.tsx` | Title + description + actions | `text-[var(--text-xl)]`, `text-[var(--fg-muted)]` |

---

## UI primitives

| Component | Path | Purpose | Token classes |
| --------- | ---- | ------- | ------------- |
| `Button` | `components/ui/button.tsx` | primary/secondary/ghost/danger/outline | primary: `bg-[var(--brand)] text-[var(--brand-fg)] hover:bg-[var(--brand-hover)]`; radius `rounded-[var(--radius-md)]` |
| `Badge` | `components/ui/badge.tsx` | status chips | brand/success/warning/danger/info subtles + `rounded-[var(--radius-full)]` |
| `Card` | `components/ui/card.tsx` | surface container | `bg-[var(--surface)] border-[var(--border)] rounded-[var(--radius-lg)] shadow-[var(--shadow-sm)]` |
| `Input` / `Textarea` / `Label` | `components/ui/*` | form primitives | `border-[var(--border)]`, focus `ring-[var(--brand)]` |
| `Switch` | `components/ui/switch.tsx` | toggles | checked `bg-[var(--brand)]` |
| `Skeleton` | `components/ui/skeleton.tsx` | loading placeholders | `bg-[var(--surface-2)]` |
| `EmptyState` | `components/ui/empty-state.tsx` | empty/error recovery | dashed `border-[var(--border)]`, icon on `bg-[var(--brand-subtle)]` |
| `Separator` | `components/ui/separator.tsx` | dividers | `bg-[var(--border)]` |

---

## Domain

| Component | Path | Purpose | Token classes |
| --------- | ---- | ------- | ------------- |
| `StatCard` | `components/dashboard/stat-card.tsx` | dashboard KPI | icon on `bg-[var(--brand-subtle)] text-[var(--brand)]` |
| `UsageMeter` | `components/billing/usage-meter.tsx` | quota bar | fill `bg-[var(--brand)]` or near-limit `bg-[var(--warning)]` |
| `ScoreBar` | `components/leads/score-bar.tsx` | 0–100 score | HOT/WARM/COLD stage colors |
| `StageBadge` | `components/leads/stage-badge.tsx` | HOT/WARM/COLD/… | `--stage-*` + subtle backgrounds |
| `LeadsBoard` | `components/leads/leads-board.tsx` | Live list filters (nuqs) + table | chip active `bg-[var(--brand)]` |
| `LeadsTable` | `components/leads/leads-table.tsx` | Leads CRM table states | card/surface tokens |
| `ThreadList` | `components/conversations/thread-list.tsx` | inbox left pane | active `bg-[var(--brand-subtle)]` |
| `ChatBubble` | `components/conversations/chat-bubble.tsx` | in/out + AI label | `--bubble-in-*` / `--bubble-out-*` |
| `Composer` | `components/conversations/composer.tsx` | reply + DNC/24h | DNC uses `--danger-subtle` |
| `ApprovalCard` | `components/listening/approval-card.tsx` | auto-reply feed card + Dismiss | success badge for sent; warning when gate-blocked |
| `ListeningFeed` | `components/listening/listening-feed.tsx` | live GET /listening + dismiss | skeletons / empty / toast on error |
| `MediaGrid` | `components/media/media-grid.tsx` | brand asset grid | card surface tokens |

---

## Components

See tables above — registered as of frontend F0–F2 rebuild.
