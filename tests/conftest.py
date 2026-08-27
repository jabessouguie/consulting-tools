"""
Shared pytest fixtures for Consulting Tools test suite.
"""
import pytest
from unittest.mock import patch

from routers.shared import limiter

# Le rate limiting est desactive pour toute la suite : sinon un test qui appelle
# un endpoint limite plusieurs fois (ou plusieurs tests visant le meme endpoint)
# recoit un 429 selon l'ordre d'execution, ce qui rend la suite non
# deterministe. Le comportement de limitation se teste explicitement, pas
# incidemment.
limiter.enabled = False


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
    with patch("app.get_current_user", return_value="test_admin"), \
         patch("routers.auth.get_current_user", return_value="test_admin"), \
         patch("routers.meeting_capture.get_current_user", return_value="test_admin"), \
         patch("routers.skills_market.get_current_user", return_value="test_admin"), \
         patch("routers.tenderscout.get_current_user", return_value="test_admin"):
        yield
