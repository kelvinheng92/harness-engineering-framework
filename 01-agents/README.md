# Agents

Six specialist sub-agents are available org-wide. Each is scoped to a domain, uses an appropriate model, and has a restricted tool set.

## Available agents

| Agent | Invoke when you say… | Model | Tools |
|-------|----------------------|-------|-------|
| `data-analyst` | "write a query", "SQL", "Hive", "Impala", "analyse this data", "build a report" | haiku | Read, Write, Edit, Bash(python:\*), Bash(hive:\*), Bash(git:\*), Glob, Grep |
| `backend-developer` | "build an API", "FastAPI", "endpoint", "schema", "service", "backend" | sonnet | Read, Write, Edit, Bash(git:\*), Bash(python:\*), Bash(pytest:\*), Bash(mypy:\*), Glob, Grep |
| `data-scientist` | "build a model", "train", "feature engineering", "MLflow", "Feast", "churn", "credit scoring" | sonnet | Read, Write, Edit, Bash(git:\*), Bash(python:\*), Bash(pytest:\*), Glob, Grep |
| `frontend-developer` | "build a component", "scaffold a page", "OCBC UI", "dashboard", "RM portal" | sonnet | Read, Write, Edit, Glob, Grep |
| `product-manager` | "write a PRD", "user stories", "acceptance criteria", "prioritise the backlog" | sonnet | Read, Write, Edit, Glob, Grep |
| `quality-assurance` | "write tests", "test plan", "pytest", "review this code", "find bugs", "data validation" | sonnet | Read, Write, Edit, Bash(git:\*), Bash(python:\*), Bash(pytest:\*), Glob, Grep |

## How agents are linked into your project

`setup.sh` creates symlinks in your project's `.claude/agents/` pointing to these files. The agent definitions live here in the framework so updates propagate when you pull a new framework version.

## Adding a project-specific agent

Drop a new `.md` file into your project's `.claude/agents/` alongside the symlinks:

```
.claude/agents/
├── data-analyst.md        ← symlink → org agent (do not edit)
├── backend-developer.md   ← symlink → org agent (do not edit)
└── credit-risk-model.md   ← your project-specific agent (edit freely)
```

## Overriding an org agent

Delete the symlink and create your own file with the same name. Your file will be used instead.

## Agent file format

Each agent `.md` file uses YAML front matter to declare its metadata:

```yaml
---
name: agent-name
description: >
  What this agent does and when Claude Code should invoke it.
  Include trigger phrases so auto-routing works correctly.
model: haiku | sonnet | opus
tools: Read, Write, Edit, Bash(tool:*), Glob, Grep
---

# Agent title

Instructions and context for the agent...
```
