"""Tests for the HTML Slide Generator agent"""

import os
import sys
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestHtmlSlideGenerator:
    """Tests for HtmlSlideGeneratorAgent"""

    def test_imports(self):
        """Test that the module can be imported"""
        from agents.html_slide_generator import HtmlSlideGeneratorAgent

        assert HtmlSlideGeneratorAgent is not None

    def test_init(self):
        """Test agent initialization"""
        from agents.html_slide_generator import HtmlSlideGeneratorAgent

        agent = HtmlSlideGeneratorAgent()
        assert agent.llm.provider == "gemini"
        assert agent.llm.model == "gemini-3.1-pro-preview"
        assert agent.base_dir.exists()

    def test_extract_design_system(self):
        """Test design system extraction returns expected structure"""
        from agents.html_slide_generator import HtmlSlideGeneratorAgent

        agent = HtmlSlideGeneratorAgent()
        design = agent.extract_design_system()

        assert "colors" in design
        assert "fonts" in design
        assert "dimensions" in design

        assert design["colors"]["coral"] == "#FF6B58"
        assert design["colors"]["dark"] == "#1F1F1F"
        assert design["colors"]["terracotta"] == "#C0504D"
        assert design["colors"]["white"] == "#FFFFFF"
        assert design["colors"]["rose_poudre"] == "#FBF0F4"

        assert design["fonts"]["title"] == "Chakra Petch"
        assert design["fonts"]["body"] == "Inter"

        assert design["dimensions"]["width"] == 960
        assert design["dimensions"]["height"] == 540
        assert design["dimensions"]["ratio"] == "16:9"

    def test_design_system_cache(self):
        """Test that extract_design_system caches results"""
        from agents.html_slide_generator import HtmlSlideGeneratorAgent

        HtmlSlideGeneratorAgent._design_cache = None  # Reset cache
        agent = HtmlSlideGeneratorAgent()
        result1 = agent.extract_design_system()
        result2 = agent.extract_design_system()
        assert result1 is result2  # Same object (cached)
        assert HtmlSlideGeneratorAgent._design_cache is result1
        HtmlSlideGeneratorAgent._design_cache = None  # Cleanup

    def test_max_tokens_scales_with_slide_count(self):
        """Test that max_tokens scales based on num_slides"""
        # Formula: min(num_slides * 1500 + 2000, 65536)
        # 5 slides: 9500, 20 slides: 32000, 40 slides: 62000, 50: capped
        assert min(5 * 1500 + 2000, 65536) == 9500
        assert min(20 * 1500 + 2000, 65536) == 32000
        assert min(40 * 1500 + 2000, 65536) == 62000
        assert min(50 * 1500 + 2000, 65536) == 65536

    def test_build_prompt_returns_tuple(self):
        """Test that build_prompt returns system_instruction and user_prompt"""
        from agents.html_slide_generator import HtmlSlideGeneratorAgent

        agent = HtmlSlideGeneratorAgent()
        design = agent.extract_design_system()

        system_inst, user_prompt = agent.build_prompt("Introduction a l'IA", 10, design)

        assert isinstance(system_inst, str)
        assert isinstance(user_prompt, str)

    def test_build_prompt_contains_design_system(self):
        """Test that the system instruction contains design system values"""
        from agents.html_slide_generator import HtmlSlideGeneratorAgent

        agent = HtmlSlideGeneratorAgent()
        design = agent.extract_design_system()

        system_inst, user_prompt = agent.build_prompt("Introduction a l'IA", 10, design)

        assert "#FF6B58" in system_inst
        assert "#1F1F1F" in system_inst
        assert "Chakra Petch" in system_inst
        assert "Inter" in system_inst
        assert "960" in system_inst
        assert "540" in system_inst

    def test_system_instruction_has_visual_rules(self):
        """Test that system instruction includes visual and branding rules"""
        from agents.html_slide_generator import HtmlSlideGeneratorAgent

        agent = HtmlSlideGeneratorAgent()
        design = agent.extract_design_system()
        system_inst, _ = agent.build_prompt("Test", 10, design)
        # Branding elements
        assert "WENVISION" in system_inst
        assert "60%" in system_inst or "60-30-10" in system_inst
        # SVG illustrations
        assert "SVG" in system_inst
        # CSS diagrams
        assert "diagramme" in system_inst.lower() or "DIAGRAMME" in system_inst

    def test_user_prompt_has_visual_reminder(self):
        """Test that user prompts include visual reminder for all types"""
        from agents.html_slide_generator import HtmlSlideGeneratorAgent

        agent = HtmlSlideGeneratorAgent()
        design = agent.extract_design_system()
        for gen_type in ["presentation", "proposal", "formation", "rex"]:
            _, user_prompt = agent.build_prompt("Test", 10, design, gen_type=gen_type)
            assert "VISUEL" in user_prompt or "visuel" in user_prompt

    def test_no_hashtag_tags_in_prompts(self):
        """Test that hashtag tags are not in the prompts"""
        from agents.html_slide_generator import HtmlSlideGeneratorAgent

        agent = HtmlSlideGeneratorAgent()
        design = agent.extract_design_system()
        system_inst, _ = agent.build_prompt("Test", 10, design)
        assert "#TECH" not in system_inst
        assert "#CONTEXTE" not in system_inst
        assert "Tags en en-tete" not in system_inst

    def test_build_prompt_contains_topic(self):
        """Test that the user prompt contains the topic"""
        from agents.html_slide_generator import HtmlSlideGeneratorAgent

        agent = HtmlSlideGeneratorAgent()
        design = agent.extract_design_system()

        _, user_prompt = agent.build_prompt("Strategie Data 2026", 5, design)

        assert "Strategie Data 2026" in user_prompt
        assert "5" in user_prompt

    def test_clean_html_strips_backticks(self):
        """Test that markdown backticks are properly stripped"""
        from agents.html_slide_generator import HtmlSlideGeneratorAgent

        agent = HtmlSlideGeneratorAgent()

        raw = "```html\n<!DOCTYPE html><html><body></body></html>\n```"
        cleaned = agent.clean_html_response(raw)

        assert cleaned.startswith("<!DOCTYPE html>")
        assert "```" not in cleaned

    def test_clean_html_strips_triple_backticks(self):
        """Test stripping of triple backticks without html marker"""
        from agents.html_slide_generator import HtmlSlideGeneratorAgent

        agent = HtmlSlideGeneratorAgent()

        raw = "```\n<!DOCTYPE html><html><body></body></html>\n```"
        cleaned = agent.clean_html_response(raw)

        assert cleaned.startswith("<!DOCTYPE html>")

    def test_clean_html_passthrough(self):
        """Test that clean HTML passes through unchanged"""
        from agents.html_slide_generator import HtmlSlideGeneratorAgent

        agent = HtmlSlideGeneratorAgent()

        raw = "<!DOCTYPE html><html><body></body></html>"
        cleaned = agent.clean_html_response(raw)

        assert cleaned == raw

    def test_clean_html_finds_doctype_in_text(self):
        """Test that HTML is found even with preceding text"""
        from agents.html_slide_generator import HtmlSlideGeneratorAgent

        agent = HtmlSlideGeneratorAgent()

        raw = "Voici le code:\n<!DOCTYPE html><html><body></body></html>"
        cleaned = agent.clean_html_response(raw)

        assert cleaned.startswith("<!DOCTYPE html>")

    @patch("agents.html_slide_generator.LLMClient")
    def test_run_pipeline(self, mock_llm_class):
        """Test full pipeline with mocked LLM"""
        mock_llm = MagicMock()
        mock_llm.provider = "gemini"
        mock_llm.model = "gemini-3.1-pro-preview"
        mock_llm.generate_with_context.return_value = (
            "<!DOCTYPE html><html><head><style>.slide{width:960px;height:540px;}"
            '</style></head><body><section class="slide"><h1>Test</h1></section>'
            "</body></html>"
        )
        mock_llm_class.return_value = mock_llm

        from agents.html_slide_generator import HtmlSlideGeneratorAgent

        agent = HtmlSlideGeneratorAgent()
        agent.llm = mock_llm

        result = agent.run("Test topic", num_slides=5)

        assert "html_content" in result
        assert "html_path" in result
        assert "topic" in result
        assert result["topic"] == "Test topic"
        assert result["num_slides"] == 5
        assert result["html_path"].endswith(".html")
        assert "<!DOCTYPE html>" in result["html_content"]

    @patch("agents.html_slide_generator.LLMClient")
    def test_save_html_creates_file(self, mock_llm_class):
        """Test that save_html creates the output file"""
        mock_llm = MagicMock()
        mock_llm.provider = "gemini"
        mock_llm.model = "gemini-3.1-pro-preview"
        mock_llm_class.return_value = mock_llm

        from agents.html_slide_generator import HtmlSlideGeneratorAgent

        agent = HtmlSlideGeneratorAgent()
        agent.llm = mock_llm

        html = "<!DOCTYPE html><html><body>Test</body></html>"
        path = agent.save_html(html)

        full_path = agent.base_dir / path
        assert full_path.exists()
        assert path.startswith("output/")
        assert path.endswith(".html")

        # Cleanup
        full_path.unlink()

    def test_has_run_method(self):
        """Test agent has the run method"""
        from agents.html_slide_generator import HtmlSlideGeneratorAgent

        agent = HtmlSlideGeneratorAgent()
        assert hasattr(agent, "run")
        assert callable(agent.run)

    def test_has_required_methods(self):
        """Test agent has all required methods"""
        from agents.html_slide_generator import HtmlSlideGeneratorAgent

        agent = HtmlSlideGeneratorAgent()
        assert hasattr(agent, "extract_design_system")
        assert hasattr(agent, "build_prompt")
        assert hasattr(agent, "clean_html_response")
        assert hasattr(agent, "save_html")
        assert hasattr(agent, "run")
        assert hasattr(agent, "run_streaming")
        assert hasattr(agent, "extract_sections_from_buffer")
        assert hasattr(agent, "parse_section_to_json")
        assert hasattr(agent, "extract_head_html")

    # =========================================
    # Tests for extract_sections_from_buffer
    # =========================================

    def test_extract_sections_single(self):
        """Test extracting a single complete section"""
        from agents.html_slide_generator import HtmlSlideGeneratorAgent

        buf = '<section class="slide" data-type="cover"><h1>Title</h1></section>'
        sections = HtmlSlideGeneratorAgent.extract_sections_from_buffer(buf)
        assert len(sections) == 1
        assert 'data-type="cover"' in sections[0]

    def test_extract_sections_multiple(self):
        """Test extracting multiple complete sections"""
        from agents.html_slide_generator import HtmlSlideGeneratorAgent

        buf = (
            '<section class="slide" data-type="cover"><h1>Title</h1></section>'
            '<section class="slide" data-type="content"><p>Body</p></section>'
        )
        sections = HtmlSlideGeneratorAgent.extract_sections_from_buffer(buf)
        assert len(sections) == 2

    def test_extract_sections_incomplete(self):
        """Test that incomplete sections are not extracted"""
        from agents.html_slide_generator import HtmlSlideGeneratorAgent

        buf = (
            '<section class="slide" data-type="cover"><h1>Title</h1></section>'
            '<section class="slide" data-type="content"><p>Incomplete'
        )
        sections = HtmlSlideGeneratorAgent.extract_sections_from_buffer(buf)
        assert len(sections) == 1

    def test_extract_sections_nested(self):
        """Test extraction with nested section-like elements"""
        from agents.html_slide_generator import HtmlSlideGeneratorAgent

        buf = '<section class="slide"><section class="inner">Nested</section></section>'
        sections = HtmlSlideGeneratorAgent.extract_sections_from_buffer(buf)
        assert len(sections) == 1
        assert "Nested" in sections[0]

    def test_extract_sections_empty_buffer(self):
        """Test extraction from empty buffer"""
        from agents.html_slide_generator import HtmlSlideGeneratorAgent

        assert HtmlSlideGeneratorAgent.extract_sections_from_buffer("") == []

    def test_extract_sections_no_sections(self):
        """Test extraction from buffer with no sections"""
        from agents.html_slide_generator import HtmlSlideGeneratorAgent

        buf = "<div><p>No sections here</p></div>"
        assert HtmlSlideGeneratorAgent.extract_sections_from_buffer(buf) == []

    # =========================================
    # Tests for extract_head_html
    # =========================================

    def test_extract_head_html(self):
        """Test head HTML extraction"""
        from agents.html_slide_generator import HtmlSlideGeneratorAgent

        buf = "<html><head><style>.slide{width:960px}</style></head><body></body></html>"
        head = HtmlSlideGeneratorAgent.extract_head_html(buf)
        assert "<style>" in head
        assert "960px" in head

    def test_extract_head_html_incomplete(self):
        """Test head extraction with incomplete head tag"""
        from agents.html_slide_generator import HtmlSlideGeneratorAgent

        buf = "<html><head><style>.slide{width:960px}</style>"
        head = HtmlSlideGeneratorAgent.extract_head_html(buf)
        assert head == ""  # No closing </head>

    def test_extract_head_html_no_head(self):
        """Test head extraction with no head tag"""
        from agents.html_slide_generator import HtmlSlideGeneratorAgent

        buf = "<html><body><p>No head</p></body></html>"
        head = HtmlSlideGeneratorAgent.extract_head_html(buf)
        assert head == ""

    # =========================================
    # Tests for parse_section_to_json
    # =========================================

    def test_parse_section_cover(self):
        """Test parsing a cover section"""
        from agents.html_slide_generator import HtmlSlideGeneratorAgent

        html = '<section class="slide" data-type="cover"><h1>Mon Titre</h1><p>Sous-titre</p><div class="notes">Speaker notes ici</div></section>'
        result = HtmlSlideGeneratorAgent.parse_section_to_json(html)
        assert result["type"] == "cover"
        assert result["title"] == "Mon Titre"
        assert result["notes"] == "Speaker notes ici"
        assert result["subtitle"] == "Sous-titre"

    def test_parse_section_content_with_bullets(self):
        """Test parsing a content section with bullet points"""
        from agents.html_slide_generator import HtmlSlideGeneratorAgent

        html = '<section class="slide" data-type="content"><h2>Points cles</h2><ul><li>Point A</li><li>Point B</li></ul></section>'
        result = HtmlSlideGeneratorAgent.parse_section_to_json(html)
        assert result["type"] == "content"
        assert result["title"] == "Points cles"
        assert result["bullets"] == ["Point A", "Point B"]

    def test_parse_section_quote(self):
        """Test parsing a quote section"""
        from agents.html_slide_generator import HtmlSlideGeneratorAgent

        html = '<section class="slide" data-type="quote"><blockquote>La donnee est le nouveau petrole</blockquote></section>'
        result = HtmlSlideGeneratorAgent.parse_section_to_json(html)
        assert result["type"] == "quote"
        assert "petrole" in result["quote_text"]

    def test_parse_section_table(self):
        """Test parsing a table section"""
        from agents.html_slide_generator import HtmlSlideGeneratorAgent

        html = '<section class="slide" data-type="table"><h2>Planning</h2><table><tr><th>Phase</th><th>Echeance</th></tr><tr><td>Phase 1</td><td>T1 2026</td></tr></table></section>'
        result = HtmlSlideGeneratorAgent.parse_section_to_json(html)
        assert result["type"] == "table"
        assert result["headers"] == ["Phase", "Echeance"]
        assert result["rows"] == [["Phase 1", "T1 2026"]]

    def test_parse_section_highlight(self):
        """Test parsing a highlight section"""
        from agents.html_slide_generator import HtmlSlideGeneratorAgent

        html = '<section class="slide" data-type="highlight"><h2>Nos convictions</h2><ul><li>Point 1</li><li>Point 2</li></ul></section>'
        result = HtmlSlideGeneratorAgent.parse_section_to_json(html)
        assert result["type"] == "highlight"
        assert result["key_points"] == ["Point 1", "Point 2"]

    def test_parse_section_no_data_type_heuristic(self):
        """Test heuristic type detection when data-type is missing"""
        from agents.html_slide_generator import HtmlSlideGeneratorAgent

        html = '<section class="slide"><h1>Merci</h1></section>'
        result = HtmlSlideGeneratorAgent.parse_section_to_json(html)
        # Should fall back to 'content' since no dark background markers
        assert result["type"] in ("content", "cover", "closing")
        assert result["title"] == "Merci"

    def test_parse_section_missing_title(self):
        """Test parsing section with no title defaults gracefully"""
        from agents.html_slide_generator import HtmlSlideGeneratorAgent

        html = '<section class="slide" data-type="stat"><p>Some text</p></section>'
        result = HtmlSlideGeneratorAgent.parse_section_to_json(html)
        assert "title" in result

    # =========================================
    # Tests for type-specific prompts
    # =========================================

    def test_build_prompt_proposal_type(self):
        """Test proposal type prompt contains expected keywords"""
        from agents.html_slide_generator import HtmlSlideGeneratorAgent

        agent = HtmlSlideGeneratorAgent()
        design = agent.extract_design_system()
        _, user_prompt = agent.build_prompt("Migration Cloud", 10, design, gen_type="proposal")
        assert "PROPOSITION COMMERCIALE" in user_prompt
        assert "Methodologie" in user_prompt or "methodologie" in user_prompt

    def test_build_prompt_formation_type(self):
        """Test formation type prompt contains pedagogical elements"""
        from agents.html_slide_generator import HtmlSlideGeneratorAgent

        agent = HtmlSlideGeneratorAgent()
        design = agent.extract_design_system()
        _, user_prompt = agent.build_prompt("Python avance", 15, design, gen_type="formation")
        assert "FORMATION" in user_prompt
        assert "THEORIE" in user_prompt or "PRATIQUE" in user_prompt

    def test_build_prompt_rex_type(self):
        """Test REX type prompt contains mission keywords"""
        from agents.html_slide_generator import HtmlSlideGeneratorAgent

        agent = HtmlSlideGeneratorAgent()
        design = agent.extract_design_system()
        _, user_prompt = agent.build_prompt("Migration SAP", 10, design, gen_type="rex")
        assert "RETOUR D'EXPERIENCE" in user_prompt or "REX" in user_prompt

    def test_build_prompt_presentation_default(self):
        """Test default presentation type"""
        from agents.html_slide_generator import HtmlSlideGeneratorAgent

        agent = HtmlSlideGeneratorAgent()
        design = agent.extract_design_system()
        _, user_prompt = agent.build_prompt("IA Generative", 10, design, gen_type="presentation")
        assert "PRESENTATION" in user_prompt

    def test_build_prompt_with_audience(self):
        """Test prompt includes audience when specified"""
        from agents.html_slide_generator import HtmlSlideGeneratorAgent

        agent = HtmlSlideGeneratorAgent()
        design = agent.extract_design_system()
        _, user_prompt = agent.build_prompt("Topic", 10, design, audience="CTO et DSI")
        assert "CTO et DSI" in user_prompt

    def test_build_prompt_with_document_text(self):
        """Test prompt includes document source text"""
        from agents.html_slide_generator import HtmlSlideGeneratorAgent

        agent = HtmlSlideGeneratorAgent()
        design = agent.extract_design_system()
        _, user_prompt = agent.build_prompt(
            "Topic", 10, design, document_text="Contenu du document source"
        )
        assert "Contenu du document source" in user_prompt

    # =========================================
    # Tests for run_streaming
    # =========================================

    @patch("agents.html_slide_generator.LLMClient")
    def test_run_streaming_yields_slides(self, mock_llm_class):
        """Test that run_streaming yields slide dicts"""
        mock_llm = MagicMock()
        mock_llm.provider = "gemini"
        mock_llm.model = "gemini-3.1-pro-preview"

        html_response = (
            "<html><head><style>.slide{width:960px}</style></head><body>"
            '<section class="slide" data-type="cover"><h1>Titre</h1>'
            '<div class="notes">Notes cover</div></section>'
            '<section class="slide" data-type="content"><h2>Contenu</h2>'
            "<ul><li>Point 1</li><li>Point 2</li></ul></section>"
            "</body></html>"
        )
        mock_llm.stream_with_context.return_value = iter([html_response])
        mock_llm_class.return_value = mock_llm

        from agents.html_slide_generator import HtmlSlideGeneratorAgent

        agent = HtmlSlideGeneratorAgent()
        agent.llm = mock_llm

        results = list(agent.run_streaming("Test topic", num_slides=5))
        assert len(results) == 2

        # First slide: cover with head_html
        assert results[0]["head_html"] != ""
        assert results[0]["index"] == 0
        assert results[0]["slide_json"]["type"] == "cover"
        assert results[0]["slide_json"]["title"] == "Titre"
        assert "html_section" in results[0]

        # Second slide: content without head_html
        assert results[1]["head_html"] == ""
        assert results[1]["index"] == 1
        assert results[1]["slide_json"]["type"] == "content"
        assert results[1]["slide_json"]["bullets"] == ["Point 1", "Point 2"]

    @patch("agents.html_slide_generator.LLMClient")
    def test_run_streaming_scales_tokens_for_large_count(self, mock_llm_class):
        """Test that run_streaming uses scaled max_tokens for 20+ slides"""
        mock_llm = MagicMock()
        mock_llm.provider = "gemini"
        mock_llm.model = "gemini-3.1-pro-preview"
        mock_llm.stream_with_context.return_value = iter([""])
        mock_llm_class.return_value = mock_llm

        from agents.html_slide_generator import HtmlSlideGeneratorAgent

        agent = HtmlSlideGeneratorAgent()
        agent.llm = mock_llm

        list(agent.run_streaming("Test", num_slides=20))
        call_kwargs = mock_llm.stream_with_context.call_args[1]
        # 20 * 1500 + 2000 = 32000
        assert call_kwargs["max_tokens"] == 32000

    @patch("agents.html_slide_generator.LLMClient")
    def test_run_streaming_empty_response(self, mock_llm_class):
        """Test run_streaming with empty LLM response"""
        mock_llm = MagicMock()
        mock_llm.provider = "gemini"
        mock_llm.model = "gemini-3.1-pro-preview"
        mock_llm.stream_with_context.return_value = iter([""])
        mock_llm_class.return_value = mock_llm

        from agents.html_slide_generator import HtmlSlideGeneratorAgent

        agent = HtmlSlideGeneratorAgent()
        agent.llm = mock_llm

        results = list(agent.run_streaming("Test", num_slides=5))
        assert len(results) == 0
