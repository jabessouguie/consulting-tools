"""Extra coverage tests for agents/meeting_summarizer.py — lines 258, 260, 262."""
import os
import sys
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestGenerateEmailParsing:
    """Covers lines 258, 260, 262 in generate_email: OBJET: / CORPS: / in_body parsing."""

    def _make_agent(self):
        with patch("agents.meeting_summarizer.LLMClient"), \
             patch("agents.meeting_summarizer.get_consultant_info",
                   return_value={"name": "Test", "title": "Consultant", "company": "TestCo"}):
            from agents.meeting_summarizer import MeetingSummarizerAgent
            agent = MeetingSummarizerAgent.__new__(MeetingSummarizerAgent)
            agent.llm = MagicMock()
            agent.consultant_name = "Test"
            agent.consultant_title = "Consultant"
            agent.company_name = "TestCo"
            return agent

    def test_generate_email_parses_objet_and_corps(self):
        # lines 257-262: OBJET: and CORPS: parsing branches
        agent = self._make_agent()
        agent.llm.generate.return_value = (
            "OBJET: Compte rendu de la réunion\n"
            "\n"
            "CORPS:\n"
            "Bonjour,\n"
            "Voici le compte rendu.\n"
            "Cordialement"
        )
        result = agent.generate_email("info", "minutes text")
        # line 258: subject extracted from OBJET: line
        assert result["subject"] == "Compte rendu de la réunion"
        # lines 260-262: body lines captured after CORPS:
        assert "Bonjour" in result["body"]
        assert "Cordialement" in result["body"]

    def test_generate_email_missing_objet_uses_default(self):
        agent = self._make_agent()
        # No OBJET: line → default subject
        agent.llm.generate.return_value = "CORPS:\nJuste le corps."
        result = agent.generate_email("info", "minutes")
        assert result["subject"] == "Compte rendu de réunion"
        assert "Juste le corps." in result["body"]

    def test_generate_email_missing_corps_uses_full_response(self):
        agent = self._make_agent()
        # No CORPS: line, no OBJET: → body = full response
        agent.llm.generate.return_value = "Pas de structure formelle."
        result = agent.generate_email("info", "minutes")
        assert "Pas de structure formelle." in result["body"]
