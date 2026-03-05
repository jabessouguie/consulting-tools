"""
Tests unitaires pour utils/consultant_profile.py
"""

import json
import os
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.consultant import ConsultantConfig


@pytest.fixture(autouse=True)
def reset_consultant_config():
    """Reset singleton cache before each test."""
    ConsultantConfig.reset()
    yield
    ConsultantConfig.reset()


@pytest.fixture()
def mock_consultant_env(monkeypatch):
    """Patch environment so get_consultant_info() does not raise."""
    monkeypatch.setenv("CONSULTANT_NAME", "Test Consultant")
    monkeypatch.setenv("CONSULTANT_TITLE", "Senior Consultant")
    monkeypatch.setenv("COMPANY_NAME", "TestCo")


@pytest.fixture()
def profile_in_tmp(tmp_path, mock_consultant_env):
    """Return a ConsultantProfile whose base_dir points to tmp_path."""
    from utils.consultant_profile import ConsultantProfile

    (tmp_path / "output").mkdir()
    (tmp_path / "data").mkdir()
    return ConsultantProfile(base_dir=str(tmp_path))


# ---------------------------------------------------------------------------
# ConsultantProfile.__init__
# ---------------------------------------------------------------------------


class TestConsultantProfileInit:
    def test_default_base_dir(self, mock_consultant_env):
        from utils.consultant_profile import ConsultantProfile

        profile = ConsultantProfile()
        assert profile.base_dir == Path(__file__).parent.parent

    def test_custom_base_dir(self, tmp_path, mock_consultant_env):
        from utils.consultant_profile import ConsultantProfile

        profile = ConsultantProfile(base_dir=str(tmp_path))
        assert profile.base_dir == tmp_path
        assert profile.output_dir == tmp_path / "output"
        assert profile.data_dir == tmp_path / "data"


# ---------------------------------------------------------------------------
# load_previous_articles
# ---------------------------------------------------------------------------


class TestLoadPreviousArticles:
    def test_returns_empty_when_no_files(self, profile_in_tmp):
        result = profile_in_tmp.load_previous_articles()
        assert result == []

    def test_loads_article_files(self, profile_in_tmp, tmp_path):
        article = tmp_path / "output" / "article_test.md"
        article.write_text(
            "---\ntitle: Mon Article\ndate: 2024-01-01\n---\n\nContenu de l article."
        )
        result = profile_in_tmp.load_previous_articles()
        assert len(result) == 1
        assert result[0]["path"] == "article_test.md"
        assert "metadata" in result[0]
        assert "excerpt" in result[0]
        assert "full_content" in result[0]

    def test_respects_limit(self, profile_in_tmp, tmp_path):
        output = tmp_path / "output"
        for i in range(8):
            (output / f"article_{i}.md").write_text(f"# Article {i}\n\nContent {i}")
        result = profile_in_tmp.load_previous_articles(limit=3)
        assert len(result) <= 3

    def test_handles_unreadable_file_gracefully(self, profile_in_tmp, tmp_path):
        bad_file = tmp_path / "output" / "article_bad.md"
        bad_file.write_text("ok")
        with patch("builtins.open", side_effect=IOError("Cannot read")):
            result = profile_in_tmp.load_previous_articles()
        assert isinstance(result, list)

    def test_metadata_extracted(self, profile_in_tmp, tmp_path):
        article = tmp_path / "output" / "article_meta.md"
        article.write_text(
            '---\ntitle: "Test Title"\nauthor: "Auteur"\n---\n\nParagraph.'
        )
        result = profile_in_tmp.load_previous_articles()
        assert result[0]["metadata"].get("title") == "Test Title"

    def test_full_content_limited(self, profile_in_tmp, tmp_path):
        big_content = "x" * 5000
        article = tmp_path / "output" / "article_big.md"
        article.write_text(big_content)
        result = profile_in_tmp.load_previous_articles()
        assert len(result[0]["full_content"]) <= 3000


# ---------------------------------------------------------------------------
# load_personality
# ---------------------------------------------------------------------------


class TestLoadPersonality:
    def test_returns_content_if_file_exists(self, profile_in_tmp, tmp_path):
        personality_file = tmp_path / "data" / "personality.md"
        personality_file.write_text("# Ma personnalite\nJe suis pragmatique.")
        result = profile_in_tmp.load_personality()
        assert "pragmatique" in result

    def test_creates_default_if_missing(self, profile_in_tmp, tmp_path):
        result = profile_in_tmp.load_personality()
        assert len(result) > 0
        # Default file should now exist
        assert (tmp_path / "data" / "personality.md").exists()

    def test_default_content_is_non_empty(self, profile_in_tmp):
        result = profile_in_tmp.load_personality()
        assert "Vision" in result or "vision" in result.lower() or len(result) > 10


# ---------------------------------------------------------------------------
# load_linkedin_profile
# ---------------------------------------------------------------------------


class TestLoadLinkedinProfile:
    def test_returns_dict_with_expected_keys(self, profile_in_tmp):
        result = profile_in_tmp.load_linkedin_profile()
        for key in ("name", "title", "company", "bio", "experiences", "recent_posts", "persona"):
            assert key in result

    def test_fallback_json_file(self, profile_in_tmp, tmp_path):
        linkedin_data = {"bio": "Expert IA", "experiences": ["CTO at Foo"]}
        json_path = tmp_path / "data" / "linkedin_profile.json"
        json_path.write_text(json.dumps(linkedin_data))
        result = profile_in_tmp.load_linkedin_profile()
        assert result["bio"] == "Expert IA"

    def test_fallback_persona_md(self, profile_in_tmp, tmp_path):
        persona_path = tmp_path / "data" / "linkedin_persona.md"
        persona_path.write_text("# Mon persona\nStyle: direct")
        result = profile_in_tmp.load_linkedin_profile()
        assert "Mon persona" in result["persona"]

    def test_loads_from_linkedin_dir_json(self, profile_in_tmp, tmp_path):
        linkedin_dir = tmp_path / "data" / "linkedin_profile"
        linkedin_dir.mkdir()
        profile_data = {"bio": "Dir bio", "name": "Dir Name"}
        (linkedin_dir / "profile.json").write_text(json.dumps(profile_data))
        result = profile_in_tmp.load_linkedin_profile()
        assert result["bio"] == "Dir bio"

    def test_loads_persona_from_linkedin_dir(self, profile_in_tmp, tmp_path):
        linkedin_dir = tmp_path / "data" / "linkedin_profile"
        linkedin_dir.mkdir()
        (linkedin_dir / "persona.md").write_text("# Persona content")
        result = profile_in_tmp.load_linkedin_profile()
        assert "Persona content" in result["persona"]

    def test_loads_additional_docs_from_linkedin_dir_md(self, profile_in_tmp, tmp_path):
        linkedin_dir = tmp_path / "data" / "linkedin_profile"
        linkedin_dir.mkdir()
        (linkedin_dir / "posts.md").write_text("## Recent posts\nPost 1")
        result = profile_in_tmp.load_linkedin_profile()
        assert len(result["additional_docs"]) >= 1

    def test_loads_additional_docs_json(self, profile_in_tmp, tmp_path):
        linkedin_dir = tmp_path / "data" / "linkedin_profile"
        linkedin_dir.mkdir()
        extra_data = {"stats": 42}
        (linkedin_dir / "stats.json").write_text(json.dumps(extra_data))
        result = profile_in_tmp.load_linkedin_profile()
        assert any(d.get("type") == "json" for d in result["additional_docs"])

    def test_persona_stripped(self, profile_in_tmp, tmp_path):
        persona_path = tmp_path / "data" / "linkedin_persona.md"
        persona_path.write_text("   \n  Content  \n  ")
        result = profile_in_tmp.load_linkedin_profile()
        assert result["persona"] == result["persona"].strip()


# ---------------------------------------------------------------------------
# load_tech_trends
# ---------------------------------------------------------------------------


class TestLoadTechTrends:
    def test_returns_empty_on_import_error(self, profile_in_tmp):
        with patch.dict("sys.modules", {"utils.article_db": None}):
            result = profile_in_tmp.load_tech_trends()
        assert isinstance(result, list)

    def test_returns_formatted_articles(self, profile_in_tmp):
        mock_db = MagicMock()
        mock_db.get_articles.return_value = [
            {"title": "AI Trends", "summary": "Summary here", "source": "TechCrunch", "date": "2024-01-01"},
        ]
        mock_module = MagicMock()
        mock_module.ArticleDatabase.return_value = mock_db
        with patch.dict("sys.modules", {"utils.article_db": mock_module}):
            result = profile_in_tmp.load_tech_trends()
        assert len(result) == 1
        assert result[0]["title"] == "AI Trends"
        assert result[0]["source"] == "TechCrunch"

    def test_summary_truncated_to_200(self, profile_in_tmp):
        long_summary = "x" * 500
        mock_db = MagicMock()
        mock_db.get_articles.return_value = [
            {"title": "T", "summary": long_summary, "source": "S", "date": "2024-01-01"},
        ]
        mock_module = MagicMock()
        mock_module.ArticleDatabase.return_value = mock_db
        with patch.dict("sys.modules", {"utils.article_db": mock_module}):
            result = profile_in_tmp.load_tech_trends()
        assert len(result[0]["summary"]) <= 200

    def test_handles_exception_gracefully(self, profile_in_tmp):
        mock_module = MagicMock()
        mock_module.ArticleDatabase.side_effect = RuntimeError("DB error")
        with patch.dict("sys.modules", {"utils.article_db": mock_module}):
            result = profile_in_tmp.load_tech_trends()
        assert result == []


# ---------------------------------------------------------------------------
# analyze_writing_style
# ---------------------------------------------------------------------------


class TestAnalyzeWritingStyle:
    def test_empty_articles_returns_defaults(self, profile_in_tmp):
        result = profile_in_tmp.analyze_writing_style([])
        assert result == {"keywords": [], "avg_length": 0, "common_phrases": []}

    def test_extracts_keywords(self, profile_in_tmp):
        articles = [{"full_content": "intelligence artificielle gouvernance donnees strategie"}]
        result = profile_in_tmp.analyze_writing_style(articles)
        assert "keywords" in result
        assert isinstance(result["keywords"], list)

    def test_avg_length_computed(self, profile_in_tmp):
        content = "a" * 100
        articles = [{"full_content": content}, {"full_content": content}]
        result = profile_in_tmp.analyze_writing_style(articles)
        assert result["avg_length"] == 100

    def test_num_articles_analyzed(self, profile_in_tmp):
        articles = [
            {"full_content": "premier article contenu important"},
            {"full_content": "deuxieme article different autre"},
        ]
        result = profile_in_tmp.analyze_writing_style(articles)
        assert result["num_articles_analyzed"] == 2

    def test_stop_words_filtered(self, profile_in_tmp):
        articles = [{"full_content": "le la les des avec pour dans sur"}]
        result = profile_in_tmp.analyze_writing_style(articles)
        # Stop words should not appear in keywords
        assert "le" not in result["keywords"]
        assert "la" not in result["keywords"]

    def test_top_keywords_max_15(self, profile_in_tmp):
        # Create article with many unique long words
        words = [f"keyword{i}" for i in range(30)]
        content = " ".join(words * 3)
        articles = [{"full_content": content}]
        result = profile_in_tmp.analyze_writing_style(articles)
        assert len(result["keywords"]) <= 15


# ---------------------------------------------------------------------------
# build_context
# ---------------------------------------------------------------------------


class TestBuildContext:
    def test_returns_expected_keys(self, profile_in_tmp):
        with patch.object(profile_in_tmp, "load_previous_articles", return_value=[]):
            with patch.object(profile_in_tmp, "load_personality", return_value="personality text"):
                with patch.object(profile_in_tmp, "load_linkedin_profile", return_value={"name": "Test", "title": "T", "company": "C", "bio": "", "experiences": [], "recent_posts": [], "persona": "", "additional_docs": []}):
                    with patch.object(profile_in_tmp, "load_tech_trends", return_value=[]):
                        context = profile_in_tmp.build_context()
        for key in ("previous_articles", "personality", "linkedin_profile", "tech_trends", "writing_style"):
            assert key in context

    def test_writing_style_included(self, profile_in_tmp):
        articles = [{"full_content": "intelligence artificielle strategie gouvernance donnees"}]
        with patch.object(profile_in_tmp, "load_previous_articles", return_value=articles):
            with patch.object(profile_in_tmp, "load_personality", return_value=""):
                with patch.object(profile_in_tmp, "load_linkedin_profile", return_value={"name": "T", "title": "T", "company": "C", "bio": "", "experiences": [], "recent_posts": [], "persona": "", "additional_docs": []}):
                    with patch.object(profile_in_tmp, "load_tech_trends", return_value=[]):
                        context = profile_in_tmp.build_context()
        assert "num_articles_analyzed" in context["writing_style"]


# ---------------------------------------------------------------------------
# format_context_for_prompt
# ---------------------------------------------------------------------------


class TestFormatContextForPrompt:
    def _make_context(
        self,
        personality="",
        keywords=None,
        previous_articles=None,
        tech_trends=None,
        linkedin_profile=None,
    ):
        return {
            "personality": personality,
            "writing_style": {"keywords": keywords or [], "avg_length": 500},
            "previous_articles": previous_articles or [],
            "tech_trends": tech_trends or [],
            "linkedin_profile": linkedin_profile or {"bio": "", "persona": "", "title": "", "additional_docs": []},
        }

    def test_empty_context_returns_empty_string(self, profile_in_tmp):
        context = self._make_context()
        result = profile_in_tmp.format_context_for_prompt(context)
        assert isinstance(result, str)

    def test_personality_included(self, profile_in_tmp):
        context = self._make_context(personality="Je suis pragmatique")
        result = profile_in_tmp.format_context_for_prompt(context)
        assert "pragmatique" in result

    def test_keywords_included(self, profile_in_tmp):
        context = self._make_context(keywords=["IA", "gouvernance", "strategie"])
        result = profile_in_tmp.format_context_for_prompt(context)
        assert "IA" in result

    def test_previous_articles_included(self, profile_in_tmp):
        articles = [
            {
                "metadata": {"title": "Mon Article"},
                "excerpt": "Extrait de l article",
            }
        ]
        context = self._make_context(previous_articles=articles)
        result = profile_in_tmp.format_context_for_prompt(context)
        assert "Mon Article" in result

    def test_tech_trends_included(self, profile_in_tmp):
        trends = [{"title": "AI Revolution", "source": "TechCrunch"}]
        context = self._make_context(tech_trends=trends)
        result = profile_in_tmp.format_context_for_prompt(context)
        assert "AI Revolution" in result

    def test_linkedin_bio_included(self, profile_in_tmp):
        linkedin = {"bio": "Expert en IA", "persona": "", "title": "CTO", "additional_docs": []}
        context = self._make_context(linkedin_profile=linkedin)
        result = profile_in_tmp.format_context_for_prompt(context)
        assert "Expert en IA" in result

    def test_linkedin_persona_included(self, profile_in_tmp):
        linkedin = {"bio": "Bio", "persona": "Style direct et impactant", "title": "CTO", "additional_docs": []}
        context = self._make_context(linkedin_profile=linkedin)
        result = profile_in_tmp.format_context_for_prompt(context)
        assert "direct et impactant" in result

    def test_linkedin_additional_docs_markdown(self, profile_in_tmp):
        docs = [{"filename": "posts.md", "type": "markdown", "content": "Contenu posts"}]
        linkedin = {"bio": "Bio", "persona": "Persona", "title": "CTO", "additional_docs": docs}
        context = self._make_context(linkedin_profile=linkedin)
        result = profile_in_tmp.format_context_for_prompt(context)
        assert "posts.md" in result

    def test_linkedin_additional_docs_json(self, profile_in_tmp):
        docs = [{"filename": "stats.json", "type": "json", "content": {"views": 100}}]
        linkedin = {"bio": "Bio", "persona": "Persona", "title": "CTO", "additional_docs": docs}
        context = self._make_context(linkedin_profile=linkedin)
        result = profile_in_tmp.format_context_for_prompt(context)
        assert "stats.json" in result

    def test_only_first_3_articles_shown(self, profile_in_tmp):
        articles = [
            {"metadata": {"title": f"Article {i}"}, "excerpt": "Extrait"}
            for i in range(6)
        ]
        context = self._make_context(previous_articles=articles)
        result = profile_in_tmp.format_context_for_prompt(context)
        # Article 0 title should appear; Article 4 title (4th article, 0-indexed) should not
        assert "Article 0" in result
        assert ": Article 4" not in result

    def test_only_first_8_trends_shown(self, profile_in_tmp):
        trends = [{"title": f"Trend {i}", "source": "Source"} for i in range(12)]
        context = self._make_context(tech_trends=trends)
        result = profile_in_tmp.format_context_for_prompt(context)
        assert "Trend 0" in result
        assert "Trend 9" not in result


# ---------------------------------------------------------------------------
# _extract_yaml_metadata
# ---------------------------------------------------------------------------


class TestExtractYamlMetadata:
    def test_extracts_simple_key_value(self, profile_in_tmp):
        content = "---\ntitle: Mon Titre\nauthor: Moi\n---\nContenu"
        result = profile_in_tmp._extract_yaml_metadata(content)
        assert result["title"] == "Mon Titre"
        assert result["author"] == "Moi"

    def test_returns_empty_dict_without_frontmatter(self, profile_in_tmp):
        result = profile_in_tmp._extract_yaml_metadata("Juste du contenu")
        assert result == {}

    def test_strips_quotes_from_values(self, profile_in_tmp):
        content = '---\ntitle: "Mon Titre Entre Guillemets"\n---\nContenu'
        result = profile_in_tmp._extract_yaml_metadata(content)
        assert result["title"] == "Mon Titre Entre Guillemets"

    def test_handles_tags_list(self, profile_in_tmp):
        content = '---\ntags: ["IA", "Data", "Cloud"]\n---\nContenu'
        result = profile_in_tmp._extract_yaml_metadata(content)
        assert isinstance(result["tags"], list)

    def test_handles_invalid_tags(self, profile_in_tmp):
        content = "---\ntags: not-valid-python\n---\nContenu"
        result = profile_in_tmp._extract_yaml_metadata(content)
        assert result["tags"] == []


# ---------------------------------------------------------------------------
# _extract_excerpt
# ---------------------------------------------------------------------------


class TestExtractExcerpt:
    def test_strips_yaml_frontmatter(self, profile_in_tmp):
        content = "---\ntitle: Test\n---\n\nCeci est le contenu principal."
        result = profile_in_tmp._extract_excerpt(content)
        assert "---" not in result
        assert "Ceci" in result

    def test_strips_image_placeholder(self, profile_in_tmp):
        content = "> **[IMAGE PLACEHOLDER] Description\n\nParagraphe reel."
        result = profile_in_tmp._extract_excerpt(content)
        assert "IMAGE PLACEHOLDER" not in result

    def test_respects_max_chars(self, profile_in_tmp):
        content = "Premier paragraphe.\n\n" + "x" * 1000
        result = profile_in_tmp._extract_excerpt(content, max_chars=100)
        assert len(result) <= 100

    def test_skips_headings(self, profile_in_tmp):
        content = "# Un Titre\n\nUn vrai paragraphe ici.\n\n## Sous-titre\n\nAutre paragraphe."
        result = profile_in_tmp._extract_excerpt(content)
        assert "Un Titre" not in result
        assert "vrai paragraphe" in result

    def test_joins_multiple_paragraphs(self, profile_in_tmp):
        content = "Premier para.\n\nDeuxieme para.\n\nTroisieme para."
        result = profile_in_tmp._extract_excerpt(content, max_chars=5000)
        assert "Premier" in result
        assert "Deuxieme" in result
