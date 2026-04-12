# OCBC Component Patterns

Common patterns for OCBC internal tools and portals. Use these as references — always prefer
`@ocbc-internal/ui` equivalents when available.

---

## Navigation

### Top Navigation Bar (Web)
- Height: 64px
- Background: `#FFFFFF`, bottom border `1px solid #E0E0E0`
- OCBC logo left-aligned (from `@ocbc-internal/ui`)
- Nav links: `#404040`, active state: `#D0021B` with 2px red underline
- User avatar / name right-aligned

### Side Navigation (Internal Tools)
- Width: 240px collapsed → 64px icon-only
- Background: `#FFFFFF`, right border `1px solid #E0E0E0`
- Active item: `#FFF0F0` background, left border `3px solid #D0021B`
- Section labels: `#767676`, 11px uppercase

---

## Cards

### Standard Data Card
```tsx
<Card style={{
  background: 'var(--ocbc-white)',
  border: '1px solid var(--ocbc-grey-light)',
  borderRadius: 'var(--radius-md)',
  boxShadow: 'var(--shadow-card)',
  padding: 'var(--space-6)',
}}>
  <h3 style={{ color: 'var(--ocbc-grey-dark)', fontSize: '18px', fontWeight: 600 }}>
    Card Title
  </h3>
  {/* content */}
</Card>
```

### Summary / KPI Card
- Background: `#FFF0F0`
- Large metric value: 32px, `#D0021B`, bold
- Label below metric: 13px, `#767676`
- Change indicator: green `#009650` / red `#D0021B` with arrow icon

---

## Forms

### Input Field Pattern
```tsx
<div className={styles.fieldGroup}>
  <label htmlFor="fieldId" className={styles.label}>
    Field Label <span aria-label="required">*</span>
  </label>
  <input
    id="fieldId"
    type="text"
    className={styles.input}
    aria-describedby="fieldId-error"
  />
  <span id="fieldId-error" className={styles.error} role="alert">
    Error message
  </span>
</div>
```

```css
.label    { font-size: 13px; font-weight: 500; color: #404040; margin-bottom: 6px; }
.input    { border: 1px solid #E0E0E0; border-radius: 4px; padding: 10px 12px;
            font-size: 14px; color: #404040; width: 100%; }
.input:focus { border-color: #D0021B; outline: none; box-shadow: 0 0 0 2px rgba(208,2,27,0.15); }
.error    { font-size: 12px; color: #D0021B; margin-top: 4px; }
```

---

## Buttons

| Variant | Background | Text | Border | Use case |
|---------|-----------|------|--------|----------|
| Primary | `#D0021B` | `#FFFFFF` | none | Main CTA (one per view) |
| Secondary | `#FFFFFF` | `#D0021B` | `1px solid #D0021B` | Secondary actions |
| Ghost | transparent | `#404040` | `1px solid #E0E0E0` | Low-emphasis actions |
| Danger | `#D0021B` | `#FFFFFF` | none | Destructive actions (same as primary but context-semantic) |
| Disabled | `#E0E0E0` | `#767676` | none | Always `disabled` attr + `aria-disabled` |

Button sizing: height 40px (default), 32px (compact), 48px (large). Border radius `var(--radius-md)`.

---

## Data Tables

```css
/* Table styles */
.table       { width: 100%; border-collapse: collapse; }
.thead th    { background: #F5F5F5; color: #404040; font-weight: 600; font-size: 13px;
               padding: 12px 16px; text-align: left; border-bottom: 2px solid #E0E0E0; }
.tbody tr    { border-bottom: 1px solid #E0E0E0; }
.tbody tr:hover { background: #FFF0F0; }
.tbody td    { padding: 12px 16px; font-size: 14px; color: #404040; }
```

- Sortable columns: show sort icon (`↑↓`) on hover; active sort shows single arrow in `#D0021B`
- Pagination: show `Showing X–Y of Z results` + prev/next + page numbers
- Empty state: centred illustration + text `No data available`

---

## PII Masking Patterns

```tsx
// Account number — show last 4 only
const maskAccount = (acct: string) =>
  `****-****-${acct.slice(-4)}`;

// NRIC — never display, show placeholder
const maskNric = () => 'S****XXX*';

// Name — initials only for list views, full name only on detail pages
// with confirmed access rights
const maskName = (name: string) =>
  name.split(' ').map(n => n[0] + '.').join(' ');
```

---

## Dashboards

Standard OCBC dashboard layout:

```
┌─────────────────────────────────────────┐
│  Top Nav                                │
├──────────┬──────────────────────────────┤
│          │  Page Title + Breadcrumb     │
│  Side    ├──────────────────────────────┤
│  Nav     │  KPI Card Row (4 cards)      │
│          ├──────────────────────────────┤
│          │  Primary Chart / Table       │
│          ├──────────────────────────────┤
│          │  Secondary Content           │
└──────────┴──────────────────────────────┘
```

KPI card row: 4 equal columns on desktop, 2×2 grid on tablet.
Primary chart: full width, min-height 320px.

---

## Status Badges

```tsx
const statusColors = {
  active:   { bg: 'rgba(0,150,80,0.1)',    text: '#009650' },
  pending:  { bg: 'rgba(232,160,0,0.15)',  text: '#B87800' },
  rejected: { bg: 'rgba(208,2,27,0.1)',    text: '#D0021B' },
  draft:    { bg: '#F5F5F5',               text: '#767676' },
};
// Border radius: var(--radius-pill); padding: 3px 10px; font-size: 12px; font-weight: 500
```

---

## Loading States

- Skeleton loaders: `#F5F5F5` → `#E0E0E0` shimmer animation, matches layout shape
- Button loading: spinner replaces label text, button disabled
- Full-page loading: OCBC spinner (from `@ocbc-internal/ui`) centred on `#FFFFFF` overlay
