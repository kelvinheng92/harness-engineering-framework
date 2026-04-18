# Frontend Rules

@claude-framework/CLAUDE.md

---

## App identity

<!-- What this frontend does and who uses it. -->
<!-- Example: RM portal for viewing customer risk scores and product recommendations. -->

## Stack

<!-- React version, key libraries, build tool, deployment target. -->
<!-- Example: React 18, TypeScript 5, Vite, @ocbc-internal/ui, deployed to internal CDN -->

---

## Frontend-specific rules

### Component library

- Always check `@ocbc-internal/ui` for an existing component before building a custom one
- Do not override design-token CSS variables inline — raise a design system request instead
- Use the design system's spacing, colour, and typography tokens; no hardcoded hex values or px sizes outside the token **scale**

### Data display & PII masking

- Account numbers must show last 4 digits only: `XXX-XXXXX-1234` — never the full number
- NRIC/FIN must never be rendered in the DOM, even masked
- Customer full names may be shown but must not be combined with account or ID numbers in the same element
- Scores and amounts must be formatted via shared locale utilities — no inline `toFixed()` or `toLocaleString()`

### State & storage

- No PII in URL params, query strings, `localStorage`, or `sessionStorage`
- Session tokens are managed by the auth library only — never stored manually
- Server state (API responses) lives in React Query; do not duplicate it in `useState`
- Global UI state (sidebar open, active tab) lives in Zustand; do not use React context for cross-cutting state

### API calls

- All API calls go through the centralised API client — no raw `fetch()` or `axios` in components
- The API base URL must come from an environment variable (`VITE_API_BASE_URL`), never hardcoded
- Handle loading, error, and empty states explicitly for every data-fetching component
- Requests that mutate data must show a confirmation dialog when the action is irreversible

### Accessibility

- All interactive elements must have WCAG AA-compliant labels (visible or `aria-label`)
- Form fields must have associated `<label>` elements — no placeholder-only labels
- Error messages must be linked to their field via `aria-describedby`
- Keyboard navigation must work for all primary user flows; test with tab order

### TypeScript

- `strict: true` in `tsconfig.json` — no `any`, no `@ts-ignore` without an explanatory comment
- API response shapes must be typed via generated or hand-written interface files in `src/types/`
- Avoid type assertions (`as SomeType`) except at validated API boundary deserialization

### Performance

- Lazy-load routes with `React.lazy` + `Suspense`; do not eagerly import heavy pages
- Images must have explicit `width` and `height` to prevent layout shift
- Avoid `useEffect` for data fetching — use React Query's `useQuery` instead

### Testing

- Unit-test all utility functions and custom hooks
- Component tests use React Testing Library; test behaviour, not implementation details
- Do not query elements by class name or element type — use accessible roles, labels, or `data-testid`
- E2E smoke tests must cover the primary happy path for each major feature
