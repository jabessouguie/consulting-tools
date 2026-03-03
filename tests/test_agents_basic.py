"""
Tests basiques pour tous les agents - augmente la couverture rapidement
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestAgentsBasic:
    """Tests basiques d'initialisation pour tous les agents"""

    def test_formation_generator_init(self):
        """Test init FormationGeneratorAgent"""
        from agents.formation_generator import FormationGeneratorAgent

        agent = FormationGeneratorAgent()
        assert agent is not None
        assert hasattr(agent, "llm")
        assert hasattr(agent, "template")

    def test_meeting_summarizer_init(self):
        """Test init MeetingSummarizerAgent"""
        from agents.meeting_summarizer import MeetingSummarizerAgent

        agent = MeetingSummarizerAgent()
        assert agent is not None
        assert hasattr(agent, "llm")

    def test_article_generator_init(self):
        """Test init ArticleGeneratorAgent"""
        from agents.article_generator import ArticleGeneratorAgent

        agent = ArticleGeneratorAgent()
        assert agent is not None
        assert hasattr(agent, "llm")

    def test_cv_reference_adapter_init(self):
        """Test init CVReferenceAdapterAgent"""
        from agents.cv_reference_adapter import CVReferenceAdapterAgent

        agent = CVReferenceAdapterAgent()
        assert agent is not None
        assert hasattr(agent, "llm")

    def test_doc_to_presentation_init(self):
        """Test init DocToPresentationAgent"""
        from agents.doc_to_presentation import DocToPresentationAgent

        agent = DocToPresentationAgent()
        assert agent is not None
        assert hasattr(agent, "llm")


class TestStripPreamble:
    """Tests pour la fonction _strip_preamble du meeting summarizer"""

    def test_strip_absolument(self):
        from agents.meeting_summarizer import _strip_preamble
        result = _strip_preamble("Absolument. Voici le compte rendu :\n## Titre")
        assert result.startswith("#")

    def test_strip_bien_sur(self):
        from agents.meeting_summarizer import _strip_preamble
        result = _strip_preamble("Bien sûr, voici le résumé:\n## Résumé")
        assert result.startswith("#")

    def test_strip_parfait(self):
        from agents.meeting_summarizer import _strip_preamble
        result = _strip_preamble("Parfait! ## Titre du compte rendu")
        assert "Parfait" not in result

    def test_no_preamble_unchanged(self):
        from agents.meeting_summarizer import _strip_preamble
        text = "# Compte Rendu\n\n**Date** : 01/01/2025"
        assert _strip_preamble(text) == text

    def test_strip_empty_string(self):
        from agents.meeting_summarizer import _strip_preamble
        assert _strip_preamble("") == ""

    def test_strip_voici(self):
        from agents.meeting_summarizer import _strip_preamble
        result = _strip_preamble("Voici l'analyse :\n## Contenu")
        assert result.startswith("#")

    def test_strip_multiple_preambles(self):
        from agents.meeting_summarizer import _strip_preamble
        result = _strip_preamble("Absolument. Bien sûr, ## Corps")
        assert "Absolument" not in result
