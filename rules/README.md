# Rules

Constraint definitions for the OCBC Claude Code Framework. Rules define hard boundaries and requirements that apply across all projects and agents.

## Purpose

Rules complement `CLAUDE.md` memory by providing explicit, structured constraint definitions that can be versioned, referenced, and extended per project or domain.

## Structure

```
rules/
├── README.md          ← this file
└── code-standards.md  ← Python, Git, and general coding constraints
```

## How to use

Reference rules from your project `CLAUDE.md` or subdirectory `CLAUDE.md` files using `@`-imports:

```markdown
@claude-framework/rules/code-standards.md
```

## Adding project-specific rules

Create a `rules/` directory in your project and define constraints scoped to that repo:

```
<project>/
└── rules/
    └── model-governance.md   ← e.g. MLflow experiment tracking requirements
```
