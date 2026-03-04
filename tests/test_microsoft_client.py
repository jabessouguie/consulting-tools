"""
Tests pour utils/microsoft_client.py — MicrosoftClient (MSAL + Graph API)
"""
import sys
from unittest.mock import MagicMock, patch, call

import pytest

from utils.microsoft_client import (
    MicrosoftAuthError,
    MicrosoftAPIError,
    MicrosoftClient,
)


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------

class TestExceptions:
    def test_auth_error_is_exception(self):
        err = MicrosoftAuthError("auth failed")
        assert isinstance(err, Exception)
        assert str(err) == "auth failed"

    def test_api_error_is_exception(self):
        err = MicrosoftAPIError("api failed")
        assert isinstance(err, Exception)
        assert str(err) == "api failed"


# ---------------------------------------------------------------------------
# MicrosoftClient.__init__
# ---------------------------------------------------------------------------

class TestInit:
    def test_stores_explicit_credentials(self):
        client = MicrosoftClient(
            tenant_id="t1", client_id="c1", client_secret="s1"
        )
        assert client.tenant_id == "t1"
        assert client.client_id == "c1"
        assert client.client_secret == "s1"

    def test_reads_credentials_from_env(self, monkeypatch):
        monkeypatch.setenv("MICROSOFT_TENANT_ID", "env-tenant")
        monkeypatch.setenv("MICROSOFT_CLIENT_ID", "env-client")
        monkeypatch.setenv("MICROSOFT_CLIENT_SECRET", "env-secret")
        client = MicrosoftClient()
        assert client.tenant_id == "env-tenant"
        assert client.client_id == "env-client"
        assert client.client_secret == "env-secret"

    def test_explicit_overrides_env(self, monkeypatch):
        monkeypatch.setenv("MICROSOFT_TENANT_ID", "env-tenant")
        client = MicrosoftClient(tenant_id="explicit-tenant")
        assert client.tenant_id == "explicit-tenant"

    def test_defaults_to_empty_strings(self, monkeypatch):
        monkeypatch.delenv("MICROSOFT_TENANT_ID", raising=False)
        monkeypatch.delenv("MICROSOFT_CLIENT_ID", raising=False)
        monkeypatch.delenv("MICROSOFT_CLIENT_SECRET", raising=False)
        client = MicrosoftClient()
        assert client.tenant_id == ""
        assert client.client_id == ""
        assert client.client_secret == ""

    def test_app_is_none_initially(self):
        client = MicrosoftClient()
        assert client._app is None

    def test_token_cache_is_empty(self):
        client = MicrosoftClient()
        assert client._token_cache == {}


# ---------------------------------------------------------------------------
# _get_app
# ---------------------------------------------------------------------------

class TestGetApp:
    def test_raises_auth_error_if_msal_not_installed(self):
        client = MicrosoftClient(tenant_id="t", client_id="c", client_secret="s")
        with patch.dict("sys.modules", {"msal": None}):
            with pytest.raises(MicrosoftAuthError, match="msal"):
                client._get_app()

    def test_raises_auth_error_if_credentials_missing(self):
        client = MicrosoftClient(tenant_id="", client_id="", client_secret="")
        mock_msal = MagicMock()
        with patch.dict("sys.modules", {"msal": mock_msal}):
            with pytest.raises(MicrosoftAuthError, match="requis"):
                client._get_app()

    def test_creates_msal_app_with_correct_params(self):
        mock_msal = MagicMock()
        mock_app = MagicMock()
        mock_msal.ConfidentialClientApplication.return_value = mock_app

        client = MicrosoftClient(tenant_id="tenant1", client_id="client1", client_secret="secret1")
        with patch.dict("sys.modules", {"msal": mock_msal}):
            result = client._get_app()

        mock_msal.ConfidentialClientApplication.assert_called_once_with(
            "client1",
            authority="https://login.microsoftonline.com/tenant1",
            client_credential="secret1",
        )
        assert result is mock_app

    def test_returns_cached_app_on_second_call(self):
        mock_msal = MagicMock()
        mock_app = MagicMock()
        mock_msal.ConfidentialClientApplication.return_value = mock_app

        client = MicrosoftClient(tenant_id="t", client_id="c", client_secret="s")
        with patch.dict("sys.modules", {"msal": mock_msal}):
            r1 = client._get_app()
            r2 = client._get_app()

        assert r1 is r2
        mock_msal.ConfidentialClientApplication.assert_called_once()


# ---------------------------------------------------------------------------
# authenticate
# ---------------------------------------------------------------------------

class TestAuthenticate:
    def _make_client_with_mock_app(self):
        mock_app = MagicMock()
        client = MicrosoftClient(tenant_id="t", client_id="c", client_secret="s")
        client._app = mock_app
        return client, mock_app

    def test_returns_access_token(self):
        client, mock_app = self._make_client_with_mock_app()
        mock_app.acquire_token_for_client.return_value = {"access_token": "tok123"}
        token = client.authenticate()
        assert token == "tok123"

    def test_caches_token(self):
        client, mock_app = self._make_client_with_mock_app()
        mock_app.acquire_token_for_client.return_value = {"access_token": "cached-tok"}
        client.authenticate()
        client.authenticate()  # second call
        mock_app.acquire_token_for_client.assert_called_once()  # only once

    def test_uses_custom_scopes(self):
        client, mock_app = self._make_client_with_mock_app()
        mock_app.acquire_token_for_client.return_value = {"access_token": "t"}
        client.authenticate(scopes=["custom.scope"])
        mock_app.acquire_token_for_client.assert_called_once_with(scopes=["custom.scope"])

    def test_raises_auth_error_on_failure(self):
        client, mock_app = self._make_client_with_mock_app()
        mock_app.acquire_token_for_client.return_value = {
            "error": "invalid_client",
            "error_description": "Client secret is wrong",
        }
        with pytest.raises(MicrosoftAuthError, match="Client secret is wrong"):
            client.authenticate()

    def test_raises_auth_error_with_generic_error(self):
        client, mock_app = self._make_client_with_mock_app()
        mock_app.acquire_token_for_client.return_value = {"error": "some_error"}
        with pytest.raises(MicrosoftAuthError, match="some_error"):
            client.authenticate()

    def test_separate_scope_caches(self):
        client, mock_app = self._make_client_with_mock_app()
        mock_app.acquire_token_for_client.side_effect = [
            {"access_token": "tok1"},
            {"access_token": "tok2"},
        ]
        t1 = client.authenticate(scopes=["scope1"])
        t2 = client.authenticate(scopes=["scope2"])
        assert t1 == "tok1"
        assert t2 == "tok2"


# ---------------------------------------------------------------------------
# _graph_request
# ---------------------------------------------------------------------------

class TestGraphRequest:
    def _make_client(self, token="test-token"):
        client = MicrosoftClient(tenant_id="t", client_id="c", client_secret="s")
        client.authenticate = MagicMock(return_value=token)
        return client

    def test_raises_api_error_if_requests_not_installed(self):
        client = self._make_client()
        with patch.dict("sys.modules", {"requests": None}):
            with pytest.raises(MicrosoftAPIError, match="requests"):
                client._graph_request("GET", "/me")

    def test_returns_empty_dict_on_204(self):
        mock_resp = MagicMock()
        mock_resp.status_code = 204
        mock_resp.ok = True
        mock_requests = MagicMock()
        mock_requests.request.return_value = mock_resp

        client = self._make_client()
        with patch.dict("sys.modules", {"requests": mock_requests}):
            result = client._graph_request("DELETE", "/something")
        assert result == {}

    def test_returns_json_on_success(self):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.ok = True
        mock_resp.json.return_value = {"id": "abc123"}
        mock_requests = MagicMock()
        mock_requests.request.return_value = mock_resp

        client = self._make_client()
        with patch.dict("sys.modules", {"requests": mock_requests}):
            result = client._graph_request("GET", "/me")
        assert result == {"id": "abc123"}

    def test_raises_api_error_on_http_error(self):
        mock_resp = MagicMock()
        mock_resp.status_code = 403
        mock_resp.ok = False
        mock_resp.json.return_value = {"error": {"message": "Access denied"}}
        mock_requests = MagicMock()
        mock_requests.request.return_value = mock_resp

        client = self._make_client()
        with patch.dict("sys.modules", {"requests": mock_requests}):
            with pytest.raises(MicrosoftAPIError, match="Access denied"):
                client._graph_request("GET", "/me")

    def test_raises_api_error_with_status_code(self):
        mock_resp = MagicMock()
        mock_resp.status_code = 500
        mock_resp.ok = False
        mock_resp.json.return_value = {"error": {"message": "Internal Server Error"}}
        mock_requests = MagicMock()
        mock_requests.request.return_value = mock_resp

        client = self._make_client()
        with patch.dict("sys.modules", {"requests": mock_requests}):
            with pytest.raises(MicrosoftAPIError, match="500"):
                client._graph_request("GET", "/me")

    def test_handles_json_parse_error(self):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.ok = True
        mock_resp.json.side_effect = ValueError("bad json")
        mock_resp.text = "some raw text"
        mock_requests = MagicMock()
        mock_requests.request.return_value = mock_resp

        client = self._make_client()
        with patch.dict("sys.modules", {"requests": mock_requests}):
            result = client._graph_request("GET", "/me")
        assert result == {"raw": "some raw text"}

    def test_includes_bearer_token_in_headers(self):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.ok = True
        mock_resp.json.return_value = {}
        mock_requests = MagicMock()
        mock_requests.request.return_value = mock_resp

        client = self._make_client(token="my-token")
        with patch.dict("sys.modules", {"requests": mock_requests}):
            client._graph_request("GET", "/me")

        _, kwargs = mock_requests.request.call_args
        assert kwargs["headers"]["Authorization"] == "Bearer my-token"

    def test_builds_correct_url(self):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.ok = True
        mock_resp.json.return_value = {}
        mock_requests = MagicMock()
        mock_requests.request.return_value = mock_resp

        client = self._make_client()
        with patch.dict("sys.modules", {"requests": mock_requests}):
            client._graph_request("GET", "/me/drive")

        _, kwargs = mock_requests.request.call_args
        assert kwargs["url"] == "https://graph.microsoft.com/v1.0/me/drive"


# ---------------------------------------------------------------------------
# send_teams_message
# ---------------------------------------------------------------------------

class TestSendTeamsMessage:
    def _make_client(self):
        client = MicrosoftClient(tenant_id="t", client_id="c", client_secret="s")
        client._graph_request = MagicMock(return_value={"id": "msg1"})
        return client

    def test_raises_api_error_on_invalid_channel_id(self):
        client = self._make_client()
        with pytest.raises(MicrosoftAPIError, match="teamId/channelId"):
            client.send_teams_message("invalid-format", "Hello")

    def test_calls_correct_endpoint(self):
        client = self._make_client()
        client.send_teams_message("team1/chan1", "Hello Teams!")
        client._graph_request.assert_called_once_with(
            "POST",
            "/teams/team1/channels/chan1/messages",
            json_data={"body": {"contentType": "html", "content": "Hello Teams!"}},
        )

    def test_returns_message_metadata(self):
        client = self._make_client()
        result = client.send_teams_message("team1/chan1", "msg")
        assert result == {"id": "msg1"}


# ---------------------------------------------------------------------------
# upload_to_onedrive
# ---------------------------------------------------------------------------

class TestUploadToOnedrive:
    def test_uploads_file_content(self, tmp_path):
        file = tmp_path / "doc.docx"
        file.write_bytes(b"docx-content")

        client = MicrosoftClient(tenant_id="t", client_id="c", client_secret="s")
        client._graph_request = MagicMock(return_value={"id": "file1"})

        result = client.upload_to_onedrive(str(file), "/Documents/doc.docx")

        client._graph_request.assert_called_once_with(
            "PUT",
            "/me/drive/root:/Documents/doc.docx:/content",
            files=b"docx-content",
            content_type="application/octet-stream",
        )
        assert result == {"id": "file1"}

    def test_strips_leading_slash_from_remote_path(self, tmp_path):
        file = tmp_path / "f.txt"
        file.write_bytes(b"x")

        client = MicrosoftClient(tenant_id="t", client_id="c", client_secret="s")
        client._graph_request = MagicMock(return_value={})

        client.upload_to_onedrive(str(file), "/no-leading.txt")
        _, kwargs = client._graph_request.call_args
        path_arg = client._graph_request.call_args[0][1]
        assert path_arg == "/me/drive/root:/no-leading.txt:/content"


# ---------------------------------------------------------------------------
# get_sharepoint_files
# ---------------------------------------------------------------------------

class TestGetSharepointFiles:
    def test_returns_file_list(self):
        client = MicrosoftClient(tenant_id="t", client_id="c", client_secret="s")
        client._graph_request = MagicMock(
            return_value={"value": [{"name": "file1.docx"}, {"name": "file2.xlsx"}]}
        )
        result = client.get_sharepoint_files("site123")
        assert result == [{"name": "file1.docx"}, {"name": "file2.xlsx"}]
        client._graph_request.assert_called_once_with("GET", "/sites/site123/drive/root/children")

    def test_returns_empty_list_when_no_value(self):
        client = MicrosoftClient(tenant_id="t", client_id="c", client_secret="s")
        client._graph_request = MagicMock(return_value={})
        result = client.get_sharepoint_files("site123")
        assert result == []


# ---------------------------------------------------------------------------
# get_teams_transcript
# ---------------------------------------------------------------------------

class TestGetTeamsTranscript:
    def test_returns_empty_string_when_no_transcripts(self):
        client = MicrosoftClient(tenant_id="t", client_id="c", client_secret="s")
        client._graph_request = MagicMock(return_value={"value": []})
        result = client.get_teams_transcript("meeting123")
        assert result == ""

    def test_returns_transcript_content(self):
        client = MicrosoftClient(tenant_id="t", client_id="c", client_secret="s")
        call_results = [
            {"value": [{"id": "transcript1"}]},
            {"content": "Bonjour tout le monde"},
        ]
        client._graph_request = MagicMock(side_effect=call_results)
        result = client.get_teams_transcript("meeting123")
        assert result == "Bonjour tout le monde"

    def test_returns_empty_when_transcript_has_no_id(self):
        client = MicrosoftClient(tenant_id="t", client_id="c", client_secret="s")
        client._graph_request = MagicMock(return_value={"value": [{"id": ""}]})
        result = client.get_teams_transcript("meeting123")
        assert result == ""

    def test_calls_correct_endpoints(self):
        client = MicrosoftClient(tenant_id="t", client_id="c", client_secret="s")
        client._graph_request = MagicMock(side_effect=[
            {"value": [{"id": "t1"}]},
            {"content": "text"},
        ])
        client.get_teams_transcript("mtg1")
        calls = client._graph_request.call_args_list
        assert calls[0][0] == ("GET", "/me/onlineMeetings/mtg1/transcripts")
        assert calls[1][0] == ("GET", "/me/onlineMeetings/mtg1/transcripts/t1/content")


# ---------------------------------------------------------------------------
# create_outlook_draft
# ---------------------------------------------------------------------------

class TestCreateOutlookDraft:
    def test_calls_correct_endpoint(self):
        client = MicrosoftClient(tenant_id="t", client_id="c", client_secret="s")
        client._graph_request = MagicMock(return_value={"id": "draft1"})

        result = client.create_outlook_draft(
            to="test@example.com",
            subject="Test Subject",
            body="<p>Hello</p>",
        )

        client._graph_request.assert_called_once_with(
            "POST",
            "/me/messages",
            json_data={
                "subject": "Test Subject",
                "body": {"contentType": "HTML", "content": "<p>Hello</p>"},
                "toRecipients": [{"emailAddress": {"address": "test@example.com"}}],
            },
        )
        assert result == {"id": "draft1"}

    def test_custom_body_type(self):
        client = MicrosoftClient(tenant_id="t", client_id="c", client_secret="s")
        client._graph_request = MagicMock(return_value={})

        client.create_outlook_draft(
            to="x@y.com", subject="S", body="plain text", body_type="Text"
        )
        _, kwargs = client._graph_request.call_args
        assert kwargs["json_data"]["body"]["contentType"] == "Text"


# ---------------------------------------------------------------------------
# test_connection
# ---------------------------------------------------------------------------

class TestTestConnection:
    def test_returns_true_on_success(self):
        client = MicrosoftClient(tenant_id="t", client_id="c", client_secret="s")
        client._graph_request = MagicMock(return_value={"driveType": "personal"})
        assert client.test_connection() is True
        client._graph_request.assert_called_once_with("GET", "/me/drive")

    def test_propagates_api_error(self):
        client = MicrosoftClient(tenant_id="t", client_id="c", client_secret="s")
        client._graph_request = MagicMock(
            side_effect=MicrosoftAPIError("Forbidden")
        )
        with pytest.raises(MicrosoftAPIError, match="Forbidden"):
            client.test_connection()

    def test_propagates_auth_error(self):
        client = MicrosoftClient(tenant_id="t", client_id="c", client_secret="s")
        client._graph_request = MagicMock(
            side_effect=MicrosoftAuthError("Invalid credentials")
        )
        with pytest.raises(MicrosoftAuthError, match="Invalid credentials"):
            client.test_connection()
