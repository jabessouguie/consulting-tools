"""
Tests unitaires pour GmailClient
"""

import os

# Add parent dir to path
import sys
import tempfile
from unittest.mock import Mock, patch

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.gmail_client import GmailClient, send_quick_email  # noqa: E402


class TestGmailClient:
    """Tests pour GmailClient"""

    @patch("utils.gmail_client.GoogleAPIClient")
    def test_init(self, mock_google_client):
        """Test initialisation du client"""
        client = GmailClient()
        assert client is not None
        mock_google_client.assert_called_once()

    @patch("utils.gmail_client.GoogleAPIClient")
    def test_create_message_simple(self, mock_google_client):
        """Test création message simple"""
        client = GmailClient()

        message = client._create_message(
            to="test@example.com", subject="Test Subject", body="Test Body"
        )

        assert "raw" in message
        assert isinstance(message["raw"], str)

    @patch("utils.gmail_client.GoogleAPIClient")
    def test_create_message_with_cc_bcc(self, mock_google_client):
        """Test création message avec CC et BCC"""
        client = GmailClient()

        message = client._create_message(
            to="test@example.com",
            subject="Test",
            body="Body",
            cc=["cc1@example.com", "cc2@example.com"],
            bcc=["bcc@example.com"],
        )

        assert "raw" in message

    @patch("utils.gmail_client.GoogleAPIClient")
    def test_attach_file(self, mock_google_client):
        """Test attachement de fichier"""
        from email.mime.multipart import MIMEMultipart

        client = GmailClient()
        message = MIMEMultipart()

        # Créer fichier temporaire
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write("Test content")
            temp_path = f.name

        try:
            client._attach_file(message, temp_path)
            # Vérifier qu'une pièce jointe a été ajoutée
            assert len(message.get_payload()) > 0
        finally:
            os.unlink(temp_path)

    @patch("utils.gmail_client.GoogleAPIClient")
    def test_attach_file_not_found(self, mock_google_client):
        """Test attachement fichier inexistant"""
        from email.mime.multipart import MIMEMultipart

        client = GmailClient()
        message = MIMEMultipart()

        with pytest.raises(FileNotFoundError):
            client._attach_file(message, "/nonexistent/file.txt")

    @patch("utils.gmail_client.GoogleAPIClient")
    def test_send_message_success(self, mock_google_client):
        """Test envoi message avec succès"""
        client = GmailClient()

        # Mock service
        mock_service = Mock()
        mock_send = Mock(return_value=Mock(execute=Mock(return_value={"id": "msg123"})))
        mock_service.users.return_value.messages.return_value.send = mock_send
        client.service = mock_service

        result = client._send_message({"raw": "test"})

        assert result["id"] == "msg123"
        mock_send.assert_called_once()

    @patch("utils.gmail_client.GoogleAPIClient")
    def test_send_message_failure(self, mock_google_client):
        """Test échec envoi message"""
        client = GmailClient()

        # Mock service qui lève une exception
        mock_service = Mock()
        mock_service.users.return_value.messages.return_value.send.side_effect = Exception(
            "API Error"
        )
        client.service = mock_service

        with pytest.raises(Exception):
            client._send_message({"raw": "test"})

    @patch("utils.gmail_client.GoogleAPIClient")
    def test_send_email_integration(self, mock_google_client):
        """Test intégration send_email complète"""
        client = GmailClient()

        # Mock service
        mock_service = Mock()
        mock_execute = Mock(return_value={"id": "msg456", "threadId": "thread789"})
        mock_service.users.return_value.messages.return_value.send.return_value.execute = (
            mock_execute
        )
        client.service = mock_service

        # Créer fichier temporaire
        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
            f.write("# Test Markdown")
            temp_path = f.name

        try:
            result = client.send_email(
                to="recipient@example.com",
                subject="Test Email",
                body="This is a test",
                attachments=[temp_path],
            )

            assert result["id"] == "msg456"
            assert result["status"] == "sent"
            assert result["thread_id"] == "thread789"
        finally:
            os.unlink(temp_path)

    @patch("utils.gmail_client.GmailClient")
    def test_send_quick_email(self, mock_gmail_client):
        """Test fonction helper send_quick_email"""
        mock_instance = Mock()
        mock_instance.send_email.return_value = {"id": "quick123", "status": "sent"}
        mock_gmail_client.return_value = mock_instance

        result = send_quick_email(to="test@example.com", subject="Quick Test", body="Quick body")

        assert result["id"] == "quick123"
        mock_instance.send_email.assert_called_once()

    @patch("utils.gmail_client.GoogleAPIClient")
    def test_mime_types(self, mock_google_client):
        """Test détection types MIME"""
        from email.mime.multipart import MIMEMultipart

        client = GmailClient()

        test_files = {
            ".pdf": "application/pdf",
            ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            ".txt": "text/plain",
            ".md": "text/markdown",
            ".csv": "text/csv",
            ".json": "application/json",
        }

        for ext, expected_mime in test_files.items():
            with tempfile.NamedTemporaryFile(mode="w", suffix=ext, delete=False) as f:
                f.write("test")
                temp_path = f.name

            try:
                message_test = MIMEMultipart()
                client._attach_file(message_test, temp_path)
                # Vérifier que l'attachement a été créé
                assert len(message_test.get_payload()) > 0
            finally:
                os.unlink(temp_path)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
