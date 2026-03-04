"""
Tests pour agents/formation_generator.py
Phase 5 - Coverage improvement
"""
import os
from datetime import datetime
from unittest.mock import MagicMock, patch, mock_open

import pytest

os.environ.setdefault("AUTH_PASSWORD", "testpass")
os.environ.setdefault("SECRET_KEY", "testsecret")
os.environ.setdefault("GEMINI_API_KEY", "test-gemini-key")
os.environ.setdefault("ANTHROPIC_API_KEY", "test-anthropic-key")
os.environ.setdefault("CONSULTANT_NAME", "Test Consultant")


@pytest.fixture()
def agent():
    with patch("agents.formation_generator.LLMClient") as MockLLM:
        mock_llm = MagicMock()
        MockLLM.return_value = mock_llm
        mock_llm.generate.return_value = "# **Formation IA**\n## F300\nDurée du cours : 3 jours"
        with patch("builtins.open", mock_open(read_data="# Template {{title}}")):
            from agents.formation_generator import FormationGeneratorAgent
            a = FormationGeneratorAgent()
            yield a


class TestFormationGeneratorAgentInit:
    def test_has_llm(self, agent):
        assert hasattr(agent, "llm")

    def test_has_template(self, agent):
        assert hasattr(agent, "template")

    def test_template_is_string(self, agent):
        assert isinstance(agent.template, str)

    def test_load_template_missing_file(self):
        with patch("agents.formation_generator.LLMClient"):
            with patch("builtins.open", side_effect=FileNotFoundError("not found")):
                from agents.formation_generator import FormationGeneratorAgent
                a = FormationGeneratorAgent()
        assert a.template == ""


class TestGenerateProgramme:
    def test_returns_dict(self, agent):
        result = agent.generate_programme("Besoin client: formation IA")
        assert isinstance(result, dict)

    def test_has_markdown_key(self, agent):
        result = agent.generate_programme("Besoin client")
        assert "markdown" in result

    def test_has_metadata_key(self, agent):
        result = agent.generate_programme("Besoin client")
        assert "metadata" in result

    def test_has_generated_at(self, agent):
        result = agent.generate_programme("Besoin client")
        assert "generated_at" in result

    def test_strips_markdown_code_fence(self, agent):
        agent.llm.generate.return_value = "```markdown\n# Contenu\n```"
        result = agent.generate_programme("Besoin")
        assert not result["markdown"].startswith("```")

    def test_strips_plain_code_fence(self, agent):
        agent.llm.generate.return_value = "```\n# Contenu\n```"
        result = agent.generate_programme("Besoin")
        assert not result["markdown"].startswith("```")

    def test_calls_llm(self, agent):
        agent.generate_programme("Test besoin")
        agent.llm.generate.assert_called_once()

    def test_uses_client_needs_in_prompt(self, agent):
        agent.generate_programme("Formation IA avancée")
        call_kwargs = agent.llm.generate.call_args
        args = call_kwargs[1] if call_kwargs[1] else {}
        prompt_arg = call_kwargs[0][0] if call_kwargs[0] else args.get("prompt", "")
        assert "Formation IA avancée" in prompt_arg


class TestRegenerateWithFeedback:
    def test_returns_dict(self, agent):
        agent.llm.generate.return_value = "# **Formation Améliorée**\nDurée du cours : 2 jours"
        result = agent.regenerate_with_feedback("Previous programme", "Feedback: add more examples")
        assert isinstance(result, dict)

    def test_has_markdown_key(self, agent):
        agent.llm.generate.return_value = "# Updated programme"
        result = agent.regenerate_with_feedback("Previous", "Feedback")
        assert "markdown" in result

    def test_has_generated_at(self, agent):
        agent.llm.generate.return_value = "Updated content"
        result = agent.regenerate_with_feedback("Previous", "Feedback")
        assert "generated_at" in result

    def test_strips_markdown_fence(self, agent):
        agent.llm.generate.return_value = "```markdown\n# Updated\n```"
        result = agent.regenerate_with_feedback("Previous", "Feedback")
        assert not result["markdown"].startswith("```")

    def test_calls_llm(self, agent):
        agent.regenerate_with_feedback("Previous programme", "Add exercises")
        agent.llm.generate.assert_called_once()

    def test_uses_feedback_in_prompt(self, agent):
        agent.llm.generate.return_value = "Updated content"
        agent.regenerate_with_feedback("Programme", "Plus d'exercices pratiques")
        call_args = agent.llm.generate.call_args
        prompt = call_args[0][0] if call_args[0] else call_args[1].get("prompt", "")
        assert "Plus d'exercices pratiques" in prompt


class TestExtractMetadata:
    def test_extracts_title(self, agent):
        md = "# **Introduction to Machine Learning**\n\nContent here."
        metadata = agent._extract_metadata(md)
        assert metadata.get("title") == "Introduction to Machine Learning"

    def test_extracts_duration(self, agent):
        md = "## Section\nDurée du cours : 3 jours\n"
        metadata = agent._extract_metadata(md)
        assert "3 jours" in metadata.get("duration", "")

    def test_extracts_first_h2_as_code(self, agent):
        md = "# **Title**\n## F300-AI\nContent"
        metadata = agent._extract_metadata(md)
        assert metadata.get("code") == "F300-AI"

    def test_skips_template_placeholder_h2(self, agent):
        md = "## {code}\nContent"
        metadata = agent._extract_metadata(md)
        assert "code" not in metadata

    def test_returns_empty_dict_for_empty_markdown(self, agent):
        metadata = agent._extract_metadata("")
        assert metadata == {}

    def test_ignores_untitled_content(self, agent):
        md = "Some content without headings\n- bullet"
        metadata = agent._extract_metadata(md)
        assert "title" not in metadata
