# Changelog

All notable changes to this framework are documented here.
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).
This framework uses [Semantic Versioning](https://semver.org/).

When upgrading, pay attention to changes in the **`deny`** list of
`settings.json` — these reflect org-level security decisions and should
be merged into your project copy.

---

## [1.0.0] — 2026-04-05

### Added
- Org-wide `CLAUDE.md` base rules: data handling, PII policy, code
  standards, response behaviour, and prohibited actions
- 6 specialist sub-agents: `data-analyst`, `backend-developer`,
  `data-scientist`, `frontend-developer`, `product-manager`,
  `quality-assurance`
- Agent model routing — `haiku` for data-analyst and product-manager;
  `sonnet` for all others
- Scoped `tools:` per agent — Bash access limited to the specific
  commands each agent legitimately needs
- `ocbc-frontend` skill with OCBC design tokens, component patterns,
  and design system references
- Project `CLAUDE.md` templates for ML pipelines (`CLAUDE.pipeline.md`),
  FastAPI services (`CLAUDE.api.md`), and React frontends
  (`CLAUDE.frontend.md`)
- `.claudeignore` excluding data files, ML artefacts, build dirs, and logs
- Org-wide `settings.json` with allow/deny tool permission lists and
  `_framework_version` field for drift detection
- `setup.sh` bootstrap script — idempotent, symlinks agents and skills,
  copies editable config files into the consuming project
