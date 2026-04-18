# Code Standards

## Git workflow — REQUIRED before any file edit

**Before editing any file**, check what branch you are on:

```bash
git branch --show-current
```

If the current branch is `staging` or `main`, stop and create a branch first:

```bash
git checkout -b feat/<description>   # for new features or additions
git checkout -b fix/<description>    # for bug fixes or corrections
```

Never commit directly to `staging` or `main`. This applies to every change,
including small doc fixes, config tweaks, and chores.

---

## Python

- Type-annotate all function signatures
- Docstrings required for all public functions (Google style)
- Logging via `structlog`, not `print()`
- Use pip for dependency management

## Commits

- Follow Conventional Commits: `feat:`, `fix:`, `chore:`, `docs:`, `refactor:`
- No secrets or data files — `.gitignore` must cover `*.csv`, `*.parquet`, `*.json` data files, `.env`
