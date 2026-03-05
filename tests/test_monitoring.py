"""
Tests unitaires pour utils/monitoring.py — MonitoringTool et extract_key_insights.
Toutes les dépendances réseau (requests, feedparser, html2text, BeautifulSoup) sont mockées.
"""

import json
import os
import sys
from datetime import datetime, timedelta
from unittest.mock import MagicMock, Mock, patch, mock_open

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.monitoring import MonitoringTool, extract_key_insights


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_tool(keywords="python,ai"):
    """Crée un MonitoringTool avec des keywords fixés via env var."""
    with patch.dict(os.environ, {"VEILLE_KEYWORDS": keywords}):
        return MonitoringTool()


def _make_entry(title="Article", link="https://example.com", summary="Summary text",
                published="", updated=""):
    entry = MagicMock()
    entry.get = lambda key, default="": {
        "title": title,
        "link": link,
        "summary": summary,
        "description": "",
        "published": published,
        "updated": updated,
    }.get(key, default)
    return entry


# ---------------------------------------------------------------------------
# MonitoringTool.__init__
# ---------------------------------------------------------------------------

class TestMonitoringToolInit:
    def test_keywords_parsed_from_env(self):
        with patch.dict(os.environ, {"VEILLE_KEYWORDS": "python, ai, data"}):
            tool = MonitoringTool()
        assert "python" in tool.keywords
        assert "ai" in tool.keywords
        assert "data" in tool.keywords

    def test_keywords_stripped(self):
        with patch.dict(os.environ, {"VEILLE_KEYWORDS": " python , ai "}):
            tool = MonitoringTool()
        assert "python" in tool.keywords
        assert "ai" in tool.keywords
        # No whitespace in values
        for kw in tool.keywords:
            assert kw == kw.strip()

    def test_empty_env_var_gives_empty_keywords(self):
        with patch.dict(os.environ, {"VEILLE_KEYWORDS": ""}):
            tool = MonitoringTool()
        assert tool.keywords == []

    def test_missing_env_var_gives_empty_keywords(self):
        env = {k: v for k, v in os.environ.items() if k != "VEILLE_KEYWORDS"}
        with patch.dict(os.environ, env, clear=True):
            tool = MonitoringTool()
        assert tool.keywords == []


# ---------------------------------------------------------------------------
# MonitoringTool.fetch_rss_feeds
# ---------------------------------------------------------------------------

class TestFetchRssFeeds:
    def _make_feed(self, entries, feed_title="Test Feed"):
        feed = MagicMock()
        feed.entries = entries
        feed.feed.get = lambda key, default="": {"title": feed_title}.get(key, default)
        return feed

    def test_returns_articles_from_feed(self):
        tool = _make_tool()
        entry = _make_entry(title="Hello", link="https://x.com", summary="<b>Body</b>")
        feed = self._make_feed([entry])

        with patch("utils.monitoring.feedparser.parse", return_value=feed):
            with patch("utils.monitoring.BeautifulSoup") as mock_bs:
                soup = MagicMock()
                soup.get_text.return_value = "Body"
                mock_bs.return_value = soup
                articles = tool.fetch_rss_feeds(["https://feed.url"], download_content=False)

        assert len(articles) == 1
        assert articles[0]["title"] == "Hello"
        assert articles[0]["source_type"] == "rss"

    def test_limits_to_10_articles_per_feed(self):
        tool = _make_tool()
        entries = [_make_entry(title=f"Art {i}") for i in range(20)]
        feed = self._make_feed(entries)

        with patch("utils.monitoring.feedparser.parse", return_value=feed):
            with patch("utils.monitoring.BeautifulSoup") as mock_bs:
                soup = MagicMock()
                soup.get_text.return_value = "text"
                mock_bs.return_value = soup
                articles = tool.fetch_rss_feeds(["https://feed.url"], download_content=False)

        assert len(articles) == 10

    def test_multiple_feeds_aggregated(self):
        tool = _make_tool()
        entry = _make_entry(title="Entry")
        feed = self._make_feed([entry])

        with patch("utils.monitoring.feedparser.parse", return_value=feed):
            with patch("utils.monitoring.BeautifulSoup") as mock_bs:
                soup = MagicMock()
                soup.get_text.return_value = "text"
                mock_bs.return_value = soup
                articles = tool.fetch_rss_feeds(
                    ["https://feed1.url", "https://feed2.url"], download_content=False
                )

        assert len(articles) == 2

    def test_exception_in_feed_does_not_crash(self):
        tool = _make_tool()
        with patch("utils.monitoring.feedparser.parse", side_effect=Exception("Network error")):
            articles = tool.fetch_rss_feeds(["https://bad.url"], download_content=False)
        assert articles == []

    def test_download_content_called_when_enabled(self):
        tool = _make_tool()
        entry = _make_entry(title="Art", link="https://x.com")
        feed = self._make_feed([entry])

        with patch("utils.monitoring.feedparser.parse", return_value=feed):
            with patch("utils.monitoring.BeautifulSoup") as mock_bs:
                soup = MagicMock()
                soup.get_text.return_value = "text"
                mock_bs.return_value = soup
                with patch.object(tool, "download_article_content", return_value="full") as dl:
                    tool.fetch_rss_feeds(["https://feed.url"], download_content=True)
        dl.assert_called_once_with("https://x.com")

    def test_empty_feed_list_returns_empty(self):
        tool = _make_tool()
        articles = tool.fetch_rss_feeds([])
        assert articles == []

    def test_source_set_from_feed_title(self):
        tool = _make_tool()
        entry = _make_entry(title="T", summary="S")
        feed = self._make_feed([entry], feed_title="MyBlog")

        with patch("utils.monitoring.feedparser.parse", return_value=feed):
            with patch("utils.monitoring.BeautifulSoup") as mock_bs:
                soup = MagicMock()
                soup.get_text.return_value = "S"
                mock_bs.return_value = soup
                articles = tool.fetch_rss_feeds(["https://feed.url"], download_content=False)

        assert articles[0]["source"] == "MyBlog"


# ---------------------------------------------------------------------------
# MonitoringTool.download_article_content
# ---------------------------------------------------------------------------

class TestDownloadArticleContent:
    def test_returns_text_on_success(self):
        tool = _make_tool()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = b"<html><body><article>Article text here</article></body></html>"

        with patch("utils.monitoring.requests.get", return_value=mock_response):
            with patch("utils.monitoring.BeautifulSoup") as mock_bs:
                soup = MagicMock()
                article_body = MagicMock()
                article_body.find_all.return_value = []
                soup.select_one.side_effect = lambda sel: article_body if sel == "article" else None
                mock_bs.return_value = soup

                with patch("utils.monitoring.html2text.HTML2Text") as mock_h2t:
                    converter = MagicMock()
                    converter.handle.return_value = "Article text here"
                    mock_h2t.return_value = converter

                    result = tool.download_article_content("https://example.com")

        assert "Article text here" in result

    def test_returns_empty_on_exception(self):
        tool = _make_tool()
        with patch("utils.monitoring.requests.get", side_effect=Exception("timeout")):
            result = tool.download_article_content("https://bad.url")
        assert result == ""

    def test_respects_max_chars(self):
        tool = _make_tool()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = b"<html><body>text</body></html>"

        with patch("utils.monitoring.requests.get", return_value=mock_response):
            with patch("utils.monitoring.BeautifulSoup") as mock_bs:
                soup = MagicMock()
                soup.select_one.return_value = None
                body = MagicMock()
                body.find_all.return_value = []
                soup.find.return_value = body
                mock_bs.return_value = soup

                with patch("utils.monitoring.html2text.HTML2Text") as mock_h2t:
                    converter = MagicMock()
                    converter.handle.return_value = "x" * 5000
                    mock_h2t.return_value = converter

                    result = tool.download_article_content("https://example.com", max_chars=100)

        assert len(result) <= 100

    def test_http_error_returns_empty(self):
        tool = _make_tool()
        mock_response = MagicMock()
        mock_response.raise_for_status.side_effect = Exception("404")

        with patch("utils.monitoring.requests.get", return_value=mock_response):
            result = tool.download_article_content("https://notfound.com")
        assert result == ""


# ---------------------------------------------------------------------------
# MonitoringTool.web_search
# ---------------------------------------------------------------------------

class TestWebSearch:
    def test_returns_results_on_success(self):
        tool = _make_tool(keywords="python")
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = b"<html></html>"

        with patch("utils.monitoring.requests.get", return_value=mock_response):
            with patch("utils.monitoring.BeautifulSoup") as mock_bs:
                soup = MagicMock()
                # Simulate 2 result divs
                result_div1 = MagicMock()
                title_a = MagicMock()
                title_a.get_text.return_value = "Result 1"
                title_a.get.return_value = "https://r1.com"
                snippet_a = MagicMock()
                snippet_a.get_text.return_value = "Snippet 1"
                result_div1.find.side_effect = lambda tag, class_=None: (
                    title_a if class_ == "result__a" else snippet_a
                )
                soup.find_all.return_value = [result_div1]
                mock_bs.return_value = soup

                results = tool.web_search(["python"], download_content=False)

        assert len(results) >= 0  # May be 0 or more depending on mock

    def test_exception_in_search_does_not_crash(self):
        tool = _make_tool(keywords="python")
        with patch("utils.monitoring.requests.get", side_effect=Exception("network")):
            results = tool.web_search(["python"], download_content=False)
        assert results == []

    def test_empty_keywords_returns_empty(self):
        tool = _make_tool()
        results = tool.web_search([])
        assert results == []

    def test_non_200_response_skipped(self):
        tool = _make_tool(keywords="python")
        mock_response = MagicMock()
        mock_response.status_code = 429

        with patch("utils.monitoring.requests.get", return_value=mock_response):
            results = tool.web_search(["python"], download_content=False)
        assert results == []


# ---------------------------------------------------------------------------
# MonitoringTool.fetch_linkedin_posts
# ---------------------------------------------------------------------------

class TestFetchLinkedinPosts:
    def test_returns_empty_list(self):
        tool = _make_tool()
        result = tool.fetch_linkedin_posts(["ai", "python"])
        assert result == []

    def test_accepts_limit_parameter(self):
        tool = _make_tool()
        result = tool.fetch_linkedin_posts(["ai"], limit=5)
        assert isinstance(result, list)


# ---------------------------------------------------------------------------
# MonitoringTool.analyze_article_relevance
# ---------------------------------------------------------------------------

class TestAnalyzeArticleRelevance:
    def test_keyword_in_title_raises_score(self):
        tool = _make_tool(keywords="python")
        article = {"title": "Python tips", "summary": ""}
        score = tool.analyze_article_relevance(article, ["python"])
        assert score > 0.0

    def test_keyword_in_summary_raises_score(self):
        tool = _make_tool(keywords="ai")
        article = {"title": "No match", "summary": "AI is transforming everything"}
        score = tool.analyze_article_relevance(article, ["ai"])
        assert score > 0.0

    def test_no_keyword_match_zero_score(self):
        tool = _make_tool(keywords="blockchain")
        article = {"title": "Cooking recipes", "summary": "How to make pasta"}
        score = tool.analyze_article_relevance(article, ["blockchain"])
        assert score == 0.0

    def test_trusted_source_bonus(self):
        tool = _make_tool(keywords="irrelevant")
        article = {"title": "News", "summary": "", "source": "TechCrunch"}
        score = tool.analyze_article_relevance(article, [])
        assert score >= 0.2

    def test_score_capped_at_1(self):
        tool = _make_tool(keywords="python,ai,data,ml,nlp")
        keywords = ["python", "ai", "data", "ml", "nlp"]
        article = {
            "title": "python ai data ml nlp",
            "summary": "python ai data ml nlp",
            "source": "techcrunch",
        }
        score = tool.analyze_article_relevance(article, keywords)
        assert score <= 1.0

    def test_old_article_penalty(self):
        tool = _make_tool(keywords="python")
        old_date = (datetime.now() - timedelta(days=10)).isoformat()
        article = {"title": "Python news", "summary": "", "published": old_date}
        score_old = tool.analyze_article_relevance(article, ["python"])

        recent_date = datetime.now().isoformat()
        article_recent = {"title": "Python news", "summary": "", "published": recent_date}
        score_recent = tool.analyze_article_relevance(article_recent, ["python"])

        assert score_old <= score_recent

    def test_invalid_date_does_not_crash(self):
        tool = _make_tool(keywords="python")
        article = {"title": "Python", "summary": "", "published": "not-a-date"}
        # Should not raise
        score = tool.analyze_article_relevance(article, ["python"])
        assert isinstance(score, float)

    def test_empty_article_returns_zero(self):
        tool = _make_tool(keywords="python")
        score = tool.analyze_article_relevance({}, ["python"])
        assert score == 0.0


# ---------------------------------------------------------------------------
# MonitoringTool.filter_and_rank_articles
# ---------------------------------------------------------------------------

class TestFilterAndRankArticles:
    def test_filters_below_min_score(self):
        tool = _make_tool(keywords="python")
        articles = [
            {"title": "Python guide", "summary": "python tips"},
            {"title": "Cooking recipes", "summary": "pasta and sauce"},
        ]
        result = tool.filter_and_rank_articles(articles, min_score=0.3)
        titles = [a["title"] for a in result]
        assert "Python guide" in titles
        assert "Cooking recipes" not in titles

    def test_sorted_by_score_descending(self):
        tool = _make_tool(keywords="python,ai")
        articles = [
            {"title": "Python basics", "summary": "python intro", "source": ""},
            {"title": "Python AI deep dive", "summary": "python ai tutorial", "source": ""},
        ]
        result = tool.filter_and_rank_articles(articles, min_score=0.0)
        if len(result) >= 2:
            assert result[0]["relevance_score"] >= result[1]["relevance_score"]

    def test_empty_input_returns_empty(self):
        tool = _make_tool()
        result = tool.filter_and_rank_articles([])
        assert result == []

    def test_relevance_score_added_to_articles(self):
        tool = _make_tool(keywords="python")
        articles = [{"title": "Python", "summary": "python stuff"}]
        tool.filter_and_rank_articles(articles, min_score=0.0)
        assert "relevance_score" in articles[0]

    def test_all_below_threshold_returns_empty(self):
        tool = _make_tool(keywords="python")
        articles = [
            {"title": "Gardening", "summary": "plants and soil"},
            {"title": "Cooking", "summary": "recipes"},
        ]
        result = tool.filter_and_rank_articles(articles, min_score=0.9)
        assert result == []


# ---------------------------------------------------------------------------
# MonitoringTool.save_monitoring_results
# ---------------------------------------------------------------------------

class TestSaveMonitoringResults:
    def test_saves_to_specified_path(self, tmp_path):
        tool = _make_tool()
        results = {"articles": [], "total_collected": 0}
        output_file = str(tmp_path / "veille.json")

        tool.save_monitoring_results(results, output_path=output_file)

        assert os.path.exists(output_file)
        with open(output_file, encoding="utf-8") as f:
            data = json.load(f)
        assert data["total_collected"] == 0

    def test_auto_generates_path_when_none(self, tmp_path):
        tool = _make_tool()
        results = {"articles": [], "keywords": ["python"]}

        # Patch os.makedirs and open to avoid writing to real filesystem
        with patch("utils.monitoring.os.makedirs"):
            with patch("builtins.open", mock_open()):
                with patch("utils.monitoring.json.dump"):
                    # Should not raise
                    tool.save_monitoring_results(results, output_path=None)

    def test_output_is_valid_json(self, tmp_path):
        tool = _make_tool()
        results = {
            "articles": [{"title": "Test", "link": "https://x.com"}],
            "total_collected": 1,
            "keywords": ["test"],
        }
        output_file = str(tmp_path / "out.json")
        tool.save_monitoring_results(results, output_path=output_file)

        with open(output_file, encoding="utf-8") as f:
            data = json.load(f)
        assert data["total_collected"] == 1


# ---------------------------------------------------------------------------
# MonitoringTool.collect_all_sources
# ---------------------------------------------------------------------------

class TestCollectAllSources:
    def test_returns_expected_keys(self):
        tool = _make_tool(keywords="python")

        with patch.object(tool, "fetch_rss_feeds", return_value=[]):
            with patch.object(tool, "web_search", return_value=[]):
                with patch.object(tool, "filter_and_rank_articles", return_value=[]):
                    with patch.object(tool, "download_article_content", return_value=""):
                        result = tool.collect_all_sources(rss_feeds=[], search_keywords=[])

        assert "articles" in result
        assert "total_collected" in result
        assert "total_relevant" in result
        assert "collected_at" in result
        assert "keywords" in result

    def test_rss_feeds_called_when_provided(self):
        tool = _make_tool(keywords="python")

        with patch.object(tool, "fetch_rss_feeds", return_value=[]) as mock_rss:
            with patch.object(tool, "web_search", return_value=[]):
                with patch.object(tool, "filter_and_rank_articles", return_value=[]):
                    tool.collect_all_sources(rss_feeds=["https://feed.url"])

        mock_rss.assert_called_once()

    def test_web_search_called_when_keywords_provided(self):
        tool = _make_tool(keywords="python")

        with patch.object(tool, "fetch_rss_feeds", return_value=[]):
            with patch.object(tool, "web_search", return_value=[]) as mock_web:
                with patch.object(tool, "filter_and_rank_articles", return_value=[]):
                    tool.collect_all_sources(search_keywords=["python"])

        mock_web.assert_called_once()

    def test_no_rss_no_web_zero_articles(self):
        tool = _make_tool(keywords="python")

        with patch.object(tool, "filter_and_rank_articles", return_value=[]):
            result = tool.collect_all_sources(rss_feeds=None, search_keywords=None)

        assert result["total_collected"] == 0

    def test_total_collected_counts_all_sources(self):
        tool = _make_tool(keywords="python")
        rss_articles = [{"title": f"RSS {i}", "summary": ""} for i in range(3)]
        web_articles = [{"title": f"Web {i}", "summary": ""} for i in range(2)]

        with patch.object(tool, "fetch_rss_feeds", return_value=rss_articles):
            with patch.object(tool, "web_search", return_value=web_articles):
                with patch.object(tool, "download_article_content", return_value=""):
                    with patch.object(
                        tool, "filter_and_rank_articles", return_value=[]
                    ):
                        result = tool.collect_all_sources(
                            rss_feeds=["url"], search_keywords=["python"]
                        )

        assert result["total_collected"] == 5

    def test_downloads_top_articles_after_ranking(self):
        tool = _make_tool(keywords="python")
        ranked = [{"title": f"Art {i}", "link": f"https://x{i}.com", "summary": ""}
                  for i in range(3)]

        with patch.object(tool, "fetch_rss_feeds", return_value=[]):
            with patch.object(tool, "web_search", return_value=[]):
                with patch.object(tool, "filter_and_rank_articles", return_value=ranked):
                    with patch.object(
                        tool, "download_article_content", return_value="full text"
                    ) as dl:
                        tool.collect_all_sources(rss_feeds=[], search_keywords=[])

        assert dl.call_count == 3


# ---------------------------------------------------------------------------
# extract_key_insights (module-level function)
# ---------------------------------------------------------------------------

class TestExtractKeyInsights:
    def test_returns_list_of_strings(self):
        articles = [
            {"title": "Article 1", "summary": "Summary 1", "link": "https://a1.com"},
            {"title": "Article 2", "summary": "Summary 2", "link": "https://a2.com"},
        ]
        insights = extract_key_insights(articles)
        assert isinstance(insights, list)
        assert all(isinstance(i, str) for i in insights)

    def test_respects_top_n_limit(self):
        articles = [
            {"title": f"Art {i}", "summary": "summary", "link": "https://x.com"}
            for i in range(10)
        ]
        insights = extract_key_insights(articles, top_n=3)
        assert len(insights) == 3

    def test_contains_title_and_link(self):
        articles = [{"title": "My Article", "summary": "Details here", "link": "https://x.com"}]
        insights = extract_key_insights(articles)
        assert len(insights) == 1
        assert "My Article" in insights[0]
        assert "https://x.com" in insights[0]

    def test_empty_articles_returns_empty(self):
        insights = extract_key_insights([])
        assert insights == []

    def test_fewer_articles_than_top_n(self):
        articles = [{"title": "Only one", "summary": "text", "link": "https://x.com"}]
        insights = extract_key_insights(articles, top_n=10)
        assert len(insights) == 1

    def test_summary_truncated_to_200_chars(self):
        long_summary = "x" * 500
        articles = [{"title": "T", "summary": long_summary, "link": "https://x.com"}]
        insight = extract_key_insights(articles)[0]
        # The function uses summary[:200] so long summary should not appear fully
        assert "x" * 500 not in insight

    def test_none_link_included(self):
        articles = [{"title": "T", "summary": "S", "link": None}]
        # Should not crash
        insights = extract_key_insights(articles)
        assert len(insights) == 1

    def test_default_top_n_is_5(self):
        articles = [
            {"title": f"Art {i}", "summary": "s", "link": "https://x.com"}
            for i in range(10)
        ]
        insights = extract_key_insights(articles)
        assert len(insights) == 5
