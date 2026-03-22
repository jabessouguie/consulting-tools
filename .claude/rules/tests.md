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
- 66 pre-existing failures are expected — do not try to fix them (test_settings 404s, test_microsoft_api 404s, openpyxl)
- New tests: mirror existing test file structure, use `AsyncClient` from `httpx` for API tests
