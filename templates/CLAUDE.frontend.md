# React Frontend — Project Rules
# Extends: org-wide CLAUDE.md (do not duplicate those rules here)

## Scope
This directory contains a React 18 + TypeScript internal web application.
All UI must follow the OCBC design system — see the `ocbc-frontend` skill
at `.claude/skills/ocbc-frontend/SKILL.md` for the full reference.

## Frontend-specific standards

### Component authoring order
1. Check `@ocbc-internal/ui` for an existing component first
2. If none exists, build a custom component in `src/components/[Name]/`
3. Note clearly in a comment why a custom component was needed

### State management
- Server state (API data): React Query only — no manual `useEffect` fetching
- Global UI state: Zustand only — keep stores small and colocated
- Local component state: `useState` / `useReducer`

### API calls
- All API base URLs via env var: `VITE_API_BASE_URL`
- Never construct URLs with user input — use path params from a typed route map
- All requests must include the OCBC SSO cookie (set via httpOnly — never
  manually attach tokens in JS)

### PII display rules
- Account numbers: show last 4 digits only — `****-****-1234`
- NRIC: never display, not even partially
- Full name: display only after explicit masking approval is documented

### Before marking any component done
- [ ] Keyboard navigable (Tab, Enter, Space, Escape)
- [ ] ARIA labels on all icon-only buttons
- [ ] All form inputs have associated `<label>`
- [ ] Colour contrast >= 4.5:1 verified

## Allowed agents for this directory
- `frontend-developer` — component and page code
- `quality-assurance` — React Testing Library tests
