# Memory

Claude Code loads `CLAUDE.md` files at multiple levels. The framework sits at the bottom; project and subdirectory files layer on top.

## Layering model

```
~/.claude/CLAUDE.md               ← user-level (personal preferences, all projects)
<project>/CLAUDE.md               ← project-level (@-imports org base below)
  └── @claude-framework/CLAUDE.md ← org base rules (this file, do not copy)
<project>/src/X/CLAUDE.md         ← subdirectory-level (scoped overrides)
```

Rules are additive. A rule lower in the stack applies unless a higher file explicitly overrides it.

## Org base rules (`../../CLAUDE.md`)

The root `CLAUDE.md` of this framework is the authoritative org baseline. It covers:

- **Identity** — senior DS/ML engineering assistant for OCBC Cloudera platform
- **Data handling** — never output PII, account numbers, credentials, or transaction data
- **Python standards** — type annotations, Google docstrings, structlog, pip
- **Git standards** — `feat/`/`fix/` branches, Conventional Commits, no data files committed
- **Prohibited actions** — no auth bypass, no logging suppression, no external data egress

Import it into your project `CLAUDE.md` with one line — never copy the content:

```markdown
@claude-framework/CLAUDE.md
```

## Project `CLAUDE.md`

`setup.sh` creates a starter file in your project root:

```markdown
@claude-framework/CLAUDE.md

---

## Project identity

<!-- Describe this project: what it does, the team, the stack. -->

## Project-specific rules

<!-- Rules that apply only to this repo. -->
```

Add project rules below the import. They take precedence over the org base for any conflicts.

## Subdirectory `CLAUDE.md`

For directories with distinct concerns, create a scoped rules file using one of the templates:

```bash
cp claude-framework/02-memory/templates/CLAUDE.pipeline.md src/pipelines/CLAUDE.md
cp claude-framework/02-memory/templates/CLAUDE.api.md      src/api/CLAUDE.md
cp claude-framework/02-memory/templates/CLAUDE.frontend.md src/frontend/CLAUDE.md
```

Claude Code automatically loads the nearest `CLAUDE.md` when working in a subdirectory.

## Templates

| File | Use for |
|------|---------|
| `templates/CLAUDE.pipeline.md` | ML pipeline directories |
| `templates/CLAUDE.api.md` | FastAPI service directories |
| `templates/CLAUDE.frontend.md` | React frontend directories |
