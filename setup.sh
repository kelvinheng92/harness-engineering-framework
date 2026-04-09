#!/usr/bin/env bash
# setup.sh — Bootstrap a project with the OCBC Claude Code framework
#
# Usage (from your project root, after adding the submodule):
#   bash claude-framework/setup.sh
#
# What it does:
#   1. Creates .claude/agents/ and symlinks all org-wide agents into it
#   2. Creates .claude/skills/ and symlinks all org-wide skills into it
#   3. Creates a starter CLAUDE.md that @-imports the org base rules
#   4. Copies settings.json and .claudeignore as editable starting points
#
# Run it once. Re-running is safe — it never overwrites files you've
# already customised.

set -euo pipefail

FRAMEWORK_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(pwd)"
CLAUDE_DIR="$PROJECT_ROOT/.claude"
FRAMEWORK_VERSION="$(cat "$FRAMEWORK_DIR/VERSION" 2>/dev/null || echo "unknown")"

echo "OCBC Claude Code Framework v$FRAMEWORK_VERSION — project setup"
echo "Framework : $FRAMEWORK_DIR"
echo "Project   : $PROJECT_ROOT"
echo ""

# ── 1. Agents ────────────────────────────────────────────────────────────────
mkdir -p "$CLAUDE_DIR/agents"

linked=0
for agent_src in "$FRAMEWORK_DIR/.claude/agents/"*.md; do
    [ -e "$agent_src" ] || continue
    agent_name="$(basename "$agent_src")"
    agent_dst="$CLAUDE_DIR/agents/$agent_name"

    if [ -e "$agent_dst" ]; then
        echo "  [skip]   agents/$agent_name (already exists)"
    else
        rel_src="$(python3 -c "import os; print(os.path.relpath('$agent_src', '$CLAUDE_DIR/agents'))")"
        ln -s "$rel_src" "$agent_dst"
        echo "  [linked] agents/$agent_name"
        linked=$((linked + 1))
    fi
done
echo "  $linked org agent(s) linked."
echo ""

# ── 2. Skills ────────────────────────────────────────────────────────────────
mkdir -p "$CLAUDE_DIR/skills"

linked_skills=0
for skill_src in "$FRAMEWORK_DIR/.claude/skills/"*/; do
    [ -e "$skill_src" ] || continue
    skill_name="$(basename "$skill_src")"
    skill_dst="$CLAUDE_DIR/skills/$skill_name"

    if [ -e "$skill_dst" ]; then
        echo "  [skip]   skills/$skill_name (already exists)"
    else
        rel_src="$(python3 -c "import os; print(os.path.relpath('$skill_src', '$CLAUDE_DIR/skills'))")"
        ln -s "$rel_src" "$skill_dst"
        echo "  [linked] skills/$skill_name"
        linked_skills=$((linked_skills + 1))
    fi
done
echo "  $linked_skills org skill(s) linked."
echo ""

# ── 3. CLAUDE.md ─────────────────────────────────────────────────────────────
CLAUDE_MD="$PROJECT_ROOT/CLAUDE.md"
rel_framework="$(python3 -c "import os; print(os.path.relpath('$FRAMEWORK_DIR', '$PROJECT_ROOT'))")"

if [ -f "$CLAUDE_MD" ]; then
    echo "  [skip]   CLAUDE.md (already exists — add the @-import manually if needed)"
else
    cat > "$CLAUDE_MD" <<EOF
# Project Rules
# Base org rules are imported below — do NOT remove the @import line.
# Add project-specific rules underneath it.

@$rel_framework/CLAUDE.md

---

## Project identity

<!-- Describe this project: what it does, the team, the stack. -->

## Project-specific rules

<!-- Add rules that apply only to this repo here. -->
EOF
    echo "  [created] CLAUDE.md (imports org base via @$rel_framework/CLAUDE.md)"
fi
echo ""

# ── 4. settings.json ─────────────────────────────────────────────────────────
SETTINGS="$CLAUDE_DIR/settings.json"
if [ -f "$SETTINGS" ]; then
    echo "  [skip]   .claude/settings.json (already exists)"
else
    cp "$FRAMEWORK_DIR/.claude/settings.json" "$SETTINGS"
    # Record which framework version this was copied from
    echo "# framework-version: $FRAMEWORK_VERSION" > "$CLAUDE_DIR/.settings-version"
    echo "  [copied] .claude/settings.json (from framework v$FRAMEWORK_VERSION)"
fi
echo ""

# ── 5. .claudeignore ─────────────────────────────────────────────────────────
IGNORE="$PROJECT_ROOT/.claudeignore"
if [ -f "$IGNORE" ]; then
    echo "  [skip]   .claudeignore (already exists)"
else
    cp "$FRAMEWORK_DIR/.claudeignore" "$IGNORE"
    echo "  [copied] .claudeignore — add project-specific patterns as needed"
fi
echo ""

# ── Done ─────────────────────────────────────────────────────────────────────
echo "Setup complete. Next steps:"
echo "  1. Edit CLAUDE.md — fill in the project identity section"
echo "  2. Edit .claude/settings.json — add any project-specific allow/deny rules"
echo "  3. Add project-specific agents to .claude/agents/ alongside the symlinks"
echo "  4. Copy a template from $rel_framework/templates/ into any subdirectory"
echo "     that needs scoped rules (e.g. src/pipelines/CLAUDE.md)"
echo ""
