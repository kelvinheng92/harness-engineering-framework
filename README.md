# OCBC AI Platform — Claude Code Framework

Centralised standards and tooling for safe, consistent Claude Code use across
the OCBC Data Science team. Consumed as a **git submodule** by individual
project repositories.

---

## What this framework provides

| Component | Location | Purpose |
|-----------|----------|---------|
| Org-wide base rules | `CLAUDE.md` | Data handling, code standards, behaviour guardrails |
| Sub-agents | `.claude/agents/` | 6 specialist agents (data-analyst, backend-developer, data-scientist, frontend-developer, product-manager, quality-assurance) |
| Project templates | `templates/` | Scoped `CLAUDE.md` starters for pipelines, APIs, and frontends |
| Ignore rules | `.claudeignore` | Excludes data files, ML artefacts, and build dirs from indexing |
| Permissions | `.claude/settings.json` | Org-wide allow/deny lists for tool use |
| Bootstrap script | `setup.sh` | One-command project setup |

---

## Quick start

### 1. Add as a submodule

From your project root:

```bash
git submodule add git@github.com:kelvinheng92/harness-engineering-framework.git claude-framework
git submodule update --init --recursive
```

### 2. Run the bootstrap script

```bash
bash claude-framework/setup.sh
```

This creates or updates the following in your project (never overwrites files
you have already customised):

- `.claude/agents/` — symlinks to all org-wide agents
- `CLAUDE.md` — starter file that `@`-imports the org base rules
- `.claude/settings.json` — editable copy of the org permissions
- `.claudeignore` — editable copy of the org ignore rules

### 3. Verify

Open Claude Code in your project. Run `/agents` to confirm the org agents are
visible. Check that `CLAUDE.md` loads without errors.

---

## How layering works

Claude Code loads configuration at multiple levels. The framework sits at the
bottom of the stack; project files override it layer by layer.

```
~/.claude/CLAUDE.md              ← user-level (personal preferences)
        │
<project>/CLAUDE.md              ← project-level (your file, @-imports org base)
        │   └── @claude-framework/CLAUDE.md   ← org base rules (this repo)
        │
<project>/src/pipelines/CLAUDE.md ← subdirectory-level (scoped rules)
```

### CLAUDE.md

Your project `CLAUDE.md` imports the org base with a single line:

```markdown
@claude-framework/CLAUDE.md
```

Add project-specific rules **below** the import. Rules in your file take
precedence over imported rules for conflicting instructions.

Do **not** copy the org base content into your file — always import it so you
receive updates when the framework is upgraded.

### Agents

`setup.sh` creates symlinks in `.claude/agents/` pointing to the org agents.
To add a project-specific agent, create a new `.md` file directly in
`.claude/agents/` alongside the symlinks:

```
.claude/agents/
├── data-analyst.md       ← symlink → org agent (do not edit)
├── backend-developer.md  ← symlink → org agent (do not edit)
└── credit-risk-model.md  ← your project-specific agent (add here)
```

To **override** an org agent, delete its symlink and create your own file with
the same name. Your file will be used instead.

### settings.json

`setup.sh` copies `.claude/settings.json` into your project. Edit it freely —
extend the `allow` and `deny` lists with project-specific tool permissions:

```json
{
  "permissions": {
    "allow": [
      "Bash(git:*)",
      "...all org defaults...",
      "Bash(your-internal-tool:*)"  ← add project-specific tools here
    ],
    "deny": [
      "...org defaults..."
    ]
  }
}
```

Do **not** remove org defaults — only add to them.

### .claudeignore

`setup.sh` copies `.claudeignore` into your project. Add project-specific
patterns beneath the org defaults:

```
# (org defaults above — do not remove)

# Project-specific exclusions
reports/
archive/
*.custom-ext
```

### Subdirectory CLAUDE.md (scoped rules)

For directories with distinct concerns (a pipeline, an API, a frontend),
copy the relevant template from `claude-framework/templates/` into that
directory and fill in the project-specific sections:

```bash
cp claude-framework/templates/CLAUDE.pipeline.md src/pipelines/CLAUDE.md
cp claude-framework/templates/CLAUDE.api.md src/api/CLAUDE.md
cp claude-framework/templates/CLAUDE.frontend.md src/frontend/CLAUDE.md
```

Claude Code automatically loads the nearest `CLAUDE.md` when working in a
subdirectory.

---

## Keeping the framework up to date

Pull the latest org changes into your project:

```bash
git submodule update --remote --merge claude-framework
git add claude-framework
git commit -m "chore: update claude-framework to latest"
```

Check the framework's commit history for breaking changes before merging into
production branches.

---

## Repository structure

```
claude-framework/
├── .claude/
│   ├── agents/          ← org-wide sub-agent definitions
│   ├── skills/          ← shared skills (ocbc-frontend, ...)
│   └── settings.json    ← org-wide tool permissions (reference/copy)
├── templates/
│   ├── CLAUDE.pipeline.md   ← starter rules for ML pipeline directories
│   ├── CLAUDE.api.md        ← starter rules for FastAPI service directories
│   └── CLAUDE.frontend.md   ← starter rules for React frontend directories
├── .claudeignore        ← org-wide codebase ignore rules (reference/copy)
├── CLAUDE.md            ← org-wide base rules (@-import this, do not copy)
├── setup.sh             ← bootstrap script
└── README.md
```

---

## Ownership

Maintained by the OCBC AI Lab. Raise issues or PRs via GitHub.
