# Skills

Skills are reusable, auto-invoked capabilities. Unlike agents (which handle whole tasks), skills inject domain-specific context and constraints into any conversation when triggered by keyword or context.

## Available skills

| Skill | Trigger phrases | Purpose |
|-------|----------------|---------|
| `ocbc-frontend` | "build a component", "OCBC UI", "RM portal", "dashboard", "internal tool frontend" | Enforces OCBC design system, brand tokens, and `@ocbc-internal/ui` component library for React/TypeScript |

## How skills are linked into your project

`setup.sh` creates symlinks in your project's `.claude/skills/` pointing to these directories. Each skill is a folder containing at minimum a `SKILL.md` file.

## Skill folder structure

```
03-skills/
└── <skill-name>/
    ├── SKILL.md          ← required: YAML front matter + instructions
    ├── references/       ← optional: supporting docs (tokens, patterns, etc.)
    ├── scripts/          ← optional: helper scripts the skill can invoke
    └── templates/        ← optional: output templates
```

## Adding a project-specific skill

Create a new folder in your project's `.claude/skills/` alongside the symlinks:

```
.claude/skills/
├── ocbc-frontend/          ← symlink → org skill (do not edit)
└── credit-scoring-review/  ← your project-specific skill
    └── SKILL.md
```

## Skill file format

```yaml
---
name: skill-name
description: >
  What this skill does and when it should be invoked.
  Include trigger phrases for auto-invocation.
---

# Skill title

Context, constraints, and instructions the skill injects...
```
