---
paths:
  - "tests/**/*.py"
---

# Test Rules

- Never add `@pytest.mark.asyncio` — `asyncio_mode=auto` handles it
- `conftest.py` autouse fixture mocks `app.get_current_user` → `"test_admin"` for all tests
- To test unauthenticated paths: `mocker.patch("app.get_current_user", return_value=None)` inside the test body
- When patching moved code: use the router module path, not `app.*`
  - ✅ `patch("routers.linkedin.LinkedInClient", ...)`
  - ❌ `patch("app.LinkedInClient", ...)`
- Patch target = where the name is **imported**, not where it is **defined**
- The suite is green: 1777+ passing, 0 failures (measured 27/08/2026). A failure is a regression — fix it, do not normalise it
- Rate limiting is disabled suite-wide in `conftest.py` (`limiter.enabled = False`); test it explicitly if you need it
- New tests: mirror existing test file structure, use `AsyncClient` from `httpx` for API tests
