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
