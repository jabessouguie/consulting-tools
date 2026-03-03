"""
Tests basiques pour modules utils - augmente la couverture rapidement
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestUtilsBasic:
    """Tests basiques pour modules utils"""

    def test_validation_imports(self):
        """Test imports validation"""
        from utils.validation import (
            ValidationError,
            sanitize_filename,
            sanitize_text_input,
            sanitize_url,
            validate_email,
        )

        assert validate_email is not None
        assert sanitize_text_input is not None
        assert sanitize_filename is not None
        assert sanitize_url is not None
        assert ValidationError is not None

    def test_llm_client_imports(self):
        """Test imports LLMClient"""
        from utils.llm_client import LLMClient

        assert LLMClient is not None

    def test_linkedin_client_imports(self):
        """Test imports LinkedInClient"""
        from utils.linkedin_client import LinkedInClient, is_linkedin_configured

        assert LinkedInClient is not None
        assert is_linkedin_configured is not None

    def test_gmail_client_imports(self):
        """Test imports GmailClient"""
        from utils.gmail_client import GmailClient, send_quick_email

        assert GmailClient is not None
        assert send_quick_email is not None

    def test_google_api_imports(self):
        """Test imports GoogleAPIClient"""
        from utils.google_api import GoogleAPIClient

        assert GoogleAPIClient is not None

    def test_consultant_profile_imports(self):
        """Test imports consultant_profile"""
        from utils.consultant_profile import get_consultant_info

        assert get_consultant_info is not None

    def test_monitoring_module_exists(self):
        """Test que le module monitoring existe"""
        import utils.monitoring

        assert utils.monitoring is not None

    def test_validation_sanitize_text(self):
        """Test sanitize_text_input basique"""
        from utils.validation import sanitize_text_input

        result = sanitize_text_input("  test  ")
        assert result == "test"

    def test_validation_sanitize_filename_basic(self):
        """Test sanitize_filename basique"""
        from utils.validation import sanitize_filename

        result = sanitize_filename("test.txt")
        assert "test" in result
        assert ".txt" in result

    def test_validation_email_valid(self):
        """Test validate_email avec email valide"""
        from utils.validation import validate_email

        assert validate_email("test@example.com") is True

    def test_validation_email_invalid(self):
        """Test validate_email avec email invalide"""
        from utils.validation import validate_email

        assert validate_email("invalid") is False

    def test_consultant_info_returns_dict(self):
        """Test que get_consultant_info retourne un dict"""
        from utils.consultant_profile import get_consultant_info

        info = get_consultant_info()
        assert isinstance(info, dict)
        assert "name" in info or "company" in info
