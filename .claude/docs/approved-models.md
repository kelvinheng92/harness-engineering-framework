# Approved Models & Usage Policy

Last reviewed: 2026-04-01 | Owner: OCBC AI Lab

---

## Approved Claude models

| Model | API string | Use case | Notes |
|---|---|---|---|
| Claude Opus 4.5 | `claude-opus-4-5` | Complex reasoning, architecture decisions, long-context analysis |
| Claude Sonnet 4.6 | `claude-sonnet-4-6` | Day-to-day coding, explanation, review | Faster and more cost-effective | Default model in `settings.json` |
| Claude Haiku 4.5 | `claude-haiku-4-5-20251001` | Simple tasks, quick lookups, CI automation | Use for high-volume or latency-sensitive tasks |

The `settings.json` in this repo sets `claude-sonnet-4-6` as the default.
Override per-project in your project-level `.claude/settings.json` if
you need a different model.

---

## Model selection guidance

```
Task complexity:
  High (architecture, novel algorithm, >2000 token context)  → Opus
  Medium (typical coding, debugging, code review)            → Sonnet
  Low (boilerplate gen, one-liner fixes, CI checks)          → Haiku
```

Use the lightest model that gets the job done — this reduces both cost
and latency.

---

## What models may be used

Only approved models in the table above may be used for claude code

Using unapproved models bypasses the internal proxy and audit controls.
This is a policy violation regardless of intent.

---

## Context window guidance

| Model | Context window | Practical recommendation |
|---|---|---|
| Opus 4.5 | 200K tokens | Keep prompts under 100K for reliable results |
| Sonnet 4.6 | 200K tokens | Keep prompts under 80K |
| Haiku 4.5 | 200K tokens | Best under 20K for speed |

---

## Extended thinking / reasoning

Claude's extended thinking mode is available on Opus and Sonnet. Use it for:
- Evaluating complex trade-offs in model architecture
- Debugging non-obvious bugs in pipelines
- Reviewing credit logic for edge cases

It consumes significantly more tokens. Do not enable it in automated
CI/CD pipelines.

---