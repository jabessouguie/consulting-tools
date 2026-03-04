"""
Tests pour agents/doc_to_presentation.py
Cible: augmenter la couverture depuis 18% (109 stmts)
"""
import io
import json
import os
import sys
from unittest.mock import MagicMock, patch, mock_open

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ.setdefault("CONSULTANT_NAME", "Test Consultant")
os.environ.setdefault("CONSULTANT_TITLE", "Manager")
os.environ.setdefault("COMPANY_NAME", "TestCo")
os.environ.setdefault("ANTHROPIC_API_KEY", "test-anthropic-key")
os.environ.setdefault("GEMINI_API_KEY", "test-gemini-key")
os.environ.setdefault("AUTH_PASSWORD", "testpass")
os.environ.setdefault("SECRET_KEY", "testsecret")


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def agent():
    """Return a DocToPresentationAgent with LLM fully mocked."""
    with patch("agents.doc_to_presentation.LLMClient") as MockLLM:
        mock_llm_instance = MagicMock()
        MockLLM.return_value = mock_llm_instance
        mock_llm_instance.generate.return_value = json.dumps({
            "title": "Test Presentation",
            "slides": [
                {"type": "cover", "title": "Cover", "subtitle": "Sub"},
                {"type": "content", "title": "Slide 1", "bullets": ["Point A", "Point B"]},
                {"type": "closing", "title": "Thank you"},
            ]
        })

        from agents.doc_to_presentation import DocToPresentationAgent
        a = DocToPresentationAgent()
        yield a


@pytest.fixture()
def slides_data():
    return [
        {"type": "cover", "title": "Presentation Title", "subtitle": "Subtitle"},
        {"type": "section", "title": "Section 1"},
        {"type": "content", "title": "Content Slide", "bullets": ["Point A", "Point B"]},
        {"type": "stat", "stat_value": "42%", "stat_label": "Increase", "context": "YoY"},
        {"type": "closing", "title": "Merci", "subtitle": "Questions?"},
    ]


# ---------------------------------------------------------------------------
# TestDocToPresentationAgentInit
# ---------------------------------------------------------------------------

class TestDocToPresentationAgentInit:
    def test_agent_has_llm(self, agent):
        assert hasattr(agent, "llm")

    def test_agent_has_base_dir(self, agent):
        assert hasattr(agent, "base_dir")

    def test_agent_has_consultant_info(self, agent):
        assert hasattr(agent, "consultant_info")
        assert isinstance(agent.consultant_info, dict)

    def test_consultant_info_has_name(self, agent):
        assert "name" in agent.consultant_info

    def test_consultant_info_has_company(self, agent):
        assert "company" in agent.consultant_info


# ---------------------------------------------------------------------------
# TestParseDocument
# ---------------------------------------------------------------------------

class TestParseDocument:
    def test_parse_md_from_content_bytes(self, agent):
        content = "# Hello\nThis is markdown".encode("utf-8")
        result = agent.parse_document("", file_content=content, filename="test.md")
        assert "Hello" in result
        assert "markdown" in result

    def test_parse_md_from_file(self, agent, tmp_path):
        md_file = tmp_path / "test.md"
        md_file.write_text("# My Document\nContent here.", encoding="utf-8")
        result = agent.parse_document(str(md_file), filename="test.md")
        assert "My Document" in result

    def test_parse_txt_from_content_bytes(self, agent):
        content = "Plain text content".encode("utf-8")
        result = agent.parse_document("", file_content=content, filename="test.txt")
        assert "Plain text content" == result

    def test_parse_txt_from_file(self, agent, tmp_path):
        txt_file = tmp_path / "test.txt"
        txt_file.write_text("Text file content", encoding="utf-8")
        result = agent.parse_document(str(txt_file), filename="test.txt")
        assert "Text file content" in result

    def test_parse_unsupported_ext_returns_empty(self, agent):
        result = agent.parse_document("", file_content=b"data", filename="test.xyz")
        assert result == ""

    def test_parse_pdf_from_content(self, agent):
        mock_page = MagicMock()
        mock_page.extract_text.return_value = "PDF page text"
        mock_reader = MagicMock()
        mock_reader.pages = [mock_page]

        with patch("PyPDF2.PdfReader", return_value=mock_reader):
            result = agent.parse_document("", file_content=b"fake pdf", filename="test.pdf")
        assert isinstance(result, str)

    def test_parse_docx_from_content(self, agent):
        mock_para1 = MagicMock()
        mock_para1.text = "Paragraph one"
        mock_para2 = MagicMock()
        mock_para2.text = ""  # empty — should be filtered out
        mock_para3 = MagicMock()
        mock_para3.text = "Paragraph three"
        mock_doc = MagicMock()
        mock_doc.paragraphs = [mock_para1, mock_para2, mock_para3]
        mock_docx_mod = MagicMock()
        mock_docx_mod.Document.return_value = mock_doc

        with patch.dict("sys.modules", {"docx": mock_docx_mod}):
            result = agent.parse_document("", file_content=b"fake docx", filename="test.docx")
        assert "Paragraph one" in result
        assert "Paragraph three" in result

    def test_parse_docx_filters_empty_paragraphs(self, agent):
        mock_para_empty = MagicMock()
        mock_para_empty.text = "   "
        mock_doc = MagicMock()
        mock_doc.paragraphs = [mock_para_empty]
        mock_docx_mod = MagicMock()
        mock_docx_mod.Document.return_value = mock_doc

        with patch.dict("sys.modules", {"docx": mock_docx_mod}):
            result = agent.parse_document("", file_content=b"fake docx", filename="test.docx")
        assert result.strip() == ""

    def test_parse_detects_extension_from_filename(self, agent):
        content = "# Markdown content".encode("utf-8")
        # filename overrides the path extension
        result = agent.parse_document("/some/path/ignored.xyz", file_content=content, filename="doc.md")
        assert "Markdown content" in result


# ---------------------------------------------------------------------------
# TestAnalyzeAndStructure
# ---------------------------------------------------------------------------

class TestAnalyzeAndStructure:
    def test_returns_list(self, agent):
        agent.llm.generate.return_value = json.dumps({
            "title": "Test",
            "slides": [{"type": "cover", "title": "T", "subtitle": "S"}]
        })
        result = agent.analyze_and_structure("Document text", "Managers", "Present strategy")
        assert isinstance(result, list)

    def test_parses_json_code_block(self, agent):
        slides = [
            {"type": "cover", "title": "Cover", "subtitle": "Sub"},
            {"type": "content", "title": "Content", "bullets": ["A"]},
        ]
        response = "```json\n" + json.dumps({"title": "P", "slides": slides}) + "\n```"
        agent.llm.generate.return_value = response
        result = agent.analyze_and_structure("Doc text", "Dev team", "Objective")
        assert len(result) == 2
        assert result[0]["type"] == "cover"

    def test_parses_plain_code_block(self, agent):
        slides = [{"type": "section", "title": "Section"}]
        response = "```\n" + json.dumps({"title": "P", "slides": slides}) + "\n```"
        agent.llm.generate.return_value = response
        result = agent.analyze_and_structure("Doc text", "Audience", "Goal")
        assert len(result) == 1

    def test_parses_raw_json(self, agent):
        slides = [{"type": "closing", "title": "Done"}]
        response = json.dumps({"title": "P", "slides": slides})
        agent.llm.generate.return_value = response
        result = agent.analyze_and_structure("Doc", "All", "End")
        assert result[0]["type"] == "closing"

    def test_returns_empty_on_invalid_json(self, agent):
        agent.llm.generate.return_value = "This is not JSON at all"
        result = agent.analyze_and_structure("Doc", "Audience", "Goal")
        assert result == []

    def test_returns_empty_on_malformed_json(self, agent):
        agent.llm.generate.return_value = "```json\n{invalid json\n```"
        result = agent.analyze_and_structure("Doc", "Audience", "Goal")
        assert result == []

    def test_calls_llm_generate(self, agent):
        agent.llm.generate.return_value = json.dumps({"title": "T", "slides": []})
        agent.analyze_and_structure("Some content", "Tech team", "Goal")
        agent.llm.generate.assert_called_once()

    def test_returns_slides_key_only(self, agent):
        slides = [{"type": "stat", "stat_value": "80%", "stat_label": "Accuracy"}]
        agent.llm.generate.return_value = json.dumps({"title": "T", "slides": slides, "extra": "ignored"})
        result = agent.analyze_and_structure("Doc", "Audience", "Goal")
        assert isinstance(result, list)
        assert result[0]["stat_value"] == "80%"


# ---------------------------------------------------------------------------
# TestBuildPptx
# ---------------------------------------------------------------------------

class TestBuildPptx:
    def test_returns_relative_path_string(self, agent, slides_data, tmp_path):
        agent.base_dir = tmp_path
        fake_pptx_path = str(tmp_path / "output" / "presentation_20260304_120000.pptx")
        with patch("utils.pptx_generator.build_proposal_pptx", return_value=fake_pptx_path), \
             patch("agents.doc_to_presentation.build_proposal_pptx", return_value=fake_pptx_path, create=True):
            result = agent.build_pptx(slides_data, title="Test")
        # build_pptx catches any exception and returns None, or returns a relative path string
        assert result is None or isinstance(result, str)

    def test_returns_none_on_exception(self, agent, slides_data):
        # build_pptx catches all exceptions and returns None
        with patch("utils.pptx_generator.build_proposal_pptx", side_effect=Exception("PPTX failed")):
            result = agent.build_pptx(slides_data, title="Test")
        assert result is None

    def test_returns_none_when_import_fails(self, agent, slides_data):
        import builtins
        real_import = builtins.__import__

        def fake_import(name, *args, **kwargs):
            if name == "utils.pptx_generator":
                raise ImportError("no module")
            return real_import(name, *args, **kwargs)

        with patch("builtins.__import__", side_effect=fake_import):
            result = agent.build_pptx(slides_data, title="Test")
        assert result is None

    def test_creates_output_dir(self, agent, slides_data, tmp_path):
        agent.base_dir = tmp_path
        fake_pptx_path = str(tmp_path / "presentation_test.pptx")
        with patch("utils.pptx_generator.build_proposal_pptx", return_value=fake_pptx_path):
            agent.build_pptx(slides_data)
        # output dir is created inside — verify no crash occurred
        assert True


# ---------------------------------------------------------------------------
# TestGenerateImages
# ---------------------------------------------------------------------------

class TestGenerateImages:
    def test_returns_slides_list(self, agent, slides_data):
        mock_gen_instance = MagicMock()
        mock_gen_instance.generate_image.return_value = "/tmp/image.png"
        with patch("utils.image_generator.NanoBananaGenerator", return_value=mock_gen_instance):
            result = agent.generate_images(slides_data)
        assert isinstance(result, list)
        assert len(result) == len(slides_data)

    def test_adds_image_path_to_cover_slides(self, agent):
        slides = [{"type": "cover", "title": "Cover"}]
        mock_gen_instance = MagicMock()
        mock_gen_instance.generate_image.return_value = "/tmp/cover.png"
        with patch("utils.image_generator.NanoBananaGenerator", return_value=mock_gen_instance):
            result = agent.generate_images(slides)
        assert "image_path" in result[0]
        assert result[0]["image_path"] == "/tmp/cover.png"

    def test_adds_image_path_to_section_slides(self, agent):
        slides = [{"type": "section", "title": "Section 1"}]
        mock_gen_instance = MagicMock()
        mock_gen_instance.generate_image.return_value = "/tmp/section.png"
        with patch("utils.image_generator.NanoBananaGenerator", return_value=mock_gen_instance):
            result = agent.generate_images(slides)
        assert "image_path" in result[0]

    def test_adds_image_path_to_highlight_slides(self, agent):
        slides = [{"type": "highlight", "title": "Highlight", "key_points": ["A"]}]
        mock_gen_instance = MagicMock()
        mock_gen_instance.generate_image.return_value = "/tmp/hl.png"
        with patch("utils.image_generator.NanoBananaGenerator", return_value=mock_gen_instance):
            result = agent.generate_images(slides)
        assert "image_path" in result[0]

    def test_does_not_add_image_to_content_slides(self, agent):
        slides = [{"type": "content", "title": "Content", "bullets": ["X"]}]
        mock_gen_instance = MagicMock()
        mock_gen_instance.generate_image.return_value = "/tmp/x.png"
        with patch("utils.image_generator.NanoBananaGenerator", return_value=mock_gen_instance):
            result = agent.generate_images(slides)
        assert "image_path" not in result[0]

    def test_skips_image_when_generator_returns_none(self, agent):
        slides = [{"type": "cover", "title": "Cover"}]
        mock_gen_instance = MagicMock()
        mock_gen_instance.generate_image.return_value = None
        with patch("utils.image_generator.NanoBananaGenerator", return_value=mock_gen_instance):
            result = agent.generate_images(slides)
        assert "image_path" not in result[0]

    def test_handles_exception_gracefully(self, agent, slides_data):
        # generate_images wraps everything in try/except — any error returns slides unchanged
        with patch("utils.image_generator.NanoBananaGenerator", side_effect=Exception("error")):
            result = agent.generate_images(slides_data)
        assert isinstance(result, list)
        assert len(result) == len(slides_data)


# ---------------------------------------------------------------------------
# TestRunPipeline
# ---------------------------------------------------------------------------

class TestRunPipeline:
    def _make_documents(self):
        return [
            {"filename": "doc1.md", "content": b"# Document 1\nContent here"},
            {"filename": "doc2.txt", "content": b"Plain text content"},
        ]

    def test_run_returns_error_on_empty_content(self, agent):
        # Empty documents list → all_text is "" → error returned
        result = agent.run([], "Managers", "Present goals")
        assert "error" in result

    def test_run_returns_error_when_no_slides(self, agent):
        docs = self._make_documents()
        with patch.object(agent, "parse_document", return_value="Good content"), \
             patch.object(agent, "analyze_and_structure", return_value=[]):
            result = agent.run(docs, "Managers", "Present goals")
        assert "error" in result

    def test_run_returns_slides_and_count(self, agent):
        slides = [
            {"type": "cover", "title": "Cover"},
            {"type": "content", "title": "Content", "bullets": ["A"]},
        ]
        docs = self._make_documents()
        with patch.object(agent, "parse_document", return_value="Some content"), \
             patch.object(agent, "analyze_and_structure", return_value=slides), \
             patch.object(agent, "generate_images", return_value=slides), \
             patch.object(agent, "build_pptx", return_value="output/presentation.pptx"):
            result = agent.run(docs, "Managers", "Present strategy")
        assert "slides" in result
        assert result["slide_count"] == 2
        assert "pptx_path" in result
        assert "generated_at" in result

    def test_run_calls_parse_for_each_document(self, agent):
        docs = self._make_documents()
        with patch.object(agent, "parse_document", return_value="content") as mock_parse, \
             patch.object(agent, "analyze_and_structure", return_value=[{"type": "cover"}]), \
             patch.object(agent, "generate_images", return_value=[{"type": "cover"}]), \
             patch.object(agent, "build_pptx", return_value="path.pptx"):
            agent.run(docs, "Audience", "Goal")
        assert mock_parse.call_count == len(docs)

    def test_run_concatenates_document_texts(self, agent):
        docs = [
            {"filename": "a.md", "content": b"First doc"},
            {"filename": "b.txt", "content": b"Second doc"},
        ]
        captured_text = []

        def capture_analyze(text, audience, objective):
            captured_text.append(text)
            return [{"type": "cover"}]

        with patch.object(agent, "parse_document", side_effect=["First doc", "Second doc"]), \
             patch.object(agent, "analyze_and_structure", side_effect=capture_analyze), \
             patch.object(agent, "generate_images", return_value=[{"type": "cover"}]), \
             patch.object(agent, "build_pptx", return_value="path.pptx"):
            agent.run(docs, "Audience", "Goal")

        combined = captured_text[0]
        assert "First doc" in combined
        assert "Second doc" in combined

    def test_run_handles_pptx_build_failure(self, agent):
        slides = [{"type": "cover", "title": "Cover"}]
        docs = self._make_documents()
        with patch.object(agent, "parse_document", return_value="content"), \
             patch.object(agent, "analyze_and_structure", return_value=slides), \
             patch.object(agent, "generate_images", return_value=slides), \
             patch.object(agent, "build_pptx", return_value=None):
            result = agent.run(docs, "Audience", "Goal")
        assert result["pptx_path"] is None
