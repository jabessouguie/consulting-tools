"""
Tests unitaires pour LinkedInClient
"""

import os

# Add parent dir to path
import sys
from unittest.mock import Mock, patch

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.linkedin_client import (  # noqa: E402
    LinkedInClient,
    has_linkedin_access_token,
    is_linkedin_configured,
)


class TestLinkedInClient:
    """Tests pour LinkedInClient"""

    @patch.dict(
        os.environ,
        {
            "LINKEDIN_CLIENT_ID": "test_client_id",
            "LINKEDIN_CLIENT_SECRET": "test_client_secret",  # pragma: allowlist secret
            "LINKEDIN_REDIRECT_URI": "http://localhost:8000/callback",
        },
    )
    def test_init_with_config(self):
        """Test initialisation avec configuration complète"""
        client = LinkedInClient()
        assert client.client_id == "test_client_id"
        assert client.client_secret == "test_client_secret"
        assert client.redirect_uri == "http://localhost:8000/callback"

    @patch.dict(os.environ, {}, clear=True)
    def test_init_without_config(self):
        """Test initialisation sans configuration"""
        with pytest.raises(ValueError, match="LinkedIn OAuth not configured"):
            LinkedInClient()

    @patch.dict(
        os.environ,
        {
            "LINKEDIN_CLIENT_ID": "test_id",
            "LINKEDIN_CLIENT_SECRET": "test_secret",
            "LINKEDIN_REDIRECT_URI": "http://localhost/callback",
            "LINKEDIN_ACCESS_TOKEN": "test_token",  # pragma: allowlist secret
        },
    )
    def test_is_configured(self):
        """Test vérification configuration"""
        client = LinkedInClient()
        assert client.is_configured() is True

    @patch.dict(
        os.environ,
        {
            "LINKEDIN_CLIENT_ID": "test_id",
            "LINKEDIN_CLIENT_SECRET": "test_secret",
            "LINKEDIN_REDIRECT_URI": "http://localhost/callback",
        },
    )
    def test_is_not_configured(self):
        """Test vérification configuration incomplète"""
        client = LinkedInClient()
        assert client.is_configured() is False

    @patch.dict(
        os.environ,
        {
            "LINKEDIN_CLIENT_ID": "id",
            "LINKEDIN_CLIENT_SECRET": "secret",  # pragma: allowlist secret
            "LINKEDIN_REDIRECT_URI": "http://localhost/callback",
        },
    )
    def test_get_auth_url(self):
        """Test génération URL OAuth"""
        client = LinkedInClient()
        auth_url = client.get_auth_url(state="test_state")

        assert "linkedin.com/oauth/v2/authorization" in auth_url
        assert "client_id=id" in auth_url
        assert "state=test_state" in auth_url
        assert "scope=w_member_social" in auth_url

    @patch.dict(
        os.environ,
        {
            "LINKEDIN_CLIENT_ID": "id",
            "LINKEDIN_CLIENT_SECRET": "secret",
            "LINKEDIN_REDIRECT_URI": "http://localhost/callback",
        },
    )
    @patch("utils.linkedin_client.requests.post")
    def test_exchange_code_success(self, mock_post):
        """Test échange code pour token"""
        mock_response = Mock()
        mock_response.json.return_value = {"access_token": "new_token_123", "expires_in": 5184000}
        mock_response.raise_for_status = Mock()
        mock_post.return_value = mock_response

        client = LinkedInClient()
        result = client.exchange_code_for_token("auth_code_123")

        assert result["access_token"] == "new_token_123"
        assert client.access_token == "new_token_123"
        mock_post.assert_called_once()

    @patch.dict(
        os.environ,
        {
            "LINKEDIN_CLIENT_ID": "id",
            "LINKEDIN_CLIENT_SECRET": "secret",
            "LINKEDIN_REDIRECT_URI": "http://localhost/callback",
            "LINKEDIN_ACCESS_TOKEN": "token",
        },
    )
    @patch("utils.linkedin_client.requests.get")
    def test_get_person_id(self, mock_get):
        """Test récupération person ID"""
        mock_response = Mock()
        mock_response.json.return_value = {"id": "person123"}
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        client = LinkedInClient()
        person_id = client.get_person_id()

        assert person_id == "urn:li:person:person123"
        mock_get.assert_called_once()

    @patch.dict(
        os.environ,
        {
            "LINKEDIN_CLIENT_ID": "id",
            "LINKEDIN_CLIENT_SECRET": "secret",
            "LINKEDIN_REDIRECT_URI": "http://localhost/callback",
        },
    )
    def test_get_person_id_no_token(self):
        """Test get_person_id sans token"""
        client = LinkedInClient()

        with pytest.raises(ValueError, match="No access token"):
            client.get_person_id()

    @patch.dict(
        os.environ,
        {
            "LINKEDIN_CLIENT_ID": "id",
            "LINKEDIN_CLIENT_SECRET": "secret",
            "LINKEDIN_REDIRECT_URI": "http://localhost/callback",
            "LINKEDIN_ACCESS_TOKEN": "token",
        },
    )
    @patch("utils.linkedin_client.requests.get")
    @patch("utils.linkedin_client.requests.post")
    def test_publish_post_success(self, mock_post, mock_get):
        """Test publication post avec succès"""
        # Mock get_person_id
        mock_get_response = Mock()
        mock_get_response.json.return_value = {"id": "person123"}
        mock_get_response.raise_for_status = Mock()
        mock_get.return_value = mock_get_response

        # Mock publish
        mock_post_response = Mock()
        mock_post_response.json.return_value = {"id": "post456"}
        mock_post_response.raise_for_status = Mock()
        mock_post.return_value = mock_post_response

        client = LinkedInClient()
        result = client.publish_post(text="Test post content")

        assert result["id"] == "post456"
        assert result["status"] == "published"
        assert "linkedin.com/feed/update/post456" in result["url"]

    @patch.dict(
        os.environ,
        {
            "LINKEDIN_CLIENT_ID": "id",
            "LINKEDIN_CLIENT_SECRET": "secret",
            "LINKEDIN_REDIRECT_URI": "http://localhost/callback",
        },
    )
    def test_publish_post_no_token(self):
        """Test publish sans token"""
        client = LinkedInClient()

        with pytest.raises(ValueError, match="No access token"):
            client.publish_post(text="Test")

    @patch.dict(
        os.environ,
        {
            "LINKEDIN_CLIENT_ID": "id",
            "LINKEDIN_CLIENT_SECRET": "secret",
            "LINKEDIN_REDIRECT_URI": "http://localhost/callback",
            "LINKEDIN_ACCESS_TOKEN": "token",
        },
    )
    def test_publish_post_too_long(self):
        """Test publication post trop long"""
        client = LinkedInClient()
        long_text = "x" * 3001

        with pytest.raises(ValueError, match="too long"):
            client.publish_post(text=long_text)

    @patch.dict(
        os.environ,
        {
            "LINKEDIN_CLIENT_ID": "id",
            "LINKEDIN_CLIENT_SECRET": "secret",
            "LINKEDIN_REDIRECT_URI": "http://localhost/callback",
        },
    )
    def test_is_linkedin_configured_true(self):
        """Test helper is_linkedin_configured"""
        assert is_linkedin_configured() is True

    @patch.dict(os.environ, {}, clear=True)
    def test_is_linkedin_configured_false(self):
        """Test helper is_linkedin_configured sans config"""
        assert is_linkedin_configured() is False

    @patch.dict(os.environ, {"LINKEDIN_ACCESS_TOKEN": "token"})
    def test_has_access_token_true(self):
        """Test helper has_access_token"""
        assert has_linkedin_access_token() is True

    @patch.dict(os.environ, {}, clear=True)
    def test_has_access_token_false(self):
        """Test helper has_access_token sans token"""
        assert has_linkedin_access_token() is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
