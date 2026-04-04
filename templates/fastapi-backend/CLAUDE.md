# [Project Name] — Backend API

> Extends: ~/claude-framework/claude-config/CLAUDE.md
> Project type: FastAPI backend / ML serving
> Data classification: [INTERNAL / CONFIDENTIAL / SECRET — fill in]
> Owner: [DS/engineer name] | [team]
> Last updated: [date]

---

## Project context

[Describe the API in 2–3 sentences. e.g.:
"REST API that exposes the corporate credit scoring model to the RM portal.
Accepts financial statement inputs, calls the internal ML serving endpoint,
and returns structured risk assessment outputs."]

---

## API standards

### Framework & libraries

- FastAPI 0.110+ with Pydantic v2 for request/response models
- `uvicorn` as ASGI server in development; `gunicorn + uvicorn workers` in prod
- `structlog` for structured JSON logging
- `prometheus-fastapi-instrumentator` for metrics
- `httpx` for internal service calls (not `requests`)

### Project structure

```
project/
├── CLAUDE.md
├── pyproject.toml
├── src/
│   ├── api/
│   │   ├── main.py          ← FastAPI app factory
│   │   ├── routers/         ← one file per resource group
│   │   ├── models/          ← Pydantic request/response schemas
│   │   └── dependencies.py  ← shared FastAPI deps (auth, db, etc.)
│   ├── services/            ← business logic (no FastAPI imports here)
│   ├── clients/             ← internal service clients (MLflow, HDFS, etc.)
│   └── config.py            ← settings via pydantic-settings + env vars
├── tests/
│   ├── unit/
│   └── integration/
├── Dockerfile
└── configs/
    ├── dev.env.example      ← env var template (no real values)
    └── prod.env.example
```

### Security requirements — mandatory

Every endpoint must have:

1. **Authentication** — validate the internal OCBC SSO JWT token
   ```python
   from src.api.dependencies import require_auth
   @router.get("/score", dependencies=[Depends(require_auth)])
   ```

2. **Input validation** — Pydantic models with strict field constraints;
   no raw dict or `Any` types in request models

3. **Audit logging** — every prediction/decision logged to the audit table:
   - `request_id`, `user_id`, `endpoint`, `timestamp`, `input_hash`,
     `output_summary`  
   - Never log raw input values that may contain PII

4. **Rate limiting** — use the internal rate-limit middleware; default
   100 req/min per authenticated user

5. **No PII in logs or responses** — mask or hash any customer identifiers
   before logging; strip from error messages

### Response schema conventions

```python
# All responses wrapped in a standard envelope
class APIResponse(BaseModel):
    request_id: str
    status: Literal["success", "error"]
    data: YourDataModel | None = None
    error: str | None = None
    metadata: dict = {}
```

---

## Internal service endpoints

| Service | URL | Notes |
|---|---|---|
| ML serving | `http://mlflow-serving.internal:5000` | Internal model API |
| Feature store | `http://feast.internal:6566` | Feature retrieval |
| Auth service | `http://sso.internal/validate` | JWT validation |
| Vault | `http://vault.internal:8200` | Secrets |

---

## Running locally

```bash
# Install deps
uv sync

# Set env vars (copy from template, fill in dev values — no prod creds locally)
cp configs/dev.env.example .env

# Start dev server
uvicorn src.api.main:app --reload --port 8000

# Run tests
pytest tests/ -v --cov=src

# Lint
ruff check . && mypy src/
```

---

## Things Claude should flag in this project

- Any endpoint missing authentication
- Logging raw request bodies (may contain PII)
- Hardcoded URLs or credentials (use `src/config.py` + env vars)
- `response_model=None` or untyped return values
- Calling external (non-internal) URLs from endpoint handlers
