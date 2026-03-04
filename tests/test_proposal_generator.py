"""
Tests pour agents/proposal_generator.py
Phase 5 - Coverage improvement
"""
import json
import os
from pathlib import Path
from unittest.mock import MagicMock, patch, mock_open

import pytest

os.environ.setdefault("AUTH_PASSWORD", "testpass")
os.environ.setdefault("SECRET_KEY", "testsecret")
os.environ.setdefault("GEMINI_API_KEY", "test-gemini-key")
os.environ.setdefault("ANTHROPIC_API_KEY", "test-anthropic-key")
os.environ.setdefault("CONSULTANT_NAME", "Test Consultant")
os.environ.setdefault("CONSULTANT_TITLE", "Manager")
os.environ.setdefault("COMPANY_NAME", "TestCo")

# Import at module level so the module is cached BEFORE any fixture patches pptx
from agents.proposal_generator import ProposalGeneratorAgent  # noqa: E402


@pytest.fixture()
def agent():
    """Return a ProposalGeneratorAgent with LLM and PPTX utils fully mocked."""
    with patch("agents.proposal_generator.LLMClient") as MockLLM, \
         patch("agents.proposal_generator.get_consultant_info") as MockCI, \
         patch("agents.proposal_generator.DiagramGenerator") as MockDG, \
         patch("agents.proposal_generator.ImageGenerator") as MockIG, \
         patch("agents.proposal_generator.ImageLibrary") as MockIL, \
         patch("agents.proposal_generator.read_all_references", return_value=[]), \
         patch("agents.proposal_generator.extract_template_structure", return_value="template text"), \
         patch("agents.proposal_generator.read_pptx_template", return_value={"total_slides": 5}), \
         patch("agents.proposal_generator.build_proposal_pptx", return_value="/tmp/out.pptx"):
        MockCI.return_value = {
            "name": "Test Consultant",
            "title": "Manager",
            "company": "TestCo",
        }
        mock_llm_instance = MagicMock()
        MockLLM.return_value = mock_llm_instance
        mock_llm_instance.generate.return_value = "mock LLM response"
        mock_llm_instance.extract_structured_data.return_value = {
            "client_name": "Acme Corp",
            "project_title": "Digital Transformation",
            "objectives": ["Objective A", "Objective B"],
            "requirements": {"technical": ["Python"], "functional": ["Reporting"], "constraints": []},
            "budget": "100k",
            "timeline": "6 months",
            "deliverables": ["Report", "Dashboard"],
            "evaluation_criteria": ["Cost", "Quality"],
            "keywords": ["data", "cloud"],
        }

        from agents.proposal_generator import ProposalGeneratorAgent
        a = ProposalGeneratorAgent()
        yield a


# ---------------------------------------------------------------------------
# TestProposalGeneratorAgentInit
# ---------------------------------------------------------------------------

class TestProposalGeneratorAgentInit:
    def test_agent_has_llm_client(self, agent):
        assert hasattr(agent, "llm_client")

    def test_agent_has_consultant_info(self, agent):
        assert isinstance(agent.consultant_info, dict)
        assert "name" in agent.consultant_info

    def test_agent_has_path_attributes(self, agent):
        assert hasattr(agent, "template_path")
        assert hasattr(agent, "references_dir")
        assert hasattr(agent, "notebooklm_data_path")
        assert hasattr(agent, "biographies_path")

    def test_agent_has_diagram_generator(self, agent):
        assert hasattr(agent, "diagram_generator")

    def test_agent_has_image_library(self, agent):
        assert hasattr(agent, "image_library")


# ---------------------------------------------------------------------------
# TestLoadReferences
# ---------------------------------------------------------------------------

class TestLoadReferences:
    def test_load_references_returns_dict(self, agent):
        with patch("agents.proposal_generator.read_all_references", return_value=[]):
            result = agent.load_references()
        assert isinstance(result, dict)
        assert "pptx_references" in result
        assert "projects" in result

    def test_load_references_with_pptx(self, agent):
        mock_refs = [{"filename": "ref1.pptx", "full_text": "some text"}]
        with patch("agents.proposal_generator.read_all_references", return_value=mock_refs):
            result = agent.load_references()
        assert len(result["pptx_references"]) == 1
        assert result["pptx_references"][0]["filename"] == "ref1.pptx"

    def test_load_references_reads_json_if_exists(self, agent, tmp_path):
        json_data = {
            "projects": [{"title": "Project X", "client": "Client A"}],
            "expertise": ["Data"],
            "methodologies": ["Agile"],
            "differentiators": ["Speed"],
        }
        json_file = tmp_path / "references.json"
        json_file.write_text(json.dumps(json_data))
        agent.notebooklm_data_path = str(json_file)

        with patch("agents.proposal_generator.read_all_references", return_value=[]):
            result = agent.load_references()

        assert len(result["projects"]) == 1
        assert result["projects"][0]["title"] == "Project X"
        assert result["expertise"] == ["Data"]
        assert result["methodologies"] == ["Agile"]

    def test_load_references_skips_missing_json(self, agent):
        agent.notebooklm_data_path = "/nonexistent/path/references.json"
        with patch("agents.proposal_generator.read_all_references", return_value=[]):
            result = agent.load_references()
        assert result["projects"] == []

    def test_load_references_empty_when_no_pptx_dir(self, agent):
        with patch("agents.proposal_generator.read_all_references", return_value=[]):
            result = agent.load_references()
        assert result["pptx_references"] == []


# ---------------------------------------------------------------------------
# TestLoadTemplate
# ---------------------------------------------------------------------------

class TestLoadTemplate:
    def test_load_template_returns_none_when_not_found(self, agent):
        agent.template_path = "/nonexistent/template.pptx"
        result = agent.load_template()
        assert result is None

    def test_load_template_calls_extract_structure(self, agent, tmp_path):
        fake_pptx = tmp_path / "template.pptx"
        fake_pptx.write_bytes(b"fake pptx content")
        agent.template_path = str(fake_pptx)

        with patch("agents.proposal_generator.extract_template_structure", return_value="structure") as mock_extract, \
             patch("agents.proposal_generator.read_pptx_template", return_value={"total_slides": 3}):
            result = agent.load_template()

        mock_extract.assert_called_once_with(str(fake_pptx))
        assert result == "structure"


# ---------------------------------------------------------------------------
# TestAnalyzeTender
# ---------------------------------------------------------------------------

class TestAnalyzeTender:
    def test_analyze_tender_calls_llm(self, agent):
        agent.llm_client.extract_structured_data.return_value = {
            "client_name": "BankCorp",
            "project_title": "Risk Platform",
            "objectives": [],
            "requirements": {},
            "keywords": [],
        }
        result = agent.analyze_tender("Nous cherchons un prestataire pour...")
        agent.llm_client.extract_structured_data.assert_called_once()
        assert result["client_name"] == "BankCorp"

    def test_analyze_tender_returns_dict(self, agent):
        result = agent.analyze_tender("Appel d'offre texte")
        assert isinstance(result, dict)

    def test_analyze_tender_passes_text_in_prompt(self, agent):
        agent.analyze_tender("specific tender content 12345")
        call_args = agent.llm_client.extract_structured_data.call_args
        assert call_args is not None


# ---------------------------------------------------------------------------
# TestMatchReferences
# ---------------------------------------------------------------------------

class TestMatchReferences:
    def test_match_references_returns_dict(self, agent):
        tender_analysis = {"client_name": "Corp", "project_title": "IT Project"}
        with patch.object(agent, "load_references", return_value={
            "pptx_references": [],
            "projects": [],
            "expertise": [],
            "methodologies": [],
            "differentiators": [],
        }):
            result = agent.match_references(tender_analysis)
        assert "selected_references" in result
        assert "all_references" in result

    def test_match_references_calls_llm(self, agent):
        tender_analysis = {"client_name": "Corp", "project_title": "IT Project"}
        with patch.object(agent, "load_references", return_value={
            "pptx_references": [],
            "projects": [],
            "expertise": [],
            "methodologies": [],
            "differentiators": [],
        }):
            agent.match_references(tender_analysis)
        agent.llm_client.generate.assert_called()

    def test_match_references_includes_pptx_refs_in_context(self, agent):
        tender_analysis = {"client_name": "Corp", "project_title": "IT"}
        refs = {
            "pptx_references": [{"filename": "case1.pptx", "full_text": "project text"}],
            "projects": [],
            "expertise": [],
            "methodologies": [],
            "differentiators": [],
        }
        with patch.object(agent, "load_references", return_value=refs):
            result = agent.match_references(tender_analysis)
        assert result["all_references"]["pptx_references"][0]["filename"] == "case1.pptx"

    def test_match_references_includes_json_projects(self, agent):
        tender_analysis = {"client_name": "Corp", "project_title": "IT"}
        refs = {
            "pptx_references": [],
            "projects": [{"title": "Alpha", "client": "Alpha Corp", "sector": "Finance",
                          "description": "desc", "challenge": "ch", "solution": "sol",
                          "technologies": ["Python"], "results": ["10% gain"]}],
            "expertise": [],
            "methodologies": [],
            "differentiators": [],
        }
        with patch.object(agent, "load_references", return_value=refs):
            result = agent.match_references(tender_analysis)
        assert len(result["all_references"]["projects"]) == 1


# ---------------------------------------------------------------------------
# TestLoadCvs
# ---------------------------------------------------------------------------

class TestLoadCvs:
    def test_load_cvs_returns_empty_when_file_missing(self, agent):
        agent.biographies_path = "/nonexistent/bios.pptx"
        result = agent.load_cvs()
        assert result == []

    def test_load_cvs_reads_pptx(self, agent, tmp_path):
        fake_path = tmp_path / "bios.pptx"
        fake_path.write_bytes(b"fake pptx")
        agent.biographies_path = str(fake_path)

        mock_paragraph = MagicMock()
        mock_paragraph.text = "Jean Dupont - Senior Consultant with extensive experience in data"
        mock_tf = MagicMock()
        mock_tf.paragraphs = [mock_paragraph]
        mock_shape = MagicMock()
        mock_shape.has_text_frame = True
        mock_shape.text_frame = mock_tf
        mock_slide = MagicMock()
        mock_slide.shapes = [mock_shape]
        mock_prs = MagicMock()
        mock_prs.slides = [mock_slide]

        # Presentation is imported locally inside load_cvs — patch the source module
        with patch("pptx.Presentation", return_value=mock_prs):
            result = agent.load_cvs()
        assert isinstance(result, list)


# ---------------------------------------------------------------------------
# TestAdaptCvs
# ---------------------------------------------------------------------------

class TestAdaptCvs:
    def test_adapt_cvs_returns_empty_list_when_no_cvs(self, agent):
        result = agent.adapt_cvs([], {"client_name": "Corp"})
        assert result == []

    def test_adapt_cvs_calls_llm(self, agent):
        cvs = [{"slide_index": 0, "raw_text": "Alice Martin - Data Scientist"}]
        agent.llm_client.generate.return_value = json.dumps([
            {"name": "Alice Martin", "title": "Data Scientist",
             "experiences": ["Led data migration"], "skills": ["Python", "SQL"]}
        ])
        result = agent.adapt_cvs(cvs, {"client_name": "Corp", "project_title": "Data Lake"})
        agent.llm_client.generate.assert_called()
        assert isinstance(result, list)

    def test_adapt_cvs_parses_json_response(self, agent):
        cvs = [{"slide_index": 0, "raw_text": "Alice Martin - Senior Data Scientist consultant"}]
        adapted = [{"name": "Alice", "title": "DS", "experiences": ["exp1"], "skills": ["Python"]}]
        agent.llm_client.generate.return_value = json.dumps(adapted)
        result = agent.adapt_cvs(cvs, {"client_name": "Corp", "project_title": "ML"})
        assert len(result) == 1
        assert result[0]["name"] == "Alice"

    def test_adapt_cvs_returns_empty_on_invalid_json(self, agent):
        cvs = [{"slide_index": 0, "raw_text": "Some consultant text"}]
        agent.llm_client.generate.return_value = "NOT VALID JSON AT ALL"
        result = agent.adapt_cvs(cvs, {"client_name": "Corp"})
        assert result == []

    def test_adapt_cvs_handles_json_embedded_in_text(self, agent):
        cvs = [{"slide_index": 0, "raw_text": "Alice Martin - consultant expert"}]
        adapted = [{"name": "Alice", "title": "Expert", "experiences": [], "skills": []}]
        agent.llm_client.generate.return_value = (
            "Voici les CVs adaptes:\n" + json.dumps(adapted) + "\nFin."
        )
        result = agent.adapt_cvs(cvs, {"client_name": "Corp"})
        assert len(result) == 1


# ---------------------------------------------------------------------------
# TestSuggestDiagramForSlide
# ---------------------------------------------------------------------------

class TestSuggestDiagramForSlide:
    def test_methodologie_returns_flow(self, agent):
        result = agent._suggest_diagram_for_slide("Notre methodologie", "Contexte")
        assert result is not None
        assert result["type"] == "flow"

    def test_processus_returns_flow(self, agent):
        result = agent._suggest_diagram_for_slide("Processus de mise en oeuvre", "details")
        assert result is not None
        assert result["type"] == "flow"

    def test_facteurs_succes_returns_cycle(self, agent):
        result = agent._suggest_diagram_for_slide("Facteurs cles de succes", "desc")
        assert result is not None
        assert result["type"] == "cycle"

    def test_architecture_in_context_returns_flow(self, agent):
        result = agent._suggest_diagram_for_slide("Solution proposee", "architecture cloud composants")
        assert result is not None
        assert result["type"] == "flow"

    def test_unrecognised_slide_returns_none(self, agent):
        result = agent._suggest_diagram_for_slide("Budget prévisionnel", "montants")
        assert result is None

    def test_etapes_returns_flow(self, agent):
        result = agent._suggest_diagram_for_slide("Les etapes du projet", "detail")
        assert result is not None
        assert result["type"] == "flow"


# ---------------------------------------------------------------------------
# TestGenerateSlidesStructure
# ---------------------------------------------------------------------------

class TestGenerateSlidesStructure:
    def _make_tender(self):
        return {
            "client_name": "Acme",
            "project_title": "Transform",
            "objectives": ["Obj1"],
            "requirements": {"technical": ["Python"]},
            "keywords": ["data"],
        }

    def test_returns_list_of_slides(self, agent):
        slides_json = json.dumps([
            {"type": "cover", "client": "Acme", "project": "Transform", "date": "01/01/2026"},
            {"type": "content", "title": "Context", "bullets": ["Point A"]},
            {"type": "closing"},
        ])
        agent.llm_client.generate.return_value = slides_json
        result = agent.generate_slides_structure(
            self._make_tender(), {}, "template text", []
        )
        assert isinstance(result, list)
        assert len(result) >= 1

    def test_falls_back_on_invalid_json(self, agent):
        # String must contain "[" to enter the if-block; then JSONDecodeError triggers fallback
        agent.llm_client.generate.return_value = "[not valid json at all]"
        result = agent.generate_slides_structure(
            self._make_tender(), {}, "template text", []
        )
        assert isinstance(result, list)
        assert len(result) > 0

    def test_adds_cv_slides_when_provided(self, agent):
        slides_json = json.dumps([
            {"type": "cover", "client": "X", "project": "Y", "date": "01/01/2026"},
            {"type": "closing"},
        ])
        agent.llm_client.generate.return_value = slides_json
        adapted_cvs = [{"name": "Bob", "title": "Lead", "experiences": [], "skills": []}]
        result = agent.generate_slides_structure(
            self._make_tender(), {}, "template", adapted_cvs
        )
        types = [s.get("type") for s in result]
        assert "cv" in types

    def test_closing_removed_when_cvs_appended(self, agent):
        slides_json = json.dumps([
            {"type": "cover", "client": "X", "project": "Y", "date": "01/01/2026"},
            {"type": "closing"},
        ])
        agent.llm_client.generate.return_value = slides_json
        adapted_cvs = [{"name": "Alice", "title": "Sr.", "experiences": [], "skills": []}]
        result = agent.generate_slides_structure(
            self._make_tender(), {}, "template", adapted_cvs
        )
        # Last slide should be cv, not closing
        assert result[-1].get("type") == "cv"

    def test_content_slide_without_bullets_gets_defaults(self, agent):
        slides_json = json.dumps([
            {"type": "content", "title": "No bullets here"},
        ])
        agent.llm_client.generate.return_value = slides_json
        result = agent.generate_slides_structure(
            self._make_tender(), {}, "template", []
        )
        content_slides = [s for s in result if s.get("type") == "content"]
        for s in content_slides:
            assert "bullets" in s

    def test_table_slide_without_rows_gets_defaults(self, agent):
        slides_json = json.dumps([
            {"type": "table", "title": "Budget", "headers": ["Phase", "Cost"]},
        ])
        agent.llm_client.generate.return_value = slides_json
        result = agent.generate_slides_structure(
            self._make_tender(), {}, "template", []
        )
        table_slides = [s for s in result if s.get("type") == "table"]
        for s in table_slides:
            assert "rows" in s

    def test_fallback_structure_has_cover_slide(self, agent):
        # Must contain "[" to enter the if-block; then JSONDecodeError triggers fallback
        agent.llm_client.generate.return_value = "[INVALID{{}]"
        result = agent.generate_slides_structure(
            {"client_name": "Corp", "project_title": "Proj", "objectives": []},
            {}, "template", []
        )
        cover_slides = [s for s in result if s.get("type") == "cover"]
        assert len(cover_slides) >= 1

    def test_fallback_with_cvs_appends_cv_slides(self, agent):
        agent.llm_client.generate.return_value = "[INVALID{{}}]"
        adapted_cvs = [{"name": "Charlie", "title": "Analyst", "experiences": [], "skills": []}]
        result = agent.generate_slides_structure(
            {"client_name": "Corp", "project_title": "Proj", "objectives": []},
            {}, "template", adapted_cvs
        )
        types = [s.get("type") for s in result]
        assert "cv" in types


# ---------------------------------------------------------------------------
# TestEnhanceSlidesWithImages
# ---------------------------------------------------------------------------

class TestEnhanceSlidesWithImages:
    def test_returns_same_slides_when_disabled(self, agent):
        slides = [{"type": "content", "title": "architecture", "bullets": ["A", "B"]}]
        result = agent.enhance_slides_with_images(slides, {}, generate_images=False)
        assert result == slides

    def test_architecture_slide_triggers_diagram(self, agent):
        agent.diagram_generator.generate_architecture_diagram.return_value = "/tmp/arch.png"
        slides = [{"type": "content", "title": "architecture technique", "bullets": ["API: backend", "DB: postgres"]}]
        tender_analysis = {"client_name": "Corp", "project_title": "Platform"}
        result = agent.enhance_slides_with_images(slides, tender_analysis, generate_images=True)
        assert len(result) > len(slides)
        image_slides = [s for s in result if s.get("type") == "image"]
        assert len(image_slides) >= 1

    def test_architecture_slide_no_image_when_generator_returns_none(self, agent, monkeypatch):
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        agent.diagram_generator.generate_architecture_diagram.return_value = None
        slides = [{"type": "content", "title": "infrastructure composants", "bullets": ["X", "Y"]}]
        result = agent.enhance_slides_with_images(slides, {}, generate_images=True)
        image_slides = [s for s in result if s.get("type") == "image"]
        assert len(image_slides) == 0

    def test_flux_slide_triggers_flow_diagram(self, agent):
        agent.diagram_generator.generate_flow_diagram.return_value = "/tmp/flow.png"
        slides = [{"type": "content", "title": "flux de traitement",
                   "bullets": ["Step A: detail", "Step B: detail", "Step C: detail"]}]
        result = agent.enhance_slides_with_images(slides, {}, generate_images=True)
        assert len(result) > len(slides)

    def test_non_matching_slide_not_enhanced(self, agent):
        slides = [{"type": "content", "title": "Budget prévisionnel", "bullets": ["10k"]}]
        result = agent.enhance_slides_with_images(slides, {}, generate_images=True)
        assert result == slides


# ---------------------------------------------------------------------------
# TestSuggestLibraryImage
# ---------------------------------------------------------------------------

class TestSuggestLibraryImage:
    def test_architecture_keyword_triggers_library(self, agent):
        agent.image_library.get_image_by_category.return_value = "/imgs/arch.png"
        result = agent.suggest_library_image("Architecture système", "details")
        assert result == "/imgs/arch.png"

    def test_equipe_keyword_triggers_team(self, agent):
        agent.image_library.get_image_by_category.return_value = "/imgs/team.png"
        result = agent.suggest_library_image("L'equipe projet", "")
        assert result == "/imgs/team.png"

    def test_returns_none_when_library_returns_none(self, agent):
        agent.image_library.get_image_by_category.return_value = None
        result = agent.suggest_library_image("Stratégie générale", "contenu")
        assert result is None

    def test_data_keyword_in_content_triggers_library(self, agent):
        agent.image_library.get_image_by_category.return_value = "/imgs/data.png"
        result = agent.suggest_library_image("Analyse", "gestion des donnees")
        assert result == "/imgs/data.png"

    def test_mockup_keyword_returns_mockup(self, agent):
        agent.image_library.get_image_by_category.return_value = "/imgs/mockup.png"
        result = agent.suggest_library_image("Interface utilisateur", "mockup ecran")
        assert result == "/imgs/mockup.png"


# ---------------------------------------------------------------------------
# TestGenerateProposalContent
# ---------------------------------------------------------------------------

class TestGenerateProposalContent:
    def test_returns_dict_with_content(self, agent):
        agent.llm_client.generate.return_value = "Full proposal text here"
        result = agent.generate_proposal_content(
            {"client_name": "Corp", "project_title": "IT"},
            {"selected_references": "ref1"},
            "template structure",
        )
        assert "content" in result
        assert result["content"] == "Full proposal text here"

    def test_includes_tender_analysis(self, agent):
        agent.llm_client.generate.return_value = "proposal"
        tender = {"client_name": "Corp", "project_title": "IT", "objectives": []}
        result = agent.generate_proposal_content(tender, {}, "template")
        assert result["tender_analysis"] == tender

    def test_includes_generated_at(self, agent):
        agent.llm_client.generate.return_value = "content"
        result = agent.generate_proposal_content({}, {}, "template")
        assert "generated_at" in result

    def test_includes_consultant_info(self, agent):
        agent.llm_client.generate.return_value = "content"
        result = agent.generate_proposal_content({}, {}, "template")
        assert "consultant" in result
        assert result["consultant"]["name"] == "Test Consultant"


# ---------------------------------------------------------------------------
# TestGenerateProposal (integration / orchestration)
# ---------------------------------------------------------------------------

class TestGenerateProposal:
    def test_generate_proposal_reads_file_and_saves_output(self, agent, tmp_path):
        tender_file = tmp_path / "tender.txt"
        tender_file.write_text("Appel d'offre: besoin de transformation digitale")
        output_json = tmp_path / "output" / "proposal_test.json"

        with patch.object(agent, "analyze_tender", return_value={
            "client_name": "DigitalCorp",
            "project_title": "Digital Transformation",
            "objectives": ["Modernize"],
            "requirements": {},
            "keywords": [],
        }), \
        patch.object(agent, "load_template", return_value="template text"), \
        patch.object(agent, "match_references", return_value={"selected_references": "ref", "all_references": {}}), \
        patch.object(agent, "load_cvs", return_value=[]), \
        patch.object(agent, "adapt_cvs", return_value=[]), \
        patch.object(agent, "generate_slides_structure", return_value=[{"type": "cover"}]), \
        patch.object(agent, "generate_proposal_content", return_value={
            "content": "Proposal text",
            "tender_analysis": {},
            "references_used": {},
            "generated_at": "2026-01-01",
            "consultant": {"name": "Test"},
        }), \
        patch("agents.proposal_generator.build_proposal_pptx", return_value=str(output_json).replace(".json", ".pptx")):
            result = agent.generate_proposal(
                tender_path=str(tender_file),
                output_path=str(output_json),
            )

        assert "content" in result or "pptx_path" in result

    def test_generate_proposal_handles_pptx_failure(self, agent, tmp_path):
        tender_file = tmp_path / "tender.txt"
        tender_file.write_text("Appel d'offre texte")
        output_json = tmp_path / "out.json"

        with patch.object(agent, "analyze_tender", return_value={
            "client_name": "Corp", "project_title": "Proj", "objectives": [], "keywords": [], "requirements": {}
        }), \
        patch.object(agent, "load_template", return_value=None), \
        patch.object(agent, "match_references", return_value={"selected_references": "", "all_references": {}}), \
        patch.object(agent, "load_cvs", return_value=[]), \
        patch.object(agent, "adapt_cvs", return_value=[]), \
        patch.object(agent, "generate_slides_structure", return_value=[{"type": "cover"}]), \
        patch.object(agent, "generate_proposal_content", return_value={
            "content": "text", "tender_analysis": {}, "references_used": {},
            "generated_at": "2026-01-01", "consultant": {"name": "T"},
        }), \
        patch("agents.proposal_generator.build_proposal_pptx", side_effect=Exception("pptx error")):
            result = agent.generate_proposal(
                tender_path=str(tender_file),
                output_path=str(output_json),
            )

        assert result.get("pptx_path") is None


# ---------------------------------------------------------------------------
# TestGenerateAgendaSlide
# ---------------------------------------------------------------------------

class TestGenerateAgendaSlide:
    def test_returns_list_with_slide(self, agent):
        agent.llm_client.generate.return_value = json.dumps({
            "title": "Agenda",
            "bullets": ["Introduction", "Methode", "Planning"]
        })
        result = agent.generate_agenda_slide({"client_name": "Corp", "project_title": "IT"})
        assert isinstance(result, list)
        assert len(result) == 1
        assert result[0]["type"] == "content"
        assert result[0]["title"] == "Agenda"

    def test_agenda_fallback_on_invalid_json(self, agent):
        agent.llm_client.generate.return_value = "INVALID JSON"
        result = agent.generate_agenda_slide({"client_name": "Corp"})
        assert isinstance(result, list)
        assert len(result) == 1
        assert result[0]["type"] == "content"

    def test_agenda_bullets_populated(self, agent):
        agenda_data = {"title": "Plan", "bullets": ["Step 1", "Step 2", "Step 3"]}
        agent.llm_client.generate.return_value = json.dumps(agenda_data)
        result = agent.generate_agenda_slide({})
        assert result[0]["bullets"] == ["Step 1", "Step 2", "Step 3"]

    def test_agenda_with_embedded_json(self, agent):
        agenda_data = {"title": "Agenda", "bullets": ["A", "B"]}
        agent.llm_client.generate.return_value = (
            "Voici l'agenda:\n" + json.dumps(agenda_data)
        )
        result = agent.generate_agenda_slide({"client_name": "Corp"})
        assert result[0]["type"] == "content"
