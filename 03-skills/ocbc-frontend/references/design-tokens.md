# OCBC Design Tokens — Extended Reference

## Colour System

| Token | Value | Usage |
|-------|-------|-------|
| `--ocbc-red` | `#D0021B` | Primary buttons, active nav, links, error borders |
| `--ocbc-red-hover` | `rgba(208,2,27,0.85)` | Hover state on red buttons |
| `--ocbc-red-light` | `rgba(208,2,27,0.1)` | Error background wash, alert banners |
| `--ocbc-grey-dark` | `#404040` | Body text, headings, labels |
| `--ocbc-grey-mid` | `#767676` | Secondary text, placeholders, disabled labels |
| `--ocbc-grey-light` | `#E0E0E0` | Borders, dividers, disabled backgrounds |
| `--ocbc-white` | `#FFFFFF` | Page background, modal background |
| `--ocbc-pink-light` | `#FFF0F0` | Card backgrounds, info containers, row highlights |
| `--ocbc-gold` | `#E8A000` | Accent badges, warning states, highlights |
| `--ocbc-gold-light` | `rgba(232,160,0,0.15)` | Warning background wash |

## Typography

| Role | Size | Weight | Token |
|------|------|--------|-------|
| Page heading (H1) | 28px | 700 | `--text-h1` |
| Section heading (H2) | 22px | 600 | `--text-h2` |
| Card heading (H3) | 18px | 600 | `--text-h3` |
| Body | 14px | 400 | `--text-body` |
| Small / caption | 12px | 400 | `--text-caption` |
| Label | 13px | 500 | `--text-label` |

Font stack: `'OCBC Sans', system-ui, -apple-system, sans-serif`
OCBC Sans is loaded from `https://cdn.internal/fonts/ocbc-sans.css`

## Spacing Scale (4px base grid)

```
4px   (--space-1)  micro gaps, icon padding
8px   (--space-2)  tight spacing, badge padding
12px  (--space-3)  compact rows
16px  (--space-4)  standard content padding
24px  (--space-6)  section separation
32px  (--space-8)  large section gaps
48px  (--space-12) page-level vertical rhythm
```

## Elevation / Shadow

```css
--shadow-card:   0 1px 4px rgba(0,0,0,0.10);   /* standard card */
--shadow-modal:  0 4px 24px rgba(0,0,0,0.18);  /* modals, drawers */
--shadow-tooltip:0 2px 8px rgba(0,0,0,0.14);   /* tooltips, popovers */
```

## Border Radius

```css
--radius-sm:  4px;   /* inputs, small badges */
--radius-md:  8px;   /* cards, buttons */
--radius-lg: 12px;   /* modals, drawers */
--radius-pill: 999px; /* pill badges, tags */
```

## Motion / Transitions

```css
--transition-fast:   150ms ease;   /* hover states */
--transition-normal: 250ms ease;   /* UI state changes */
--transition-slow:   400ms ease;   /* page transitions */
```

## Status Colours

| Status | Background | Border/Text |
|--------|-----------|-------------|
| Success | `rgba(0,150,80,0.1)` | `#009650` |
| Warning | `rgba(232,160,0,0.15)` | `#E8A000` |
| Error | `rgba(208,2,27,0.1)` | `#D0021B` |
| Info | `rgba(0,100,200,0.1)` | `#0064C8` |
| Neutral | `#F5F5F5` | `#767676` |