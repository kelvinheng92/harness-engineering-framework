# OCBC AI Platform — Claude Code Framework

Centralised standards and tooling for safe, consistent use of Claude Code across the data science team.

## What this repo gives you

| Component | Purpose |
|---|---|
| Base `CLAUDE.md` |
| `hooks/` | Pre-commit PII & secrets scanner |
| `templates/` | Project-type starter `CLAUDE.md` files (ML, FastAPI, frontend) |
| `docs/` | data classification rules, approved models |

## Repo structure

```
claude-framework/
├── CLAUDE.md
├── README.md
├── docs
│   ├── approved-models.md
│   └── data-classification.md
├── hooks
│   ├── pre_commit_pii.py
│   └── pre_tool_check.py
└── templates
    ├── fastapi-backend
    │   └── CLAUDE.md
    ├── frontend-app
    │   └── CLAUDE.md
    └── ml-pipeline
        └── CLAUDE.md
```

## Ownership

Maintained by the OCBC AI Lab. Raise issues or PRs via Bitbucket.
