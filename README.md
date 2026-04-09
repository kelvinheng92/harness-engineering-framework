# OCBC AI Platform — Claude Code Framework

[![Version](https://img.shields.io/badge/version-1.0.0-brightgreen)](CHANGELOG.md)

Centralised standards and tooling for safe, consistent Claude Code use across the OCBC Data Science team. Used as a **git submodule** by project repos.

**[Browse the full feature catalog →](CATALOG.md)**

---

## Table of Contents

- [What's Included](#whats-included)
- [Quick Start](#quick-start)
- [How It Works](#how-it-works)
- [Org Rules Overview](#org-rules-overview)
- [Module Guide](#module-guide)
- [Customising](#customising)
- [Updating](#updating)
- [Structure](#structure)

---

## What's Included

| Module | Contents |
|--------|----------|
| [`01-agents/`](01-agents/) | 6 specialist sub-agents (data-analyst, backend-developer, data-scientist, frontend-developer, product-manager, quality-assurance) |
| [`02-memory/`](02-memory/) | Org base rules, memory layering guide, CLAUDE.md templates |
| [`03-skills/`](03-skills/) | Shared skills (ocbc-frontend) |
| [`04-hooks/`](04-hooks/) | Hook event reference and configuration guide |
| [`CATALOG.md`](CATALOG.md) | Full feature reference with trigger phrases and settings |
| [`.claude/settings.json`](.claude/settings.json) | Org-wide tool allow/deny lists |
| `.claudeignore` | Files Claude should never read |
| `setup.sh` | One-command project bootstrap |

---

## Quick Start

```bash
# 1. Add as submodule
git submodule add git@github.com:kelvinheng92/harness-engineering-framework.git claude-framework
git submodule update --init --recursive

# 2. Bootstrap your project
bash claude-framework/setup.sh
```

`setup.sh` symlinks agents and skills into `.claude/`, and copies `settings.json`, `.claudeignore`, and a starter `CLAUDE.md` — without overwriting anything you've already customised.

---

## How It Works

```
~/.claude/CLAUDE.md               ← user-level (personal preferences, all projects)
<project>/CLAUDE.md               ← project-level (@-imports org base below)
  └── @claude-framework/CLAUDE.md ← org base rules (this repo)
<project>/src/X/CLAUDE.md         ← subdirectory-level (scoped overrides)
```

Your project `CLAUDE.md` imports the org base, then adds project rules below it:

```markdown
@claude-framework/CLAUDE.md

## Project-specific rules
<!-- Add rules that apply only to this repo -->
```

Never copy the org base content — always import so you get updates automatically.

---

## Org Rules Overview

`CLAUDE.md` enforces the following across all projects that import it:

| Area | Rules |
|------|-------|
| **Data handling** | Never output PII, account numbers, UENs, credentials, or transaction data — even synthetic-looking values. Hardcoded secrets must be moved to Vault/env vars. |
| **Python** | Type annotations on all functions, Google-style docstrings, `structlog` for logging, `pip` for deps |
| **Git** | `feat/`/`fix/` branch prefixes, Conventional Commits, no data files or secrets committed |
| **Claude behaviour** | Flag security/compliance concerns before writing code; show full file paths; prefer working code |
| **Hard limits** | No bypassing auth/audit logging, no suppressing logs, no sending data outside the internal network |

---

## Module Guide

| Module | Read when… |
|--------|-----------|
| [`01-agents/`](01-agents/) | You want to understand the 6 agents, add a project agent, or override an org agent |
| [`02-memory/`](02-memory/) | You want to understand memory layering or create subdirectory `CLAUDE.md` files |
| [`03-skills/`](03-skills/) | You want to understand the ocbc-frontend skill or add a new skill |
| [`04-hooks/`](04-hooks/) | You want to add automation hooks to your project |

---

## Customising

**Add a project agent** — drop a `.md` file into your project's `.claude/agents/` alongside the symlinks.  
**Override an org agent** — delete its symlink and create your own file with the same name.  
**Extend permissions** — add to `allow`/`deny` in `.claude/settings.json`; never remove org `deny` entries.  
**Extend ignores** — append patterns to `.claudeignore` below the org defaults.  
**Subdirectory rules** — copy a template and place it next to the relevant code:

```bash
cp claude-framework/02-memory/templates/CLAUDE.pipeline.md src/pipelines/CLAUDE.md
```

---

## Updating

```bash
cd claude-framework && git fetch && git checkout v1.0.0
cd .. && git add claude-framework
git commit -m "chore: update claude-framework to v1.0.0"
```

| Bump | Meaning | Action |
|------|---------|--------|
| Patch `1.0.x` | Fixes, new agents/skills | Pull freely |
| Minor `1.x.0` | New deny rules or behaviour changes | Review `CHANGELOG.md` |
| Major `x.0.0` | Breaking changes | Coordinate with AI Lab |

---

## Structure

```
claude-framework/
├── 01-agents/           ← 6 org-wide agent definitions + README
├── 02-memory/           ← memory layering guide + CLAUDE.md templates
│   └── templates/       ← CLAUDE.pipeline.md, CLAUDE.api.md, CLAUDE.frontend.md
├── 03-skills/           ← shared skills (ocbc-frontend) + README
├── 04-hooks/            ← hook event reference + README
├── .claude/
│   └── settings.json    ← org permissions baseline (copy via setup.sh)
├── .claudeignore        ← org ignore rules (copy via setup.sh)
├── CATALOG.md           ← full feature reference
├── CLAUDE.md            ← org base rules (@-import, do not copy)
├── CHANGELOG.md
├── VERSION
└── setup.sh
```

---

Maintained by the OCBC AI Lab. Raise issues or PRs via GitHub.
