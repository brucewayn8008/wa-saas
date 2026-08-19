# UI Rules

Conventions for building the dashboard UI. Read alongside `ui-tokens.md` and `ui-registry.md`. Match existing patterns before inventing new ones.

---

## Layout

- **App shell:** fixed left sidebar (nav + org switcher) + main content area. Sidebar collapses to icons under 1024px.
- Content max-width `1280px`, centered, with `--space-6` gutters. Data tables may go full-width.
- Page structure: page header (title + primary action) → optional filter bar → content.
- Consistent vertical rhythm using the spacing scale — no arbitrary margins.

---

## Components

- Use the component in `ui-registry.md` if it exists — match its exact classes. Only build new when none fits, then register it.
- Cards: `--surface`, `--border`, `--radius-lg`, `--shadow-sm`. Padding `--space-6`.
- Buttons: primary (`--brand`), secondary (outline `--border-strong`), ghost, danger (`--danger`). One primary action per view.
- Badges for status: use the semantic/stage tokens. Text `--text-xs`, `--font-medium`, `--radius-full`.
- Inputs: `--surface`, `--border`, `--radius-md`; focus ring `--brand`. Always a visible label (not placeholder-as-label).

---

## States (every data view must handle all four)

1. **Loading** — skeletons that match final layout (not spinners) for lists/cards.
2. **Empty** — icon + one-line explanation + primary action (e.g. "No conversations yet — connect WhatsApp to start").
3. **Error** — inline, human-readable, with a retry affordance. Never expose raw errors.
4. **Populated** — the real content.

---

## Conversations inbox (special)

- Two-pane: thread list (left) + active thread (right). On mobile, list → thread drill-in.
- Incoming bubbles use `--bubble-in-*`, agent/AI bubbles use `--bubble-out-*`.
- **Agent (AI) messages are visibly labeled** (small "AI" tag on the bubble) — reinforces disclosure in the UI, not just the message text.
- Show delivery status (sent/delivered/read) and timestamps subtly (`--fg-subtle`, `--text-xs`).
- Human-takeover toggle is prominent at the top of the thread; when on, the composer is the human's, and a banner notes the agent is paused.

---

## Lead stages & scores

- Stage badge uses `--stage-*` tokens. Score shown as a compact 0–100 with a color-coded bar (reuse a single `ScoreBar` component).
- Never rely on color alone — pair color with a label (accessibility).

---

## Compliance surfaces (must be visible, not hidden)

- **Listening inbox** items show the original public group message and the **AI reply that was automatically sent** (or why the gate blocked it). Dismiss removes the card; there is no Approve & send step.
- Contacts on do-not-contact show a clear DNC badge; composer is disabled with an explanation.
- Template sends show the 24h-window state and whether a template is required.
- Quota/usage near limits surface a warning banner (`--warning`).

---

## Accessibility

- WCAG AA contrast for all text/background pairs (tokens are chosen to pass).
- All interactive elements keyboard-reachable; visible focus ring.
- Icons that convey meaning have `aria-label`. Status never color-only.
- Respect `prefers-reduced-motion` — disable non-essential animation.

---

## Motion

- Subtle and fast (120–200ms ease-out) for hovers, panel transitions, new-message insert.
- No decorative animation in data-dense views. Typing indicator in chat is the exception.

---

## Icons

- `lucide-react` only. Consistent stroke width. Size to the text line-height.
