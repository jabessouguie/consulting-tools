"""Tests for the Bug Report system"""

import json
import os
import sys
from unittest.mock import patch

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestBugReportAPI:
    """Tests for the /api/bug-report endpoint"""

    @pytest.fixture
    def client(self):
        """Create test client with auth bypassed and CSRF origin set"""
        with patch.dict(os.environ, {"AUTH_PASSWORD": ""}):
            from fastapi.testclient import TestClient

            from app import app

            c = TestClient(app)
            c.headers.update({"Origin": "http://localhost:8000"})
            return c

    @pytest.fixture
    def bug_reports_file(self, tmp_path):
        """Use a temp file for bug reports"""
        import app as app_module

        original = app_module.BUG_REPORTS_FILE
        app_module.BUG_REPORTS_FILE = tmp_path / "bug_reports.json"
        yield app_module.BUG_REPORTS_FILE
        app_module.BUG_REPORTS_FILE = original

    def test_submit_bug_report(self, client, bug_reports_file):
        """Test POST /api/bug-report with valid data"""
        with patch("utils.llm_client.LLMClient") as mock_llm_cls:
            mock_llm = mock_llm_cls.return_value
            mock_llm.generate_with_context.return_value = "Bouton ne fonctionne pas"

            resp = client.post(
                "/api/bug-report",
                json={
                    "description": "Le bouton Generer ne repond pas au clic",
                    "severity": "high",
                    "page_url": "/slide-editor",
                    "user_agent": "TestAgent/1.0",
                },
            )

        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert "id" in data
        assert "title" in data

        # Verify file was written
        reports = json.loads(bug_reports_file.read_text())
        assert len(reports) == 1
        assert reports[0]["description"] == "Le bouton Generer ne repond pas au clic"
        assert reports[0]["severity"] == "high"

    def test_submit_bug_report_empty_description(self, client, bug_reports_file):
        """Test POST /api/bug-report with empty description returns 400"""
        resp = client.post("/api/bug-report", json={"description": "", "severity": "low"})
        assert resp.status_code == 400
        assert "description" in resp.json()["error"].lower()

    def test_submit_bug_report_missing_description(self, client, bug_reports_file):
        """Test POST /api/bug-report with no description returns 400"""
        resp = client.post("/api/bug-report", json={"severity": "medium"})
        assert resp.status_code == 400

    def test_submit_bug_report_invalid_severity_defaults(self, client, bug_reports_file):
        """Test that invalid severity defaults to medium"""
        with patch("utils.llm_client.LLMClient") as mock_llm_cls:
            mock_llm = mock_llm_cls.return_value
            mock_llm.generate_with_context.return_value = "Bug titre"

            resp = client.post(
                "/api/bug-report", json={"description": "Un probleme", "severity": "unknown_level"}
            )

        assert resp.status_code == 200
        reports = json.loads(bug_reports_file.read_text())
        assert reports[0]["severity"] == "medium"

    def test_submit_multiple_bug_reports(self, client, bug_reports_file):
        """Test that multiple reports are appended"""
        with patch("utils.llm_client.LLMClient") as mock_llm_cls:
            mock_llm = mock_llm_cls.return_value
            mock_llm.generate_with_context.return_value = "Bug"

            client.post("/api/bug-report", json={"description": "Bug 1"})
            client.post("/api/bug-report", json={"description": "Bug 2"})

        reports = json.loads(bug_reports_file.read_text())
        assert len(reports) == 2

    def test_bug_report_llm_failure_uses_fallback_title(self, client, bug_reports_file):
        """Test that LLM failure falls back to description truncation"""
        with patch("utils.llm_client.LLMClient") as mock_llm_cls:
            mock_llm_cls.side_effect = Exception("LLM down")

            resp = client.post(
                "/api/bug-report", json={"description": "Le bouton export PDF ne marche plus"}
            )

        assert resp.status_code == 200
        data = resp.json()
        assert "title" in data
        assert len(data["title"]) <= 80


class TestBugReportTemplate:
    """Tests for bug report UI elements in base.html"""

    def _read_template(self):
        template_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "templates", "base.html"
        )
        with open(template_path, "r", encoding="utf-8") as f:
            return f.read()

    def test_bug_report_button_exists(self):
        """Test that bug report button is in the footer"""
        content = self._read_template()
        assert "openBugReportModal()" in content
        assert "Signaler un bug" in content

    def test_bug_report_modal_exists(self):
        """Test that bug report modal HTML exists"""
        content = self._read_template()
        assert 'id="bug-report-overlay"' in content
        assert 'id="bug-description"' in content
        assert 'id="bug-severity"' in content
        assert 'id="bug-screenshot"' in content

    def test_bug_report_severity_options(self):
        """Test that severity options exist"""
        content = self._read_template()
        assert 'value="low"' in content
        assert 'value="medium"' in content
        assert 'value="high"' in content
        assert 'value="critical"' in content


class TestBugReportJS:
    """Tests for bug report JS functions in ui-enhancements.js"""

    def _read_js(self):
        js_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "static",
            "ui-enhancements.js",
        )
        with open(js_path, "r", encoding="utf-8") as f:
            return f.read()

    def test_js_has_bug_report_functions(self):
        """Test that JS bug report functions are defined"""
        content = self._read_js()
        assert "function openBugReportModal()" in content
        assert "function closeBugReportModal()" in content
        assert "function submitBugReport()" in content

    def test_js_exports_bug_report_functions(self):
        """Test that bug report functions are exported globally"""
        content = self._read_js()
        assert "window.openBugReportModal" in content
        assert "window.closeBugReportModal" in content
        assert "window.submitBugReport" in content
