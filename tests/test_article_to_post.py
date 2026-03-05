"""
Tests pour agents/article_to_post.py
Cible: augmenter la couverture depuis 23% (112 stmts)
"""
import os
import sys
from unittest.mock import MagicMock, patch, mock_open

import pytest

# Ensure project root is on path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Pre-set required env vars before any imports
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
    """Return an ArticleToPostAgent with all external deps mocked."""
    from config.consultant import ConsultantConfig
    ConsultantConfig.reset()

    with patch("agents.article_to_post.LLMClient") as MockLLM, \
         patch("agents.article_to_post.get_consultant_info") as MockCI:
        MockCI.return_value = {
            "name": "Test Consultant",
            "title": "Manager",
            "company": "TestCo",
        }
        mock_llm_instance = MagicMock()
        MockLLM.return_value = mock_llm_instance
        mock_llm_instance.generate.return_value = "Generated post content"

        from agents.article_to_post import ArticleToPostAgent
        a = ArticleToPostAgent()
        yield a


@pytest.fixture()
def sample_article():
    """Return a sample article dict as returned by fetch_article."""
    return {
        "url": "https://example.com/article",
        "title": "Test Article Title",
        "meta_description": "A brief description of the article.",
        "content": "This is the full article content for testing purposes.",
        "fetched_at": "2026-03-04T10:00:00",
    }


# ---------------------------------------------------------------------------
# TestArticleToPostAgentInit
# ---------------------------------------------------------------------------

class TestArticleToPostAgentInit:
    def test_agent_has_llm_client(self, agent):
        assert hasattr(agent, "llm_client")

    def test_agent_has_html_converter(self, agent):
        assert hasattr(agent, "html_converter")

    def test_agent_has_consultant_info(self, agent):
        assert hasattr(agent, "consultant_info")
        assert isinstance(agent.consultant_info, dict)

    def test_consultant_info_has_name(self, agent):
        assert "name" in agent.consultant_info
        assert agent.consultant_info["name"] == "Test Consultant"

    def test_html_converter_ignores_images(self, agent):
        assert agent.html_converter.ignore_images is True

    def test_html_converter_body_width_zero(self, agent):
        assert agent.html_converter.body_width == 0


# ---------------------------------------------------------------------------
# TestFetchArticle
# ---------------------------------------------------------------------------

class TestFetchArticle:
    def _make_mock_response(self, html_content):
        mock_resp = MagicMock()
        mock_resp.content = html_content.encode("utf-8")
        mock_resp.raise_for_status = MagicMock()
        return mock_resp

    def test_fetch_returns_dict(self, agent):
        html = "<html><body><h1>My Title</h1><p>Content here.</p></body></html>"
        with patch("agents.article_to_post.requests.get") as mock_get:
            mock_get.return_value = self._make_mock_response(html)
            result = agent.fetch_article("https://example.com/test")
        assert isinstance(result, dict)

    def test_fetch_extracts_h1_title(self, agent):
        html = "<html><body><h1>H1 Title</h1><p>Body text.</p></body></html>"
        with patch("agents.article_to_post.requests.get") as mock_get:
            mock_get.return_value = self._make_mock_response(html)
            result = agent.fetch_article("https://example.com/test")
        assert result["title"] == "H1 Title"

    def test_fetch_falls_back_to_title_tag(self, agent):
        html = "<html><head><title>Page Title</title></head><body><p>Text.</p></body></html>"
        with patch("agents.article_to_post.requests.get") as mock_get:
            mock_get.return_value = self._make_mock_response(html)
            result = agent.fetch_article("https://example.com/test")
        assert result["title"] == "Page Title"

    def test_fetch_extracts_meta_description(self, agent):
        html = (
            '<html><head><meta name="description" content="Meta desc here"/>'
            "</head><body><h1>T</h1></body></html>"
        )
        with patch("agents.article_to_post.requests.get") as mock_get:
            mock_get.return_value = self._make_mock_response(html)
            result = agent.fetch_article("https://example.com/test")
        assert result["meta_description"] == "Meta desc here"

    def test_fetch_result_contains_url(self, agent):
        html = "<html><body><h1>T</h1></body></html>"
        url = "https://example.com/my-article"
        with patch("agents.article_to_post.requests.get") as mock_get:
            mock_get.return_value = self._make_mock_response(html)
            result = agent.fetch_article(url)
        assert result["url"] == url

    def test_fetch_result_contains_fetched_at(self, agent):
        html = "<html><body><h1>T</h1></body></html>"
        with patch("agents.article_to_post.requests.get") as mock_get:
            mock_get.return_value = self._make_mock_response(html)
            result = agent.fetch_article("https://example.com/test")
        assert "fetched_at" in result
        assert result["fetched_at"]  # non-empty

    def test_fetch_result_contains_content(self, agent):
        html = "<html><body><article><p>Article content here.</p></article></body></html>"
        with patch("agents.article_to_post.requests.get") as mock_get:
            mock_get.return_value = self._make_mock_response(html)
            result = agent.fetch_article("https://example.com/test")
        assert "content" in result
        assert len(result["content"]) > 0

    def test_fetch_strips_script_tags(self, agent):
        html = (
            "<html><body><h1>T</h1>"
            "<script>alert('xss')</script>"
            "<p>Real content</p></body></html>"
        )
        with patch("agents.article_to_post.requests.get") as mock_get:
            mock_get.return_value = self._make_mock_response(html)
            result = agent.fetch_article("https://example.com/test")
        assert "alert" not in result["content"]

    def test_fetch_uses_article_selector_first(self, agent):
        html = (
            "<html><body>"
            "<nav>Nav stuff</nav>"
            "<article><p>Article body</p></article>"
            "<footer>Footer</footer>"
            "</body></html>"
        )
        with patch("agents.article_to_post.requests.get") as mock_get:
            mock_get.return_value = self._make_mock_response(html)
            result = agent.fetch_article("https://example.com/test")
        assert "Article body" in result["content"]

    def test_fetch_truncates_content_to_6000(self, agent):
        long_text = "x" * 10000
        html = "<html><body><h1>T</h1><p>" + long_text + "</p></body></html>"
        with patch("agents.article_to_post.requests.get") as mock_get:
            mock_get.return_value = self._make_mock_response(html)
            result = agent.fetch_article("https://example.com/test")
        assert len(result["content"]) <= 6000

    def test_fetch_raises_on_http_error(self, agent):
        import requests
        with patch("agents.article_to_post.requests.get") as mock_get:
            mock_resp = MagicMock()
            mock_resp.raise_for_status.side_effect = requests.HTTPError("404")
            mock_get.return_value = mock_resp
            with pytest.raises(requests.HTTPError):
                agent.fetch_article("https://example.com/notfound")

    def test_fetch_empty_title_when_no_heading(self, agent):
        html = "<html><body><p>Just text, no title.</p></body></html>"
        with patch("agents.article_to_post.requests.get") as mock_get:
            mock_get.return_value = self._make_mock_response(html)
            result = agent.fetch_article("https://example.com/test")
        assert result["title"] == ""


# ---------------------------------------------------------------------------
# TestGeneratePost
# ---------------------------------------------------------------------------

class TestGeneratePost:
    def test_generate_returns_dict(self, agent, sample_article):
        with patch("os.path.exists", return_value=False):
            result = agent.generate_post(sample_article)
        assert isinstance(result, dict)

    def test_generate_contains_main_post(self, agent, sample_article):
        agent.llm_client.generate.return_value = "Main post text"
        with patch("os.path.exists", return_value=False):
            result = agent.generate_post(sample_article)
        assert "main_post" in result
        assert result["main_post"] == "Main post text"

    def test_generate_contains_short_version(self, agent, sample_article):
        agent.llm_client.generate.side_effect = ["Main post text", "Short version text"]
        with patch("os.path.exists", return_value=False):
            result = agent.generate_post(sample_article)
        assert "short_version" in result
        assert result["short_version"] == "Short version text"

    def test_generate_contains_tone(self, agent, sample_article):
        with patch("os.path.exists", return_value=False):
            result = agent.generate_post(sample_article, tone="casual")
        assert result["tone"] == "casual"

    def test_generate_contains_article_title(self, agent, sample_article):
        with patch("os.path.exists", return_value=False):
            result = agent.generate_post(sample_article)
        assert result["article_title"] == sample_article["title"]

    def test_generate_contains_article_url(self, agent, sample_article):
        with patch("os.path.exists", return_value=False):
            result = agent.generate_post(sample_article)
        assert result["article_url"] == sample_article["url"]

    def test_generate_contains_consultant(self, agent, sample_article):
        with patch("os.path.exists", return_value=False):
            result = agent.generate_post(sample_article)
        assert "consultant" in result
        assert result["consultant"]["name"] == "Test Consultant"

    def test_generate_contains_generated_at(self, agent, sample_article):
        with patch("os.path.exists", return_value=False):
            result = agent.generate_post(sample_article)
        assert "generated_at" in result

    def test_generate_calls_llm_twice(self, agent, sample_article):
        with patch("os.path.exists", return_value=False):
            agent.generate_post(sample_article)
        assert agent.llm_client.generate.call_count == 2

    def test_generate_expert_tone_default(self, agent, sample_article):
        with patch("os.path.exists", return_value=False):
            result = agent.generate_post(sample_article)
        assert result["tone"] == "expert"

    def test_generate_provocateur_tone(self, agent, sample_article):
        with patch("os.path.exists", return_value=False):
            result = agent.generate_post(sample_article, tone="provocateur")
        assert result["tone"] == "provocateur"

    def test_generate_reads_persona_when_exists(self, agent, sample_article, tmp_path):
        persona_content = (
            "### ✨ Ton & Style\nStyle test content\n"
            "### 🎨 Thématiques favorites\nThemes"
        )
        # Code looks for BASE_PATH/data/linkedin_persona.md
        data_dir = tmp_path / "data"
        data_dir.mkdir()
        persona_file = data_dir / "linkedin_persona.md"
        persona_file.write_text(persona_content, encoding="utf-8")

        with patch("agents.article_to_post.BASE_PATH", str(tmp_path)):
            result = agent.generate_post(sample_article)
        assert isinstance(result, dict)

    def test_generate_with_emoji_false(self, agent, sample_article):
        with patch("os.path.exists", return_value=False):
            result = agent.generate_post(sample_article, include_emoji=False)
        # Verify llm was called — emoji flag affects prompt text
        assert agent.llm_client.generate.called
        assert isinstance(result, dict)


# ---------------------------------------------------------------------------
# TestRunPipeline
# ---------------------------------------------------------------------------

class TestRunPipeline:
    def test_run_calls_fetch_and_generate(self, agent, tmp_path):
        sample_art = {
            "url": "https://example.com/art",
            "title": "Some Title",
            "meta_description": "",
            "content": "Content text",
            "fetched_at": "2026-03-04T10:00:00",
        }
        generate_result = {
            "main_post": "Main post",
            "short_version": "Short",
            "tone": "expert",
            "article_title": "Some Title",
            "article_url": "https://example.com/art",
            "generated_at": "2026-03-04T10:00:00",
            "consultant": {"name": "Test Consultant"},
        }
        with patch.object(agent, "fetch_article", return_value=sample_art) as mock_fetch, \
             patch.object(agent, "generate_post", return_value=generate_result) as mock_gen, \
             patch("agents.article_to_post.BASE_PATH", str(tmp_path)), \
             patch("agents.article_to_post.os.makedirs"), \
             patch("builtins.open", mock_open()):
            result = agent.run("https://example.com/art")

        mock_fetch.assert_called_once_with("https://example.com/art")
        mock_gen.assert_called_once()
        assert "main_post" in result

    def test_run_saves_md_file(self, agent, tmp_path):
        sample_art = {
            "url": "https://example.com/art",
            "title": "Title",
            "meta_description": "",
            "content": "Content",
            "fetched_at": "2026-03-04T10:00:00",
        }
        generate_result = {
            "main_post": "Main post",
            "short_version": "Short",
            "tone": "expert",
            "article_title": "Title",
            "article_url": "https://example.com/art",
            "generated_at": "2026-03-04T10:00:00",
            "consultant": {"name": "Test Consultant"},
        }
        with patch.object(agent, "fetch_article", return_value=sample_art), \
             patch.object(agent, "generate_post", return_value=generate_result), \
             patch("agents.article_to_post.BASE_PATH", str(tmp_path)):
            result = agent.run("https://example.com/art")

        assert "md_path" in result
        assert result["md_path"].endswith(".md")

    def test_run_passes_tone_to_generate(self, agent, tmp_path):
        sample_art = {
            "url": "https://example.com/art",
            "title": "T",
            "meta_description": "",
            "content": "C",
            "fetched_at": "2026-03-04T10:00:00",
        }
        generate_result = {
            "main_post": "Post",
            "short_version": "Short",
            "tone": "casual",
            "article_title": "T",
            "article_url": "https://example.com/art",
            "generated_at": "2026-03-04T10:00:00",
            "consultant": {"name": "Test Consultant"},
        }
        with patch.object(agent, "fetch_article", return_value=sample_art), \
             patch.object(agent, "generate_post", return_value=generate_result) as mock_gen, \
             patch("agents.article_to_post.BASE_PATH", str(tmp_path)):
            agent.run("https://example.com/art", tone="casual")

        call_kwargs = mock_gen.call_args
        assert call_kwargs is not None
        # tone should be passed
        args, kwargs = call_kwargs
        assert kwargs.get("tone") == "casual" or (len(args) > 1 and args[1] == "casual")


# ---------------------------------------------------------------------------
# main() entry point
# ---------------------------------------------------------------------------

class TestMainFunction:
    def test_main_calls_run(self):
        with patch("agents.article_to_post.LLMClient"), \
             patch("agents.article_to_post.get_consultant_info",
                   return_value={"name": "T", "title": "T", "company": "T"}):
            from agents.article_to_post import ArticleToPostAgent, main
        mock_result = {
            "main_post": "Le post LinkedIn généré",
            "short_version": "Version courte",
            "tone": "expert",
            "article_title": "Article Title",
            "article_url": "https://example.com",
            "generated_at": "2026-01-01",
            "md_path": "/tmp/post.md",
        }
        with patch("sys.argv", ["article_to_post.py", "https://example.com/article"]):
            with patch.object(ArticleToPostAgent, "run", return_value=mock_result):
                main()

    def test_main_with_tone_flag(self):
        with patch("agents.article_to_post.LLMClient"), \
             patch("agents.article_to_post.get_consultant_info",
                   return_value={"name": "T", "title": "T", "company": "T"}):
            from agents.article_to_post import ArticleToPostAgent, main
        mock_result = {
            "main_post": "Post",
            "short_version": "Short",
            "tone": "casual",
            "article_title": "T",
            "article_url": "https://example.com",
            "generated_at": "2026-01-01",
            "md_path": "/tmp/post.md",
        }
        with patch("sys.argv", ["article_to_post.py", "https://example.com", "--tone", "casual"]):
            with patch.object(ArticleToPostAgent, "run", return_value=mock_result):
                main()
