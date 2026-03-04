"""
Tests unitaires pour le module validation
"""

import os
import sys
from unittest.mock import AsyncMock, MagicMock

import pytest

# Fix import order
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.validation import (  # noqa: E402
    MAX_SHORT_INPUT_LENGTH,
    MAX_TEXT_INPUT_LENGTH,
    MAX_UPLOAD_SIZE,
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

    def test_sanitize_filename_replaces_slashes(self):
        """Les slashes sont remplacés par des underscores"""
        result = sanitize_filename("some/path/file.txt")
        assert "/" not in result
        assert "file.txt" in result

    def test_sanitize_filename_special_chars(self):
        """Les caractères spéciaux sont remplacés"""
        result = sanitize_filename("file name!@#.pdf")
        assert "!" not in result
        assert "@" not in result
        assert "#" not in result

    def test_sanitize_filename_removes_backslash_traversal(self):
        """Test backslash path traversal"""
        result = sanitize_filename("..\\etc\\passwd")
        assert "..\\" not in result

    def test_sanitize_filename_long_no_extension(self):
        """Fichier long sans extension"""
        long_name = "a" * 300
        result = sanitize_filename(long_name)
        assert len(result) <= 255


class TestMaskSecret:
    """Tests pour mask_secret"""

    def test_none_returns_stars(self):
        assert mask_secret(None) == "***"

    def test_empty_string_returns_stars(self):
        assert mask_secret("") == "***"

    def test_short_secret_returns_stars(self):
        # len < show_chars*2 + 3 = 4*2+3 = 11
        assert mask_secret("short") == "***"

    def test_long_secret_masks_middle(self):
        result = mask_secret("sk-ant-api-key-12345")
        assert result.startswith("sk-a")
        assert "***" in result
        assert result.endswith("2345")

    def test_custom_show_chars(self):
        result = mask_secret("abcdefghijklmnop", show_chars=2)
        assert result.startswith("ab")
        assert result.endswith("op")
        assert "***" in result

    def test_exactly_at_boundary_returns_stars(self):
        # show_chars=4, boundary = 4*2+3 = 11
        # len == 10 should return "***"
        assert mask_secret("1234567890") == "***"

    def test_just_above_boundary(self):
        # len == 11 exactly at boundary, should show masked
        result = mask_secret("12345678901", show_chars=4)
        assert result != "***"


class TestMaskApiKey:
    """Tests pour mask_api_key"""

    def test_none_api_key(self):
        assert mask_api_key(None) == "***"

    def test_valid_api_key(self):
        result = mask_api_key("sk-ant-api-key-abcdefghijklmnop")
        assert "***" in result
        assert result.startswith("sk-a")

    def test_short_api_key(self):
        assert mask_api_key("short") == "***"


class TestMaskPassword:
    """Tests pour mask_password"""

    def test_none_password(self):
        assert mask_password(None) == "***"

    def test_valid_password(self):
        assert mask_password("SuperSecretPassword123!") == "***"

    def test_empty_password(self):
        assert mask_password("") == "***"


class TestSanitizeErrorMessage:
    """Tests pour sanitize_error_message"""

    def test_plain_message_unchanged(self):
        msg = "Something went wrong"
        result = sanitize_error_message(msg)
        assert result == msg

    def test_masks_anthropic_api_key(self):
        # Anthropic key pattern: sk-ant- followed by 40+ chars
        key = "sk-ant-" + "a" * 45
        msg = "Error with key " + key
        result = sanitize_error_message(msg)
        assert key not in result
        assert "******" in result

    def test_masks_google_api_key(self):
        # Google key: AIza followed by 35+ chars
        key = "AIza" + "B" * 36
        msg = "Failed with " + key
        result = sanitize_error_message(msg)
        assert key not in result
        assert "******" in result

    def test_masks_url_password(self):
        msg = "Connection error: postgres://user:mysecretpassword@localhost/db"
        result = sanitize_error_message(msg)
        assert "mysecretpassword" not in result

    def test_empty_message(self):
        result = sanitize_error_message("")
        assert result == ""


class TestValidateTopic:
    """Tests pour validate_topic"""

    def test_valid_topic(self):
        result = validate_topic("Machine Learning Basics")
        assert result == "Machine Learning Basics"

    def test_empty_topic(self):
        result = validate_topic("")
        assert result == ""

    def test_topic_too_long(self):
        long_topic = "a" * 1001
        with pytest.raises(ValidationError):
            validate_topic(long_topic)

    def test_topic_at_limit(self):
        topic = "a" * 1000
        result = validate_topic(topic)
        assert len(result) == 1000


class TestValidateDescription:
    """Tests pour validate_description"""

    def test_valid_description(self):
        result = validate_description("A detailed description of the topic.")
        assert result == "A detailed description of the topic."

    def test_empty_description(self):
        result = validate_description("")
        assert result == ""

    def test_description_too_long(self):
        long_desc = "a" * 5001
        with pytest.raises(ValidationError):
            validate_description(long_desc)

    def test_description_at_limit(self):
        desc = "a" * 5000
        result = validate_description(desc)
        assert len(result) == 5000


class TestValidateTitle:
    """Tests pour validate_title"""

    def test_valid_title(self):
        result = validate_title("My Report Title")
        assert result == "My Report Title"

    def test_empty_title(self):
        result = validate_title("")
        assert result == ""

    def test_title_too_long(self):
        long_title = "a" * (MAX_SHORT_INPUT_LENGTH + 1)
        with pytest.raises(ValidationError):
            validate_title(long_title)

    def test_title_strips_whitespace(self):
        result = validate_title("  Trimmed  ")
        assert result == "Trimmed"


class TestSanitizeTextInputExtended:
    """Tests supplémentaires pour sanitize_text_input"""

    def test_removes_control_characters(self):
        # \x00 and \x01 are control chars that should be removed
        text = "hello\x00world\x01!"
        result = sanitize_text_input(text)
        assert "\x00" not in result
        assert "\x01" not in result
        assert "hello" in result
        assert "world" in result

    def test_preserves_newline_and_tab(self):
        # \n, \t, \r should be preserved (not in the stripped range)
        text = "line1\nline2\ttabbed\rcarriage"
        result = sanitize_text_input(text)
        assert "\n" in result
        assert "\t" in result

    def test_at_exact_max_length(self):
        text = "a" * MAX_TEXT_INPUT_LENGTH
        result = sanitize_text_input(text)
        assert len(result) == MAX_TEXT_INPUT_LENGTH

    def test_over_max_length_raises(self):
        text = "a" * (MAX_TEXT_INPUT_LENGTH + 1)
        with pytest.raises(ValidationError, match="trop long"):
            sanitize_text_input(text)

    def test_custom_field_name_in_error(self):
        text = "a" * 101
        with pytest.raises(ValidationError, match="myfield"):
            sanitize_text_input(text, max_length=100, field_name="myfield")


class TestValidateEmailExtended:
    """Tests supplémentaires pour validate_email"""

    def test_with_numbers_in_local(self):
        assert validate_email("user123@example.com") is True

    def test_with_subdomain(self):
        assert validate_email("user@mail.example.com") is True

    def test_missing_at_sign(self):
        assert validate_email("userexample.com") is False

    def test_multiple_at_signs(self):
        assert validate_email("user@@example.com") is False

    def test_short_tld(self):
        # TLD must be >= 2 chars
        assert validate_email("user@example.c") is False

    def test_none_like_empty(self):
        assert validate_email("") is False


class TestSanitizeUrlExtended:
    """Tests supplémentaires pour sanitize_url"""

    def test_strips_whitespace(self):
        result = sanitize_url("  https://example.com  ")
        assert result == "https://example.com"

    def test_javascript_protocol_blocked(self):
        # Fails at http/https check before reaching javascript-specific message
        with pytest.raises(ValidationError):
            sanitize_url("javascript:alert('xss')")

    def test_data_protocol_blocked(self):
        # Fails at http/https check before reaching data-specific message
        with pytest.raises(ValidationError):
            sanitize_url("data:text/html,<h1>hello</h1>")

    def test_url_too_long(self):
        long_url = "https://example.com/" + "a" * 2000
        with pytest.raises(ValidationError, match="trop longue"):
            sanitize_url(long_url)

    def test_vbscript_blocked(self):
        with pytest.raises(ValidationError):
            sanitize_url("vbscript:msgbox('hi')")

    def test_file_protocol_blocked(self):
        with pytest.raises(ValidationError):
            sanitize_url("file:///etc/passwd")

    def test_embedded_javascript_in_http_url_blocked(self):
        """Protocole dangereux embarqué dans une URL http: bloqué (line 205)."""
        with pytest.raises(ValidationError, match="javascript"):
            sanitize_url("http://example.com/javascript:alert(1)")

    def test_embedded_data_in_http_url_blocked(self):
        """Protocole data: embarqué dans une URL http: bloqué."""
        with pytest.raises(ValidationError, match="data:"):
            sanitize_url("http://example.com?x=data:text/html,<h1>xss</h1>")


class TestValidateFileUpload:
    """Tests pour validate_file_upload (async)"""

    @pytest.mark.asyncio
    async def test_valid_pdf_file(self):
        from utils.validation import validate_file_upload

        mock_file = MagicMock()
        mock_file.filename = "document.pdf"
        mock_file.read = AsyncMock(return_value=b"PDF content here")

        result = await validate_file_upload(mock_file)
        assert result == b"PDF content here"

    @pytest.mark.asyncio
    async def test_invalid_extension_raises(self):
        from utils.validation import validate_file_upload
        from fastapi import HTTPException

        mock_file = MagicMock()
        mock_file.filename = "script.exe"
        mock_file.read = AsyncMock(return_value=b"binary")

        with pytest.raises(HTTPException) as exc_info:
            await validate_file_upload(mock_file)
        assert exc_info.value.status_code == 400

    @pytest.mark.asyncio
    async def test_file_too_large_raises(self):
        from utils.validation import validate_file_upload
        from fastapi import HTTPException

        mock_file = MagicMock()
        mock_file.filename = "big.pdf"
        # 11MB content
        mock_file.read = AsyncMock(return_value=b"x" * (11 * 1024 * 1024))

        with pytest.raises(HTTPException) as exc_info:
            await validate_file_upload(mock_file)
        assert exc_info.value.status_code == 413

    @pytest.mark.asyncio
    async def test_empty_file_raises(self):
        from utils.validation import validate_file_upload
        from fastapi import HTTPException

        mock_file = MagicMock()
        mock_file.filename = "empty.pdf"
        mock_file.read = AsyncMock(return_value=b"")

        with pytest.raises(HTTPException) as exc_info:
            await validate_file_upload(mock_file)
        assert exc_info.value.status_code == 400

    @pytest.mark.asyncio
    async def test_no_filename_raises(self):
        from utils.validation import validate_file_upload
        from fastapi import HTTPException

        mock_file = MagicMock()
        mock_file.filename = None
        mock_file.read = AsyncMock(return_value=b"data")

        with pytest.raises(HTTPException) as exc_info:
            await validate_file_upload(mock_file)
        assert exc_info.value.status_code == 400

    @pytest.mark.asyncio
    async def test_custom_allowed_extensions(self):
        from utils.validation import validate_file_upload

        mock_file = MagicMock()
        mock_file.filename = "photo.jpg"
        mock_file.read = AsyncMock(return_value=b"image data")

        result = await validate_file_upload(mock_file, allowed_extensions={".jpg", ".png"})
        assert result == b"image data"

    @pytest.mark.asyncio
    async def test_custom_max_size(self):
        from utils.validation import validate_file_upload
        from fastapi import HTTPException

        mock_file = MagicMock()
        mock_file.filename = "doc.txt"
        mock_file.read = AsyncMock(return_value=b"x" * 200)

        with pytest.raises(HTTPException) as exc_info:
            await validate_file_upload(mock_file, max_size=100)
        assert exc_info.value.status_code == 413

    @pytest.mark.asyncio
    async def test_docx_extension_allowed(self):
        from utils.validation import validate_file_upload

        mock_file = MagicMock()
        mock_file.filename = "report.docx"
        mock_file.read = AsyncMock(return_value=b"docx binary content")

        result = await validate_file_upload(mock_file)
        assert result == b"docx binary content"
