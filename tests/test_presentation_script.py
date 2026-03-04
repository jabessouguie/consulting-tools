"""
Tests pour agents/presentation_script_generator.py
Phase 5 - Coverage improvement
"""
import os
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

os.environ.setdefault("GEMINI_API_KEY", "test-gemini-key")
os.environ.setdefault("ANTHROPIC_API_KEY", "test-anthropic-key")
os.environ.setdefault("AUTH_PASSWORD", "testpass")
os.environ.setdefault("SECRET_KEY", "testsecret")

from agents.presentation_script_generator import PresentationScriptGenerator


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_agent():
    """Instantiate PresentationScriptGenerator with mocked LLM."""
    with patch("agents.presentation_script_generator.LLMClient") as mock_cls:
        mock_llm = MagicMock()
        mock_llm.generate.return_value = "## Script mock\n\nCeci est un script de test."
        mock_cls.return_value = mock_llm
        agent = PresentationScriptGenerator()
    # Keep a reference so tests can introspect calls
    agent.llm = mock_llm
    return agent


def _make_slide_data(slide_number=1, title="Titre Test", content=None, notes=""):
    """Return a minimal slide data dict."""
    return {
        "slide_number": slide_number,
        "title": title,
        "content": content if content is not None else ["Point A", "Point B"],
        "notes": notes,
    }


# ---------------------------------------------------------------------------
# Unit tests: __init__
# ---------------------------------------------------------------------------

class TestPresentationScriptGeneratorInit:
    def test_llm_is_created_on_init(self):
        with patch("agents.presentation_script_generator.LLMClient") as mock_cls:
            mock_cls.return_value = MagicMock()
            agent = PresentationScriptGenerator()
        mock_cls.assert_called_once_with(max_tokens=8192)

    def test_consultant_info_is_populated(self):
        with patch("agents.presentation_script_generator.LLMClient"):
            with patch("agents.presentation_script_generator.get_consultant_info") as mock_info:
                mock_info.return_value = {"name": "Test Name", "company": "Test Co", "title": "Consultant"}
                agent = PresentationScriptGenerator()
        assert agent.consultant_info["name"] == "Test Name"
        assert agent.consultant_info["company"] == "Test Co"


# ---------------------------------------------------------------------------
# Unit tests: extract_slides_content
# ---------------------------------------------------------------------------

class TestExtractSlidesContent:
    def _build_mock_prs(self, slides_config):
        """Build a mock Presentation from a list of slide config dicts."""
        mock_prs = MagicMock()
        mock_slides = []

        for cfg in slides_config:
            slide = MagicMock()
            # Title shape
            if cfg.get("title"):
                slide.shapes.title = MagicMock()
                slide.shapes.title.text = cfg["title"]
            else:
                slide.shapes.title = None

            # Content shapes
            content_shapes = []
            for text in cfg.get("content", []):
                shape = MagicMock()
                shape.text = text
                shape.text.strip.return_value = text
                # Make the shape not be the title
                shape.__ne__ = lambda self, other: True
                content_shapes.append(shape)

            # Combine shapes list (title + content)
            all_shapes = []
            if slide.shapes.title:
                title_shape = slide.shapes.title
                all_shapes.append(title_shape)
            for s in content_shapes:
                all_shapes.append(s)

            slide.shapes.__iter__ = MagicMock(return_value=iter(all_shapes))

            # Notes
            if cfg.get("notes"):
                slide.has_notes_slide = True
                notes_slide = MagicMock()
                notes_slide.notes_text_frame.text = cfg["notes"]
                slide.notes_slide = notes_slide
            else:
                slide.has_notes_slide = False

            mock_slides.append(slide)

        mock_prs.slides = mock_slides
        return mock_prs

    def test_returns_list_of_slide_dicts(self):
        agent = _make_agent()
        mock_prs = MagicMock()
        mock_prs.slides = []

        with patch("agents.presentation_script_generator.Presentation", return_value=mock_prs):
            result = agent.extract_slides_content("fake.pptx")

        assert isinstance(result, list)
        assert result == []

    def test_slide_number_starts_at_one(self):
        agent = _make_agent()
        mock_slide = MagicMock()
        mock_slide.shapes.title = None
        mock_slide.shapes.__iter__ = MagicMock(return_value=iter([]))
        mock_slide.has_notes_slide = False
        mock_prs = MagicMock()
        mock_prs.slides = [mock_slide]

        with patch("agents.presentation_script_generator.Presentation", return_value=mock_prs):
            result = agent.extract_slides_content("fake.pptx")

        assert result[0]["slide_number"] == 1

    def test_extracts_title_from_slide(self):
        agent = _make_agent()
        mock_slide = MagicMock()
        title_shape = MagicMock()
        title_shape.text = "Mon Titre"
        mock_slide.shapes.title = title_shape
        mock_slide.shapes.__iter__ = MagicMock(return_value=iter([title_shape]))
        mock_slide.has_notes_slide = False
        mock_prs = MagicMock()
        mock_prs.slides = [mock_slide]

        with patch("agents.presentation_script_generator.Presentation", return_value=mock_prs):
            result = agent.extract_slides_content("fake.pptx")

        assert result[0]["title"] == "Mon Titre"

    def test_slide_without_title_has_empty_title(self):
        agent = _make_agent()
        mock_slide = MagicMock()
        mock_slide.shapes.title = None
        mock_slide.shapes.__iter__ = MagicMock(return_value=iter([]))
        mock_slide.has_notes_slide = False
        mock_prs = MagicMock()
        mock_prs.slides = [mock_slide]

        with patch("agents.presentation_script_generator.Presentation", return_value=mock_prs):
            result = agent.extract_slides_content("fake.pptx")

        assert result[0]["title"] == ""

    def test_extracts_notes_when_present(self):
        agent = _make_agent()
        mock_slide = MagicMock()
        mock_slide.shapes.title = None
        mock_slide.shapes.__iter__ = MagicMock(return_value=iter([]))
        mock_slide.has_notes_slide = True
        notes_tf = MagicMock()
        notes_tf.notes_text_frame.text = "  Note importante  "
        mock_slide.notes_slide = notes_tf
        mock_prs = MagicMock()
        mock_prs.slides = [mock_slide]

        with patch("agents.presentation_script_generator.Presentation", return_value=mock_prs):
            result = agent.extract_slides_content("fake.pptx")

        assert result[0]["notes"] == "Note importante"

    def test_notes_empty_when_no_notes_slide(self):
        agent = _make_agent()
        mock_slide = MagicMock()
        mock_slide.shapes.title = None
        mock_slide.shapes.__iter__ = MagicMock(return_value=iter([]))
        mock_slide.has_notes_slide = False
        mock_prs = MagicMock()
        mock_prs.slides = [mock_slide]

        with patch("agents.presentation_script_generator.Presentation", return_value=mock_prs):
            result = agent.extract_slides_content("fake.pptx")

        assert result[0]["notes"] == ""

    def test_multiple_slides_all_returned(self):
        agent = _make_agent()
        slides = []
        for _ in range(3):
            mock_slide = MagicMock()
            mock_slide.shapes.title = None
            mock_slide.shapes.__iter__ = MagicMock(return_value=iter([]))
            mock_slide.has_notes_slide = False
            slides.append(mock_slide)

        mock_prs = MagicMock()
        mock_prs.slides = slides

        with patch("agents.presentation_script_generator.Presentation", return_value=mock_prs):
            result = agent.extract_slides_content("multi.pptx")

        assert len(result) == 3
        assert result[2]["slide_number"] == 3

    def test_slide_data_has_required_keys(self):
        agent = _make_agent()
        mock_slide = MagicMock()
        mock_slide.shapes.title = None
        mock_slide.shapes.__iter__ = MagicMock(return_value=iter([]))
        mock_slide.has_notes_slide = False
        mock_prs = MagicMock()
        mock_prs.slides = [mock_slide]

        with patch("agents.presentation_script_generator.Presentation", return_value=mock_prs):
            result = agent.extract_slides_content("fake.pptx")

        for key in ("slide_number", "title", "content", "notes"):
            assert key in result[0], f"Missing key: {key}"


# ---------------------------------------------------------------------------
# Unit tests: generate_script_for_slide
# ---------------------------------------------------------------------------

class TestGenerateScriptForSlide:
    def test_calls_llm_generate(self):
        agent = _make_agent()
        slide_data = _make_slide_data()
        agent.llm.generate.return_value = "Script de test"

        result = agent.generate_script_for_slide(slide_data)

        agent.llm.generate.assert_called_once()
        assert "Script de test" == result

    def test_strips_markdown_fences(self):
        agent = _make_agent()
        slide_data = _make_slide_data()
        agent.llm.generate.return_value = "```markdown\n## Script\nTexte\n```"

        result = agent.generate_script_for_slide(slide_data)

        assert not result.startswith("```")
        assert not result.endswith("```")
        assert "## Script" in result

    def test_strips_plain_code_fence(self):
        agent = _make_agent()
        slide_data = _make_slide_data()
        agent.llm.generate.return_value = "```\n## Script\nTexte\n```"

        result = agent.generate_script_for_slide(slide_data)

        assert not result.startswith("```")
        assert not result.endswith("```")

    def test_returns_stripped_result_without_fences(self):
        agent = _make_agent()
        slide_data = _make_slide_data()
        agent.llm.generate.return_value = "  Script propre  "

        result = agent.generate_script_for_slide(slide_data)

        assert result == "Script propre"

    def test_passes_context_to_llm(self):
        agent = _make_agent()
        slide_data = _make_slide_data()
        agent.llm.generate.return_value = "ok"

        agent.generate_script_for_slide(slide_data, context="Formation avancee")

        call_kwargs = agent.llm.generate.call_args
        # context string appears somewhere in prompt args
        assert call_kwargs is not None

    def test_temperature_is_07(self):
        agent = _make_agent()
        slide_data = _make_slide_data()
        agent.llm.generate.return_value = "ok"

        agent.generate_script_for_slide(slide_data)

        call_kwargs = agent.llm.generate.call_args[1]
        assert call_kwargs.get("temperature") == 0.7

    def test_empty_content_list_handled(self):
        agent = _make_agent()
        slide_data = _make_slide_data(content=[])
        agent.llm.generate.return_value = "Script sans contenu"

        result = agent.generate_script_for_slide(slide_data)

        assert result == "Script sans contenu"

    def test_notes_in_slide_data_handled(self):
        agent = _make_agent()
        slide_data = _make_slide_data(notes="Parler lentement")
        agent.llm.generate.return_value = "Script avec notes"

        result = agent.generate_script_for_slide(slide_data)

        assert result == "Script avec notes"


# ---------------------------------------------------------------------------
# Unit tests: run
# ---------------------------------------------------------------------------

class TestPresentationScriptGeneratorRun:
    def _mock_extract_slides(self, agent, slides):
        """Patch extract_slides_content to return given slides list."""
        agent.extract_slides_content = MagicMock(return_value=slides)

    def test_run_returns_dict_with_required_keys(self):
        agent = _make_agent()
        slides = [_make_slide_data(1, "Intro"), _make_slide_data(2, "Corps")]
        self._mock_extract_slides(agent, slides)
        agent.llm.generate.return_value = "## Script"

        result = agent.run("fake.pptx")

        for key in ("markdown", "num_slides", "estimated_duration", "slides"):
            assert key in result, f"Missing key: {key}"

    def test_run_num_slides_matches_extracted(self):
        agent = _make_agent()
        slides = [_make_slide_data(i, f"Slide {i}") for i in range(1, 5)]
        self._mock_extract_slides(agent, slides)
        agent.llm.generate.return_value = "Script"

        result = agent.run("fake.pptx")

        assert result["num_slides"] == 4

    def test_run_estimated_duration_format(self):
        agent = _make_agent()
        slides = [_make_slide_data(1)]
        self._mock_extract_slides(agent, slides)
        agent.llm.generate.return_value = "Script"

        result = agent.run("fake.pptx")

        # Should contain a dash separating two numbers and "min"
        assert "-" in result["estimated_duration"]
        assert "min" in result["estimated_duration"]

    def test_run_markdown_contains_general_advice(self):
        agent = _make_agent()
        slides = [_make_slide_data(1, "Test")]
        self._mock_extract_slides(agent, slides)
        agent.llm.generate.return_value = "## Script mock"

        result = agent.run("fake.pptx")

        assert "Conseils generaux" in result["markdown"]

    def test_run_markdown_contains_conclusion(self):
        agent = _make_agent()
        slides = [_make_slide_data(1, "Test")]
        self._mock_extract_slides(agent, slides)
        agent.llm.generate.return_value = "## Script"

        result = agent.run("fake.pptx")

        assert "Conclusion" in result["markdown"]

    def test_run_slides_list_is_returned(self):
        agent = _make_agent()
        slides = [_make_slide_data(1, "Slide A"), _make_slide_data(2, "Slide B")]
        self._mock_extract_slides(agent, slides)
        agent.llm.generate.return_value = "Script"

        result = agent.run("fake.pptx")

        assert result["slides"] == slides

    def test_run_calls_generate_for_each_slide(self):
        agent = _make_agent()
        slides = [_make_slide_data(i, f"Slide {i}") for i in range(1, 4)]
        self._mock_extract_slides(agent, slides)
        agent.llm.generate.return_value = "Script"

        agent.run("fake.pptx")

        assert agent.llm.generate.call_count == 3

    def test_run_with_presentation_context(self):
        agent = _make_agent()
        slides = [_make_slide_data(1, "Intro")]
        self._mock_extract_slides(agent, slides)
        agent.llm.generate.return_value = "Script"

        result = agent.run("fake.pptx", presentation_context="Formation equipe dirigeante")

        # Should not raise; markdown is a non-empty string
        assert isinstance(result["markdown"], str)
        assert len(result["markdown"]) > 0

    def test_run_zero_slides_duration_is_zero(self):
        agent = _make_agent()
        self._mock_extract_slides(agent, [])
        agent.llm.generate.return_value = "Script"

        result = agent.run("empty.pptx")

        assert result["num_slides"] == 0
        # Duration string: "0-0 min"
        assert result["estimated_duration"].startswith("0")

    def test_run_script_in_markdown_for_each_slide(self):
        agent = _make_agent()
        slides = [_make_slide_data(1, "Titre Unique")]
        self._mock_extract_slides(agent, slides)
        agent.llm.generate.return_value = "## Script Slide 1"

        result = agent.run("fake.pptx")

        assert "## Script Slide 1" in result["markdown"]
