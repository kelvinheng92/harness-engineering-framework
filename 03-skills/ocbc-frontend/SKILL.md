---
name: ocbc-frontend
description: >
  OCBC frontend skill for building React web components and pages that strictly follow the OCBC design system,
  brand tokens, and internal component library (@ocbc-internal/ui). Use this skill whenever the user asks to
  build, scaffold, or generate any frontend component, page, feature, or screen for an OCBC internal tool or
  customer-facing web application — even if they don't explicitly say "OCBC design system". Triggers on:
  "new component", "scaffold page", "OCBC style", "internal tool UI", "RM portal", "dashboard",
  "frontend feature", or any request to build UI for an OCBC project.
---

# OCBC Frontend Skill

You are building UI for OCBC's internal tools or customer-facing applications. All output must follow the
OCBC design system exactly — no improvised styling, no external libraries, no guessed colour values.

---

## 1. Design Tokens (always use these — never hardcode other values)

```css
/* Brand colours */
--ocbc-red:        #D0021B;   /* Primary CTA, active states, brand accent */
--ocbc-grey-dark:  #404040;   /* Body text, headings */
--ocbc-white:      #FFFFFF;   /* Page background */
--ocbc-pink-light: #FFF0F0;   /* Card backgrounds, subtle containers */
--ocbc-gold:       #E8A000;   /* Accent, highlights, warning states */

/* Typography */
--ocbc-font: 'OCBC Sans', system-ui, sans-serif;  /* loaded from internal CDN */

/* Spacing scale (use multiples of 4px) */
--space-1: 4px;  --space-2: 8px;  --space-3: 12px;
--space-4: 16px; --space-6: 24px; --space-8: 32px; --space-12: 48px;
```

All colours come from the token list above. If a design calls for a shade not listed, derive it by using
opacity on the nearest token (e.g. `rgba(208, 2, 27, 0.1)` for a light red wash).

---

## 2. Component Library

Always import from `@ocbc-internal/ui` before writing custom components. Browse available components at
`https://design.internal/components` before scaffolding anything new. Only build a custom component if
the library genuinely doesn't have what you need — and note this clearly in a comment.

```tsx
// Prefer this
import { Button, Card, Input, Badge } from '@ocbc-internal/ui';

// Only when the library has no equivalent
// Custom: <OcbcDataTable /> — no tabular data component in @ocbc-internal/ui as of [date]
```

The internal npm registry is at `https://npm.internal`. The `.npmrc` must be present:
```
registry=https://npm.internal
@ocbc-internal:registry=https://npm.internal
```

---

## 3. Tech Stack Constraints

| Concern | Approved choice | Not allowed |
|---------|----------------|-------------|
| Framework | React 18 + TypeScript (strict) | Vue, Angular, plain JS |
| Styling | CSS Modules | Tailwind, Bootstrap, styled-components CDN |
| Global state | Zustand | Redux, MobX |
| Server state | React Query | SWR, Apollo |
| Build | Vite | CRA, Webpack |
| Charts | Recharts or D3 | Chart.js from public CDN |
| HTTP | axios (internal base URL via env var) | fetch to external URLs, requests |
| Auth tokens | httpOnly cookies via OCBC SSO | localStorage, sessionStorage |

---

## 4. Project File Structure

When scaffolding a new component, follow this layout:

```
src/components/[ComponentName]/
├── index.tsx                      ← public export
├── [ComponentName].tsx            ← component logic
├── [ComponentName].module.css     ← scoped styles using design tokens
└── [ComponentName].test.tsx       ← unit tests
```

When scaffolding a new page:

```
src/pages/[PageName]/
├── index.tsx
├── [PageName].tsx
├── [PageName].module.css
└── components/                    ← page-local sub-components only
```

---

## 5. Web Component Template

Use this as your starting point when scaffolding any new component:

```tsx
// src/components/[ComponentName]/[ComponentName].tsx
import React from 'react';
import styles from './[ComponentName].module.css';
// Import from @ocbc-internal/ui first; add custom imports only if needed

interface [ComponentName]Props {
  // Define all props with strict types — no `any`
}

export const [ComponentName]: React.FC<[ComponentName]Props> = ({ ...props }) => {
  return (
    <div className={styles.container}>
      {/* component content */}
    </div>
  );
};
```

```css
/* [ComponentName].module.css */
.container {
  font-family: var(--ocbc-font);
  color: var(--ocbc-grey-dark);
  background: var(--ocbc-white);
}
```

---

## 6. Security — Non-Negotiable

Every component must respect these rules. Flag violations before writing code.

| Rule | Implementation |
|------|---------------|
| Mask PII | Account numbers: last 4 digits only (`****-****-1234`). NRIC: never display |
| No PII in URLs | Sensitive IDs go in POST bodies or headers, never query strings |
| No external CDN | All assets from `https://cdn.internal` — no unpkg, cdnjs, fonts.google |
| Sanitise HTML | Use `DOMPurify` (internal npm) for any `dangerouslySetInnerHTML` |
| Auth | Redirect to OCBC SSO; tokens in httpOnly cookies only |
| CSP | No `unsafe-inline` scripts; declare strict Content-Security-Policy |

---

## 7. Accessibility Baseline

Every component must pass these before it's done:

- All interactive elements keyboard-navigable (Tab, Enter, Space, Escape)
- Icon-only buttons have `aria-label`
- All form inputs have associated `<label>` — no placeholder-only labelling
- Colour contrast ≥ 4.5:1 (WCAG AA) — the OCBC red on white passes; always verify text on `#FFF0F0`

---

## 8. Scaffolding Workflow

When the user asks to build a component, page, or screen:

1. **Clarify scope** — new component or new page?
2. **Check the library** — state which `@ocbc-internal/ui` components you'll use (or why you can't)
3. **Generate the files** — follow the file structure above; use tokens, not hardcoded values
4. **Security pass** — confirm PII masking, auth, and CDN rules are satisfied
5. **Accessibility pass** — confirm keyboard nav, ARIA labels, and contrast
6. **Output the full file path** for every file created or modified

Read `references/design-tokens.md` for extended token documentation if you need spacing, elevation, or
motion values not listed above.
Read `references/component-patterns.md` for common OCBC UI patterns (tables, forms, dashboards, nav).
