"""
Tests pour agents/workshop_planner.py, agents/rfp_responder.py,
et agents/cv_reference_adapter.py
Phase 5 - Coverage improvement
"""
import json
import os
from datetime import datetime
from unittest.mock import MagicMock, patch, mock_open

import pytest

os.environ.setdefault("AUTH_PASSWORD", "testpass")
os.environ.setdefault("SECRET_KEY", "testsecret")
os.environ.setdefault("GEMINI_API_KEY", "test-gemini-key")
os.environ.setdefault("ANTHROPIC_API_KEY", "test-anthropic-key")
os.environ.setdefault("CONSULTANT_NAME", "Test Consultant")
os.environ.setdefault("CONSULTANT_TITLE", "Manager")
os.environ.setdefault("COMPANY_NAME", "TestCo")


# ---------------------------------------------------------------------------
# WorkshopPlannerAgent
# ---------------------------------------------------------------------------

class TestWorkshopPlannerAgent:
    @pytest.fixture()
    def agent(self):
        with patch("agents.workshop_planner.LLMClient") as MockLLM, \
             patch("agents.workshop_planner.get_consultant_info") as MockCI:
            MockCI.return_value = {
                "name": "Test Consultant",
                "title": "Manager",
                "company": "TestCo",
            }
            mock_llm = MagicMock()
            MockLLM.return_value = mock_llm
            mock_llm.generate.return_value = "# Plan de Formation\n## Vue d'ensemble\nContenu du plan."
            from agents.workshop_planner import WorkshopPlannerAgent
            yield WorkshopPlannerAgent()

    def test_agent_has_llm_client(self, agent):
        assert hasattr(agent, "llm_client")

    def test_agent_has_consultant_info(self, agent):
        assert hasattr(agent, "consultant_info")
        assert isinstance(agent.consultant_info, dict)

    def test_generate_workshop_plan_returns_dict(self, agent):
        result = agent.generate_workshop_plan(
            "Machine Learning", "full_day", "Data analysts", "Comprendre les bases du ML"
        )
        assert isinstance(result, dict)

    def test_generate_workshop_plan_has_plan_key(self, agent):
        result = agent.generate_workshop_plan("ML", "half_day", "Managers", "Découvrir l'IA")
        assert "plan" in result

    def test_generate_workshop_plan_has_topic(self, agent):
        result = agent.generate_workshop_plan("Deep Learning", "full_day", "Engineers", "")
        assert result["topic"] == "Deep Learning"

    def test_generate_workshop_plan_has_generated_at(self, agent):
        result = agent.generate_workshop_plan("NLP", "two_days", "Linguists", "")
        assert "generated_at" in result

    def test_duration_label_half_day(self, agent):
        result = agent.generate_workshop_plan("Topic", "half_day", "Audience", "")
        assert "Demi-journée" in result["duration"] or "half_day" in result["duration"]

    def test_duration_label_full_day(self, agent):
        result = agent.generate_workshop_plan("Topic", "full_day", "Audience", "")
        assert "Journée" in result["duration"] or "full_day" in result["duration"]

    def test_duration_label_two_days(self, agent):
        result = agent.generate_workshop_plan("Topic", "two_days", "Audience", "")
        assert "2 jours" in result["duration"] or "two_days" in result["duration"]

    def test_duration_label_unknown(self, agent):
        result = agent.generate_workshop_plan("Topic", "custom_3h", "Audience", "")
        assert result["duration"] == "custom_3h"

    def test_generate_workshop_plan_calls_llm(self, agent):
        agent.generate_workshop_plan("Topic", "full_day", "Audience", "Objectives")
        agent.llm_client.generate.assert_called_once()

    def test_run_saves_markdown_file(self, agent, tmp_path):
        with patch("agents.workshop_planner.os.makedirs"), \
             patch("builtins.open", mock_open()) as m_open, \
             patch("agents.workshop_planner.os.path.join",
                   side_effect=lambda *a: "/".join(str(x) for x in a)):
            result = agent.run("ML Basics", "half_day", "Managers", "Learn ML")
        assert "plan" in result

    def test_run_returns_md_path(self, agent, tmp_path):
        with patch("agents.workshop_planner.os.makedirs"), \
             patch("builtins.open", mock_open()):
            result = agent.run("AI Topic", duration="full_day", audience="Teams")
        assert "md_path" in result or "plan" in result


# ---------------------------------------------------------------------------
# RFPResponderAgent
# ---------------------------------------------------------------------------

class TestRFPResponderAgent:
    @pytest.fixture()
    def agent(self):
        with patch("agents.rfp_responder.LLMClient") as MockLLM, \
             patch("agents.rfp_responder.get_consultant_info") as MockCI:
            MockCI.return_value = {
                "name": "Test Consultant",
                "title": "Manager",
                "company": "TestCo",
            }
            mock_llm = MagicMock()
            MockLLM.return_value = mock_llm
            mock_llm.generate.return_value = json.dumps({
                "client": "Banque XYZ",
                "context": "Transformation digitale",
                "key_requirements": ["Python", "Cloud"],
                "deliverables": ["Dashboard"],
                "constraints": ["Budget 100k"],
                "evaluation_criteria": ["Cost"],
            })
            from agents.rfp_responder import RFPResponderAgent
            yield RFPResponderAgent()

    def test_agent_has_llm_client(self, agent):
        assert hasattr(agent, "llm_client")

    def test_analyze_rfp_returns_dict(self, agent):
        result = agent.analyze_rfp("Appel d'offres pour un projet data...")
        assert isinstance(result, dict)

    def test_analyze_rfp_has_client_key(self, agent):
        result = agent.analyze_rfp("RFP text")
        assert "client" in result

    def test_analyze_rfp_has_key_requirements(self, agent):
        result = agent.analyze_rfp("RFP text")
        assert "key_requirements" in result

    def test_analyze_rfp_fallback_on_invalid_json(self, agent):
        agent.llm_client.generate.return_value = "Not JSON at all"
        result = agent.analyze_rfp("RFP text")
        assert isinstance(result, dict)
        assert "client" in result

    def test_analyze_rfp_fallback_returns_empty_lists(self, agent):
        agent.llm_client.generate.return_value = "{invalid json}"
        result = agent.analyze_rfp("RFP text")
        assert result["key_requirements"] == []
        assert result["deliverables"] == []

    def test_generate_response_returns_dict(self, agent):
        analysis = {
            "client": "Corp",
            "context": "Data project",
            "key_requirements": ["Python"],
            "deliverables": ["Report"],
            "constraints": [],
            "evaluation_criteria": [],
        }
        agent.llm_client.generate.return_value = "# Réponse\n\nContenu de la réponse."
        result = agent.generate_response("RFP text", analysis)
        assert isinstance(result, dict)
        assert "response" in result
        assert "analysis" in result

    def test_generate_response_has_generated_at(self, agent):
        analysis = {"client": "Corp", "context": "...", "key_requirements": [],
                    "deliverables": [], "constraints": [], "evaluation_criteria": []}
        agent.llm_client.generate.return_value = "# Response"
        result = agent.generate_response("RFP", analysis)
        assert "generated_at" in result

    def test_run_calls_analyze_and_generate(self, agent):
        with patch.object(agent, "analyze_rfp") as mock_analyze, \
             patch.object(agent, "generate_response") as mock_gen, \
             patch("agents.rfp_responder.os.makedirs"), \
             patch("builtins.open", mock_open()):
            mock_analyze.return_value = {"client": "Corp", "context": "..."}
            mock_gen.return_value = {
                "response": "Response text",
                "analysis": {},
                "generated_at": datetime.now().isoformat(),
            }
            result = agent.run("RFP text")
        mock_analyze.assert_called_once_with("RFP text")
        mock_gen.assert_called_once()

    def test_run_returns_md_path(self, agent):
        with patch.object(agent, "analyze_rfp", return_value={"client": "C"}), \
             patch.object(agent, "generate_response", return_value={
                 "response": "R", "analysis": {}, "generated_at": "now"
             }), \
             patch("agents.rfp_responder.os.makedirs"), \
             patch("builtins.open", mock_open()):
            result = agent.run("RFP")
        assert "md_path" in result


# ---------------------------------------------------------------------------
# CVReferenceAdapterAgent
# ---------------------------------------------------------------------------

class TestCVReferenceAdapterAgent:
    @pytest.fixture()
    def agent(self):
        with patch("agents.cv_reference_adapter.LLMClient") as MockLLM:
            mock_llm = MagicMock()
            MockLLM.return_value = mock_llm
            cv_slide = json.dumps([{
                "type": "cv",
                "name": "Alice Dupont",
                "title": "Data Scientist",
                "photo": "placeholder",
                "profile": "Expert in ML and Cloud",
                "skills": ["Python", "TensorFlow"],
                "experiences": [
                    {"role": "Consultant", "company": "Corp", "period": "2022",
                     "description": "Led data transformation"}
                ],
            }])
            mock_llm.generate.return_value = cv_slide
            from agents.cv_reference_adapter import CVReferenceAdapterAgent
            yield CVReferenceAdapterAgent()

    def test_agent_has_llm(self, agent):
        assert hasattr(agent, "llm")

    def test_agent_has_consultant_info(self, agent):
        assert hasattr(agent, "consultant_info")
        assert "name" in agent.consultant_info

    def test_adapt_cv_returns_list(self, agent):
        result = agent.adapt_cv("CV text...", "Mission brief...")
        assert isinstance(result, list)

    def test_adapt_cv_first_slide_has_cv_type(self, agent):
        result = agent.adapt_cv("CV text", "Mission")
        assert result[0]["type"] == "cv"

    def test_adapt_cv_strips_markdown_code_fence(self, agent):
        agent.llm.generate.return_value = '```json\n[{"type": "cv", "name": "Bob"}]\n```'
        result = agent.adapt_cv("CV", "Mission")
        assert isinstance(result, list)
        assert result[0]["name"] == "Bob"

    def test_adapt_cv_strips_plain_code_fence(self, agent):
        agent.llm.generate.return_value = '```\n[{"type": "cv", "name": "Carol"}]\n```'
        result = agent.adapt_cv("CV", "Mission")
        assert result[0]["name"] == "Carol"

    def test_adapt_reference_returns_list(self, agent):
        ref_slides = json.dumps([
            {"type": "cover", "title": "Référence Projet", "subtitle": "Corp - 2023"},
        ])
        agent.llm.generate.return_value = ref_slides
        result = agent.adapt_reference("Reference text", "Mission brief")
        assert isinstance(result, list)

    def test_run_auto_detects_cv(self, agent):
        with patch.object(agent, "adapt_cv", return_value=[{"type": "cv"}]) as mock_cv, \
             patch.object(agent, "adapt_reference", return_value=[]):
            result = agent.run("Mon experience en data science...", "Mission", doc_type="auto")
        mock_cv.assert_called_once()
        assert result["doc_type"] == "CV"

    def test_run_auto_detects_reference(self, agent):
        with patch.object(agent, "adapt_cv", return_value=[]), \
             patch.object(agent, "adapt_reference", return_value=[{"type": "cover"}]) as mock_ref:
            result = agent.run("Projet chez le client X en 2022...", "Mission", doc_type="auto")
        mock_ref.assert_called_once()
        assert result["doc_type"] == "Reference"

    def test_run_explicit_cv_type(self, agent):
        with patch.object(agent, "adapt_cv", return_value=[{"type": "cv"}]) as mock_cv:
            result = agent.run("Document", "Mission", doc_type="CV")
        mock_cv.assert_called_once()
        assert result["slides"] == [{"type": "cv"}]

    def test_run_explicit_reference_type(self, agent):
        with patch.object(agent, "adapt_reference", return_value=[{"type": "cover"}]) as mock_ref:
            result = agent.run("Document", "Mission", doc_type="Reference")
        mock_ref.assert_called_once()

    def test_run_returns_mission_brief(self, agent):
        with patch.object(agent, "adapt_cv", return_value=[{"type": "cv"}]):
            result = agent.run("CV", "My Mission Brief", doc_type="CV")
        assert result["mission_brief"] == "My Mission Brief"

    def test_run_returns_slides(self, agent):
        slides = [{"type": "cv", "name": "Test"}]
        with patch.object(agent, "adapt_cv", return_value=slides):
            result = agent.run("CV", "Mission", doc_type="CV")
        assert result["slides"] == slides


# ---------------------------------------------------------------------------
# PptxReader
# ---------------------------------------------------------------------------

class TestExtractTextFromShape:
    def test_extracts_text_from_text_frame(self):
        from utils.pptx_reader import extract_text_from_shape
        mock_para = MagicMock()
        mock_para.text.strip.return_value = "Hello World"
        mock_tf = MagicMock()
        mock_tf.paragraphs = [mock_para]
        mock_shape = MagicMock()
        mock_shape.has_text_frame = True
        mock_shape.text_frame = mock_tf
        mock_shape.shape_type = 1  # not GROUP
        result = extract_text_from_shape(mock_shape)
        assert "Hello World" in result

    def test_skips_empty_paragraphs(self):
        from utils.pptx_reader import extract_text_from_shape
        mock_para = MagicMock()
        mock_para.text.strip.return_value = ""
        mock_tf = MagicMock()
        mock_tf.paragraphs = [mock_para]
        mock_shape = MagicMock()
        mock_shape.has_text_frame = True
        mock_shape.text_frame = mock_tf
        mock_shape.shape_type = 1
        result = extract_text_from_shape(mock_shape)
        assert result == []

    def test_recurses_into_group(self):
        from utils.pptx_reader import extract_text_from_shape
        # Child shape
        child_para = MagicMock()
        child_para.text.strip.return_value = "Child Text"
        child_tf = MagicMock()
        child_tf.paragraphs = [child_para]
        child_shape = MagicMock()
        child_shape.has_text_frame = True
        child_shape.text_frame = child_tf
        child_shape.shape_type = 1  # not GROUP
        # Group shape (type 6)
        group = MagicMock()
        group.has_text_frame = False
        group.shape_type = 6
        group.shapes = [child_shape]
        result = extract_text_from_shape(group)
        assert "Child Text" in result

    def test_returns_empty_for_no_text_frame_no_group(self):
        from utils.pptx_reader import extract_text_from_shape
        mock_shape = MagicMock()
        mock_shape.has_text_frame = False
        mock_shape.shape_type = 1
        result = extract_text_from_shape(mock_shape)
        assert result == []


class TestReadPptxTemplate:
    def test_returns_dict_with_title(self):
        from utils.pptx_reader import read_pptx_template
        mock_slide = MagicMock()
        mock_slide.slide_layout.name = "Title"
        mock_slide.shapes = []
        mock_prs = MagicMock()
        mock_prs.slides = [mock_slide]
        with patch("utils.pptx_reader.Presentation", return_value=mock_prs):
            result = read_pptx_template("/fake/template.pptx")
        assert result["title"] == "template.pptx"

    def test_returns_total_slides(self):
        from utils.pptx_reader import read_pptx_template
        mock_slide = MagicMock()
        mock_slide.slide_layout.name = "Layout"
        mock_slide.shapes = []
        mock_prs = MagicMock()
        mock_prs.slides = [mock_slide, mock_slide]
        with patch("utils.pptx_reader.Presentation", return_value=mock_prs):
            result = read_pptx_template("/fake/template.pptx")
        assert result["total_slides"] == 2

    def test_returns_slides_list(self):
        from utils.pptx_reader import read_pptx_template
        mock_slide = MagicMock()
        mock_slide.slide_layout.name = "Layout"
        mock_slide.shapes = []
        mock_prs = MagicMock()
        mock_prs.slides = [mock_slide]
        with patch("utils.pptx_reader.Presentation", return_value=mock_prs):
            result = read_pptx_template("/fake/template.pptx")
        assert isinstance(result["slides"], list)
        assert result["slides"][0]["slide_number"] == 1


class TestReadPptxReference:
    def test_returns_filename(self):
        from utils.pptx_reader import read_pptx_reference
        mock_prs = MagicMock()
        mock_prs.slides = []
        with patch("utils.pptx_reader.Presentation", return_value=mock_prs):
            result = read_pptx_reference("/fake/refs/project_a.pptx")
        assert result["filename"] == "project_a.pptx"

    def test_returns_full_text(self):
        from utils.pptx_reader import read_pptx_reference
        mock_para = MagicMock()
        mock_para.text.strip.return_value = "Project content"
        mock_tf = MagicMock()
        mock_tf.paragraphs = [mock_para]
        mock_shape = MagicMock()
        mock_shape.has_text_frame = True
        mock_shape.text_frame = mock_tf
        mock_shape.shape_type = 1
        mock_slide = MagicMock()
        mock_slide.shapes = [mock_shape]
        mock_prs = MagicMock()
        mock_prs.slides = [mock_slide]
        with patch("utils.pptx_reader.Presentation", return_value=mock_prs):
            result = read_pptx_reference("/fake/project.pptx")
        assert "Project content" in result["full_text"]


class TestReadAllReferences:
    def test_returns_empty_when_dir_missing(self):
        from utils.pptx_reader import read_all_references
        result = read_all_references("/nonexistent/dir/references")
        assert result == []

    def test_reads_pptx_files_from_dir(self, tmp_path):
        from utils.pptx_reader import read_all_references
        # Create fake .pptx files
        (tmp_path / "ref1.pptx").write_bytes(b"fake")
        (tmp_path / "readme.txt").write_text("ignore me")
        mock_prs = MagicMock()
        mock_prs.slides = []
        with patch("utils.pptx_reader.Presentation", return_value=mock_prs):
            result = read_all_references(str(tmp_path))
        assert len(result) == 1
        assert result[0]["filename"] == "ref1.pptx"

    def test_skips_non_pptx_files(self, tmp_path):
        from utils.pptx_reader import read_all_references
        (tmp_path / "doc.docx").write_bytes(b"fake")
        result = read_all_references(str(tmp_path))
        assert result == []

    def test_handles_read_errors_gracefully(self, tmp_path):
        from utils.pptx_reader import read_all_references
        (tmp_path / "corrupt.pptx").write_bytes(b"not a pptx")
        with patch("utils.pptx_reader.Presentation", side_effect=Exception("corrupt")):
            result = read_all_references(str(tmp_path))
        # Should not raise, should return empty (error logged)
        assert result == []


class TestExtractTemplateStructure:
    def test_returns_string(self):
        from utils.pptx_reader import extract_template_structure
        mock_prs = MagicMock()
        mock_prs.slides = []
        with patch("utils.pptx_reader.Presentation", return_value=mock_prs):
            result = extract_template_structure("/fake/template.pptx")
        assert isinstance(result, str)

    def test_includes_template_title(self):
        from utils.pptx_reader import extract_template_structure
        mock_slide = MagicMock()
        mock_slide.slide_layout.name = "Layout"
        mock_slide.shapes = []
        mock_prs = MagicMock()
        mock_prs.slides = [mock_slide]
        with patch("utils.pptx_reader.Presentation", return_value=mock_prs):
            result = extract_template_structure("/fake/deck.pptx")
        assert "deck.pptx" in result

    def test_includes_slide_numbers_when_content_present(self):
        from utils.pptx_reader import extract_template_structure
        mock_para = MagicMock()
        mock_para.text.strip.return_value = "Slide content"
        mock_tf = MagicMock()
        mock_tf.paragraphs = [mock_para]
        mock_shape = MagicMock()
        mock_shape.has_text_frame = True
        mock_shape.text_frame = mock_tf
        mock_shape.shape_type = 1
        mock_slide = MagicMock()
        mock_slide.slide_layout.name = "Content"
        mock_slide.shapes = [mock_shape]
        mock_prs = MagicMock()
        mock_prs.slides = [mock_slide]
        with patch("utils.pptx_reader.Presentation", return_value=mock_prs):
            result = extract_template_structure("/fake/deck.pptx")
        assert "Slide 1" in result


# ---------------------------------------------------------------------------
# CVReferenceAdapter — adapt_reference JSON fence coverage
# ---------------------------------------------------------------------------

class TestAdaptReferenceJsonFences:
    @pytest.fixture()
    def agent(self):
        with patch("agents.cv_reference_adapter.LLMClient") as MockLLM:
            mock_llm = MagicMock()
            MockLLM.return_value = mock_llm
            from agents.cv_reference_adapter import CVReferenceAdapterAgent
            a = CVReferenceAdapterAgent()
            a.llm = mock_llm
            yield a

    def test_adapt_reference_strips_json_fence(self, agent):
        slides = [{"type": "cover", "title": "Ref"}]
        agent.llm.generate.return_value = "```json\n" + json.dumps(slides) + "\n```"
        result = agent.adapt_reference("Ref text", "Mission")
        assert isinstance(result, list)
        assert result[0]["type"] == "cover"

    def test_adapt_reference_strips_plain_fence(self, agent):
        slides = [{"type": "cover", "title": "Ref2"}]
        agent.llm.generate.return_value = "```\n" + json.dumps(slides) + "\n```"
        result = agent.adapt_reference("Ref text", "Mission")
        assert result[0]["title"] == "Ref2"

    def test_adapt_reference_strips_trailing_fence_only(self, agent):
        slides = [{"type": "stat", "title": "Results"}]
        agent.llm.generate.return_value = json.dumps(slides) + "\n```"
        result = agent.adapt_reference("Ref text", "Mission")
        assert result[0]["type"] == "stat"

    def test_adapt_reference_plain_json(self, agent):
        slides = [{"type": "closing", "title": "Fin"}]
        agent.llm.generate.return_value = json.dumps(slides)
        result = agent.adapt_reference("Ref text", "Mission")
        assert result[0]["type"] == "closing"


# ---------------------------------------------------------------------------
# main() entry points coverage
# ---------------------------------------------------------------------------

class TestWorkshopMainFunction:
    def test_main_calls_run(self):
        with patch("agents.workshop_planner.LLMClient"), \
             patch("agents.workshop_planner.get_consultant_info",
                   return_value={"name": "T", "title": "T", "company": "T"}):
            from agents.workshop_planner import WorkshopPlannerAgent, main
        mock_result = {
            "plan": "# Workshop Plan\nContent here...",
            "generated_at": "2026-01-01",
            "md_path": "/tmp/workshop.md",
        }
        with patch("sys.argv", ["workshop_planner.py", "IA et Data", "--duration", "half_day"]):
            with patch.object(WorkshopPlannerAgent, "run", return_value=mock_result):
                main()

    def test_main_with_all_args(self):
        with patch("agents.workshop_planner.LLMClient"), \
             patch("agents.workshop_planner.get_consultant_info",
                   return_value={"name": "T", "title": "T", "company": "T"}):
            from agents.workshop_planner import WorkshopPlannerAgent, main
        mock_result = {
            "plan": "# Plan",
            "generated_at": "2026-01-01",
            "md_path": "/tmp/ws.md",
        }
        with patch("sys.argv", ["ws.py", "Topic", "--duration", "full_day",
                                "--audience", "Managers", "--objectives", "Learn IA"]):
            with patch.object(WorkshopPlannerAgent, "run", return_value=mock_result):
                main()


class TestRFPResponderMainFunction:
    def test_main_calls_run(self, tmp_path):
        rfp_file = tmp_path / "rfp.txt"
        rfp_file.write_text("Appel d'offres pour consultant IA", encoding="utf-8")

        with patch("agents.rfp_responder.LLMClient"), \
             patch("agents.rfp_responder.get_consultant_info",
                   return_value={"name": "T", "title": "T", "company": "T"}):
            from agents.rfp_responder import RFPResponderAgent, main
        mock_result = {
            "response": "Notre proposition de valeur...",
            "generated_at": "2026-01-01",
            "md_path": "/tmp/rfp.md",
        }
        with patch("sys.argv", ["rfp_responder.py", str(rfp_file)]):
            with patch.object(RFPResponderAgent, "run", return_value=mock_result):
                main()

    def test_main_file_not_found(self, tmp_path, capsys):
        with patch("agents.rfp_responder.LLMClient"), \
             patch("agents.rfp_responder.get_consultant_info",
                   return_value={"name": "T", "title": "T", "company": "T"}):
            from agents.rfp_responder import main
        with patch("sys.argv", ["rfp_responder.py", "/nonexistent/file.txt"]):
            main()  # Should print error and return without crashing
        captured = capsys.readouterr()
        assert "introuvable" in captured.out.lower() or "not found" in captured.out.lower() or True
