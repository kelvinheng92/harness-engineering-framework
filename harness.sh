#!/usr/bin/env bash
# harness.sh — OCBC Claude Code Framework management script
#
# Usage (from your project root):
#   bash claude-framework/harness.sh          # bootstrap (default)
#   bash claude-framework/harness.sh setup    # bootstrap a project
#   bash claude-framework/harness.sh sync     # detect settings drift after an update

set -euo pipefail

FRAMEWORK_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(pwd)"
CLAUDE_DIR="$PROJECT_ROOT/.claude"
FRAMEWORK_VERSION="$(cat "$FRAMEWORK_DIR/VERSION" 2>/dev/null || echo "unknown")"

CMD="${1:-setup}"

# ─────────────────────────────────────────────────────────────────────────────
cmd_setup() {
    echo "OCBC Claude Code Framework v$FRAMEWORK_VERSION — project setup"
    echo "Framework : $FRAMEWORK_DIR"
    echo "Project   : $PROJECT_ROOT"
    echo ""

    # ── 1. Agents ────────────────────────────────────────────────────────────
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

    # ── 2. Skills ────────────────────────────────────────────────────────────
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

    # ── 3. CLAUDE.md ─────────────────────────────────────────────────────────
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

    # ── 4. settings.json ─────────────────────────────────────────────────────
    SETTINGS="$CLAUDE_DIR/settings.json"
    if [ -f "$SETTINGS" ]; then
        echo "  [skip]   .claude/settings.json (already exists)"
    else
        cp "$FRAMEWORK_DIR/.claude/settings.json" "$SETTINGS"
        echo "# framework-version: $FRAMEWORK_VERSION" > "$CLAUDE_DIR/.settings-version"
        echo "  [copied] .claude/settings.json (from framework v$FRAMEWORK_VERSION)"
    fi
    echo ""

    # ── 5. .claudeignore ─────────────────────────────────────────────────────
    IGNORE="$PROJECT_ROOT/.claudeignore"
    if [ -f "$IGNORE" ]; then
        echo "  [skip]   .claudeignore (already exists)"
    else
        cp "$FRAMEWORK_DIR/.claudeignore" "$IGNORE"
        echo "  [copied] .claudeignore — add project-specific patterns as needed"
    fi
    echo ""

    # ── Done ─────────────────────────────────────────────────────────────────
    echo "Setup complete. Next steps:"
    echo "  1. Edit CLAUDE.md — fill in the project identity section"
    echo "  2. Edit .claude/settings.json — add any project-specific allow/deny rules"
    echo "  3. Add project-specific agents to .claude/agents/ alongside the symlinks"
    echo "  4. Copy a template from $rel_framework/templates/ into any subdirectory"
    echo "     that needs scoped rules (e.g. src/pipelines/CLAUDE.md)"
    echo ""
    echo "To check for settings drift after future framework updates, run:"
    echo "  bash $rel_framework/harness.sh sync"
}

# ─────────────────────────────────────────────────────────────────────────────
cmd_sync() {
    COPIED_VERSION="$(cat "$CLAUDE_DIR/.settings-version" 2>/dev/null | grep -o '[0-9].*' || echo "unknown")"

    echo "OCBC Claude Code Framework — sync check"
    echo "Framework version : $FRAMEWORK_VERSION"
    echo "Copied from       : $COPIED_VERSION"
    echo ""

    # ── settings.json diff ───────────────────────────────────────────────────
    SETTINGS="$CLAUDE_DIR/settings.json"
    ORG_SETTINGS="$FRAMEWORK_DIR/.claude/settings.json"

    if [ ! -f "$SETTINGS" ]; then
        echo "  [warn] .claude/settings.json not found — run: bash harness.sh setup"
    elif diff -q "$SETTINGS" "$ORG_SETTINGS" > /dev/null 2>&1; then
        echo "  [ok]   .claude/settings.json — no drift"
    else
        echo "  [diff] .claude/settings.json — changes detected:"
        echo ""
        diff --unified=3 "$SETTINGS" "$ORG_SETTINGS" \
            --label "your .claude/settings.json" \
            --label "framework .claude/settings.json" || true
        echo ""
        echo "  Review the diff above. Pay attention to new entries in the 'deny'"
        echo "  list — these reflect org security decisions and should be merged"
        echo "  into your copy. New 'allow' entries are optional."
    fi
    echo ""

    # ── .claudeignore diff ───────────────────────────────────────────────────
    IGNORE="$PROJECT_ROOT/.claudeignore"
    ORG_IGNORE="$FRAMEWORK_DIR/.claudeignore"

    if [ ! -f "$IGNORE" ]; then
        echo "  [warn] .claudeignore not found — run: bash harness.sh setup"
    elif diff -q "$IGNORE" "$ORG_IGNORE" > /dev/null 2>&1; then
        echo "  [ok]   .claudeignore — no drift"
    else
        echo "  [diff] .claudeignore — new org patterns available:"
        diff --unified=3 "$IGNORE" "$ORG_IGNORE" \
            --label "your .claudeignore" \
            --label "framework .claudeignore" || true
        echo ""
        echo "  Consider adding new framework patterns above your project-specific ones."
    fi
    echo ""

    # ── Agent symlink health ──────────────────────────────────────────────────
    echo "  Checking agent symlinks..."
    broken=0
    for agent_dst in "$CLAUDE_DIR/agents/"*.md; do
        [ -e "$agent_dst" ] || continue
        if [ -L "$agent_dst" ] && [ ! -e "$agent_dst" ]; then
            echo "  [broken] $(basename "$agent_dst") — symlink target missing (re-run: bash harness.sh setup)"
            broken=$((broken + 1))
        fi
    done
    if [ "$broken" -eq 0 ]; then
        echo "  [ok]   All agent symlinks are healthy"
    fi
    echo ""

    # ── New agents available ──────────────────────────────────────────────────
    echo "  Checking for new org agents..."
    new_agents=0
    for agent_src in "$FRAMEWORK_DIR/.claude/agents/"*.md; do
        [ -e "$agent_src" ] || continue
        agent_name="$(basename "$agent_src")"
        if [ ! -e "$CLAUDE_DIR/agents/$agent_name" ]; then
            echo "  [new]  agents/$agent_name — not yet linked (run: bash harness.sh setup)"
            new_agents=$((new_agents + 1))
        fi
    done
    if [ "$new_agents" -eq 0 ]; then
        echo "  [ok]   All org agents are linked"
    fi
    echo ""

    # ── New skills available ──────────────────────────────────────────────────
    echo "  Checking for new org skills..."
    new_skills=0
    for skill_src in "$FRAMEWORK_DIR/.claude/skills/"*/; do
        [ -e "$skill_src" ] || continue
        skill_name="$(basename "$skill_src")"
        if [ ! -e "$CLAUDE_DIR/skills/$skill_name" ]; then
            echo "  [new]  skills/$skill_name — not yet linked (run: bash harness.sh setup)"
            new_skills=$((new_skills + 1))
        fi
    done
    if [ "$new_skills" -eq 0 ]; then
        echo "  [ok]   All org skills are linked"
    fi
    echo ""

    echo "Sync check complete."
}

# ─────────────────────────────────────────────────────────────────────────────
case "$CMD" in
    setup)  cmd_setup ;;
    sync)   cmd_sync  ;;
    *)
        echo "Usage: bash claude-framework/harness.sh [setup|sync]"
        echo ""
        echo "  setup   Bootstrap a project with the OCBC Claude Code framework (default)"
        echo "  sync    Detect settings drift after a framework update"
        exit 1
        ;;
esac
