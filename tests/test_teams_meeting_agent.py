"""
Tests pour agents/teams_meeting_agent.py — TeamsMeetingAgent

Note sur les patches :
  - MicrosoftClient est importé lazily dans __init__
    → patch "utils.microsoft_client.MicrosoftClient"
  - MeetingSummarizerAgent est importé lazily dans _analyze_transcript
    → patch "agents.meeting_summarizer.MeetingSummarizerAgent"
"""
import os
from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest

os.environ.setdefault("GEMINI_API_KEY", "test-gemini-key")

# Patch MicrosoftClient at import time to avoid real credentials
MS_CLIENT_PATH = "utils.microsoft_client.MicrosoftClient"
SUMMARIZER_PATH = "agents.meeting_summarizer.MeetingSummarizerAgent"


class TestTeamsMeetingAgentInit:
    def test_stores_api_key(self):
        from agents.teams_meeting_agent import TeamsMeetingAgent

        with patch(MS_CLIENT_PATH):
            agent = TeamsMeetingAgent(api_key="my-api-key")
            assert agent.api_key == "my-api-key"

    def test_reads_api_key_from_env(self, monkeypatch):
        monkeypatch.setenv("GEMINI_API_KEY", "env-key")
        from agents.teams_meeting_agent import TeamsMeetingAgent

        with patch(MS_CLIENT_PATH):
            agent = TeamsMeetingAgent()
            assert agent.api_key == "env-key"

    def test_creates_microsoft_client(self):
        from agents.teams_meeting_agent import TeamsMeetingAgent

        with patch(MS_CLIENT_PATH) as MockClient:
            agent = TeamsMeetingAgent(
                tenant_id="t1",
                client_id="c1",
                client_secret="s1",
            )
            MockClient.assert_called_once_with(
                tenant_id="t1",
                client_id="c1",
                client_secret="s1",
            )
            assert agent.ms is MockClient.return_value

    def test_ms_client_stored(self):
        from agents.teams_meeting_agent import TeamsMeetingAgent

        with patch(MS_CLIENT_PATH) as MockClient:
            mock_instance = MagicMock()
            MockClient.return_value = mock_instance
            agent = TeamsMeetingAgent()
            assert agent.ms is mock_instance


class TestGetTranscript:
    def test_returns_transcript_from_ms(self):
        from agents.teams_meeting_agent import TeamsMeetingAgent

        with patch(MS_CLIENT_PATH) as MockClient:
            agent = TeamsMeetingAgent()
            agent.ms.get_teams_transcript.return_value = "Bonjour tout le monde"
            result = agent._get_transcript("mtg1")

        assert result == "Bonjour tout le monde"
        agent.ms.get_teams_transcript.assert_called_once_with("mtg1")

    def test_returns_empty_string_on_exception(self):
        from agents.teams_meeting_agent import TeamsMeetingAgent

        with patch(MS_CLIENT_PATH):
            agent = TeamsMeetingAgent()
            agent.ms.get_teams_transcript.side_effect = Exception("Network error")
            result = agent._get_transcript("mtg1")

        assert result == ""

    def test_returns_empty_string_on_auth_error(self):
        from agents.teams_meeting_agent import TeamsMeetingAgent
        from utils.microsoft_client import MicrosoftAuthError

        with patch(MS_CLIENT_PATH):
            agent = TeamsMeetingAgent()
            agent.ms.get_teams_transcript.side_effect = MicrosoftAuthError("Auth failed")
            result = agent._get_transcript("mtg1")

        assert result == ""

    def test_returns_empty_string_on_api_error(self):
        from agents.teams_meeting_agent import TeamsMeetingAgent
        from utils.microsoft_client import MicrosoftAPIError

        with patch(MS_CLIENT_PATH):
            agent = TeamsMeetingAgent()
            agent.ms.get_teams_transcript.side_effect = MicrosoftAPIError("404")
            result = agent._get_transcript("mtg1")

        assert result == ""


class TestAnalyzeMeeting:
    def test_returns_error_when_no_transcript(self):
        from agents.teams_meeting_agent import TeamsMeetingAgent

        with patch(MS_CLIENT_PATH):
            agent = TeamsMeetingAgent()
            agent.ms.get_teams_transcript.return_value = ""
            result = agent.analyze_meeting("mtg123")

        assert result["source"] == "error"
        assert "error" in result
        assert result["meeting_id"] == "mtg123"
        assert "generated_at" in result

    def test_error_message_mentions_transcriptions(self):
        from agents.teams_meeting_agent import TeamsMeetingAgent

        with patch(MS_CLIENT_PATH):
            agent = TeamsMeetingAgent()
            agent.ms.get_teams_transcript.return_value = ""
            result = agent.analyze_meeting("mtg123")

        assert (
            "transcription" in result["error"].lower()
            or "transcript" in result["error"].lower()
        )

    def test_generated_at_is_iso_format(self):
        from agents.teams_meeting_agent import TeamsMeetingAgent

        with patch(MS_CLIENT_PATH):
            agent = TeamsMeetingAgent()
            agent.ms.get_teams_transcript.return_value = ""
            result = agent.analyze_meeting("mtg1")

        dt = datetime.fromisoformat(result["generated_at"])
        assert dt is not None

    def test_calls_summarizer_when_transcript_available(self):
        from agents.teams_meeting_agent import TeamsMeetingAgent

        with patch(MS_CLIENT_PATH):
            agent = TeamsMeetingAgent()
            agent.ms.get_teams_transcript.return_value = "Hello team, let's review the agenda"

            mock_summarizer = MagicMock()
            mock_summarizer.run.return_value = {
                "minutes": "Meeting minutes...",
                "email": {"subject": "Re: meeting", "body": "..."},
            }

            with patch(SUMMARIZER_PATH, return_value=mock_summarizer):
                result = agent.analyze_meeting("mtg123")

        mock_summarizer.run.assert_called_once_with(
            "Hello team, let's review the agenda",
            generate_email=True,
        )
        assert result["source"] == "transcript"
        assert result["meeting_id"] == "mtg123"
        assert result["minutes"] == "Meeting minutes..."

    def test_analyze_meeting_source_is_transcript(self):
        from agents.teams_meeting_agent import TeamsMeetingAgent

        with patch(MS_CLIENT_PATH):
            agent = TeamsMeetingAgent()
            agent.ms.get_teams_transcript.return_value = "Some transcript text"

            mock_summarizer = MagicMock()
            mock_summarizer.run.return_value = {"minutes": "...", "email": {}}

            with patch(SUMMARIZER_PATH, return_value=mock_summarizer):
                result = agent.analyze_meeting("mtg456")

        assert result["source"] == "transcript"

    def test_meeting_id_in_result(self):
        from agents.teams_meeting_agent import TeamsMeetingAgent

        with patch(MS_CLIENT_PATH):
            agent = TeamsMeetingAgent()
            agent.ms.get_teams_transcript.return_value = "transcript"

            mock_summarizer = MagicMock()
            mock_summarizer.run.return_value = {"minutes": "", "email": {}}

            with patch(SUMMARIZER_PATH, return_value=mock_summarizer):
                result = agent.analyze_meeting("specific-meeting-id")

        assert result["meeting_id"] == "specific-meeting-id"

    def test_returns_error_when_get_transcript_returns_none(self):
        from agents.teams_meeting_agent import TeamsMeetingAgent

        with patch(MS_CLIENT_PATH):
            agent = TeamsMeetingAgent()
            # _get_transcript catches exceptions and returns ""
            # but the ms client might return empty string directly
            agent.ms.get_teams_transcript.return_value = ""
            result = agent.analyze_meeting("mtg-no-transcript")

        assert result["source"] == "error"


class TestAnalyzeTranscript:
    def test_delegates_to_meeting_summarizer(self):
        from agents.teams_meeting_agent import TeamsMeetingAgent

        with patch(MS_CLIENT_PATH):
            agent = TeamsMeetingAgent()
            mock_summarizer = MagicMock()
            mock_summarizer.run.return_value = {
                "minutes": "Compte rendu",
                "email": {"subject": "CR réunion", "body": "Bonjour"},
            }

            with patch(SUMMARIZER_PATH, return_value=mock_summarizer):
                result = agent._analyze_transcript("Hello world transcript", "mtg1")

        assert result["minutes"] == "Compte rendu"
        assert result["source"] == "transcript"
        assert result["meeting_id"] == "mtg1"

    def test_generate_email_is_true(self):
        from agents.teams_meeting_agent import TeamsMeetingAgent

        with patch(MS_CLIENT_PATH):
            agent = TeamsMeetingAgent()
            mock_summarizer = MagicMock()
            mock_summarizer.run.return_value = {"minutes": "", "email": {}}

            with patch(SUMMARIZER_PATH, return_value=mock_summarizer):
                agent._analyze_transcript("text", "mtg1")

        mock_summarizer.run.assert_called_once_with("text", generate_email=True)

    def test_preserves_email_from_summarizer(self):
        from agents.teams_meeting_agent import TeamsMeetingAgent

        with patch(MS_CLIENT_PATH):
            agent = TeamsMeetingAgent()
            mock_summarizer = MagicMock()
            mock_summarizer.run.return_value = {
                "minutes": "...",
                "email": {"subject": "Compte rendu", "body": "Voici le CR"},
            }

            with patch(SUMMARIZER_PATH, return_value=mock_summarizer):
                result = agent._analyze_transcript("t", "mtg1")

        assert result["email"]["subject"] == "Compte rendu"
