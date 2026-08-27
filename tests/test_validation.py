"""
Tests unitaires pour le module validation
"""

import os
import sys

import pytest

# Fix import order
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from unittest.mock import AsyncMock, MagicMock

from fastapi import HTTPException, UploadFile

from utils.validation import (  # noqa: E402
    ValidationError,
    mask_api_key,
    mask_password,
    mask_secret,
    sanitize_error_message,
    sanitize_filename,
    sanitize_text_input,
    sanitize_url,
    validate_description,
    validate_email,
    validate_file_upload,
    validate_title,
    validate_topic,
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

    def test_sanitize_long_filename_no_extension(self):
        # line 156: no extension branch for very long filename
        long_name = "a" * 300
        result = sanitize_filename(long_name)
        assert len(result) <= 255


class TestValidateFileUpload:
    async def test_oversized_file_raises_413(self):
        # lines 77-80
        content = b"x" * (11 * 1024 * 1024)
        mock_file = MagicMock(spec=UploadFile)
        mock_file.filename = "big.pdf"
        mock_file.read = AsyncMock(return_value=content)
        with pytest.raises(HTTPException) as exc_info:
            await validate_file_upload(mock_file)
        assert exc_info.value.status_code == 413

    async def test_empty_file_raises_400(self):
        # line 87
        mock_file = MagicMock(spec=UploadFile)
        mock_file.filename = "empty.pdf"
        mock_file.read = AsyncMock(return_value=b"")
        with pytest.raises(HTTPException) as exc_info:
            await validate_file_upload(mock_file)
        assert exc_info.value.status_code == 400


class TestSanitizeUrlExtra:
    def test_dangerous_javascript_protocol_blocked(self):
        # line 205
        with pytest.raises(ValidationError):
            sanitize_url("https://example.com?url=javascript:alert(1)")

    def test_url_too_long_raises(self):
        # line 209
        long_url = "https://example.com/" + "a" * 2000
        with pytest.raises(ValidationError):
            sanitize_url(long_url)


class TestValidateHelpers:
    def test_validate_topic(self):
        # line 217
        assert validate_topic("IA et Data Science") == "IA et Data Science"

    def test_validate_description(self):
        # line 222
        assert validate_description("Description") == "Description"

    def test_validate_title(self):
        # line 227
        assert validate_title("Mon titre") == "Mon titre"


class TestMaskSecret:
    def test_mask_none_returns_stars(self):
        # lines 252-253
        assert mask_secret(None) == "***"

    def test_mask_empty_returns_stars(self):
        # lines 252-253
        assert mask_secret("") == "***"

    def test_short_secret_fully_masked(self):
        # lines 256-257
        assert mask_secret("abc") == "***"

    def test_long_secret_partially_shown(self):
        # line 260
        result = mask_secret("sk-ant-api-key-1234567890abcdef")
        assert "***" in result
        assert result.startswith("sk-a")

    def test_mask_api_key_delegates(self):
        # line 279
        result = mask_api_key("AIzaSyD1234567890abcdefghij12345")
        assert "***" in result

    def test_mask_password_always_hidden(self):
        # line 293
        assert mask_password("mysecretpassword") == "***"
        assert mask_password(None) == "***"

    def test_sanitize_error_message_masks_tokens(self):
        msg = "Token abc" + "d" * 45 + " is invalid"
        result = sanitize_error_message(msg)
        assert "d" * 45 not in result
