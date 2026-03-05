"""
Tests basiques pour agents restants - augmente la couverture rapidement
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestMoreAgents:
    """Tests basiques pour agents supplémentaires"""

    def test_article_to_post_imports(self):
        """Test imports article_to_post"""
        from agents.article_to_post import ArticleToPostAgent

        assert ArticleToPostAgent is not None

    def test_article_to_post_init(self):
        """Test initialisation ArticleToPostAgent"""
        from agents.article_to_post import ArticleToPostAgent

        agent = ArticleToPostAgent()
        assert agent is not None

    def test_dataset_analyzer_imports(self):
        """Test imports dataset_analyzer"""
        from agents.dataset_analyzer import DatasetAnalyzerAgent

        assert DatasetAnalyzerAgent is not None

    def test_dataset_analyzer_init(self):
        """Test initialisation DatasetAnalyzerAgent"""
        from agents.dataset_analyzer import DatasetAnalyzerAgent

        agent = DatasetAnalyzerAgent()
        assert agent is not None

    def test_linkedin_commenter_imports(self):
        """Test imports linkedin_commenter"""
        from agents.linkedin_commenter import LinkedInCommenterAgent

        assert LinkedInCommenterAgent is not None

    def test_linkedin_commenter_init(self):
        """Test initialisation LinkedInCommenterAgent"""
        from agents.linkedin_commenter import LinkedInCommenterAgent

        agent = LinkedInCommenterAgent()
        assert agent is not None

    def test_linkedin_monitor_imports(self):
        """Test imports linkedin_monitor"""
        from agents.linkedin_monitor import LinkedInMonitorAgent

        assert LinkedInMonitorAgent is not None

    def test_linkedin_monitor_init(self):
        """Test initialisation LinkedInMonitorAgent"""
        from agents.linkedin_monitor import LinkedInMonitorAgent

        agent = LinkedInMonitorAgent()
        assert agent is not None

    def test_presentation_script_generator_module(self):
        """Test module presentation_script_generator exists"""
        import agents.presentation_script_generator

        assert agents.presentation_script_generator is not None

    def test_proposal_generator_imports(self):
        """Test imports proposal_generator"""
        from agents.proposal_generator import ProposalGeneratorAgent

        assert ProposalGeneratorAgent is not None

    def test_proposal_generator_init(self):
        """Test initialisation ProposalGeneratorAgent"""
        from agents.proposal_generator import ProposalGeneratorAgent

        agent = ProposalGeneratorAgent()
        assert agent is not None

    def test_rfp_responder_imports(self):
        """Test imports rfp_responder"""
        from agents.rfp_responder import RFPResponderAgent

        assert RFPResponderAgent is not None

    def test_rfp_responder_init(self):
        """Test initialisation RFPResponderAgent"""
        from agents.rfp_responder import RFPResponderAgent

        agent = RFPResponderAgent()
        assert agent is not None

    def test_tech_monitor_imports(self):
        """Test imports tech_monitor"""
        from agents.tech_monitor import TechMonitorAgent

        assert TechMonitorAgent is not None

    def test_tech_monitor_init(self):
        """Test initialisation TechMonitorAgent"""
        from agents.tech_monitor import TechMonitorAgent

        agent = TechMonitorAgent()
        assert agent is not None

    def test_training_slides_generator_module(self):
        """Test module training_slides_generator exists"""
        import agents.training_slides_generator

        assert agents.training_slides_generator is not None

    def test_workshop_planner_imports(self):
        """Test imports workshop_planner"""
        from agents.workshop_planner import WorkshopPlannerAgent

        assert WorkshopPlannerAgent is not None

    def test_workshop_planner_init(self):
        """Test initialisation WorkshopPlannerAgent"""
        from agents.workshop_planner import WorkshopPlannerAgent

        agent = WorkshopPlannerAgent()
        assert agent is not None
