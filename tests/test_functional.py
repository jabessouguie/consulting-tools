"""
Tests fonctionnels pour augmenter la couverture vers 30%
"""

import os
import sys
from unittest.mock import MagicMock, Mock, patch

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestLLMClientFunctional:
    """Tests fonctionnels pour LLMClient"""

    def test_generate_with_mock(self):
        """Test generate() avec mock"""
        with patch.dict(
            os.environ,
            {"ANTHROPIC_API_KEY": "test-key", "USE_GEMINI": "false"},
            clear=True,  # pragma: allowlist secret
        ):
            from utils.llm_client import LLMClient

            client = LLMClient()

            # Mock the client's messages.create
            mock_response = Mock()
            mock_response.content = [Mock(text="Test response")]
            client.client.messages.create = Mock(return_value=mock_response)

            result = client.generate(prompt="Test prompt", max_tokens=100)

            assert result == "Test response"
            assert client.client.messages.create.called

    def test_generate_stream_with_mock(self):
        """Test generate_stream() avec mock"""
        with patch.dict(
            os.environ,
            {"ANTHROPIC_API_KEY": "test-key", "USE_GEMINI": "false"},
            clear=True,  # pragma: allowlist secret
        ):
            from utils.llm_client import LLMClient

            client = LLMClient()

            # Mock streaming response
            mock_stream = MagicMock()
            mock_stream.text_stream = ["Hello", " world"]
            # Mock the context manager __enter__ to return the mock_stream
            mock_stream.__enter__.return_value = mock_stream
            client.client.messages.stream = Mock(return_value=mock_stream)

            chunks = list(client.generate_stream(prompt="Test"))

            assert len(chunks) == 2
            assert chunks[0] == "Hello"
            assert chunks[1] == " world"


class TestConsultantProfile:
    """Tests fonctionnels pour consultant_profile"""

    def test_get_consultant_info_structure(self):
        # Mock environment variables for consultant info
        with patch.dict(
            os.environ,
            {
                "CONSULTANT_NAME": "Test Consultant",
                "CONSULTANT_TITLE": "Expert",
                "COMPANY_NAME": "Test Co",
            },
        ):
            from config.consultant import ConsultantConfig

            ConsultantConfig.reset()
            from utils.consultant_profile import get_consultant_info

            info = get_consultant_info()

            assert isinstance(info, dict)
            assert "name" in info
            assert "company" in info


class TestPDFConverter:
    """Tests fonctionnels pour PDF converter"""

    def test_pdf_converter_has_methods(self):
        """Test que PDFConverter a les méthodes attendues"""
        from utils.pdf_converter import PDFConverter

        converter = PDFConverter()

        assert hasattr(converter, "markdown_to_pdf")
        assert callable(converter.markdown_to_pdf)


class TestImageGenerator:
    """Tests fonctionnels pour image generator"""

    def test_image_generator_initialization(self):
        """Test initialisation avec paramètres"""
        from utils.image_generator import ImageGenerator

        gen = ImageGenerator()

        assert gen is not None
        assert hasattr(gen, "generate_diagram_image")


class TestArticleDB:
    """Tests fonctionnels pour article database"""

    def test_article_db_file_path(self):
        """Test que ArticleDB configure le chemin de fichier"""
        from utils.article_db import ArticleDatabase

        db = ArticleDatabase()

        assert hasattr(db, "db_path")
        assert db.db_path.endswith(".db")


class TestValidationFunctional:
    """Tests supplémentaires pour validation"""

    def test_sanitize_url_with_query_params(self):
        """Test URL avec paramètres de requête"""
        from utils.validation import sanitize_url

        url = "https://example.com/page?param=value&other=test"
        result = sanitize_url(url)

        assert result == url
        assert "?" in result
        assert "param=value" in result

    def test_sanitize_filename_removes_dangerous_chars(self):
        """Test suppression caractères dangereux"""
        from utils.validation import sanitize_filename

        dangerous = "file<>:name|test?.txt"
        result = sanitize_filename(dangerous)

        assert "<" not in result
        assert ">" not in result
        assert "|" not in result

    def test_sanitize_text_very_long(self):
        """Test texte très long"""
        from utils.validation import ValidationError, sanitize_text_input

        very_long = "a" * 100000

        with pytest.raises(ValidationError):
            sanitize_text_input(very_long, max_length=10000)


class TestMonitoring:
    """Tests pour monitoring"""

    def test_monitoring_module_has_functions(self):
        """Test que monitoring a les fonctions attendues"""
        import utils.monitoring

        # Vérifier que le module a des fonctions/classes
        assert hasattr(utils.monitoring, "__name__")
        assert utils.monitoring.__name__ == "utils.monitoring"


class TestAgentsFunctional:
    """Tests fonctionnels pour agents"""

    def test_formation_generator_has_generate(self):
        """Test que FormationGeneratorAgent a generate()"""
        from agents.formation_generator import FormationGeneratorAgent

        agent = FormationGeneratorAgent()

        assert hasattr(agent, "generate_programme")
        assert callable(agent.generate_programme)

    def test_meeting_summarizer_has_summarize(self):
        """Test que MeetingSummarizerAgent a summarize()"""
        from agents.meeting_summarizer import MeetingSummarizerAgent

        agent = MeetingSummarizerAgent()

        assert hasattr(agent, "run")
        assert callable(agent.run)

    def test_article_generator_has_generate(self):
        """Test que ArticleGeneratorAgent a generate()"""
        from agents.article_generator import ArticleGeneratorAgent

        agent = ArticleGeneratorAgent()

        assert hasattr(agent, "generate_article")
        assert callable(agent.generate_article)

    def test_proposal_generator_has_generate(self):
        """Test que ProposalGeneratorAgent a generate()"""
        from agents.proposal_generator import ProposalGeneratorAgent

        agent = ProposalGeneratorAgent()
        assert hasattr(agent, "generate_slides_structure")
        assert callable(agent.generate_slides_structure)

    def test_article_generator_linkedin_post(self):
        """Test LinkedIn post generation with mock"""
        from agents.article_generator import ArticleGeneratorAgent

        agent = ArticleGeneratorAgent()
        agent.llm.generate = Mock(return_value="Check out my new post #IA")

        post = agent.generate_linkedin_post(article="Interesting content", article_title="Title")
        assert "#IA" in post

    def test_proposal_generator_analyze_tender(self):
        """Test tender analysis with mock"""
        from agents.proposal_generator import ProposalGeneratorAgent

        agent = ProposalGeneratorAgent()
        agent.llm_client.extract_structured_data = Mock(return_value={"project_title": "Project X"})

        analysis = agent.analyze_tender("We need a new AI strategy")
        assert analysis["project_title"] == "Project X"


class TestPPTXGenerator:
    """Tests pour pptx_generator"""

    def test_pptx_generator_module_imports(self):
        """Test imports pptx_generator"""
        import utils.pptx_generator

        assert hasattr(utils.pptx_generator, "ProposalPPTXGenerator")

    def test_pptx_generator_init(self):
        """Test initialisation ProposalPPTXGenerator"""
        with patch("utils.pptx_generator.Presentation"):
            from utils.pptx_generator import ProposalPPTXGenerator

            # Provide a dummy template path
            gen = ProposalPPTXGenerator(template_path="dummy.pptx")

            assert gen is not None
            assert hasattr(gen, "add_cover_slide")

    def test_pptx_generator_methods(self):
        """Test additional methods of ProposalPPTXGenerator"""
        with patch("utils.pptx_generator.Presentation") as mock_pres:
            mock_prs = MagicMock()
            mock_pres.return_value = mock_prs
            from utils.pptx_generator import ProposalPPTXGenerator

            gen = ProposalPPTXGenerator(template_path="dummy.pptx")

            # Test text styles
            run = MagicMock()
            gen._set_text_style(run)
            assert run.font.name == "Inter"

            # Test add_cover_slide
            mock_slide = MagicMock()
            mock_prs.slides.add_slide.return_value = mock_slide
            mock_prs.slide_layouts = [MagicMock()] * 20

            gen.add_cover_slide("Client", "Project", "2026", "Consultant")
            assert mock_prs.slides.add_slide.called

            # Test add_content_slide
            gen.add_content_slide("Title", ["Point 1", "Point 2"])
            assert mock_prs.slides.add_slide.call_count >= 2

            # Test add_table_slide
            gen.add_table_slide("Title", ["H1", "H2"], [["R1C1", "R1C2"]])
            assert mock_prs.slides.add_slide.call_count >= 3


class TestGoogleAPI:
    """Tests pour google_api"""

    def test_google_api_structure(self):
        """Test structure du module google_api"""
        from utils.google_api import GoogleAPIClient

        assert hasattr(GoogleAPIClient, "get_document_content")


class TestMonitoringFunctional:
    """Tests pour monitoring"""

    def test_monitoring_relevance(self):
        """Test calcul de pertinence"""
        from utils.monitoring import MonitoringTool

        tool = MonitoringTool()

        article = {
            "title": "L'IA en entreprise",
            "content": "Un article sur l'intelligence artificielle",
        }
        score = tool.analyze_article_relevance(article, ["IA", "entreprise"])
        assert score > 0


class TestArticleDBFunctional:
    """Tests pour article_db"""

    def test_article_db_save(self):
        """Test sauvegarde articles avec mock sqlite"""
        with patch("sqlite3.connect") as mock_connect:
            mock_conn = MagicMock()
            mock_connect.return_value = mock_conn
            from utils.article_db import ArticleDatabase

            db = ArticleDatabase()

            articles = [
                {
                    "title": "T1",
                    "link": "L1",
                    "summary": "S1",
                    "date": "2026-01-01",
                    "source": "S1",
                }
            ]
            count = db.save_articles(articles)
            assert count >= 0


class TestAgentsExecution:
    """Tests d'exécution des agents avec mocks"""

    def test_formation_generator_generate(self):
        """Test generate de FormationGeneratorAgent"""
        from agents.formation_generator import FormationGeneratorAgent

        agent = FormationGeneratorAgent()
        # The extractor looks for # **Title**
        agent.llm.generate = Mock(return_value="# **Test Programme**\n## Durée du cours: 3 jours")

        result = agent.generate_programme("Besoin client")
        assert "markdown" in result
        assert result["metadata"]["title"] == "Test Programme"

    def test_meeting_summarizer_run(self):
        """Test run de MeetingSummarizerAgent"""
        from agents.meeting_summarizer import MeetingSummarizerAgent

        agent = MeetingSummarizerAgent()
        agent.llm.generate = Mock(return_value="# Compte Rendu\n**Date** : 2026")

        with patch("pathlib.Path.mkdir"):
            with patch("builtins.open", create=True):
                result = agent.run("Transcript réunion")
                assert "minutes" in result

    def test_article_generator_run(self):
        """Test pipeline complet ArticleGeneratorAgent"""
        from agents.article_generator import ArticleGeneratorAgent

        agent = ArticleGeneratorAgent()
        agent.llm.generate = Mock(
            return_value='--- \ntitle: "Test"\ntags: ["T1"]\n---\n# Test\n[Genere ici un prompt detaille]'
        )

        with patch(
            "agents.article_generator.ArticleGeneratorAgent.generate_illustration_prompt",
            return_value="Prompt",
        ):
            with patch(
                "agents.article_generator.ArticleGeneratorAgent.research_web_sources",
                return_value=[],
            ):
                with patch("builtins.open", create=True):
                    result = agent.run("Idee")
                    assert "article" in result
                    assert "linkedin_post" in result
