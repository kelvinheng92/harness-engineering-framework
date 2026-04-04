#!/usr/bin/env bash
# setup.sh — Bootstrap a project with the OCBC Claude Code framework
#
# Usage (from your project root, after adding the submodule):
#   bash claude-framework/setup.sh
#
# What it does:
#   1. Creates .claude/agents/ and symlinks all org-wide agents into it
#   2. Creates a starter CLAUDE.md that @-imports the org base rules
#   3. Copies settings.json and .claudeignore as editable starting points
#
# Run it once. Re-running is safe — it never overwrites files you've
# already customised.

set -euo pipefail

FRAMEWORK_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(pwd)"
CLAUDE_DIR="$PROJECT_ROOT/.claude"

echo "OCBC Claude Code Framework — project setup"
echo "Framework : $FRAMEWORK_DIR"
echo "Project   : $PROJECT_ROOT"
echo ""

# ── 1. Agents ────────────────────────────────────────────────────────────────
mkdir -p "$CLAUDE_DIR/agents"

linked=0
for agent_src in "$FRAMEWORK_DIR/.claude/agents/"*.md; do
    agent_name="$(basename "$agent_src")"
    agent_dst="$CLAUDE_DIR/agents/$agent_name"

    if [ -e "$agent_dst" ]; then
        echo "  [skip]   agents/$agent_name (already exists)"
    else
        # Use a path relative to the symlink's location so it survives moves
        rel_src="$(python3 -c "import os; print(os.path.relpath('$agent_src', '$CLAUDE_DIR/agents'))")"
        ln -s "$rel_src" "$agent_dst"
        echo "  [linked] agents/$agent_name"
        linked=$((linked + 1))
    fi
done
echo "  $linked org agent(s) linked."
echo ""

# ── 2. CLAUDE.md ─────────────────────────────────────────────────────────────
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

# ── 3. settings.json ─────────────────────────────────────────────────────────
SETTINGS="$CLAUDE_DIR/settings.json"
if [ -f "$SETTINGS" ]; then
    echo "  [skip]   .claude/settings.json (already exists)"
else
    cp "$FRAMEWORK_DIR/.claude/settings.json" "$SETTINGS"
    echo "  [copied] .claude/settings.json — extend the allow/deny lists as needed"
fi
echo ""

# ── 4. .claudeignore ─────────────────────────────────────────────────────────
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
