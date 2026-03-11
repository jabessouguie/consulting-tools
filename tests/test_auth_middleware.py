"""
Integration tests for AuthMiddleware (Phase 6).

These tests verify that the AuthMiddleware correctly:
- Allows access to public paths without authentication
- Redirects unauthenticated HTML requests to /login
- Returns 401 for unauthenticated API requests
- Allows authenticated requests through

Note: conftest.py patches app.get_current_user to "test_admin" by default.
Tests that need to simulate unauthenticated access re-patch to None.
"""
import os
import sys
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


CSRF_HEADERS = {"Origin": "http://localhost:8000"}


@pytest.fixture
def sync_client():
    """Synchronous TestClient for middleware testing."""
    from app import app

    return TestClient(app, raise_server_exceptions=False)


class TestAuthMiddlewarePublicPaths:
    """Public paths must be accessible without authentication."""

    def test_login_page_is_public(self, sync_client):
        """GET /login accessible without auth."""
        with patch("app.get_current_user", return_value=None):
            resp = sync_client.get("/login")
        assert resp.status_code == 200

    def test_static_files_are_public(self, sync_client):
        """Static files accessible without auth (404 is fine, not 401/302)."""
        with patch("app.get_current_user", return_value=None):
            resp = sync_client.get("/static/style.css", follow_redirects=False)
        # 200 if file exists, 404 if not — but never 401 or 302 to /login
        assert resp.status_code not in (401, 302)

    def test_auth_oauth_path_is_public(self, sync_client):
        """OAuth callback path accessible without auth."""
        with patch("app.get_current_user", return_value=None):
            # This may return a redirect or error from OAuth, but not an auth redirect
            resp = sync_client.get("/auth/linkedin", follow_redirects=False)
        assert resp.status_code not in (401,)


class TestAuthMiddlewareUnauthenticated:
    """Unauthenticated requests must be blocked."""

    def test_html_route_redirects_to_login(self, sync_client):
        """Unauthenticated access to HTML route → 302 redirect to /login."""
        with patch("app.get_current_user", return_value=None):
            resp = sync_client.get("/", follow_redirects=False)
        assert resp.status_code == 302
        assert "/login" in resp.headers.get("location", "")

    def test_api_route_returns_401(self, sync_client):
        """Unauthenticated access to API route → 401 JSON response."""
        with patch("app.get_current_user", return_value=None):
            resp = sync_client.get("/api/skills-market/import/status")
        assert resp.status_code == 401
        assert resp.json()["detail"] == "Non authentifié"

    def test_api_post_returns_401(self, sync_client):
        """Unauthenticated POST to API route → 401."""
        with patch("app.get_current_user", return_value=None):
            resp = sync_client.post(
                "/api/skills-market/import",
                headers=CSRF_HEADERS,
            )
        assert resp.status_code == 401


class TestAuthMiddlewareAuthenticated:
    """Authenticated requests must pass through."""

    def test_html_route_accessible_when_authenticated(self, sync_client):
        """Authenticated access to HTML route succeeds (autouse mock active)."""
        resp = sync_client.get("/")
        # 200 = loaded, 500 = server error (but NOT 302 to /login)
        assert resp.status_code != 302

    def test_api_route_accessible_when_authenticated(self, sync_client):
        """Authenticated access to API route does not return 401."""
        resp = sync_client.get("/api/skills-market/import/status")
        assert resp.status_code != 401

    def test_user_stored_in_request_state(self, sync_client):
        """After auth, request.state.user equals the authenticated username.
        Verified indirectly: login page redirects to / when already authenticated.
        """
        # When authenticated, GET /login should redirect away (not show login form)
        resp = sync_client.get("/login", follow_redirects=False)
        # The login_page handler checks get_current_user and redirects if logged in
        assert resp.status_code == 302


class TestLoginLogoutFlow:
    """Login and logout endpoint behaviour."""

    def test_login_page_shows_form_when_not_logged_in(self, sync_client):
        """GET /login returns login form when not authenticated."""
        with patch("app.get_current_user", return_value=None):
            resp = sync_client.get("/login")
        assert resp.status_code == 200
        assert "Se connecter" in resp.text

    def test_login_post_with_wrong_credentials_returns_401(self, sync_client):
        """POST /login with wrong credentials → 401."""
        with patch("app.get_current_user", return_value=None):
            with patch("app.authenticate_user", return_value=False):
                resp = sync_client.post(
                    "/login",
                    data={"username": "bad", "password": "wrong"},
                    headers=CSRF_HEADERS,
                )
        assert resp.status_code == 401

    def test_login_post_with_correct_credentials_returns_success(self, sync_client):
        """POST /login with correct credentials → success JSON."""
        with patch("app.get_current_user", return_value=None):
            with patch("app.authenticate_user", return_value=True):
                resp = sync_client.post(
                    "/login",
                    data={"username": "admin", "password": "correct"},
                    headers=CSRF_HEADERS,
                )
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert data["redirect"] == "/"

    def test_logout_redirects_to_login(self, sync_client):
        """GET /logout clears session and redirects to /login."""
        resp = sync_client.get("/logout", follow_redirects=False)
        assert resp.status_code == 302
        assert "/login" in resp.headers.get("location", "")
