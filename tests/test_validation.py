"""
Tests unitaires pour le module validation
"""

import os
import sys

import pytest

# Fix import order
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.validation import (  # noqa: E402
    ValidationError,
    sanitize_filename,
    sanitize_text_input,
    sanitize_url,
    validate_email,
)


class TestValidateEmail:
    """Tests pour validate_email"""

    def test_valid_email(self):
        """Test email valide"""
        assert validate_email("user@example.com") is True
        assert validate_email("test.user@domain.co.uk") is True
        assert validate_email("user+tag@example.com") is True

    def test_invalid_email(self):
        """Test email invalide"""
        assert validate_email("invalid") is False
        assert validate_email("@example.com") is False
        assert validate_email("user@") is False
        assert validate_email("") is False


class TestSanitizeUrl:
    """Tests pour sanitize_url"""

    def test_valid_http_url(self):
        """Test URL HTTP valide"""
        result = sanitize_url("http://example.com")
        assert result == "http://example.com"

    def test_valid_https_url(self):
        """Test URL HTTPS valide"""
        result = sanitize_url("https://example.com")
        assert result == "https://example.com"

    def test_invalid_protocol(self):
        """Test URL avec protocole invalide"""
        with pytest.raises(ValidationError):
            sanitize_url("ftp://example.com")

    def test_empty_url(self):
        """Test URL vide"""
        with pytest.raises(ValidationError):
            sanitize_url("")


class TestSanitizeTextInput:
    """Tests pour sanitize_text_input"""

    def test_sanitize_normal_text(self):
        """Test sanitization texte normal"""
        result = sanitize_text_input("Hello World")
        assert result == "Hello World"

    def test_sanitize_empty_string(self):
        """Test chaîne vide"""
        result = sanitize_text_input("")
        assert result == ""

    def test_sanitize_with_max_length(self):
        """Test troncature selon max_length"""
        long_text = "a" * 1000
        with pytest.raises(ValidationError):
            sanitize_text_input(long_text, max_length=100)

    def test_sanitize_strips_whitespace(self):
        """Test que les espaces sont retirés"""
        result = sanitize_text_input("  hello  ")
        assert result == "hello"


class TestSanitizeFilename:
    """Tests pour sanitize_filename"""

    def test_sanitize_normal_filename(self):
        """Test nom de fichier normal"""
        result = sanitize_filename("document.pdf")
        assert result == "document.pdf"

    def test_sanitize_removes_path_traversal(self):
        """Test que les path traversal sont bloqués"""
        result = sanitize_filename("../../../etc/passwd")
        assert ".." not in result
        assert "/" not in result

    def test_sanitize_empty_filename(self):
        """Test nom de fichier vide"""
        result = sanitize_filename("")
        assert result == "unknown"

    def test_sanitize_long_filename(self):
        """Test nom de fichier trop long"""
        long_name = "a" * 300 + ".txt"
        result = sanitize_filename(long_name)
        assert len(result) <= 255
        assert result.endswith(".txt")
