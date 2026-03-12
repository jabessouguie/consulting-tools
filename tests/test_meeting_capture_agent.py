"""
Tests pour agents/meeting_capture_agent.py
Couverture cible : 100 %
"""

import json
import time
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch, mock_open

import pytest
from fastapi.testclient import TestClient

from agents.meeting_capture_agent import (
    GEMINI_MODELS,
    DEFAULT_GEMINI_MODEL,
    MeetingCaptureAgent,
    MeetingGmailClient,
    APIKeyError,
    AuthenticationError,
    DraftCreationError,
    QuotaExceededError,
    VideoProcessingError,
    _infer_mime,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

VALID_API_KEY = "test-gemini-api-key"
SAMPLE_RESULT = {
    "transcript": "Locuteur A : Bonjour.",
    "summary": {
        "resume_executif": "Résumé",
        "points_cles": ["Point 1"],
        "plan_action": ["Action 1"],
    },
    "email_brouillon": {
        "objet": "Compte rendu",
        "corps": "Bonjour,\n\nVeuillez trouver...",
    },
}
SAMPLE_JSON = json.dumps(SAMPLE_RESULT)


# ---------------------------------------------------------------------------
# TestMeetingCaptureAgent — __init__
# ---------------------------------------------------------------------------

class TestMeetingCaptureAgentInit:

    @patch("agents.meeting_capture_agent.genai.configure")
    @patch("agents.meeting_capture_agent.genai.GenerativeModel")
    def test_init_ok(self, mock_model, mock_configure):
        agent = MeetingCaptureAgent(VALID_API_KEY)
        mock_configure.assert_called_once_with(api_key=VALID_API_KEY)
        assert agent.model_name == DEFAULT_GEMINI_MODEL

    @patch("agents.meeting_capture_agent.genai.configure")
    @patch("agents.meeting_capture_agent.genai.GenerativeModel")
    def test_init_custom_model(self, mock_model, mock_configure):
        agent = MeetingCaptureAgent(VALID_API_KEY, model="gemini-2.5-pro")
        assert agent.model_name == "gemini-2.5-pro"
        mock_model.assert_called_once_with("gemini-2.5-pro")

    def test_init_empty_api_key_raises(self):
        with pytest.raises(APIKeyError):
            MeetingCaptureAgent("")

    def test_init_whitespace_api_key_raises(self):
        with pytest.raises(APIKeyError):
            MeetingCaptureAgent("   ")


# ---------------------------------------------------------------------------
# TestMeetingCaptureAgent — upload_video
# ---------------------------------------------------------------------------

class TestUploadVideo:

    @pytest.fixture(autouse=True)
    def agent(self):
        with patch("agents.meeting_capture_agent.genai.configure"), \
             patch("agents.meeting_capture_agent.genai.GenerativeModel"):
            yield MeetingCaptureAgent(VALID_API_KEY)

    def test_upload_ok(self, agent, tmp_path):
        video_file = tmp_path / "test.webm"
        video_file.write_bytes(b"fake video data")
        mock_file = MagicMock()
        with patch("agents.meeting_capture_agent.genai.upload_file", return_value=mock_file):
            result = agent.upload_video(str(video_file))
        assert result is mock_file

    def test_upload_file_not_found(self, agent):
        with pytest.raises(VideoProcessingError, match="introuvable"):
            agent.upload_video("/nonexistent/path/video.mp4")

    def test_upload_api_key_error_google(self, agent, tmp_path):
        from google.api_core.exceptions import GoogleAPIError
        video_file = tmp_path / "t.webm"
        video_file.write_bytes(b"x")
        err = GoogleAPIError("API key not valid")
        with patch("agents.meeting_capture_agent.genai.upload_file", side_effect=err):
            with pytest.raises(APIKeyError):
                agent.upload_video(str(video_file))

    def test_upload_quota_error_google(self, agent, tmp_path):
        from google.api_core.exceptions import GoogleAPIError
        video_file = tmp_path / "t.webm"
        video_file.write_bytes(b"x")
        err = GoogleAPIError("quota exceeded resource exhausted")
        with patch("agents.meeting_capture_agent.genai.upload_file", side_effect=err):
            with pytest.raises(QuotaExceededError):
                agent.upload_video(str(video_file))

    def test_upload_generic_google_error(self, agent, tmp_path):
        from google.api_core.exceptions import GoogleAPIError
        video_file = tmp_path / "t.webm"
        video_file.write_bytes(b"x")
        err = GoogleAPIError("some other error")
        with patch("agents.meeting_capture_agent.genai.upload_file", side_effect=err):
            with pytest.raises(VideoProcessingError):
                agent.upload_video(str(video_file))

    def test_upload_api_key_error_generic(self, agent, tmp_path):
        video_file = tmp_path / "t.webm"
        video_file.write_bytes(b"x")
        with patch("agents.meeting_capture_agent.genai.upload_file",
                   side_effect=Exception("unauthenticated request")):
            with pytest.raises(APIKeyError):
                agent.upload_video(str(video_file))

    def test_upload_quota_error_generic(self, agent, tmp_path):
        video_file = tmp_path / "t.webm"
        video_file.write_bytes(b"x")
        with patch("agents.meeting_capture_agent.genai.upload_file",
                   side_effect=Exception("resource exhausted quota")):
            with pytest.raises(QuotaExceededError):
                agent.upload_video(str(video_file))

    def test_upload_generic_exception(self, agent, tmp_path):
        video_file = tmp_path / "t.webm"
        video_file.write_bytes(b"x")
        with patch("agents.meeting_capture_agent.genai.upload_file",
                   side_effect=Exception("network error")):
            with pytest.raises(VideoProcessingError):
                agent.upload_video(str(video_file))


# ---------------------------------------------------------------------------
# TestMeetingCaptureAgent — wait_for_processing
# ---------------------------------------------------------------------------

class TestWaitForProcessing:

    @pytest.fixture(autouse=True)
    def agent(self):
        with patch("agents.meeting_capture_agent.genai.configure"), \
             patch("agents.meeting_capture_agent.genai.GenerativeModel"):
            yield MeetingCaptureAgent(VALID_API_KEY)

    def _make_file(self, state: str):
        f = MagicMock()
        f.name = "files/test123"
        f.state = state
        return f

    def test_active_immediately(self, agent):
        active_file = self._make_file("ACTIVE")
        with patch("agents.meeting_capture_agent.genai.get_file", return_value=active_file), \
             patch("agents.meeting_capture_agent.time.sleep"):
            result = agent.wait_for_processing(active_file)
        assert result is active_file

    def test_processing_then_active(self, agent):
        processing_file = self._make_file("PROCESSING")
        active_file = self._make_file("ACTIVE")
        calls = [processing_file, active_file]
        with patch("agents.meeting_capture_agent.genai.get_file", side_effect=calls), \
             patch("agents.meeting_capture_agent.time.sleep"):
            result = agent.wait_for_processing(processing_file)
        assert result is active_file

    def test_timeout(self, agent):
        processing_file = self._make_file("PROCESSING")
        with patch("agents.meeting_capture_agent.genai.get_file", return_value=processing_file), \
             patch("agents.meeting_capture_agent.time.sleep"), \
             patch("agents.meeting_capture_agent.time.time", side_effect=[0, 0, 999]):
            with pytest.raises(TimeoutError):
                agent.wait_for_processing(processing_file, timeout=10, poll_interval=1)

    def test_failed_state(self, agent):
        failed_file = self._make_file("FAILED")
        with patch("agents.meeting_capture_agent.genai.get_file", return_value=failed_file), \
             patch("agents.meeting_capture_agent.time.sleep"):
            with pytest.raises(VideoProcessingError, match="FAILED"):
                agent.wait_for_processing(failed_file)

    def test_error_state(self, agent):
        error_file = self._make_file("ERROR")
        with patch("agents.meeting_capture_agent.genai.get_file", return_value=error_file), \
             patch("agents.meeting_capture_agent.time.sleep"):
            with pytest.raises(VideoProcessingError):
                agent.wait_for_processing(error_file)


# ---------------------------------------------------------------------------
# TestMeetingCaptureAgent — analyze
# ---------------------------------------------------------------------------

class TestAnalyze:

    @pytest.fixture(autouse=True)
    def agent(self):
        with patch("agents.meeting_capture_agent.genai.configure"), \
             patch("agents.meeting_capture_agent.genai.GenerativeModel") as mock_cls:
            self.mock_model = MagicMock()
            mock_cls.return_value = self.mock_model
            yield MeetingCaptureAgent(VALID_API_KEY)

    def test_analyze_ok(self, agent):
        mock_response = MagicMock()
        mock_response.text = SAMPLE_JSON
        self.mock_model.generate_content.return_value = mock_response
        mock_file = MagicMock()
        result = agent.analyze(mock_file)
        assert result["transcript"] == SAMPLE_RESULT["transcript"]
        assert "summary" in result

    def test_analyze_raises_on_exception(self, agent):
        self.mock_model.generate_content.side_effect = Exception("Gemini error")
        with pytest.raises(VideoProcessingError, match="Erreur d'analyse"):
            agent.analyze(MagicMock())

    def test_analyze_propagates_video_processing_error(self, agent):
        """VideoProcessingError from parse_response should propagate unchanged."""
        mock_response = MagicMock()
        mock_response.text = "not json at all"
        self.mock_model.generate_content.return_value = mock_response
        with pytest.raises(VideoProcessingError):
            agent.analyze(MagicMock())


# ---------------------------------------------------------------------------
# TestMeetingCaptureAgent — parse_response
# ---------------------------------------------------------------------------

class TestParseResponse:

    @pytest.fixture(autouse=True)
    def agent(self):
        with patch("agents.meeting_capture_agent.genai.configure"), \
             patch("agents.meeting_capture_agent.genai.GenerativeModel"):
            yield MeetingCaptureAgent(VALID_API_KEY)

    def test_clean_json(self, agent):
        result = agent.parse_response(SAMPLE_JSON)
        assert result["transcript"] == SAMPLE_RESULT["transcript"]

    def test_strip_json_fence(self, agent):
        fenced = "```json\n" + SAMPLE_JSON + "\n```"
        result = agent.parse_response(fenced)
        assert "summary" in result

    def test_strip_plain_fence(self, agent):
        fenced = "```\n" + SAMPLE_JSON + "\n```"
        result = agent.parse_response(fenced)
        assert "email_brouillon" in result

    def test_invalid_json(self, agent):
        with pytest.raises(VideoProcessingError, match="JSON invalide"):
            agent.parse_response("not json {{{")

    def test_not_a_dict(self, agent):
        with pytest.raises(VideoProcessingError, match="objet JSON"):
            agent.parse_response("[1, 2, 3]")

    def test_missing_top_key(self, agent):
        data = dict(SAMPLE_RESULT)
        del data["transcript"]
        with pytest.raises(VideoProcessingError, match="Clés manquantes"):
            agent.parse_response(json.dumps(data))

    def test_missing_summary_key(self, agent):
        data = {
            "transcript": "t",
            "summary": {"resume_executif": "r", "points_cles": []},  # missing plan_action
            "email_brouillon": {"objet": "o", "corps": "c"},
        }
        with pytest.raises(VideoProcessingError, match="summary"):
            agent.parse_response(json.dumps(data))

    def test_summary_not_dict(self, agent):
        data = {"transcript": "t", "summary": "string", "email_brouillon": {"objet": "o", "corps": "c"}}
        with pytest.raises(VideoProcessingError, match="'summary'"):
            agent.parse_response(json.dumps(data))

    def test_missing_email_key(self, agent):
        data = {
            "transcript": "t",
            "summary": {"resume_executif": "r", "points_cles": [], "plan_action": []},
            "email_brouillon": {"objet": "o"},  # missing corps
        }
        with pytest.raises(VideoProcessingError, match="email_brouillon"):
            agent.parse_response(json.dumps(data))

    def test_email_not_dict(self, agent):
        data = {
            "transcript": "t",
            "summary": {"resume_executif": "r", "points_cles": [], "plan_action": []},
            "email_brouillon": "string",
        }
        with pytest.raises(VideoProcessingError, match="'email_brouillon'"):
            agent.parse_response(json.dumps(data))


# ---------------------------------------------------------------------------
# TestMeetingGmailClient
# ---------------------------------------------------------------------------

class TestMeetingGmailClient:

    @pytest.fixture(autouse=True)
    def client(self):
        self.client = MeetingGmailClient()

    def _mock_valid_creds(self):
        creds = MagicMock()
        creds.valid = True
        creds.expired = False
        creds.refresh_token = None
        return creds

    def test_authenticate_new_token(self, tmp_path):
        """Flow complète : pas de token existant → InstalledAppFlow."""
        creds = self._mock_valid_creds()
        mock_flow = MagicMock()
        mock_flow.run_local_server.return_value = creds
        creds.to_json.return_value = '{"token": "abc"}'

        token_path = tmp_path / "token.json"

        with patch("google.oauth2.credentials.Credentials.from_authorized_user_file",
                   side_effect=Exception("no token")), \
             patch("google_auth_oauthlib.flow.InstalledAppFlow.from_client_secrets_file",
                   return_value=mock_flow), \
             patch("googleapiclient.discovery.build") as mock_build:
            service = self.client.authenticate("creds.json", str(token_path))
            mock_build.assert_called_once_with("gmail", "v1", credentials=creds)

    def test_authenticate_existing_valid_token(self, tmp_path):
        """Token existant + valide → pas de refresh."""
        token_path = tmp_path / "token.json"
        token_path.write_text('{"token": "valid"}')
        creds = self._mock_valid_creds()

        with patch("google.oauth2.credentials.Credentials.from_authorized_user_file",
                   return_value=creds), \
             patch("googleapiclient.discovery.build") as mock_build:
            self.client.authenticate("creds.json", str(token_path))
            mock_build.assert_called_once()

    def test_authenticate_expired_refresh(self, tmp_path):
        """Token expiré + refresh_token → refresh automatique."""
        token_path = tmp_path / "token.json"
        token_path.write_text('{"token": "expired"}')
        creds = MagicMock()
        creds.valid = False
        creds.expired = True
        creds.refresh_token = "some_refresh"
        creds.to_json.return_value = '{"token": "refreshed"}'

        with patch("google.oauth2.credentials.Credentials.from_authorized_user_file",
                   return_value=creds), \
             patch("google.auth.transport.requests.Request"), \
             patch("googleapiclient.discovery.build"):
            self.client.authenticate("creds.json", str(token_path))
            creds.refresh.assert_called_once()

    def test_authenticate_error(self, tmp_path):
        """Exception non récupérable → AuthenticationError."""
        token_path = tmp_path / "token.json"
        with patch("google.oauth2.credentials.Credentials.from_authorized_user_file",
                   side_effect=Exception("fatal")), \
             patch("google_auth_oauthlib.flow.InstalledAppFlow.from_client_secrets_file",
                   side_effect=Exception("fatal")):
            with pytest.raises(AuthenticationError):
                self.client.authenticate("creds.json", str(token_path))

    def test_create_draft_ok(self):
        service = MagicMock()
        draft_response = {"id": "draft_id_123", "message": {"id": "msg_id_456"}}
        service.users.return_value.drafts.return_value.create.return_value.execute.return_value = draft_response

        result = self.client.create_draft(service, "to@example.com", "Subject", "Body")
        assert result["id"] == "draft_id_123"
        assert result["message_id"] == "msg_id_456"

    def test_create_draft_error(self):
        service = MagicMock()
        service.users.return_value.drafts.return_value.create.return_value.execute.side_effect = Exception("API error")

        with pytest.raises(DraftCreationError):
            self.client.create_draft(service, "to@example.com", "Subject", "Body")

    def test_create_draft_reraises_draft_creation_error(self):
        """DraftCreationError levée directement dans le try doit remonter telle quelle."""
        service = MagicMock()
        service.users.return_value.drafts.return_value.create.return_value.execute.side_effect = DraftCreationError("already a draft error")
        with pytest.raises(DraftCreationError, match="already a draft error"):
            self.client.create_draft(service, "to@example.com", "Subject", "Body")

    def test_authenticate_reraises_authentication_error(self, tmp_path):
        """AuthenticationError levée dans le try doit remonter telle quelle (ligne except AuthenticationError: raise)."""
        token_path = tmp_path / "token.json"
        token_path.write_text('{"token": "x"}')  # token file must exist so from_authorized_user_file is called
        with patch("google.oauth2.credentials.Credentials.from_authorized_user_file",
                   side_effect=AuthenticationError("direct auth error")):
            with pytest.raises(AuthenticationError, match="direct auth error"):
                self.client.authenticate("creds.json", str(token_path))


# ---------------------------------------------------------------------------
# Test _infer_mime helper
# ---------------------------------------------------------------------------

class TestInferMime:

    def test_webm(self):
        assert _infer_mime(Path("video.webm")) == "video/webm"

    def test_mp4(self):
        assert _infer_mime(Path("video.mp4")) == "video/mp4"

    def test_mov(self):
        assert _infer_mime(Path("video.mov")) == "video/quicktime"

    def test_avi(self):
        assert _infer_mime(Path("video.avi")) == "video/x-msvideo"

    def test_mkv(self):
        assert _infer_mime(Path("video.mkv")) == "video/x-matroska"

    def test_unknown_defaults_mp4(self):
        assert _infer_mime(Path("video.xyz")) == "video/mp4"


# ---------------------------------------------------------------------------
# Test constantes exportées
# ---------------------------------------------------------------------------

class TestConstants:

    def test_gemini_models_not_empty(self):
        assert len(GEMINI_MODELS) > 0

    def test_default_model_in_models(self):
        assert DEFAULT_GEMINI_MODEL in GEMINI_MODELS


# ---------------------------------------------------------------------------
# TestMeetingCaptureEndpoints — routes FastAPI
# ---------------------------------------------------------------------------

# Origin header required by CSRF middleware (TestClient base_url = http://testserver)
CSRF_HEADERS = {"origin": "http://testserver"}


@pytest.fixture(scope="module")
def client():
    """Client de test FastAPI sans authentification."""
    from app import app
    with TestClient(app, raise_server_exceptions=False) as c:
        yield c


class TestMeetingCapturePageRoute:

    def test_page_redirects_without_auth(self, client):
        resp = client.get("/meeting-capture", follow_redirects=False)
        # Sans auth → redirect vers /login ou page login (200 après redirect)
        assert resp.status_code in (302, 301, 200)

    def test_page_ok_with_auth(self):
        from app import app
        with patch("app.get_current_user", return_value={"username": "test"}):
            with TestClient(app) as c:
                resp = c.get("/meeting-capture")
                assert resp.status_code == 200
                assert "Meeting Capture" in resp.text


class TestMeetingCaptureUpload:

    @pytest.fixture(autouse=True)
    def auth(self):
        with patch("app.get_current_user", return_value={"username": "test"}):
            yield

    def test_upload_valid_webm(self):
        from app import app
        with TestClient(app) as c:
            resp = c.post(
                "/api/meeting-capture/upload",
                headers=CSRF_HEADERS,
                data={"gemini_model": "gemini-2.5-flash"},
                files={"video": ("meeting.webm", b"fake video", "video/webm")},
            )
        assert resp.status_code == 200
        assert "job_id" in resp.json()

    def test_upload_valid_mp4(self):
        from app import app
        with TestClient(app) as c:
            resp = c.post(
                "/api/meeting-capture/upload",
                headers=CSRF_HEADERS,
                data={"gemini_model": "gemini-2.5-pro"},
                files={"video": ("meeting.mp4", b"fake video", "video/mp4")},
            )
        assert resp.status_code == 200

    def test_upload_invalid_model(self):
        from app import app
        with TestClient(app) as c:
            resp = c.post(
                "/api/meeting-capture/upload",
                headers=CSRF_HEADERS,
                data={"gemini_model": "gpt-4o"},
                files={"video": ("m.webm", b"data", "video/webm")},
            )
        assert resp.status_code == 400
        assert "Modèle non supporté" in resp.json().get("detail", "")

    def test_upload_bad_extension(self):
        from app import app
        with TestClient(app) as c:
            resp = c.post(
                "/api/meeting-capture/upload",
                headers=CSRF_HEADERS,
                data={"gemini_model": "gemini-2.5-flash"},
                files={"video": ("document.txt", b"text data", "text/plain")},
            )
        assert resp.status_code == 400

    def test_upload_empty_file(self):
        from app import app
        with TestClient(app) as c:
            resp = c.post(
                "/api/meeting-capture/upload",
                headers=CSRF_HEADERS,
                data={"gemini_model": "gemini-2.5-flash"},
                files={"video": ("empty.webm", b"", "video/webm")},
            )
        assert resp.status_code == 400


class TestMeetingCaptureStream:

    def test_stream_unknown_job(self):
        from app import app
        with TestClient(app) as c:
            resp = c.get("/api/meeting-capture/stream/nonexistent999",
                         headers={"Accept": "text/event-stream"})
        assert resp.status_code == 200
        assert "error_msg" in resp.text

    def test_stream_done_job(self):
        from app import app, jobs
        job_id = "test_done"
        jobs[job_id] = {
            "type": "meeting-capture",
            "status": "done",
            "steps": [{"step": "upload", "status": "done", "progress": 100}],
            "result": SAMPLE_RESULT,
            "error": None,
        }
        with TestClient(app) as c:
            resp = c.get(
                "/api/meeting-capture/stream/" + job_id,
                headers={"Accept": "text/event-stream"},
            )
        assert resp.status_code == 200
        assert "result" in resp.text
        jobs.pop(job_id, None)

    def test_stream_error_job(self):
        from app import app, jobs
        job_id = "test_err"
        jobs[job_id] = {
            "type": "meeting-capture",
            "status": "error",
            "steps": [],
            "result": None,
            "error": "Clé API invalide",
        }
        with TestClient(app) as c:
            resp = c.get(
                "/api/meeting-capture/stream/" + job_id,
                headers={"Accept": "text/event-stream"},
            )
        assert resp.status_code == 200
        assert "error_msg" in resp.text
        jobs.pop(job_id, None)


class TestMeetingCaptureGmailDraft:

    @pytest.fixture(autouse=True)
    def auth(self):
        with patch("app.get_current_user", return_value={"username": "test"}):
            yield

    def test_gmail_draft_ok(self):
        from app import app
        with patch("routers.meeting_capture.MeetingGmailClient.authenticate", return_value=MagicMock()), \
             patch("routers.meeting_capture.MeetingGmailClient.create_draft",
                   return_value={"id": "d123", "message_id": "m456"}):
            with TestClient(app) as c:
                resp = c.post(
                    "/api/meeting-capture/gmail-draft",
                    headers=CSRF_HEADERS,
                    json={
                        "to": "dest@example.com",
                        "subject": "CR réunion",
                        "body": "Bonjour...",
                        "credentials_path": "/fake/creds.json",
                    },
                )
        assert resp.status_code == 200
        assert resp.json()["id"] == "d123"

    def test_gmail_draft_error(self):
        from app import app
        with patch("routers.meeting_capture.MeetingGmailClient.authenticate",
                   side_effect=DraftCreationError("service error")):
            with TestClient(app) as c:
                resp = c.post(
                    "/api/meeting-capture/gmail-draft",
                    headers=CSRF_HEADERS,
                    json={"to": "", "subject": "CR", "body": "corps"},
                )
        assert resp.status_code == 500

    def test_gmail_draft_invalid_body(self):
        from app import app
        with TestClient(app) as c:
            resp = c.post(
                "/api/meeting-capture/gmail-draft",
                headers={**CSRF_HEADERS, "Content-Type": "application/json"},
                content=b"not json at all",
            )
        assert resp.status_code in (400, 422, 500)
