"""
Tests pour utils/auth.py — authentification, sessions, mots de passe
"""
import os
from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException

os.environ.setdefault("AUTH_PASSWORD", "testpass")
os.environ.setdefault("AUTH_USERNAME", "admin")
os.environ.setdefault("SECRET_KEY", "testsecret")

from utils.auth import (
    authenticate_user,
    generate_session_secret,
    get_current_user,
    get_password_hash,
    get_session_secret,
    get_user_credentials,
    require_auth,
    verify_password,
)


# ---------------------------------------------------------------------------
# verify_password / get_password_hash
# ---------------------------------------------------------------------------

class TestPasswordHashing:
    def test_hash_returns_bcrypt_string(self):
        hashed = get_password_hash("mypassword")
        assert hashed.startswith("$2b$")

    def test_verify_correct_password(self):
        hashed = get_password_hash("correct")
        assert verify_password("correct", hashed) is True

    def test_verify_wrong_password(self):
        hashed = get_password_hash("correct")
        assert verify_password("wrong", hashed) is False

    def test_different_hashes_for_same_password(self):
        # bcrypt uses random salt each time
        h1 = get_password_hash("same")
        h2 = get_password_hash("same")
        assert h1 != h2

    def test_verify_empty_password(self):
        hashed = get_password_hash("")
        assert verify_password("", hashed) is True
        assert verify_password("x", hashed) is False


# ---------------------------------------------------------------------------
# get_user_credentials
# ---------------------------------------------------------------------------

class TestGetUserCredentials:
    def test_returns_username_from_env(self, monkeypatch):
        monkeypatch.setenv("AUTH_USERNAME", "testuser")
        monkeypatch.setenv("AUTH_PASSWORD", "testpass")
        creds = get_user_credentials()
        assert creds["username"] == "testuser"

    def test_hashes_plain_password(self, monkeypatch):
        monkeypatch.setenv("AUTH_PASSWORD", "plainpassword")
        creds = get_user_credentials()
        assert creds["hashed_password"].startswith("$2b$")

    def test_keeps_already_hashed_password(self, monkeypatch):
        hashed = get_password_hash("mypass")
        monkeypatch.setenv("AUTH_PASSWORD", hashed)
        creds = get_user_credentials()
        assert creds["hashed_password"] == hashed

    def test_default_username_is_admin(self, monkeypatch):
        monkeypatch.delenv("AUTH_USERNAME", raising=False)
        creds = get_user_credentials()
        assert creds["username"] == "admin"

    def test_returns_dict_with_required_keys(self, monkeypatch):
        monkeypatch.setenv("AUTH_USERNAME", "u")
        monkeypatch.setenv("AUTH_PASSWORD", "p")
        creds = get_user_credentials()
        assert "username" in creds
        assert "hashed_password" in creds


# ---------------------------------------------------------------------------
# authenticate_user
# ---------------------------------------------------------------------------

class TestAuthenticateUser:
    def test_valid_credentials_returns_true(self, monkeypatch):
        monkeypatch.setenv("AUTH_USERNAME", "admin")
        monkeypatch.setenv("AUTH_PASSWORD", "testpass")
        assert authenticate_user("admin", "testpass") is True

    def test_wrong_password_returns_false(self, monkeypatch):
        monkeypatch.setenv("AUTH_USERNAME", "admin")
        monkeypatch.setenv("AUTH_PASSWORD", "correctpass")
        assert authenticate_user("admin", "wrongpass") is False

    def test_wrong_username_returns_false(self, monkeypatch):
        monkeypatch.setenv("AUTH_USERNAME", "admin")
        monkeypatch.setenv("AUTH_PASSWORD", "pass")
        assert authenticate_user("notadmin", "pass") is False

    def test_both_wrong_returns_false(self, monkeypatch):
        monkeypatch.setenv("AUTH_USERNAME", "admin")
        monkeypatch.setenv("AUTH_PASSWORD", "pass")
        assert authenticate_user("nobody", "badpass") is False

    def test_case_sensitive_username(self, monkeypatch):
        monkeypatch.setenv("AUTH_USERNAME", "Admin")
        monkeypatch.setenv("AUTH_PASSWORD", "pass")
        assert authenticate_user("admin", "pass") is False


# ---------------------------------------------------------------------------
# get_current_user
# ---------------------------------------------------------------------------

class TestGetCurrentUser:
    def test_returns_user_from_session(self):
        mock_request = MagicMock()
        mock_request.session.get.return_value = "alice"
        assert get_current_user(mock_request) == "alice"

    def test_returns_none_when_not_in_session(self):
        mock_request = MagicMock()
        mock_request.session.get.return_value = None
        assert get_current_user(mock_request) is None

    def test_calls_session_get_with_user_key(self):
        mock_request = MagicMock()
        mock_request.session.get.return_value = "bob"
        get_current_user(mock_request)
        mock_request.session.get.assert_called_once_with("user")


# ---------------------------------------------------------------------------
# require_auth
# ---------------------------------------------------------------------------

class TestRequireAuth:
    def test_returns_user_when_authenticated(self):
        mock_request = MagicMock()
        mock_request.session.get.return_value = "alice"
        result = require_auth(mock_request)
        assert result == "alice"

    def test_raises_401_when_not_authenticated(self):
        mock_request = MagicMock()
        mock_request.session.get.return_value = None
        with pytest.raises(HTTPException) as exc_info:
            require_auth(mock_request)
        assert exc_info.value.status_code == 401

    def test_exception_detail_mentions_connexion(self):
        mock_request = MagicMock()
        mock_request.session.get.return_value = None
        with pytest.raises(HTTPException) as exc_info:
            require_auth(mock_request)
        assert "connect" in exc_info.value.detail.lower() or "authentif" in exc_info.value.detail.lower()


# ---------------------------------------------------------------------------
# generate_session_secret / get_session_secret
# ---------------------------------------------------------------------------

class TestSessionSecret:
    def test_generate_returns_string(self):
        secret = generate_session_secret()
        assert isinstance(secret, str)
        assert len(secret) > 0

    def test_generate_returns_different_values(self):
        s1 = generate_session_secret()
        s2 = generate_session_secret()
        assert s1 != s2

    def test_get_session_secret_reads_from_env(self, monkeypatch):
        monkeypatch.setenv("SESSION_SECRET", "my-env-secret")
        result = get_session_secret()
        assert result == "my-env-secret"

    def test_get_session_secret_generates_when_not_set(self, monkeypatch):
        monkeypatch.delenv("SESSION_SECRET", raising=False)
        result = get_session_secret()
        assert isinstance(result, str)
        assert len(result) > 0

    def test_generated_secret_is_urlsafe(self, monkeypatch):
        monkeypatch.delenv("SESSION_SECRET", raising=False)
        result = get_session_secret()
        # urlsafe base64 only contains these chars
        import re
        assert re.match(r'^[A-Za-z0-9_\-]+$', result)
