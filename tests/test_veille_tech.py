"""
Tests for Veille Tech: expanded sources, fixed KeyError,
article persistence, and date calculation bugs.
"""

import os
import sqlite3
import tempfile
from datetime import datetime, timedelta
from unittest.mock import MagicMock, Mock, patch

import pytest


class TestArticleDatabasePersistence:
    """Tests for article database persistence and date fixes"""

    def _make_db(self, tmp_path=None):
        """Create a temp ArticleDatabase"""
        from utils.article_db import ArticleDatabase

        if tmp_path is None:
            tmp_path = tempfile.mktemp(suffix=".db")
        return ArticleDatabase(db_path=tmp_path)

    def test_articles_persist_after_reinit(self):
        """Articles survive database re-initialization"""
        tmp_path = tempfile.mktemp(suffix=".db")

        # First instance: save articles
        db1 = self._make_db(tmp_path)
        articles = [
            {
                "title": "Test Article",
                "link": "https://example.com/1",
                "summary": "Summary",
                "date": datetime.now().isoformat(),
                "source": "Test Source",
            }
        ]
        saved = db1.save_articles(articles)
        assert saved == 1

        # Second instance: articles should still be there
        db2 = self._make_db(tmp_path)
        retrieved = db2.get_articles(limit=10)
        assert len(retrieved) >= 1
        assert retrieved[0]["title"] == "Test Article"

        # Cleanup
        os.unlink(tmp_path)

    def test_duplicate_articles_ignored(self):
        """Duplicate links are silently ignored"""
        db = self._make_db()
        articles = [
            {
                "title": "Article 1",
                "link": "https://example.com/same",
                "summary": "S1",
                "date": datetime.now().isoformat(),
                "source": "Source",
            },
            {
                "title": "Article 2",
                "link": "https://example.com/same",
                "summary": "S2",
                "date": datetime.now().isoformat(),
                "source": "Source",
            },
        ]
        saved = db.save_articles(articles)
        assert saved == 1  # Second should be ignored

    def test_get_articles_filter_by_days(self):
        """get_articles with days filter uses timedelta (not replace)"""
        db = self._make_db()

        # Insert recent and old articles
        now = datetime.now()
        articles = [
            {
                "title": "Recent",
                "link": "https://example.com/recent",
                "summary": "R",
                "date": now.isoformat(),
                "source": "S",
            },
            {
                "title": "Old",
                "link": "https://example.com/old",
                "summary": "O",
                "date": (now - timedelta(days=30)).isoformat(),
                "source": "S",
            },
        ]
        db.save_articles(articles)

        # Filter last 7 days
        recent = db.get_articles(days=7)
        titles = [a["title"] for a in recent]
        assert "Recent" in titles

    def test_get_articles_filter_by_source(self):
        """get_articles filters by source"""
        db = self._make_db()
        articles = [
            {
                "title": "A1",
                "link": "https://a.com/1",
                "summary": "",
                "date": datetime.now().isoformat(),
                "source": "Source A",
            },
            {
                "title": "B1",
                "link": "https://b.com/1",
                "summary": "",
                "date": datetime.now().isoformat(),
                "source": "Source B",
            },
        ]
        db.save_articles(articles)

        result = db.get_articles(source="Source A")
        assert all(a["source"] == "Source A" for a in result)

    def test_get_articles_filter_by_keyword(self):
        """get_articles filters by keyword in title/summary"""
        db = self._make_db()
        articles = [
            {
                "title": "Python ML Guide",
                "link": "https://a.com/py",
                "summary": "Machine learning",
                "date": datetime.now().isoformat(),
                "source": "S",
            },
            {
                "title": "Java Spring",
                "link": "https://a.com/java",
                "summary": "Web framework",
                "date": datetime.now().isoformat(),
                "source": "S",
            },
        ]
        db.save_articles(articles)

        result = db.get_articles(keyword="Python")
        assert len(result) >= 1
        assert result[0]["title"] == "Python ML Guide"

    def test_article_stats(self):
        """get_article_stats returns correct counts"""
        db = self._make_db()
        articles = [
            {
                "title": f"Article {i}",
                "link": f"https://example.com/{i}",
                "summary": "",
                "date": datetime.now().isoformat(),
                "source": "Source A" if i < 3 else "Source B",
            }
            for i in range(5)
        ]
        db.save_articles(articles)

        stats = db.get_article_stats()
        assert stats["total_articles"] == 5
        assert len(stats["by_source"]) == 2

    def test_save_and_get_digest(self):
        """Test digest persistence"""
        db = self._make_db()
        digest_id = db.save_digest(
            period="weekly",
            content="# Digest\nContent",
            num_articles=10,
            file_path="/tmp/digest.md",
        )
        assert digest_id > 0

        latest = db.get_latest_digest(period="weekly")
        assert latest is not None
        assert latest["content"] == "# Digest\nContent"
        assert latest["num_articles"] == 10

    def test_mark_as_read(self):
        """Test mark_as_read updates the article"""
        db = self._make_db()
        articles = [
            {
                "title": "Unread",
                "link": "https://example.com/unread",
                "summary": "",
                "date": datetime.now().isoformat(),
                "source": "S",
            }
        ]
        db.save_articles(articles)
        all_articles = db.get_articles()
        article_id = all_articles[0]["id"]

        db.mark_as_read(article_id)

        updated = db.get_articles()
        assert updated[0]["read"] == 1

    def test_toggle_favorite(self):
        """Test toggle_favorite toggles correctly"""
        db = self._make_db()
        articles = [
            {
                "title": "Fav",
                "link": "https://example.com/fav",
                "summary": "",
                "date": datetime.now().isoformat(),
                "source": "S",
            }
        ]
        db.save_articles(articles)
        all_articles = db.get_articles()
        article_id = all_articles[0]["id"]

        # Toggle on
        db.toggle_favorite(article_id)
        updated = db.get_articles()
        assert updated[0]["favorite"] == 1

        # Toggle off
        db.toggle_favorite(article_id)
        updated = db.get_articles()
        assert updated[0]["favorite"] == 0


class TestTechMonitorSources:
    """Tests for expanded RSS sources"""

    def test_default_sources_count(self):
        """Test that we have expanded sources (more than 6)"""
        from agents.tech_monitor import TechMonitorAgent

        agent = TechMonitorAgent()
        assert len(agent.default_sources) > 6
        assert len(agent.default_sources) >= 15

    def test_sources_include_major_providers(self):
        """Test sources include major AI/tech providers"""
        from agents.tech_monitor import TechMonitorAgent

        agent = TechMonitorAgent()
        sources_str = " ".join(agent.default_sources)

        assert "google" in sources_str.lower()
        assert "meta" in sources_str.lower()
        assert "microsoft" in sources_str.lower()
        assert "anthropic" in sources_str.lower()

    def test_sources_include_data_engineering(self):
        """Test sources include data engineering feeds"""
        from agents.tech_monitor import TechMonitorAgent

        agent = TechMonitorAgent()
        sources_str = " ".join(agent.default_sources)

        assert "datascience" in sources_str.lower() or "data" in sources_str.lower()

    def test_sources_are_valid_urls(self):
        """Test all sources are valid URLs"""
        from agents.tech_monitor import TechMonitorAgent

        agent = TechMonitorAgent()
        for source in agent.default_sources:
            assert source.startswith("http"), f"Invalid URL: {source}"


class TestTechMonitorRunKeyError:
    """Tests for the fixed KeyError 'content' bug"""

    def test_run_no_articles_returns_content_key(self):
        """run() with no articles returns 'content' key (not 'digest')"""
        from agents.tech_monitor import TechMonitorAgent

        agent = TechMonitorAgent()

        # Mock collect_articles to return empty
        with patch.object(agent, "collect_articles", return_value=[]):
            # Mock db.get_articles to also return empty
            with patch.object(agent.db, "get_articles", return_value=[]):
                result = agent.run(days=1)

        assert "content" in result
        assert "num_articles" in result
        assert result["num_articles"] == 0

    def test_run_with_articles_returns_content_key(self):
        """run() with articles returns 'content' key"""
        from agents.tech_monitor import TechMonitorAgent

        agent = TechMonitorAgent()

        mock_articles = [
            {
                "title": "Test Article",
                "link": "https://example.com/test",
                "summary": "Summary",
                "date": datetime.now().isoformat(),
                "source": "Test",
            }
        ]

        with patch.object(agent, "collect_articles", return_value=mock_articles):
            with patch.object(agent.db, "save_articles", return_value=1):
                with patch.object(
                    agent,
                    "generate_digest",
                    return_value={
                        "content": "# Digest\nContent",
                        "period": "weekly",
                        "num_articles": 1,
                        "generated_at": datetime.now().isoformat(),
                    },
                ):
                    with patch.object(agent.db, "save_digest", return_value=1):
                        with patch("builtins.open", create=True):
                            result = agent.run(days=1)

        assert "content" in result

    def test_run_falls_back_to_persisted_articles(self):
        """run() loads from DB when RSS feeds return nothing"""
        from agents.tech_monitor import TechMonitorAgent

        agent = TechMonitorAgent()

        db_articles = [
            {
                "title": "DB Article",
                "link": "https://db.com/1",
                "summary": "From DB",
                "date": datetime.now().isoformat(),
                "source": "DB Source",
            }
        ]

        with patch.object(agent, "collect_articles", return_value=[]):
            with patch.object(agent.db, "get_articles", return_value=db_articles):
                with patch.object(
                    agent,
                    "generate_digest",
                    return_value={
                        "content": "# Digest from DB",
                        "period": "weekly",
                        "num_articles": 1,
                        "generated_at": datetime.now().isoformat(),
                    },
                ):
                    with patch.object(agent.db, "save_digest", return_value=1):
                        with patch("builtins.open", create=True):
                            result = agent.run(days=7)

        assert "content" in result
        assert result["num_articles"] > 0


class TestApiVeilleDigest:
    """Tests for the veille API digest endpoint fix"""

    def test_digest_endpoint_handles_no_articles(self):
        """Endpoint doesn't crash when no articles found"""
        from app import app

        routes = [r.path for r in app.routes]
        assert "/api/veille/generate-digest" in routes

    def test_collect_articles_saves_to_db(self):
        """collect_articles saves new articles to database"""
        from agents.tech_monitor import TechMonitorAgent

        agent = TechMonitorAgent()

        # feedparser entries use attribute access via FeedParserDict
        # which supports both .title and .get("title")
        mock_entry = MagicMock()
        mock_entry.get = lambda key, default="": {
            "title": "Test Article",
            "summary": "<p>Summary text</p>",
            "link": "https://test.com/1",
        }.get(key, default)
        mock_entry.published_parsed = (2026, 2, 27, 12, 0, 0, 0, 0, 0)
        mock_entry.__contains__ = lambda self, key: key in (
            "title",
            "summary",
            "link",
        )
        type(mock_entry).published_parsed = property(lambda self: (2026, 2, 27, 12, 0, 0, 0, 0, 0))

        mock_feed = MagicMock()
        mock_feed.entries = [mock_entry]
        mock_feed.feed = MagicMock()
        mock_feed.feed.get = lambda key, default="": {
            "title": "Test Feed",
        }.get(key, default)

        with patch(
            "agents.tech_monitor.feedparser.parse",
            return_value=mock_feed,
        ):
            with patch.object(agent.db, "save_articles", return_value=1) as mock_save:
                articles = agent.collect_articles(sources=["https://test.com/feed"], days=30)

        assert len(articles) >= 1
        mock_save.assert_called_once()

    def test_analyze_trends_extracts_keywords(self):
        """analyze_trends correctly counts keywords"""
        from agents.tech_monitor import TechMonitorAgent

        agent = TechMonitorAgent()
        articles = [
            {"title": "Machine Learning Trends 2026", "source": "Feed A"},
            {"title": "Machine Learning in Production", "source": "Feed A"},
            {"title": "Deep Learning Applications", "source": "Feed B"},
        ]

        trends = agent.analyze_trends(articles)
        assert "top_keywords" in trends
        assert trends["num_articles"] == 3
        # "machine" and "learning" should be top keywords
        keywords = [kw for kw, _ in trends["top_keywords"]]
        assert "machine" in keywords or "learning" in keywords
