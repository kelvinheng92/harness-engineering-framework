# API Rules

@claude-framework/CLAUDE.md

---

## Service identity

<!-- What this service does and who calls it. -->
<!-- Example: Internal scoring API consumed by the RM portal and batch pipelines. -->

## Stack

<!-- FastAPI version, auth method, DB, deployment target. -->
<!-- Example: FastAPI 0.111, OCBC SSO JWT, PostgreSQL 15, deployed to internal K8s cluster -->

---

## API-specific rules

### Authentication & authorisation

- All endpoints (except `/health` and `/metrics`) must validate OCBC SSO JWTs via the shared `ocbc_auth` middleware
- Reject requests with expired, malformed, or unsigned tokens with `HTTP 401`
- Role-based access checks must happen in a dependency, not inline in the route handler
- Never log the raw JWT or any claim that contains **PII**

### Request / response contracts

- Every request body and response body must have a Pydantic model — no `dict` or `Any` returns
- Response models must never surface raw model scores; wrap in a domain object (e.g. `ScoreResponse`)
- Use `response_model_exclude_unset=True` to avoid leaking default field values
- Version all routes under `/v1/`, `/v2/` — never break an existing versioned path

### Observability

- Bind `request_id` (from `X-Request-ID` header, generate if absent) and `user_id` to every `structlog` entry
- Log request method, path, status code, and latency on every response via middleware — not per-route
- Never log request or response bodies that may contain PII; log field names and counts only
- Expose Prometheus metrics at `/metrics` (request count, latency histogram, error rate)

### Error handling

- Return RFC 7807-style error bodies: `{ "type", "title", "status", "detail", "instance" }`
- Map domain exceptions to HTTP status codes in a central exception handler, not in route functions
- Never expose internal stack traces or system paths in error responses
- `HTTP 422` for validation errors (Pydantic handles this); `HTTP 500` only for truly unexpected failures

### Data safety

- Mask account numbers in all responses: show last 4 digits only (`XXX-XXXXX-1234`)
- Do not return more fields than the caller's role permits — filter in the response model, not the DB query
- Inputs that reference customer or account identifiers must be validated against an allowlist pattern before use

### Performance

- Set explicit request timeouts; never let downstream calls block indefinitely
- Use async route handlers (`async def`) for any I/O-bound operation (DB, model inference, upstream API)
- Cache expensive read-only lookups (e.g. feature store reads) with a short TTL; document the TTL in the code

### Testing

- Unit-test all business logic in isolation (mock DB and model calls)
- Integration tests must use a dedicated test database, never production
- Include a contract test for each Pydantic model to catch silent schema drift
- Health check endpoint `GET /health` must return `{ "status": "ok" }` with `HTTP 200`
