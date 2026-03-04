"""
Tests pour les endpoints Microsoft 365 dans app.py :
  POST /api/microsoft/test-connection
  POST /api/teams/analyze-meeting
  POST /api/meeting-capture/export-word
  POST /api/proposal/export-word

Note : tous les imports dans les endpoints sont lazy (inside function),
donc les patches ciblent les modules sources.
"""
import os
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

os.environ.setdefault("AUTH_PASSWORD", "testpass")
os.environ.setdefault("SECRET_KEY", "testsecret")
os.environ.setdefault("GEMINI_API_KEY", "test-gemini-key")

from app import app

client = TestClient(app, raise_server_exceptions=True)
client.headers.update({"Origin": "http://localhost:8000"})

# Patch targets (lazy imports inside endpoint functions)
MS_CLIENT_CLS = "utils.microsoft_client.MicrosoftClient"
TEAMS_AGENT_CLS = "agents.teams_meeting_agent.TeamsMeetingAgent"
EXPORT_WORD_FN = "utils.word_exporter.export_to_word"


# ---------------------------------------------------------------------------
# POST /api/microsoft/test-connection
# ---------------------------------------------------------------------------

class TestMicrosoftTestConnection:
    def test_returns_ok_true_on_success(self):
        with patch(MS_CLIENT_CLS) as MockClient:
            MockClient.return_value.test_connection.return_value = True
            response = client.post("/api/microsoft/test-connection")
        assert response.status_code == 200
        assert response.json()["ok"] is True

    def test_returns_ok_false_on_auth_error(self):
        from utils.microsoft_client import MicrosoftAuthError
        with patch(MS_CLIENT_CLS) as MockClient:
            MockClient.return_value.test_connection.side_effect = MicrosoftAuthError("Invalid credentials")
            response = client.post("/api/microsoft/test-connection")
        assert response.status_code == 422
        assert response.json()["ok"] is False
        assert "error" in response.json()

    def test_returns_ok_false_on_api_error(self):
        from utils.microsoft_client import MicrosoftAPIError
        with patch(MS_CLIENT_CLS) as MockClient:
            MockClient.return_value.test_connection.side_effect = MicrosoftAPIError("Forbidden")
            response = client.post("/api/microsoft/test-connection")
        assert response.status_code == 422
        assert response.json()["ok"] is False

    def test_returns_500_on_unexpected_error(self):
        with patch(MS_CLIENT_CLS) as MockClient:
            MockClient.return_value.test_connection.side_effect = RuntimeError("Unexpected")
            response = client.post("/api/microsoft/test-connection")
        assert response.status_code == 500
        assert response.json()["ok"] is False

    def test_error_message_in_response(self):
        from utils.microsoft_client import MicrosoftAuthError
        with patch(MS_CLIENT_CLS) as MockClient:
            MockClient.return_value.test_connection.side_effect = MicrosoftAuthError("bad secret")
            response = client.post("/api/microsoft/test-connection")
        assert "bad secret" in response.json()["error"]


# ---------------------------------------------------------------------------
# POST /api/teams/analyze-meeting
# ---------------------------------------------------------------------------

class TestTeamsAnalyzeMeeting:
    def test_returns_400_when_no_meeting_id(self):
        response = client.post("/api/teams/analyze-meeting", json={})
        assert response.status_code == 400
        assert "meeting_id" in response.json()["error"]

    def test_returns_400_when_meeting_id_empty(self):
        response = client.post("/api/teams/analyze-meeting", json={"meeting_id": ""})
        assert response.status_code == 400

    def test_returns_result_on_success(self):
        mock_result = {
            "minutes": "Meeting notes...",
            "email": {"subject": "CR", "body": "..."},
            "source": "transcript",
            "meeting_id": "mtg1",
            "generated_at": "2026-01-01T00:00:00",
        }
        with patch(TEAMS_AGENT_CLS) as MockAgent:
            MockAgent.return_value.analyze_meeting.return_value = mock_result
            response = client.post(
                "/api/teams/analyze-meeting", json={"meeting_id": "mtg1"}
            )
        assert response.status_code == 200
        data = response.json()
        assert data["source"] == "transcript"
        assert data["meeting_id"] == "mtg1"

    def test_returns_422_on_auth_error(self):
        from utils.microsoft_client import MicrosoftAuthError
        with patch(TEAMS_AGENT_CLS) as MockAgent:
            MockAgent.return_value.analyze_meeting.side_effect = MicrosoftAuthError("Auth failed")
            response = client.post(
                "/api/teams/analyze-meeting", json={"meeting_id": "mtg1"}
            )
        assert response.status_code == 422
        assert "error" in response.json()

    def test_returns_422_on_api_error(self):
        from utils.microsoft_client import MicrosoftAPIError
        with patch(TEAMS_AGENT_CLS) as MockAgent:
            MockAgent.return_value.analyze_meeting.side_effect = MicrosoftAPIError("Forbidden")
            response = client.post(
                "/api/teams/analyze-meeting", json={"meeting_id": "mtg1"}
            )
        assert response.status_code == 422

    def test_error_result_passes_through(self):
        """When no transcript is available, analyze_meeting returns error dict — not an exception."""
        mock_result = {
            "error": "Aucune transcription disponible",
            "source": "error",
            "meeting_id": "mtg1",
            "generated_at": "2026-01-01T00:00:00",
        }
        with patch(TEAMS_AGENT_CLS) as MockAgent:
            MockAgent.return_value.analyze_meeting.return_value = mock_result
            response = client.post(
                "/api/teams/analyze-meeting", json={"meeting_id": "mtg1"}
            )
        assert response.status_code == 200
        assert response.json()["source"] == "error"


# ---------------------------------------------------------------------------
# POST /api/meeting-capture/export-word
# ---------------------------------------------------------------------------

class TestMeetingCaptureExportWord:
    def test_returns_400_when_no_minutes(self):
        response = client.post(
            "/api/meeting-capture/export-word", json={"title": "Test"}
        )
        assert response.status_code == 400
        assert "minutes" in response.json()["error"]

    def test_returns_400_when_minutes_empty(self):
        response = client.post(
            "/api/meeting-capture/export-word", json={"minutes": "", "title": "T"}
        )
        assert response.status_code == 400

    def test_returns_docx_file(self, tmp_path):
        fake_docx = tmp_path / "output.docx"
        fake_docx.write_bytes(b"PK fake docx content")

        with patch(EXPORT_WORD_FN, return_value=str(fake_docx)) as mock_export:
            response = client.post(
                "/api/meeting-capture/export-word",
                json={
                    "minutes": "## Introduction\nThis is the intro.\n## Conclusion\nBye.",
                    "title": "Compte Rendu Test",
                },
            )
        assert response.status_code == 200
        assert "application/vnd.openxmlformats" in response.headers["content-type"]
        mock_export.assert_called_once()

    def test_passes_title_to_exporter(self, tmp_path):
        fake_docx = tmp_path / "output.docx"
        fake_docx.write_bytes(b"PK fake")

        with patch(EXPORT_WORD_FN, return_value=str(fake_docx)) as mock_export:
            client.post(
                "/api/meeting-capture/export-word",
                json={"minutes": "## Section\nContent", "title": "My Title"},
            )
        args, kwargs = mock_export.call_args
        # title is passed as keyword arg or inside content dict
        assert "My Title" in str(args) or "My Title" in str(kwargs)

    def test_parses_markdown_sections(self, tmp_path):
        fake_docx = tmp_path / "output.docx"
        fake_docx.write_bytes(b"PK")

        with patch(EXPORT_WORD_FN, return_value=str(fake_docx)) as mock_export:
            client.post(
                "/api/meeting-capture/export-word",
                json={
                    "minutes": "## Intro\nSome text\n## Action Items\n- Do thing",
                    "title": "CR",
                },
            )
        content_arg = mock_export.call_args[0][0]
        assert "sections" in content_arg
        assert len(content_arg["sections"]) >= 1

    def test_returns_500_on_exception(self):
        with patch(EXPORT_WORD_FN, side_effect=OSError("disk full")):
            response = client.post(
                "/api/meeting-capture/export-word",
                json={"minutes": "## S\nBody", "title": "T"},
            )
        assert response.status_code == 500

    def test_filename_in_response_header(self, tmp_path):
        fake_docx = tmp_path / "out.docx"
        fake_docx.write_bytes(b"PK")

        with patch(EXPORT_WORD_FN, return_value=str(fake_docx)):
            response = client.post(
                "/api/meeting-capture/export-word",
                json={"minutes": "## S\nContent"},
            )
        assert response.status_code == 200
        cd = response.headers.get("content-disposition", "")
        assert "compte_rendu.docx" in cd


# ---------------------------------------------------------------------------
# POST /api/proposal/export-word
# ---------------------------------------------------------------------------

class TestProposalExportWord:
    def test_returns_400_when_no_content(self):
        response = client.post(
            "/api/proposal/export-word", json={"title": "Test"}
        )
        assert response.status_code == 400
        assert "content" in response.json()["error"]

    def test_returns_400_when_content_empty(self):
        response = client.post(
            "/api/proposal/export-word", json={"content": "", "title": "T"}
        )
        assert response.status_code == 400

    def test_returns_docx_file(self, tmp_path):
        fake_docx = tmp_path / "proposal.docx"
        fake_docx.write_bytes(b"PK fake docx")

        with patch(EXPORT_WORD_FN, return_value=str(fake_docx)) as mock_export:
            response = client.post(
                "/api/proposal/export-word",
                json={"content": "# Our Proposal\n\nThis is the content.", "title": "Proposition"},
            )
        assert response.status_code == 200
        assert "application/vnd.openxmlformats" in response.headers["content-type"]
        mock_export.assert_called_once()

    def test_passes_content_to_exporter(self, tmp_path):
        fake_docx = tmp_path / "p.docx"
        fake_docx.write_bytes(b"PK")

        with patch(EXPORT_WORD_FN, return_value=str(fake_docx)) as mock_export:
            client.post(
                "/api/proposal/export-word",
                json={"content": "My proposal text", "title": "T"},
            )
        content_arg = mock_export.call_args[0][0]
        assert content_arg["sections"][0]["body"] == "My proposal text"

    def test_default_title_when_not_provided(self, tmp_path):
        fake_docx = tmp_path / "p.docx"
        fake_docx.write_bytes(b"PK")

        with patch(EXPORT_WORD_FN, return_value=str(fake_docx)) as mock_export:
            client.post(
                "/api/proposal/export-word",
                json={"content": "text"},
            )
        _, kwargs = mock_export.call_args
        assert len(kwargs.get("title", "Proposition")) > 0

    def test_filename_in_response_header(self, tmp_path):
        fake_docx = tmp_path / "p.docx"
        fake_docx.write_bytes(b"PK")

        with patch(EXPORT_WORD_FN, return_value=str(fake_docx)):
            response = client.post(
                "/api/proposal/export-word",
                json={"content": "text", "title": "T"},
            )
        assert response.status_code == 200
        cd = response.headers.get("content-disposition", "")
        assert "proposition.docx" in cd

    def test_returns_500_on_exception(self):
        with patch(EXPORT_WORD_FN, side_effect=OSError("write error")):
            response = client.post(
                "/api/proposal/export-word",
                json={"content": "text", "title": "T"},
            )
        assert response.status_code == 500
