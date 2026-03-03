"""
Tests unitaires pour SkillsMarketAgent
"""

import json
import os
import sys
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


MOCK_CONSULTANT_JSON = json.dumps(
    {
        "name": "Alice Durand",
        "title": "Consultante Senior Data",
        "bio": "Experte en data science et IA appliquee",
        "skills_technical": [
            {"name": "Python", "level": "expert"},
            {"name": "SQL", "level": "senior"},
        ],
        "skills_sector": [
            {"name": "Banque", "level": "senior"},
        ],
        "missions": [
            {
                "client_name": "SocGen",
                "context_and_challenges": "Migration data lake",
                "deliverables": "Architecture cible",
                "tasks": "Cadrage, POC",
            }
        ],
        "interests": ["Machine Learning", "Yoga"],
        "strengths": ["Expertise technique", "Autonomie"],
        "improvement_areas": ["Communication orale"],
        "management_suggestions": "Proposer des formations en prise de parole",
    }
)

MOCK_SKIP_JSON = json.dumps({"skip": True})

MOCK_ANALYSIS_JSON = json.dumps(
    {
        "strengths": ["Polyvalence", "Rigueur", "Leadership"],
        "improvement_areas": ["Gestion du stress", "Delegation"],
        "management_suggestions": "Coaching individuel recommande",
    }
)

MOCK_SEARCH_JSON = json.dumps(
    {
        "results": [
            {
                "id": 1,
                "score": 90,
                "explanation": "Expertise Python et Data",
            },
            {
                "id": 3,
                "score": 60,
                "explanation": "Experience en data analytics",
            },
        ]
    }
)


MOCK_TEXT_IMPORT_JSON = json.dumps(
    {
        "consultants": [
            {
                "name": "Pierre Leroy",
                "title": "Consultant Junior",
                "bio": "Jeune consultant motive",
                "skills_technical": [{"name": "Java", "level": "confirmed"}],
                "skills_sector": [{"name": "Retail", "level": "junior"}],
                "missions": [],
                "interests": ["Cloud"],
                "strengths": ["Motivation"],
                "improvement_areas": ["Experience"],
                "management_suggestions": "Mentoring recommande",
            }
        ]
    }
)

MOCK_SINGLE_CONSULTANT_JSON = json.dumps(
    {
        "name": "Sophie Bernard",
        "title": "Manager",
        "bio": "Experte en transformation",
        "skills_technical": [{"name": "SAFe", "level": "expert"}],
        "skills_sector": [{"name": "Telecom", "level": "senior"}],
        "missions": [],
        "interests": [],
        "strengths": ["Leadership"],
        "improvement_areas": [],
        "management_suggestions": "",
    }
)


@pytest.fixture
def agent():
    """Agent avec LLM mocke"""
    with patch("agents.skills_market.LLMClient") as mock_llm_cls:
        mock_llm = MagicMock()
        mock_llm_cls.return_value = mock_llm
        from agents.skills_market import SkillsMarketAgent

        a = SkillsMarketAgent()
        a.llm = mock_llm
        yield a


class TestParseConsultantSlide:
    """Tests de parsing de slides PPTX"""

    @pytest.mark.unit
    def test_parse_valid_slide(self, agent):
        """Parse un slide valide en profil structure"""
        agent.llm.generate.return_value = MOCK_CONSULTANT_JSON

        result = agent.parse_consultant_slide(
            "Alice Durand\nConsultante Senior Data\n"
            "Python, SQL\nBanque\nSocGen - Migration data lake"
        )

        assert result is not None
        assert result["name"] == "Alice Durand"
        assert len(result["skills_technical"]) == 2
        assert len(result["missions"]) == 1

    @pytest.mark.unit
    def test_parse_empty_slide(self, agent):
        """Slide vide retourne None"""
        result = agent.parse_consultant_slide("")
        assert result is None

    @pytest.mark.unit
    def test_parse_short_slide(self, agent):
        """Slide trop court retourne None"""
        result = agent.parse_consultant_slide("Title only")
        assert result is None

    @pytest.mark.unit
    def test_parse_skip_non_cv(self, agent):
        """Slide non-CV retourne skip=True"""
        agent.llm.generate.return_value = MOCK_SKIP_JSON

        result = agent.parse_consultant_slide(
            "This is a cover slide with Wenvision logo " "and company presentation text"
        )

        assert result is not None
        assert result.get("skip") is True

    @pytest.mark.unit
    def test_parse_json_in_code_block(self, agent):
        """Parse JSON dans un bloc de code markdown"""
        agent.llm.generate.return_value = f"```json\n{MOCK_CONSULTANT_JSON}\n```"

        result = agent.parse_consultant_slide(
            "Alice Durand\nConsultante Senior Data\n" "Python, SQL, expertise bancaire"
        )

        assert result is not None
        assert result["name"] == "Alice Durand"

    @pytest.mark.unit
    def test_parse_llm_error(self, agent):
        """Erreur LLM retourne None"""
        agent.llm.generate.side_effect = Exception("LLM error")

        result = agent.parse_consultant_slide("Texte de slide assez long pour etre traite")

        assert result is None

    @pytest.mark.unit
    def test_parse_invalid_json(self, agent):
        """JSON invalide retourne None"""
        agent.llm.generate.return_value = "Not a JSON response"

        result = agent.parse_consultant_slide("Texte de slide assez long pour etre traite")

        assert result is None


class TestImportFromPptx:
    """Tests d'import depuis PPTX"""

    @pytest.mark.unit
    @patch("agents.skills_market.read_pptx_template")
    def test_import_basic(self, mock_read, agent):
        """Import basique depuis PPTX"""
        mock_read.return_value = {
            "title": "test.pptx",
            "total_slides": 2,
            "slides": [
                {
                    "slide_number": 1,
                    "layout": "CV",
                    "content": [
                        "Alice Durand",
                        "Consultante Senior Data & IA chez Wenvision",
                    ],
                },
                {
                    "slide_number": 2,
                    "layout": "CV",
                    "content": [
                        "Bob Martin",
                        "Manager Consulting Data & Strategy chez Wenvision",
                    ],
                },
            ],
        }

        agent.llm.generate.return_value = MOCK_CONSULTANT_JSON

        result = agent.import_from_pptx("test.pptx")

        assert len(result) == 2
        assert all("raw_pptx_text" in c for c in result)

    @pytest.mark.unit
    @patch("agents.skills_market.read_pptx_template")
    def test_import_skips_non_cv(self, mock_read, agent):
        """Import filtre les slides non-CV"""
        mock_read.return_value = {
            "title": "test.pptx",
            "total_slides": 3,
            "slides": [
                {
                    "slide_number": 1,
                    "layout": "Cover",
                    "content": ["Wenvision Presentation"],
                },
                {
                    "slide_number": 2,
                    "layout": "CV",
                    "content": [
                        "Alice Durand",
                        "Consultante Senior Data",
                    ],
                },
                {
                    "slide_number": 3,
                    "layout": "Blank",
                    "content": [],
                },
            ],
        }

        def side_effect(prompt, **kwargs):
            if "Alice" in prompt:
                return MOCK_CONSULTANT_JSON
            return MOCK_SKIP_JSON

        agent.llm.generate.side_effect = side_effect

        result = agent.import_from_pptx("test.pptx")

        # Slide 1 -> skip, Slide 2 -> valid, Slide 3 -> empty
        assert len(result) == 1
        assert result[0]["name"] == "Alice Durand"

    @pytest.mark.unit
    @patch("agents.skills_market.read_pptx_template")
    def test_import_progress_callback(self, mock_read, agent):
        """Import appelle le callback de progression"""
        mock_read.return_value = {
            "title": "test.pptx",
            "total_slides": 1,
            "slides": [
                {
                    "slide_number": 1,
                    "layout": "CV",
                    "content": [
                        "Alice Durand",
                        "Consultante",
                    ],
                },
            ],
        }
        agent.llm.generate.return_value = MOCK_CONSULTANT_JSON

        callback = MagicMock()
        agent.import_from_pptx("test.pptx", progress_callback=callback)

        assert callback.called


class TestAnalyzeStrengths:
    """Tests d'analyse forces/faiblesses"""

    @pytest.mark.unit
    def test_analyze_valid(self, agent):
        """Analyse retourne les forces et faiblesses"""
        agent.llm.generate.return_value = MOCK_ANALYSIS_JSON

        result = agent.analyze_strengths(
            {
                "name": "Jean Dupont",
                "title": "Consultant Senior",
                "bio": "Expert en IA",
                "skills_technical": [{"name": "Python"}],
                "skills_sector": [{"name": "Banque"}],
                "missions": [
                    {
                        "client_name": "BNP",
                        "context_and_challenges": "Migration",
                    }
                ],
            }
        )

        assert len(result["strengths"]) == 3
        assert "Polyvalence" in result["strengths"]
        assert len(result["improvement_areas"]) == 2
        assert "Coaching" in result["management_suggestions"]

    @pytest.mark.unit
    def test_analyze_llm_error_fallback(self, agent):
        """Erreur LLM retourne les donnees existantes"""
        agent.llm.generate.side_effect = Exception("LLM error")

        result = agent.analyze_strengths(
            {
                "name": "Jean",
                "strengths": ["Existant"],
                "improvement_areas": ["Existant aussi"],
                "management_suggestions": "Existante",
            }
        )

        assert result["strengths"] == ["Existant"]
        assert result["improvement_areas"] == ["Existant aussi"]


class TestNaturalLanguageSearch:
    """Tests de recherche en langage naturel"""

    @pytest.mark.unit
    def test_search_returns_ranked(self, agent):
        """Recherche retourne des resultats classes"""
        agent.llm.generate.return_value = MOCK_SEARCH_JSON

        consultants = [
            {
                "id": 1,
                "name": "Alice",
                "title": "Data Scientist",
                "top_skills": [{"name": "Python"}],
            },
            {
                "id": 2,
                "name": "Bob",
                "title": "Manager",
                "top_skills": [{"name": "Agile"}],
            },
            {
                "id": 3,
                "name": "Carol",
                "title": "Analyst",
                "top_skills": [{"name": "SQL"}],
            },
        ]

        results = agent.natural_language_search("consultant expert Python et data", consultants)

        assert len(results) == 2
        assert results[0]["id"] == 1
        assert results[0]["score"] == 90

    @pytest.mark.unit
    def test_search_empty_consultants(self, agent):
        """Recherche avec liste vide retourne vide"""
        results = agent.natural_language_search("query", [])
        assert results == []

    @pytest.mark.unit
    def test_search_llm_error(self, agent):
        """Erreur LLM retourne liste vide"""
        agent.llm.generate.side_effect = Exception("LLM error")

        results = agent.natural_language_search(
            "query",
            [{"id": 1, "name": "Test", "title": "T", "top_skills": []}],
        )
        assert results == []


class TestParseJsonResponse:
    """Tests du parsing JSON"""

    @pytest.mark.unit
    def test_parse_direct_json(self, agent):
        """Parse JSON direct"""
        result = agent._parse_json_response('{"key": "value"}')
        assert result == {"key": "value"}

    @pytest.mark.unit
    def test_parse_code_block(self, agent):
        """Parse JSON dans bloc de code"""
        result = agent._parse_json_response('```json\n{"key": "value"}\n```')
        assert result == {"key": "value"}

    @pytest.mark.unit
    def test_parse_empty(self, agent):
        """String vide retourne None"""
        result = agent._parse_json_response("")
        assert result is None

    @pytest.mark.unit
    def test_parse_none(self, agent):
        """None retourne None"""
        result = agent._parse_json_response(None)
        assert result is None

    @pytest.mark.unit
    def test_parse_invalid(self, agent):
        """Texte non-JSON retourne None"""
        result = agent._parse_json_response("This is not JSON at all")
        assert result is None


class TestImportFromText:
    """Tests d'import depuis texte brut (PDF, HTML)"""

    @pytest.mark.unit
    def test_import_multiple_consultants(self, agent):
        """Import de plusieurs consultants depuis texte"""
        agent.llm.generate.return_value = MOCK_TEXT_IMPORT_JSON

        result = agent.import_from_text(
            "Pierre Leroy - Consultant Junior chez Wenvision "
            "avec experience en Java et retail distribution",
            source_filename="cv_team.pdf",
        )

        assert len(result) == 1
        assert result[0]["name"] == "Pierre Leroy"
        assert "raw_pptx_text" in result[0]

    @pytest.mark.unit
    def test_import_single_consultant_fallback(self, agent):
        """Import d'un seul consultant (fallback sans 'consultants' key)"""
        agent.llm.generate.return_value = MOCK_SINGLE_CONSULTANT_JSON

        result = agent.import_from_text(
            "Sophie Bernard - Manager experte en transformation "
            "digitale avec 10 ans d'experience en telecom",
            source_filename="cv_sophie.html",
        )

        assert len(result) == 1
        assert result[0]["name"] == "Sophie Bernard"

    @pytest.mark.unit
    def test_import_empty_text(self, agent):
        """Texte vide retourne liste vide"""
        result = agent.import_from_text("")
        assert result == []

    @pytest.mark.unit
    def test_import_short_text(self, agent):
        """Texte trop court retourne liste vide"""
        result = agent.import_from_text("Short")
        assert result == []

    @pytest.mark.unit
    def test_import_llm_error(self, agent):
        """Erreur LLM retourne liste vide"""
        agent.llm.generate.side_effect = Exception("LLM error")

        result = agent.import_from_text(
            "Texte suffisamment long pour etre traite par le LLM "
            "contenant des informations de CV consultant",
        )
        assert result == []

    @pytest.mark.unit
    def test_import_progress_callback(self, agent):
        """Import appelle le callback de progression"""
        agent.llm.generate.return_value = MOCK_TEXT_IMPORT_JSON

        callback = MagicMock()
        agent.import_from_text(
            "Pierre Leroy consultant junior avec experience "
            "Java et expertise retail chez Wenvision consulting",
            progress_callback=callback,
        )
        assert callback.called
