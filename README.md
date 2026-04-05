# OCBC AI Platform — Claude Code Framework

Centralised standards and tooling for safe, consistent Claude Code use across
the OCBC Data Science team. Consumed as a **git submodule** by individual
project repositories.

**Current version:** see [`VERSION`](./VERSION) — [`CHANGELOG`](./CHANGELOG.md)

---

## What this framework provides

| Component | Location | Purpose |
|-----------|----------|---------|
| Org-wide base rules | `CLAUDE.md` | Data handling, code standards, behaviour guardrails |
| Sub-agents | `.claude/agents/` | 6 specialist agents (data-analyst, backend-developer, data-scientist, frontend-developer, product-manager, quality-assurance) |
| Skills | `.claude/skills/` | Shared skills |
| Ignore rules | `.claudeignore` | Exclusion for claude to ignore |
| Permissions | `.claude/settings.json` | Org-wide allow/deny lists for tool use |
| Bootstrap script | `setup.sh` | One-command project setup |
| Sync checker | `check-sync.sh` | Detects settings drift after framework updates |

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
- `.claude/skills/` — symlinks to all org-wide skills
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
~/.claude/CLAUDE.md               ← user-level (personal preferences)
         │
<project>/CLAUDE.md               ← project-level (your file, @-imports org base)
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

### Skills

`setup.sh` symlinks org-wide skills into `.claude/skills/`. Add project-specific
skills alongside them the same way as agents.

### settings.json

`setup.sh` copies `.claude/settings.json` into your project. Edit it freely —
extend the `allow` and `deny` lists with project-specific tool permissions:

```json
{
  "permissions": {
    "allow": [
      "Bash(git:*)",
      "...all org defaults...",
      "Bash(your-internal-tool:*)"
    ],
    "deny": [
      "...org defaults..."
    ]
  }
}
```

Do **not** remove org `deny` entries — only add to them. New deny rules in the
org baseline reflect security decisions and must be respected.

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
copy the relevant template from `claude-framework/templates/` and fill in the
project-specific sections:

```bash
cp claude-framework/templates/CLAUDE.pipeline.md src/pipelines/CLAUDE.md
cp claude-framework/templates/CLAUDE.api.md src/api/CLAUDE.md
cp claude-framework/templates/CLAUDE.frontend.md src/frontend/CLAUDE.md
```

Claude Code automatically loads the nearest `CLAUDE.md` when working in a
subdirectory.

---

## User-level configuration

There are three distinct levels of Claude Code configuration. Each has a
different scope and owner:

| Level | Location | Controls |
|-------|----------|---------|
| **User** | `~/.claude/CLAUDE.md` | Personal working style, tone, shortcuts — applies across all projects |
| **User** | `~/.claude/settings.local.json` | Personal tool permissions — applies across all projects |
| **Project** | `<project>/CLAUDE.md` | Project rules + `@`-import of org base |
| **Project** | `<project>/.claude/settings.json` | Org baseline + project-specific allows/denies |
| **Subdirectory** | `<project>/src/X/CLAUDE.md` | Scoped rules for a specific area of the repo |

Keep `~/.claude/CLAUDE.md` to personal preferences only — never put org rules
or project rules there, as they would leak into every project you work on.

**Example `~/.claude/CLAUDE.md`:**

```markdown
# Personal preferences
- I prefer terse responses — skip preamble, get to the code
- When in doubt about scope, ask one focused question before proceeding
- Default to structlog for any new logging I write
```

---

## Keeping the framework up to date

### Pull the latest version

```bash
cd claude-framework && git fetch && git checkout v1.0.0   # pin to a tag
# or: git checkout main                                   # always latest
cd ..
git add claude-framework
git commit -m "chore: update claude-framework to v1.0.0"
```

### Check for settings drift

After updating the submodule, run the sync checker to see what changed in
the org baseline that you may need to merge into your project copies:

```bash
bash claude-framework/check-sync.sh
```

It diffs your `settings.json` and `.claudeignore` against the framework
baseline, checks for broken agent/skill symlinks, and lists any new org
agents or skills not yet linked into your project.

Pay particular attention to **new `deny` rules** in `settings.json` — these
reflect org security decisions and should be merged into your copy.

### Versioning

This framework uses [Semantic Versioning](https://semver.org/):

- **Patch** (`1.0.x`) — safe to pull anytime: wording fixes, new agents/skills
- **Minor** (`1.x.0`) — review `CHANGELOG.md` before merging: new deny rules or
  behaviour changes
- **Major** (`x.0.0`) — breaking change; coordinate with AI Lab before upgrading

The current version is in [`VERSION`](./VERSION). The version your project's
`settings.json` was copied from is recorded in `.claude/.settings-version`.

---

## Repository structure

```
claude-framework/
├── .claude/
│   ├── agents/              ← org-wide sub-agent definitions
│   ├── skills/              ← shared skills (ocbc-frontend, ...)
│   └── settings.json        ← org-wide tool permissions (copy via setup.sh)
├── templates/
│   ├── CLAUDE.pipeline.md   ← starter rules for ML pipeline directories
│   ├── CLAUDE.api.md        ← starter rules for FastAPI service directories
│   └── CLAUDE.frontend.md   ← starter rules for React frontend directories
├── .claudeignore            ← org-wide codebase ignore rules (copy via setup.sh)
├── CLAUDE.md                ← org-wide base rules (@-import this, do not copy)
├── CHANGELOG.md             ← version history
├── VERSION                  ← current version number
├── setup.sh                 ← bootstrap script (run once per project)
├── check-sync.sh            ← drift detector (run after framework updates)
└── README.md
```

---

## Ownership

Maintained by the OCBC AI Lab. Raise issues or PRs via GitHub.
