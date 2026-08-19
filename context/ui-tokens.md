# UI Tokens

Single source of truth for design tokens. Every component uses these CSS variables — never hardcoded hex values, never raw Tailwind color classes. Defined once in `frontend-next/src/app/globals.css` under `:root` and `.dark`.

---

## Brand

WhatsApp-adjacent but distinct (avoid cloning WhatsApp's exact green to prevent brand confusion). Trustworthy, calm, business-grade.

```css
:root {
  /* Brand */
  --brand:            #128C4B;   /* primary — deep confident green */
  --brand-hover:      #0E7A41;
  --brand-fg:         #FFFFFF;   /* text on brand */
  --brand-subtle:     #E8F5EE;   /* tinted backgrounds */

  /* Accent (meetings, highlights) */
  --accent:           #2563EB;   /* blue */
  --accent-subtle:    #E8EEFE;
}
```

---

## Neutrals & Surfaces

```css
:root {
  --bg:               #F7F8FA;   /* app background */
  --surface:          #FFFFFF;   /* cards, panels */
  --surface-2:        #F1F3F5;   /* nested surfaces, chat incoming bubble */
  --border:           #E4E7EB;
  --border-strong:    #CFD4DA;

  --fg:               #10151C;   /* primary text */
  --fg-muted:         #5B6672;   /* secondary text */
  --fg-subtle:        #8A94A0;   /* tertiary, placeholders */
}
```

---

## Semantic (status)

```css
:root {
  --success:          #128C4B;   /* connected, converted, sent */
  --success-subtle:   #E8F5EE;
  --warning:          #B7791F;   /* qr pending, quota near limit */
  --warning-subtle:   #FCF3E3;
  --danger:           #C0362C;   /* disconnected, failed, DNC */
  --danger-subtle:    #FBEBEA;
  --info:             #2563EB;
  --info-subtle:      #E8EEFE;
}
```

### Lead stage / intent colors

```css
:root {
  --stage-new:        var(--fg-subtle);
  --stage-hot:        #C0362C;    /* HOT */
  --stage-warm:       #B7791F;    /* WARM */
  --stage-cold:       #2563EB;    /* COLD */
  --stage-converted:  var(--success);
}
```

---

## Typography

```css
:root {
  --font-sans: "Inter", system-ui, -apple-system, sans-serif;
  --font-mono: "JetBrains Mono", ui-monospace, monospace;

  --text-xs:   0.75rem;   /* 12 — badges, meta */
  --text-sm:   0.875rem;  /* 14 — body default in dense views */
  --text-base: 1rem;      /* 16 */
  --text-lg:   1.125rem;  /* 18 — section titles */
  --text-xl:   1.5rem;    /* 24 — page titles */
  --text-2xl:  2rem;      /* 32 — stats numbers */

  --font-normal: 400;
  --font-medium: 500;
  --font-semibold: 600;
  --font-bold: 700;

  --leading-tight: 1.25;
  --leading-normal: 1.5;
}
```

---

## Spacing, Radius, Shadow

```css
:root {
  /* 4px scale */
  --space-1: 0.25rem;  --space-2: 0.5rem;  --space-3: 0.75rem;
  --space-4: 1rem;     --space-6: 1.5rem;  --space-8: 2rem;  --space-12: 3rem;

  --radius-sm: 6px;   --radius-md: 10px;  --radius-lg: 14px;  --radius-full: 9999px;

  --shadow-sm: 0 1px 2px rgba(16,21,28,0.06);
  --shadow-md: 0 4px 12px rgba(16,21,28,0.08);
  --shadow-lg: 0 12px 32px rgba(16,21,28,0.12);
}
```

---

## Chat bubbles (conversations inbox)

```css
:root {
  --bubble-in-bg:   var(--surface-2);   /* prospect */
  --bubble-in-fg:   var(--fg);
  --bubble-out-bg:  var(--brand-subtle);/* agent (disclosed AI) */
  --bubble-out-fg:  var(--fg);
  --bubble-radius:  14px;
  --bubble-max-w:   72%;
}
```

---

## Dark mode

`.dark` overrides `--bg`, `--surface`, `--surface-2`, `--border`, and `--fg*` to dark equivalents; brand and semantic hues keep their identity with adjusted subtle backgrounds. Ship light first; dark tokens defined but low priority.

---

## Usage

```tsx
// Correct — token via Tailwind arbitrary value or CSS var
<div className="bg-[var(--surface)] text-[var(--fg)] rounded-[var(--radius-md)]" />

// Never
<div className="bg-white text-gray-900 rounded-lg" />   // ❌ hardcoded
<div style={{ background: "#fff" }} />                    // ❌ inline hex
```
