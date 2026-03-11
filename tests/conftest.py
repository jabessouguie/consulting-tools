"""
Shared pytest fixtures for Consulting Tools test suite.
"""
import pytest
from unittest.mock import patch


@pytest.fixture(autouse=True)
def mock_auth_for_tests():
    """
    Patch get_current_user in the app module so all route tests bypass
    AuthMiddleware without needing real credentials.

    Tests that explicitly test unauthenticated behaviour (expecting 401/302)
    can override this by re-patching inside the test body:
        with patch("app.get_current_user", return_value=None): ...
    The inner patch takes precedence over this autouse fixture.
    """
    with patch("app.get_current_user", return_value="test_admin"):
        yield
