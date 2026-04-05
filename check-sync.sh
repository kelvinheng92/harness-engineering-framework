#!/usr/bin/env bash
# check-sync.sh — Detect settings drift after a framework update
#
# Usage (from your project root):
#   bash claude-framework/check-sync.sh
#
# Run this after pulling a new framework version to see what changed
# in the org baseline that you may need to merge into your copy.

set -euo pipefail

FRAMEWORK_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(pwd)"
CLAUDE_DIR="$PROJECT_ROOT/.claude"
FRAMEWORK_VERSION="$(cat "$FRAMEWORK_DIR/VERSION" 2>/dev/null || echo "unknown")"
COPIED_VERSION="$(cat "$CLAUDE_DIR/.settings-version" 2>/dev/null | grep -o '[0-9].*' || echo "unknown")"

echo "OCBC Claude Code Framework — sync check"
echo "Framework version : $FRAMEWORK_VERSION"
echo "Copied from       : $COPIED_VERSION"
echo ""

# ── settings.json diff ───────────────────────────────────────────────────────
SETTINGS="$CLAUDE_DIR/settings.json"
ORG_SETTINGS="$FRAMEWORK_DIR/.claude/settings.json"

if [ ! -f "$SETTINGS" ]; then
    echo "  [warn] .claude/settings.json not found — run setup.sh first"
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

# ── .claudeignore diff ───────────────────────────────────────────────────────
IGNORE="$PROJECT_ROOT/.claudeignore"
ORG_IGNORE="$FRAMEWORK_DIR/.claudeignore"

if [ ! -f "$IGNORE" ]; then
    echo "  [warn] .claudeignore not found — run setup.sh first"
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

# ── Agent symlink health ──────────────────────────────────────────────────────
echo "  Checking agent symlinks..."
broken=0
for agent_dst in "$CLAUDE_DIR/agents/"*.md; do
    [ -e "$agent_dst" ] || continue
    if [ -L "$agent_dst" ] && [ ! -e "$agent_dst" ]; then
        echo "  [broken] $(basename "$agent_dst") — symlink target missing (re-run setup.sh)"
        broken=$((broken + 1))
    fi
done
if [ "$broken" -eq 0 ]; then
    echo "  [ok]   All agent symlinks are healthy"
fi
echo ""

# ── New agents available ──────────────────────────────────────────────────────
echo "  Checking for new org agents..."
new_agents=0
for agent_src in "$FRAMEWORK_DIR/.claude/agents/"*.md; do
    [ -e "$agent_src" ] || continue
    agent_name="$(basename "$agent_src")"
    if [ ! -e "$CLAUDE_DIR/agents/$agent_name" ]; then
        echo "  [new]  agents/$agent_name — not yet linked (run setup.sh to add)"
        new_agents=$((new_agents + 1))
    fi
done
if [ "$new_agents" -eq 0 ]; then
    echo "  [ok]   All org agents are linked"
fi
echo ""

# ── New skills available ──────────────────────────────────────────────────────
echo "  Checking for new org skills..."
new_skills=0
for skill_src in "$FRAMEWORK_DIR/.claude/skills/"*/; do
    [ -e "$skill_src" ] || continue
    skill_name="$(basename "$skill_src")"
    if [ ! -e "$CLAUDE_DIR/skills/$skill_name" ]; then
        echo "  [new]  skills/$skill_name — not yet linked (run setup.sh to add)"
        new_skills=$((new_skills + 1))
    fi
done
if [ "$new_skills" -eq 0 ]; then
    echo "  [ok]   All org skills are linked"
fi
echo ""

echo "Sync check complete."
