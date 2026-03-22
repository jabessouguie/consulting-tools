---
paths:
  - "routers/**/*.py"
---

# Router Rules

- Every router file must `from routers.shared import ...` — never re-import globals from `app.py`
- `router = APIRouter()` — never use `app` directly
- All streaming endpoints use `send_sse(event, data)` from shared.py
- Background thread helpers named `_run_<domain>(job_id, ...)` — must catch `Exception as e` and set `job["status"] = "error"`
- Rate-limited endpoints: `@limiter.limit("N/minute")` before `@router.post/get`
- Auth-gated endpoints: check `get_current_user(request)` and return 401 if None
- Import agents **inside** helper functions (not at module top level) to avoid circular imports
