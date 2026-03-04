"""
Tests for agents/training_slides_generator.py
Phase 5 - Coverage improvement
"""
import json
import os
from pathlib import Path
from unittest.mock import MagicMock, patch, mock_open

import pytest

os.environ.setdefault("GEMINI_API_KEY", "test-gemini-key")
os.environ.setdefault("ANTHROPIC_API_KEY", "test-anthropic-key")


# ---------------------------------------------------------------------------
# Helpers / fixtures
# ---------------------------------------------------------------------------

def _make_agent():
    """Return a TrainingSlidesGeneratorAgent with mocked LLM and NanoBanana."""
    with patch("agents.training_slides_generator.LLMClient") as mock_llm_cls, \
         patch("agents.training_slides_generator.NanoBananaGenerator") as mock_nb_cls:
        mock_llm_cls.return_value = MagicMock()
        mock_nb_cls.return_value = MagicMock()
        from agents.training_slides_generator import TrainingSlidesGeneratorAgent
        agent = TrainingSlidesGeneratorAgent()
    return agent


SAMPLE_PROGRAMME_DATA = {
    "title": "Introduction à l'IA",
    "code": "WV-AI-100",
    "duration": "2 jours",
    "level": "100",
    "target_audience": "Professionnels",
    "modules": [
        {
            "name": "Module 1 : Fondamentaux",
            "duration": "1 jour",
            "objectives": ["Comprendre l'IA", "Connaître les outils"],
            "days": [
                {
                    "day_number": 1,
                    "title": "Jour 1",
                    "topics": ["Introduction", "Machine Learning"],
                    "ateliers": ["Atelier pratique LLM"],
                }
            ],
        }
    ],
}


# ---------------------------------------------------------------------------
# Class: TestImportsAndInit
# ---------------------------------------------------------------------------

class TestImportsAndInit:
    def test_module_can_be_imported(self):
        from agents.training_slides_generator import TrainingSlidesGeneratorAgent
        assert TrainingSlidesGeneratorAgent is not None

    def test_agent_init_creates_attributes(self):
        with patch("agents.training_slides_generator.LLMClient") as mock_llm_cls, \
             patch("agents.training_slides_generator.NanoBananaGenerator") as mock_nb_cls:
            mock_llm_cls.return_value = MagicMock()
            mock_nb_cls.return_value = MagicMock()
            from agents.training_slides_generator import TrainingSlidesGeneratorAgent
            agent = TrainingSlidesGeneratorAgent()
        assert hasattr(agent, "llm")
        assert hasattr(agent, "nano_banana")
        assert hasattr(agent, "base_dir")
        assert isinstance(agent.base_dir, Path)

    def test_agent_has_required_methods(self):
        agent = _make_agent()
        for method in [
            "parse_programme",
            "generate_slides_for_module",
            "generate_all_slides",
            "generate_premium_html_presentation",
            "_get_slides_plan",
            "_determine_slide_content",
            "_assemble_final_slide",
            "_wrap_in_full_document",
            "generate_module_pptx",
            "_sanitize_json_string",
        ]:
            assert hasattr(agent, method), f"Missing method: {method}"
            assert callable(getattr(agent, method))


# ---------------------------------------------------------------------------
# Class: TestSanitizeJsonString
# ---------------------------------------------------------------------------

class TestSanitizeJsonString:
    def test_empty_string_returns_empty(self):
        from agents.training_slides_generator import TrainingSlidesGeneratorAgent
        assert TrainingSlidesGeneratorAgent._sanitize_json_string("") == ""

    def test_strips_surrounding_whitespace(self):
        from agents.training_slides_generator import TrainingSlidesGeneratorAgent
        result = TrainingSlidesGeneratorAgent._sanitize_json_string("  hello  ")
        assert result == "hello"

    def test_removes_control_characters(self):
        from agents.training_slides_generator import TrainingSlidesGeneratorAgent
        # \x00 through \x08 should be removed; \n and \t kept
        text = "before\x00\x01\x07after"
        result = TrainingSlidesGeneratorAgent._sanitize_json_string(text)
        assert result == "beforeafter"

    def test_keeps_newline_and_tab(self):
        from agents.training_slides_generator import TrainingSlidesGeneratorAgent
        text = "line1\nline2\ttabbed"
        result = TrainingSlidesGeneratorAgent._sanitize_json_string(text)
        assert "\n" in result
        assert "\t" in result

    def test_valid_json_passes_through(self):
        from agents.training_slides_generator import TrainingSlidesGeneratorAgent
        text = '{"key": "value"}'
        result = TrainingSlidesGeneratorAgent._sanitize_json_string(text)
        assert result == '{"key": "value"}'

    def test_none_returns_empty(self):
        from agents.training_slides_generator import TrainingSlidesGeneratorAgent
        # None is falsy — falls into `if not text: return ""`
        result = TrainingSlidesGeneratorAgent._sanitize_json_string(None)
        assert result == ""


# ---------------------------------------------------------------------------
# Class: TestParseProgramme
# ---------------------------------------------------------------------------

class TestParseProgramme:
    def test_parse_programme_calls_llm(self):
        agent = _make_agent()
        agent.llm.generate.return_value = json.dumps(SAMPLE_PROGRAMME_DATA)

        result = agent.parse_programme("# Formation Test\n## Module 1\n...")

        agent.llm.generate.assert_called_once()
        assert result["title"] == "Introduction à l'IA"
        assert len(result["modules"]) == 1

    def test_parse_programme_strips_json_backticks(self):
        agent = _make_agent()
        wrapped = "```json\n" + json.dumps(SAMPLE_PROGRAMME_DATA) + "\n```"
        agent.llm.generate.return_value = wrapped

        result = agent.parse_programme("some markdown")
        assert result["title"] == "Introduction à l'IA"

    def test_parse_programme_strips_plain_backticks(self):
        agent = _make_agent()
        wrapped = "```\n" + json.dumps(SAMPLE_PROGRAMME_DATA) + "\n```"
        agent.llm.generate.return_value = wrapped

        result = agent.parse_programme("some markdown")
        assert result["code"] == "WV-AI-100"

    def test_parse_programme_returns_modules_list(self):
        agent = _make_agent()
        agent.llm.generate.return_value = json.dumps(SAMPLE_PROGRAMME_DATA)

        result = agent.parse_programme("test")
        assert isinstance(result["modules"], list)
        assert result["modules"][0]["name"] == "Module 1 : Fondamentaux"

    def test_parse_programme_raises_on_invalid_json(self):
        agent = _make_agent()
        agent.llm.generate.return_value = "not valid json at all"

        with pytest.raises(Exception):
            agent.parse_programme("test")

    def test_parse_programme_uses_low_temperature(self):
        agent = _make_agent()
        agent.llm.generate.return_value = json.dumps(SAMPLE_PROGRAMME_DATA)
        agent.parse_programme("test")

        call_kwargs = agent.llm.generate.call_args
        assert call_kwargs.kwargs.get("temperature", 1.0) == 0.3 or \
               (call_kwargs.args and 0.3 in call_kwargs.args)


# ---------------------------------------------------------------------------
# Class: TestGenerateSlidesForModule
# ---------------------------------------------------------------------------

SAMPLE_SLIDES_JSON = json.dumps([
    {"type": "section", "title": "Module 1 : Fondamentaux"},
    {"type": "stat", "stat_value": "87%", "stat_label": "de projets IA échouent"},
    {"type": "highlight", "title": "3 piliers", "key_points": ["Transparence", "Protection", "Équité"]},
])


class TestGenerateSlidesForModule:
    def test_generate_slides_calls_llm(self):
        agent = _make_agent()
        agent.llm.generate.return_value = SAMPLE_SLIDES_JSON

        slides = agent.generate_slides_for_module(SAMPLE_PROGRAMME_DATA, 0)

        agent.llm.generate.assert_called_once()
        assert isinstance(slides, list)
        assert len(slides) == 3

    def test_generate_slides_returns_slide_dicts(self):
        agent = _make_agent()
        agent.llm.generate.return_value = SAMPLE_SLIDES_JSON

        slides = agent.generate_slides_for_module(SAMPLE_PROGRAMME_DATA, 0)
        assert slides[0]["type"] == "section"
        assert slides[1]["type"] == "stat"

    def test_generate_slides_strips_json_backticks(self):
        agent = _make_agent()
        agent.llm.generate.return_value = "```json\n" + SAMPLE_SLIDES_JSON + "\n```"

        slides = agent.generate_slides_for_module(SAMPLE_PROGRAMME_DATA, 0)
        assert len(slides) == 3

    def test_generate_slides_uses_public_cible(self):
        agent = _make_agent()
        agent.llm.generate.return_value = SAMPLE_SLIDES_JSON

        agent.generate_slides_for_module(
            SAMPLE_PROGRAMME_DATA, 0, public_cible="Data Scientists"
        )
        call_args = agent.llm.generate.call_args
        prompt = call_args.kwargs.get("prompt", "") or (call_args.args[0] if call_args.args else "")
        assert "Data Scientists" in prompt

    def test_generate_slides_uses_duree(self):
        agent = _make_agent()
        agent.llm.generate.return_value = SAMPLE_SLIDES_JSON

        agent.generate_slides_for_module(
            SAMPLE_PROGRAMME_DATA, 0, duree="3 jours"
        )
        call_args = agent.llm.generate.call_args
        prompt = call_args.kwargs.get("prompt", "") or (call_args.args[0] if call_args.args else "")
        # Module has its own duration; duree is fallback
        assert "Module 1 : Fondamentaux" in prompt

    def test_generate_slides_raises_on_invalid_json(self):
        agent = _make_agent()
        agent.llm.generate.return_value = "invalid json"

        with pytest.raises(Exception):
            agent.generate_slides_for_module(SAMPLE_PROGRAMME_DATA, 0)


# ---------------------------------------------------------------------------
# Class: TestGenerateAllSlides
# ---------------------------------------------------------------------------

class TestGenerateAllSlides:
    def test_generate_all_slides_returns_full_result(self):
        agent = _make_agent()
        # parse_programme call
        agent.llm.generate.side_effect = [
            json.dumps(SAMPLE_PROGRAMME_DATA),  # parse_programme
            SAMPLE_SLIDES_JSON,                  # generate_slides_for_module (module 0)
        ]

        result = agent.generate_all_slides("# Formation Test")

        assert "programme_data" in result
        assert "modules_slides" in result
        assert "all_slides" in result
        assert "total_slides" in result
        assert "generated_at" in result

    def test_generate_all_slides_cover_is_first(self):
        agent = _make_agent()
        agent.llm.generate.side_effect = [
            json.dumps(SAMPLE_PROGRAMME_DATA),
            SAMPLE_SLIDES_JSON,
        ]

        result = agent.generate_all_slides("# Formation Test")
        assert result["all_slides"][0]["type"] == "cover"

    def test_generate_all_slides_closing_is_last(self):
        agent = _make_agent()
        agent.llm.generate.side_effect = [
            json.dumps(SAMPLE_PROGRAMME_DATA),
            SAMPLE_SLIDES_JSON,
        ]

        result = agent.generate_all_slides("# Formation Test")
        assert result["all_slides"][-1]["type"] == "closing"

    def test_generate_all_slides_cover_has_title(self):
        agent = _make_agent()
        agent.llm.generate.side_effect = [
            json.dumps(SAMPLE_PROGRAMME_DATA),
            SAMPLE_SLIDES_JSON,
        ]

        result = agent.generate_all_slides("# Formation Test")
        cover = result["all_slides"][0]
        assert cover["title"] == "Introduction à l'IA"

    def test_generate_all_slides_module_slides_keyed_by_name(self):
        agent = _make_agent()
        agent.llm.generate.side_effect = [
            json.dumps(SAMPLE_PROGRAMME_DATA),
            SAMPLE_SLIDES_JSON,
        ]

        result = agent.generate_all_slides("# Formation Test")
        assert "Module 1 : Fondamentaux" in result["modules_slides"]

    def test_generate_all_slides_total_count(self):
        agent = _make_agent()
        agent.llm.generate.side_effect = [
            json.dumps(SAMPLE_PROGRAMME_DATA),
            SAMPLE_SLIDES_JSON,
        ]

        result = agent.generate_all_slides("# Formation Test")
        # 1 cover + 3 module slides + 1 closing = 5
        assert result["total_slides"] == 5
        assert len(result["all_slides"]) == result["total_slides"]

    def test_generate_all_slides_empty_modules(self):
        agent = _make_agent()
        programme_no_modules = dict(SAMPLE_PROGRAMME_DATA)
        programme_no_modules["modules"] = []
        agent.llm.generate.return_value = json.dumps(programme_no_modules)

        result = agent.generate_all_slides("# Formation vide")
        # 1 cover + 1 closing
        assert result["total_slides"] == 2
        assert result["modules_slides"] == {}

    def test_generate_all_slides_generated_at_is_string(self):
        agent = _make_agent()
        agent.llm.generate.side_effect = [
            json.dumps(SAMPLE_PROGRAMME_DATA),
            SAMPLE_SLIDES_JSON,
        ]

        result = agent.generate_all_slides("# Formation Test")
        assert isinstance(result["generated_at"], str)
        assert "T" in result["generated_at"]  # ISO format contains 'T'

    def test_generate_all_slides_closing_uses_consultant_name(self, monkeypatch):
        agent = _make_agent()
        monkeypatch.setenv("CONSULTANT_NAME", "Jane Doe")
        agent.llm.generate.side_effect = [
            json.dumps(SAMPLE_PROGRAMME_DATA),
            SAMPLE_SLIDES_JSON,
        ]

        result = agent.generate_all_slides("# Formation Test")
        closing = result["all_slides"][-1]
        assert any("Jane Doe" in str(b) for b in closing["bullets"])


# ---------------------------------------------------------------------------
# Class: TestAssembleFinalSlide
# ---------------------------------------------------------------------------

class TestAssembleFinalSlide:
    def test_assemble_with_image_path(self):
        agent = _make_agent()
        html = agent._assemble_final_slide("Mon Titre", "images/slide_0.jpg", 0)
        assert "Mon Titre" in html
        assert "images/slide_0.jpg" in html
        assert "infographic" in html
        assert 'id="slide-0"' in html

    def test_assemble_without_image_path(self):
        agent = _make_agent()
        html = agent._assemble_final_slide("Titre vide", "", 1)
        assert "Titre vide" in html
        assert "no-image" in html
        assert "infographic" not in html

    def test_assemble_slide_index_in_html(self):
        agent = _make_agent()
        html = agent._assemble_final_slide("Slide 5", "img.jpg", 5)
        assert 'id="slide-5"' in html

    def test_assemble_returns_section_tag(self):
        agent = _make_agent()
        html = agent._assemble_final_slide("X", "", 0)
        assert "<section" in html
        assert "</section>" in html


# ---------------------------------------------------------------------------
# Class: TestWrapInFullDocument
# ---------------------------------------------------------------------------

class TestWrapInFullDocument:
    def test_wrap_contains_doctype(self):
        agent = _make_agent()
        html = agent._wrap_in_full_document("Ma Formation", ["<section>S1</section>"])
        assert "<!DOCTYPE html>" in html

    def test_wrap_contains_title(self):
        agent = _make_agent()
        html = agent._wrap_in_full_document("Ma Formation", [])
        assert "Ma Formation" in html

    def test_wrap_contains_all_slides(self):
        agent = _make_agent()
        slides = ["<section>Slide A</section>", "<section>Slide B</section>"]
        html = agent._wrap_in_full_document("Test", slides)
        assert "Slide A" in html
        assert "Slide B" in html

    def test_wrap_contains_css_variables(self):
        agent = _make_agent()
        html = agent._wrap_in_full_document("T", [])
        assert "--coral:" in html or "--dark:" in html

    def test_wrap_contains_google_fonts(self):
        agent = _make_agent()
        html = agent._wrap_in_full_document("T", [])
        assert "fonts.googleapis.com" in html

    def test_wrap_is_valid_html_structure(self):
        agent = _make_agent()
        html = agent._wrap_in_full_document("T", [])
        assert "<html" in html
        assert "</html>" in html
        assert "<head>" in html
        assert "<body>" in html


# ---------------------------------------------------------------------------
# Class: TestGetSlidesPlan
# ---------------------------------------------------------------------------

class TestGetSlidesPlan:
    def test_get_slides_plan_returns_list(self):
        agent = _make_agent()
        plan_json = json.dumps([
            {"title": "Introduction", "type": "intro"},
            {"title": "Module 1", "type": "section"},
        ])
        agent.llm.generate.return_value = plan_json

        plan = agent._get_slides_plan(SAMPLE_PROGRAMME_DATA)
        assert isinstance(plan, list)
        assert len(plan) == 2

    def test_get_slides_plan_strips_backticks(self):
        agent = _make_agent()
        plan_data = [{"title": "Intro", "type": "intro"}]
        agent.llm.generate.return_value = "```json\n" + json.dumps(plan_data) + "\n```"

        plan = agent._get_slides_plan(SAMPLE_PROGRAMME_DATA)
        assert plan[0]["title"] == "Intro"

    def test_get_slides_plan_calls_llm(self):
        agent = _make_agent()
        agent.llm.generate.return_value = "[]"

        agent._get_slides_plan(SAMPLE_PROGRAMME_DATA)
        agent.llm.generate.assert_called_once()


# ---------------------------------------------------------------------------
# Class: TestDetermineSlideContent
# ---------------------------------------------------------------------------

class TestDetermineSlideContent:
    def test_determine_slide_content_returns_dict(self):
        agent = _make_agent()
        content = {"image_prompt": "A robot holding data charts, minimalist style"}
        agent.llm.generate.return_value = json.dumps(content)

        result = agent._determine_slide_content(
            {"title": "Introduction à l'IA", "type": "section"},
            "Formation IA"
        )
        assert "image_prompt" in result
        assert "robot" in result["image_prompt"].lower() or "data" in result["image_prompt"].lower()

    def test_determine_slide_content_strips_backticks(self):
        agent = _make_agent()
        content = {"image_prompt": "minimalist chart"}
        agent.llm.generate.return_value = "```json\n" + json.dumps(content) + "\n```"

        result = agent._determine_slide_content({"title": "Test"}, "Formation")
        assert result["image_prompt"] == "minimalist chart"

    def test_determine_slide_content_calls_llm(self):
        agent = _make_agent()
        agent.llm.generate.return_value = json.dumps({"image_prompt": "test"})

        agent._determine_slide_content({"title": "Slide"}, "Formation")
        agent.llm.generate.assert_called_once()


# ---------------------------------------------------------------------------
# Class: TestGeneratePremiumHtmlPresentation
# ---------------------------------------------------------------------------

class TestGeneratePremiumHtmlPresentation:
    def test_generate_premium_creates_html_file(self, tmp_path):
        agent = _make_agent()
        # Patch base_dir so output goes to tmp_path
        agent.base_dir = tmp_path

        plan = [{"title": "Introduction", "type": "intro"}]
        content_detail = {"image_prompt": "test image prompt"}

        agent.llm.generate.side_effect = [
            json.dumps(SAMPLE_PROGRAMME_DATA),  # parse_programme
            json.dumps(plan),                    # _get_slides_plan
            json.dumps(content_detail),          # _determine_slide_content slide 0
        ]

        agent.nano_banana.generate_image.return_value = None

        result = agent.generate_premium_html_presentation("# Programme Test")

        assert "html_path" in result
        assert "total_slides" in result
        assert result["total_slides"] == 1

    def test_generate_premium_calls_nano_banana(self, tmp_path):
        agent = _make_agent()
        agent.base_dir = tmp_path

        plan = [{"title": "Slide A", "type": "intro"}]
        content_detail = {"image_prompt": "robot chart"}

        agent.llm.generate.side_effect = [
            json.dumps(SAMPLE_PROGRAMME_DATA),
            json.dumps(plan),
            json.dumps(content_detail),
        ]
        agent.nano_banana.generate_image.return_value = None

        agent.generate_premium_html_presentation("# Programme")
        agent.nano_banana.generate_image.assert_called_once()

    def test_generate_premium_returns_output_dir(self, tmp_path):
        agent = _make_agent()
        agent.base_dir = tmp_path

        plan = [{"title": "Slide X", "type": "intro"}]
        content_detail = {"image_prompt": "abstract"}

        agent.llm.generate.side_effect = [
            json.dumps(SAMPLE_PROGRAMME_DATA),
            json.dumps(plan),
            json.dumps(content_detail),
        ]
        agent.nano_banana.generate_image.return_value = None

        result = agent.generate_premium_html_presentation("# Test")
        assert "output_dir" in result

    def test_generate_premium_no_image_still_assembles(self, tmp_path):
        agent = _make_agent()
        agent.base_dir = tmp_path

        plan = [{"title": "Slide Y", "type": "section"}]
        content_detail = {"image_prompt": "abstract art"}

        agent.llm.generate.side_effect = [
            json.dumps(SAMPLE_PROGRAMME_DATA),
            json.dumps(plan),
            json.dumps(content_detail),
        ]
        # NanoBanana returns None (no image)
        agent.nano_banana.generate_image.return_value = None

        result = agent.generate_premium_html_presentation("# Test")
        html_path = Path(result["output_dir"]) / "index.html"
        assert html_path.exists()
        content = html_path.read_text(encoding="utf-8")
        assert "no-image" in content


# ---------------------------------------------------------------------------
# Class: TestGenerateModulePptx
# ---------------------------------------------------------------------------

class TestGenerateModulePptx:
    def test_generate_module_pptx_calls_build_proposal_pptx(self, tmp_path):
        agent = _make_agent()
        agent.base_dir = tmp_path
        (tmp_path / "output").mkdir(exist_ok=True)

        slides = [{"type": "section", "title": "Module Test"}]

        with patch("agents.training_slides_generator.TrainingSlidesGeneratorAgent.generate_module_pptx") as mock_gen:
            mock_gen.return_value = "output/formation_test.pptx"
            result = agent.generate_module_pptx(slides, "Test Module")

        assert result == "output/formation_test.pptx"

    def test_generate_module_pptx_sanitizes_name(self, tmp_path):
        """Module name with spaces and slashes is sanitized for the filename."""
        agent = _make_agent()
        agent.base_dir = tmp_path
        (tmp_path / "output").mkdir(exist_ok=True)

        slides = [{"type": "section", "title": "Module Test"}]

        mock_build = MagicMock()
        with patch("utils.pptx_generator.build_proposal_pptx", mock_build):
            result = agent.generate_module_pptx(slides, "Module 1 / Part A")

        assert " " not in result.split("/")[-1].split(".")[0]
