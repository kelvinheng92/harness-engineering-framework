# FastAPI Service — Project Rules
# Extends: org-wide CLAUDE.md (do not duplicate those rules here)

## Scope
This directory contains a FastAPI internal service. All endpoints are
internal-only and require OCBC SSO authentication.

## Service-specific standards

### Project layout (required)
```
src/
├── main.py          ← app factory and router registration only
├── routers/         ← route handlers grouped by resource
├── services/        ← business logic; no HTTP or DB concerns
├── models/
│   ├── request.py   ← Pydantic input models
│   └── response.py  ← Pydantic output models
├── db/              ← Hive/Impala connectors
└── config.py        ← pydantic-settings, reads env vars only
```

### Auth
- Every router must depend on the shared `verify_sso_token` dependency
- Never add unauthenticated endpoints — even for health checks, use
  an internal network check rather than skipping auth

### Logging
- Include `request_id` (from header), `endpoint`, and `service` in every
  log context — use `structlog.contextvars.bind_contextvars` in middleware
- Audit-log customer data reads: who accessed, what, when

### Error handling
- Return structured error responses: `{"error": {"code": ..., "message": ...}}`
- Never expose stack traces or internal table names in 4xx/5xx responses

## Allowed agents for this directory
- `backend-developer` — API and service code
- `quality-assurance` — endpoint tests and contract tests
