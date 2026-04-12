# API Rules

@claude-framework/CLAUDE.md

---

## Service identity

<!-- What this service does and who calls it. -->
<!-- Example: Internal scoring API consumed by the RM portal and batch pipelines. -->

## Stack

<!-- FastAPI version, auth method, DB, deployment target. -->

## API-specific rules

<!-- Add rules that apply only within this directory. Examples: -->
<!-- - All endpoints require OCBC SSO JWT validation -->
<!-- - Never return raw model scores — wrap in a ScoreResponse schema -->
<!-- - Log request_id and user_id on every request -->
<!-- - Pydantic models for all request/response bodies, no dict returns -->
