# Framework Catalog

Quick reference for everything in the OCBC Claude Code Framework.

---

## Agents

Six specialist agents, automatically invoked by context. Symlinked into `.claude/agents/` by `setup.sh`.

| Agent | Model | Invoke when… |
|-------|-------|-------------|
| `data-analyst` | haiku | "write a query", "SQL", "Hive", "Impala", "analyse this data", "build a report", "define a metric" |
| `backend-developer` | sonnet | "build an API", "FastAPI", "endpoint", "schema", "service", "backend" |
| `data-scientist` | sonnet | "build a model", "train", "feature engineering", "MLflow", "Feast", "churn", "credit scoring" |
| `frontend-developer` | sonnet | "build a component", "scaffold a page", "OCBC UI", "dashboard", "RM portal" |
| `product-manager` | sonnet | "write a PRD", "user stories", "acceptance criteria", "prioritise the backlog" |
| `quality-assurance` | sonnet | "write tests", "test plan", "pytest", "review this code", "find bugs", "data validation" |

Source: [`agents/`](agents/)

---

## Skills

Reusable capabilities auto-invoked by trigger phrases. Symlinked into `.claude/skills/` by `setup.sh`.

| Skill | Trigger phrases | What it enforces |
|-------|----------------|-----------------|
| `ocbc-frontend` | "build a component", "OCBC UI", "dashboard", "RM portal", "internal tool frontend" | OCBC design tokens, `@ocbc-internal/ui` first, React/TypeScript constraints, PII masking, WCAG AA |

Source: [`skills/`](skills/)

---

## Memory (CLAUDE.md)

Org base rules imported via `@claude-framework/CLAUDE.md`. Covers:

| Area | Rules |
|------|-------|
| **Data handling** | No PII, account numbers, UENs, credentials, or transaction data in any output |
| **Python** | Type annotations, Google docstrings, `structlog`, `pip` |
| **Git** | `feat/`/`fix/` branches, Conventional Commits, no data files or secrets committed |
| **Claude behaviour** | Flag security/compliance concerns before writing code; show full file paths |
| **Hard limits** | No auth bypass, no logging suppression, no external data egress |

Templates for scoped subdirectory rules: [`memory/templates/`](memory/templates/)

Source: [`memory/`](memory/) · [`CLAUDE.md`](CLAUDE.md)

---

## Rules

Structured constraint definitions that can be versioned and `@`-imported into any `CLAUDE.md`.

| File | Covers |
|------|--------|
| `data-handling.md` | PII, credentials, and data egress constraints |
| `code-standards.md` | Python, Git, and general coding constraints |
| `hard-limits.md` | Prohibited actions (auth bypass, logging suppression, external egress) |

Source: [`rules/`](rules/)

---

## Hooks

Hooks run automatically at Claude Code lifecycle events. No org-wide hooks are defined yet — add project-specific hooks to your project's `.claude/hooks/`.

See [`hooks/`](hooks/) for event types and configuration reference.

---

## Permissions (`settings.json`)

Copied into your project by `setup.sh`. Key defaults:

- **Allowed:** `Bash(python:*)`, `Bash(hive:*)`, `Bash(git:*)`, `Bash(pytest:*)`, `Bash(mypy:*)`
- **Denied:** network calls, package installs from untrusted sources

Extend by adding to the `allow`/`deny` arrays. Never remove org `deny` entries.

Source: [`.claude/settings.json`](.claude/settings.json)

---

## Bootstrap

```bash
# Add framework as submodule
git submodule add git@github.com:kelvinheng92/harness-engineering-framework.git claude-framework

# Bootstrap your project (run once)
bash claude-framework/setup.sh
```

Source: [`setup.sh`](setup.sh)
