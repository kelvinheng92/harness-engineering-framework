# Hooks

Hooks are shell scripts that Claude Code executes automatically at specific lifecycle events — before or after tool calls, on session start, etc.

## Hook events

| Event | Trigger | Common use |
|-------|---------|------------|
| `PreToolUse` | Before any tool call | Validate commands, block dangerous patterns |
| `PostToolUse` | After any tool call | Log activity, run formatters, notify |
| `Notification` | On Claude notification | Route alerts to Slack/Teams |
| `Stop` | Session end | Summarise changes, update task tracker |

## Adding hooks

Place hook scripts in your project's `.claude/hooks/` directory (not this framework folder). Hooks are project-specific and are not symlinked by `setup.sh`.

Register them in your project's `.claude/settings.json`:

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Bash",
        "hooks": [{ "type": "command", "command": "bash .claude/hooks/validate-bash.sh" }]
      }
    ],
    "PostToolUse": [
      {
        "matcher": "Write",
        "hooks": [{ "type": "command", "command": "bash .claude/hooks/post-write.sh" }]
      }
    ]
  }
}
```

## Example hooks (add your own here)

This directory is a placeholder — add project-level hook scripts directly to your project's `.claude/hooks/`. Org-wide hook templates can be added here as the framework grows.
