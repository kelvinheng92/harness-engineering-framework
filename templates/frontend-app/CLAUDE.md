# [Project Name] — Frontend / Internal Tool

> Extends: ~/claude-framework/claude-config/CLAUDE.md
> Project type: Internal web application / dashboard
> Data classification: [INTERNAL / CONFIDENTIAL — fill in]
> Owner: [DS/engineer name] | [team]
> Last updated: [date]

---

## Project context

[Describe the tool in 2–3 sentences. e.g.:
"Internal dashboard used by credit RMs to review AI-generated risk
summaries during the credit origination workflow. Built with React and
served from the internal app platform."]

---

## Design system

All internal OCBC tools follow the OCBC brand and design standards:

| Token | Value |
|---|---|
| Primary red | `#D0021B` |
| Dark grey (text) | `#404040` |
| Background | `#FFFFFF` |
| Light pink (cards) | `#FFF0F0` |
| Accent / highlight | `#E8A000` (gold/yellow) |
| Font | OCBC Sans (internal CDN) or system sans-serif fallback |

Apply these consistently — do not introduce external design systems
(no Tailwind CDN, no Bootstrap from public CDN). Use the internal
component library at `https://design.internal/components`.

---

## Tech stack

- **Framework**: React 18 + TypeScript (strict mode)
- **State**: Zustand for global state; React Query for server state
- **Styling**: CSS Modules (no utility-first CSS in production apps)
- **Build**: Vite
- **Internal component library**: `@ocbc-internal/ui` (from internal npm registry)
- **Charts**: Recharts (approved) or D3 for custom visualisations
- **HTTP**: `axios` with the internal API base URL configured via env var
- **Auth**: Redirect to OCBC SSO; never store tokens in localStorage —
  use httpOnly cookies only

### Internal npm registry

```bash
# .npmrc — committed to repo
registry=https://npm.internal
@ocbc-internal:registry=https://npm.internal
```

---

## Project structure

```
project/
├── CLAUDE.md
├── package.json
├── vite.config.ts
├── tsconfig.json
├── .env.example          ← template only, no real values
├── src/
│   ├── components/       ← reusable UI components
│   │   └── [ComponentName]/
│   │       ├── index.tsx
│   │       ├── [ComponentName].module.css
│   │       └── [ComponentName].test.tsx
│   ├── pages/            ← route-level components
│   ├── hooks/            ← custom React hooks
│   ├── services/         ← API client functions (typed with Zod)
│   ├── store/            ← Zustand stores
│   ├── types/            ← shared TypeScript types
│   └── utils/
└── tests/
```

---

## Security requirements

1. **No PII displayed without masking**: customer IDs, account numbers,
   and names must be masked in the UI unless the user has explicit access
   rights (checked via the auth service)
   - Account numbers: show last 4 digits only — `****-****-1234`
   - NRIC: never display in full

2. **No data in URL params**: sensitive identifiers go in POST bodies or
   request headers, never query strings

3. **Content Security Policy**: the app must declare a strict CSP header;
   no `unsafe-inline` scripts

4. **No external CDN resources**: all assets served from internal CDN
   (`https://cdn.internal`) — no links to `unpkg`, `cdnjs`, `fonts.google`

5. **Input sanitisation**: sanitise all user inputs before rendering;
   use `DOMPurify` (from internal npm) for any HTML rendering

---

## Accessibility

- All interactive components must be keyboard-navigable
- ARIA labels required on icon-only buttons
- Colour contrast ratio ≥ 4.5:1 (WCAG AA)
- Forms must have associated labels — no placeholder-only labelling

---

## Running locally

```bash
# Install
npm install

# Copy env template
cp .env.example .env.local   # fill in internal API URLs only

# Dev server
npm run dev

# Tests
npm test

# Type check
npm run typecheck

# Lint
npm run lint
```

---

## Things Claude should flag in this project

- Displaying unmasked customer identifiers in the UI
- Fetching from external (non-internal) APIs
- Storing auth tokens in `localStorage` or `sessionStorage`
- Using `dangerouslySetInnerHTML` without DOMPurify
- Importing from public CDN URLs
- Missing TypeScript types (`any` usage without explicit justification)
