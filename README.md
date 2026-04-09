# OCBC AI Platform — Claude Code Framework

[![Version](https://img.shields.io/badge/version-1.0.0-brightgreen)](CHANGELOG.md)

Centralised standards and tooling for safe, consistent Claude Code use across the OCBC Data Science team. Used as a **git submodule** by project repos.

---

## What's included

| Component | Location | Purpose |
|-----------|----------|---------|
| Org base rules | `CLAUDE.md` | Data handling, code standards, guardrails |
| Agents | `.claude/agents/` | 6 specialist agents (data-analyst, backend-developer, data-scientist, frontend-developer, product-manager, quality-assurance) |
| Skills | `.claude/skills/` | Shared skills (e.g. ocbc-frontend) |
| Permissions | `.claude/settings.json` | Org-wide tool allow/deny lists |
| Ignore rules | `.claudeignore` | Files Claude should never read |
| Bootstrap | `setup.sh` | One-command project setup |

---

## Quick start

```bash
# 1. Add as submodule
git submodule add git@github.com:kelvinheng92/harness-engineering-framework.git claude-framework
git submodule update --init --recursive

# 2. Bootstrap your project
bash claude-framework/setup.sh
```

`setup.sh` creates symlinks for agents and skills, and copies `settings.json`, `.claudeignore`, and a starter `CLAUDE.md` — without overwriting anything you've already customised.

---

## How layering works

```
~/.claude/CLAUDE.md               ← user-level (personal preferences)
<project>/CLAUDE.md               ← project-level (@-imports org base below)
  └── @claude-framework/CLAUDE.md ← org base rules (this repo)
<project>/src/X/CLAUDE.md         ← subdirectory-level (scoped overrides)
```

Your project `CLAUDE.md` imports the org base with one line, then adds project rules below it:

```markdown
@claude-framework/CLAUDE.md

# Project-specific rules go here
```

Never copy the org base content — always import so you get updates automatically.

---

## Customising

**Add a project agent** — drop a `.md` file into `.claude/agents/` alongside the symlinks.  
**Override an org agent** — delete its symlink and create your own file with the same name.  
**Extend permissions** — add to `allow`/`deny` in `.claude/settings.json`; never remove org `deny` entries.  
**Extend ignores** — append patterns to `.claudeignore` below the org defaults.  
**Subdirectory rules** — copy a template and place it next to the relevant code:

```bash
cp claude-framework/templates/CLAUDE.pipeline.md src/pipelines/CLAUDE.md
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
├── .claude/
│   ├── agents/          ← 6 org-wide agents
│   ├── skills/          ← shared skills
│   └── settings.json    ← org permissions baseline
├── templates/           ← CLAUDE.md starters (pipeline, api, frontend)
├── .claudeignore
├── CLAUDE.md            ← org base rules (@-import, do not copy)
├── CHANGELOG.md
├── VERSION
└── setup.sh
```

---

Maintained by the OCBC AI Lab. Raise issues or PRs via GitHub.
