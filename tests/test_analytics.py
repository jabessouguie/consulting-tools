"""Tests for routers/analytics.py — Analytics dashboard and API endpoints."""
import sqlite3
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app import app


@pytest.fixture
def mock_obs_service():
    """Mock ObservabilityService to avoid real DB I/O."""
    stats = {
        "system": {"avg_latency": 42.5, "total_requests": 100, "error_rate": 2.0},
        "ai": {"total_tokens": 5000, "total_cost_usd": 0.0025, "avg_llm_latency": 800.0},
        "product": {
            "active_users_30d": 3,
            "top_features": [{"event_name": "proposal", "count": 20}],
        },
    }
    with patch("routers.analytics.obs_service") as mock:
        mock.get_stats_summary.return_value = stats
        yield mock


@pytest.fixture
def no_db(tmp_path):
    """Patch DB_PATH to a non-existent path so empty-DB branches are hit."""
    with patch("routers.analytics.DB_PATH", tmp_path / "nonexistent.db"):
        yield


# ── Page route ────────────────────────────────────────────────────────────────

class TestAnalyticsPage:
    async def test_analytics_page_ok(self):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/analytics")
        assert resp.status_code == 200
        assert "Analytics" in resp.text

    async def test_analytics_page_html_content(self):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/analytics")
        # KPI cards present
        assert "val-requests" in resp.text
        assert "val-tokens" in resp.text
        assert "val-cost" in resp.text


# ── /api/analytics/stats ──────────────────────────────────────────────────────

class TestAnalyticsStats:
    async def test_stats_returns_200(self, mock_obs_service):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/api/analytics/stats")
        assert resp.status_code == 200

    async def test_stats_structure(self, mock_obs_service):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/api/analytics/stats")
        data = resp.json()
        assert "system" in data
        assert "ai" in data
        assert "product" in data
        assert data["system"]["total_requests"] == 100
        assert data["ai"]["total_tokens"] == 5000
        assert data["product"]["active_users_30d"] == 3

    async def test_stats_error_returns_500(self):
        with patch("routers.analytics.obs_service") as mock:
            mock.get_stats_summary.side_effect = Exception("DB error")
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                resp = await client.get("/api/analytics/stats")
        assert resp.status_code == 500
        assert "error" in resp.json()


# ── /api/analytics/llm ────────────────────────────────────────────────────────

class TestAnalyticsLLM:
    async def test_llm_no_db_returns_empty(self, no_db):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/api/analytics/llm")
        assert resp.status_code == 200
        data = resp.json()
        assert data == {"by_feature": [], "by_model": [], "recent": []}

    async def test_llm_with_data(self, tmp_path):
        db = tmp_path / "obs.db"
        with sqlite3.connect(db) as conn:
            conn.execute("""CREATE TABLE llm_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                provider TEXT, model TEXT, feature TEXT,
                prompt_tokens INTEGER, completion_tokens INTEGER,
                total_tokens INTEGER, cost_usd REAL, latency_ms REAL,
                status TEXT, user_id TEXT)""")
            conn.execute(
                "INSERT INTO llm_logs (provider,model,feature,prompt_tokens,completion_tokens,total_tokens,cost_usd,latency_ms,status,user_id) VALUES (?,?,?,?,?,?,?,?,?,?)",
                ("anthropic", "claude-sonnet-4-6", "proposal", 100, 200, 300, 0.0045, 1200, "success", "admin"),
            )

        with patch("routers.analytics.DB_PATH", db):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                resp = await client.get("/api/analytics/llm")

        assert resp.status_code == 200
        data = resp.json()
        assert len(data["by_feature"]) == 1
        assert data["by_feature"][0]["feature"] == "proposal"
        assert len(data["by_model"]) == 1
        assert data["by_model"][0]["model"] == "claude-sonnet-4-6"
        assert len(data["recent"]) == 1
        assert data["recent"][0]["status"] == "success"


# ── /api/analytics/requests ───────────────────────────────────────────────────

class TestAnalyticsRequests:
    async def test_requests_no_db_returns_empty(self, no_db):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/api/analytics/requests")
        assert resp.status_code == 200
        data = resp.json()
        assert data == {"top_endpoints": [], "daily": []}

    async def test_requests_with_data(self, tmp_path):
        db = tmp_path / "obs.db"
        with sqlite3.connect(db) as conn:
            conn.execute("""CREATE TABLE http_metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                method TEXT, endpoint TEXT, status_code INTEGER,
                duration_ms REAL, user_id TEXT, ip_address TEXT)""")
            for _ in range(5):
                conn.execute(
                    "INSERT INTO http_metrics (method,endpoint,status_code,duration_ms,user_id,ip_address) VALUES (?,?,?,?,?,?)",
                    ("GET", "/analytics", 200, 45.0, "admin", "127.0.0.1"),
                )
            conn.execute(
                "INSERT INTO http_metrics (method,endpoint,status_code,duration_ms,user_id,ip_address) VALUES (?,?,?,?,?,?)",
                ("POST", "/api/proposal/generate", 200, 3200.0, "admin", "127.0.0.1"),
            )

        with patch("routers.analytics.DB_PATH", db):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                resp = await client.get("/api/analytics/requests")

        assert resp.status_code == 200
        data = resp.json()
        endpoints = data["top_endpoints"]
        assert len(endpoints) == 2
        # /analytics hit 5 times, should be first
        assert endpoints[0]["endpoint"] == "/analytics"
        assert endpoints[0]["hits"] == 5
        assert len(data["daily"]) >= 1
