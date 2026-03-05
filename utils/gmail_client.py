"""
Gmail API client pour envoyer des emails avec pieces jointes
"""

import base64
from email import encoders
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path
from typing import Any, Dict, List, Optional

from utils.google_api import GoogleAPIClient


class GmailClient:
    """Client pour envoyer des emails via Gmail API"""

    def __init__(self, credentials_path: str = None):
        """
        Initialize Gmail client with Google credentials

        Args:
            credentials_path: Path to google_credentials.json (optional)
        """
        self.google_client = GoogleAPIClient(credentials_path)
        self.service = self.google_client._build_service("gmail", "v1")

    def send_email(
        self,
        to: str,
        subject: str,
        body: str,
        attachments: Optional[List[str]] = None,
        cc: Optional[List[str]] = None,
        bcc: Optional[List[str]] = None,
        html: bool = False,
    ) -> Dict[str, Any]:
        """
        Send email with optional attachments

        Args:
            to: Recipient email
            subject: Email subject
            body: Email body (plain text or HTML)
            attachments: List of file paths to attach
            cc: CC recipients
            bcc: BCC recipients
            html: If True, body is HTML instead of plain text

        Returns:
            Dict with message ID and status

        Raises:
            Exception: If email sending fails
        """
        # Create message
        message = self._create_message(
            to=to, subject=subject, body=body, attachments=attachments, cc=cc, bcc=bcc, html=html
        )

        # Send message
        result = self._send_message(message)

        return {"id": result["id"], "status": "sent", "thread_id": result.get("threadId")}

    def _create_message(
        self,
        to: str,
        subject: str,
        body: str,
        attachments: Optional[List[str]] = None,
        cc: Optional[List[str]] = None,
        bcc: Optional[List[str]] = None,
        html: bool = False,
    ) -> Dict[str, str]:
        """
        Create a MIME message for Gmail API

        Args:
            to: Recipient email
            subject: Email subject
            body: Email body
            attachments: List of file paths
            cc: CC recipients
            bcc: BCC recipients
            html: If True, body is HTML

        Returns:
            Dict with base64url encoded raw message
        """
        # Create multipart message
        message = MIMEMultipart()
        message["To"] = to
        message["Subject"] = subject

        if cc:
            message["Cc"] = ", ".join(cc)
        if bcc:
            message["Bcc"] = ", ".join(bcc)

        # Attach body
        mime_type = "html" if html else "plain"
        message.attach(MIMEText(body, mime_type, "utf-8"))

        # Attach files
        if attachments:
            for file_path in attachments:
                self._attach_file(message, file_path)

        # Encode message
        raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode("utf-8")

        return {"raw": raw_message}

    def _attach_file(self, message: MIMEMultipart, file_path: str):
        """
        Attach a file to MIME message

        Args:
            message: MIME message to attach to
            file_path: Path to file to attach

        Raises:
            FileNotFoundError: If file does not exist
        """
        file_path = Path(file_path)

        if not file_path.exists():
            raise FileNotFoundError(f"Attachment file not found: {file_path}")

        # Read file
        with open(file_path, "rb") as f:
            file_data = f.read()

        # Detect MIME type based on extension
        extension = file_path.suffix.lower()
        mime_types = {
            ".pdf": "application/pdf",
            ".doc": "application/msword",
            ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            ".txt": "text/plain",
            ".md": "text/markdown",
            ".csv": "text/csv",
            ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            ".pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
            ".json": "application/json",
        }

        mime_type = mime_types.get(extension, "application/octet-stream")
        main_type, sub_type = mime_type.split("/", 1)

        # Create attachment
        attachment = MIMEBase(main_type, sub_type)
        attachment.set_payload(file_data)
        encoders.encode_base64(attachment)

        # Add header
        attachment.add_header("Content-Disposition", f'attachment; filename="{file_path.name}"')

        message.attach(attachment)

    def _send_message(self, message: Dict[str, str]) -> Dict[str, Any]:
        """
        Send a message via Gmail API

        Args:
            message: Encoded message dict

        Returns:
            Sent message metadata

        Raises:
            Exception: If API call fails
        """
        try:
            result = self.service.users().messages().send(userId="me", body=message).execute()

            print(f"✅ Email sent successfully (ID: {result['id']})")
            return result

        except Exception as e:
            print(f"❌ Error sending email: {str(e)}")
            raise


# Helper function for quick email sending
def send_quick_email(
    to: str, subject: str, body: str, attachments: Optional[List[str]] = None
) -> Dict[str, Any]:
    """
    Quick helper to send email without initializing client

    Args:
        to: Recipient email
        subject: Email subject
        body: Email body
        attachments: Optional file paths

    Returns:
        Dict with message ID and status
    """
    client = GmailClient()
    return client.send_email(to=to, subject=subject, body=body, attachments=attachments)
