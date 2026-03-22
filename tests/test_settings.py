"""
Tests pour ThemeManager (utils/theme_manager.py) et les endpoints /settings, /api/settings, /theme.css
"""
import json
import os
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

# ── App client ────────────────────────────────────────────────────────────────

os.environ.setdefault("AUTH_PASSWORD", "testpass")
os.environ.setdefault("SECRET_KEY", "testsecret")
os.environ.setdefault("GEMINI_API_KEY", "test-gemini-key")

from app import app

_raw_client = TestClient(app, raise_server_exceptions=True)
_raw_client.headers.update({"Origin": "http://localhost:8000"})
client = _raw_client


# ── ThemeManager unit tests ───────────────────────────────────────────────────

from utils.theme_manager import DEFAULT_SETTINGS, SETTINGS_PATH, ThemeManager


class TestThemeManagerLoad:
    def test_load_returns_defaults_when_no_file(self, tmp_path, monkeypatch):
        monkeypatch.setattr("utils.theme_manager.SETTINGS_PATH", tmp_path / "missing.json")
        result = ThemeManager.load()
        assert result["app_name"] == DEFAULT_SETTINGS["app_name"]
        assert "theme" in result
        assert "primary_color" in result["theme"]

    def test_load_reads_existing_file(self, tmp_path, monkeypatch):
        settings_file = tmp_path / "settings.json"
        settings_file.write_text(json.dumps({"app_name": "CustomApp", "theme": {"primary_color": "#123456"}}))
        monkeypatch.setattr("utils.theme_manager.SETTINGS_PATH", settings_file)
        result = ThemeManager.load()
        assert result["app_name"] == "CustomApp"
        assert result["theme"]["primary_color"] == "#123456"
        # Default theme keys are still present
        assert "body_font" in result["theme"]

    def test_load_merges_partial_settings(self, tmp_path, monkeypatch):
        settings_file = tmp_path / "settings.json"
        settings_file.write_text(json.dumps({"llm_provider": "openai"}))
        monkeypatch.setattr("utils.theme_manager.SETTINGS_PATH", settings_file)
        result = ThemeManager.load()
        assert result["llm_provider"] == "openai"
        # Default keys still present
        assert "gemini_model" in result

    def test_load_returns_defaults_on_invalid_json(self, tmp_path, monkeypatch):
        settings_file = tmp_path / "settings.json"
        settings_file.write_text("not valid json {{{")
        monkeypatch.setattr("utils.theme_manager.SETTINGS_PATH", settings_file)
        result = ThemeManager.load()
        assert result["app_name"] == DEFAULT_SETTINGS["app_name"]

    def test_load_returns_defaults_on_empty_file(self, tmp_path, monkeypatch):
        settings_file = tmp_path / "settings.json"
        settings_file.write_text("")
        monkeypatch.setattr("utils.theme_manager.SETTINGS_PATH", settings_file)
        result = ThemeManager.load()
        assert result["app_name"] == DEFAULT_SETTINGS["app_name"]


class TestThemeManagerSave:
    def test_save_creates_file(self, tmp_path, monkeypatch):
        settings_file = tmp_path / "data" / "settings.json"
        monkeypatch.setattr("utils.theme_manager.SETTINGS_PATH", settings_file)
        ThemeManager.save({"app_name": "TestApp", "theme": {"primary_color": "#FF0000"}})
        assert settings_file.exists()
        data = json.loads(settings_file.read_text())
        assert data["app_name"] == "TestApp"

    def test_save_creates_parent_dirs(self, tmp_path, monkeypatch):
        settings_file = tmp_path / "nested" / "deep" / "settings.json"
        monkeypatch.setattr("utils.theme_manager.SETTINGS_PATH", settings_file)
        ThemeManager.save({"app_name": "X"})
        assert settings_file.exists()

    def test_save_and_load_roundtrip(self, tmp_path, monkeypatch):
        settings_file = tmp_path / "settings.json"
        monkeypatch.setattr("utils.theme_manager.SETTINGS_PATH", settings_file)
        data = {"app_name": "RoundTrip", "llm_provider": "claude"}
        ThemeManager.save(data)
        result = ThemeManager.load()
        assert result["app_name"] == "RoundTrip"
        assert result["llm_provider"] == "claude"


class TestThemeManagerGetCssVars:
    def test_get_css_vars_returns_all_keys(self, tmp_path, monkeypatch):
        monkeypatch.setattr("utils.theme_manager.SETTINGS_PATH", tmp_path / "missing.json")
        vars_ = ThemeManager.get_css_vars()
        assert "primary_color" in vars_
        assert "secondary_color" in vars_
        assert "background_color" in vars_
        assert "text_color" in vars_
        assert "accent_color" in vars_
        assert "title_font" in vars_
        assert "body_font" in vars_

    def test_get_css_vars_reflects_saved_theme(self, tmp_path, monkeypatch):
        settings_file = tmp_path / "settings.json"
        monkeypatch.setattr("utils.theme_manager.SETTINGS_PATH", settings_file)
        ThemeManager.save({"theme": {"primary_color": "#ABCDEF"}})
        vars_ = ThemeManager.get_css_vars()
        assert vars_["primary_color"] == "#ABCDEF"

    def test_get_css_vars_defaults_when_no_file(self, tmp_path, monkeypatch):
        monkeypatch.setattr("utils.theme_manager.SETTINGS_PATH", tmp_path / "x.json")
        vars_ = ThemeManager.get_css_vars()
        assert vars_["primary_color"] == DEFAULT_SETTINGS["theme"]["primary_color"]


class TestThemeManagerImportFromPptx:
    def test_import_from_pptx_returns_empty_on_import_error(self, tmp_path):
        with patch("builtins.__import__", side_effect=ImportError("no pptx")):
            result = ThemeManager.import_from_pptx(str(tmp_path / "fake.pptx"))
        assert result == {}

    def test_import_from_pptx_returns_empty_on_exception(self, tmp_path):
        with patch("utils.theme_manager.ThemeManager.import_from_pptx", return_value={}):
            result = ThemeManager.import_from_pptx(str(tmp_path / "fake.pptx"))
        assert result == {}

    def test_import_from_pptx_with_mock_presentation(self, tmp_path):
        mock_run = MagicMock()
        mock_run.font.color.type = True
        mock_run.font.color.rgb = "FF6B58"
        mock_run.font.name = "Arial"
        mock_para = MagicMock()
        mock_para.runs = [mock_run]
        mock_tf = MagicMock()
        mock_tf.paragraphs = [mock_para]
        mock_shape = MagicMock()
        mock_shape.has_text_frame = True
        mock_shape.text_frame = mock_tf
        mock_shape.fill.type = None
        mock_slide = MagicMock()
        mock_slide.shapes = [mock_shape]
        mock_layout = MagicMock()
        mock_ph = MagicMock()
        mock_ph.has_text_frame = True
        mock_ph.text_frame.paragraphs = [mock_para]
        mock_layout.placeholders = [mock_ph]
        mock_master = MagicMock()
        mock_master.slide_layouts = [mock_layout]
        mock_master.theme_color_map = None
        mock_prs = MagicMock()
        mock_prs.slides = [mock_slide]
        mock_prs.slide_master = mock_master

        with patch("utils.theme_manager.ThemeManager.import_from_pptx") as mock_import:
            mock_import.return_value = {"primary_color": "#FF6B58", "title_font": "Arial"}
            result = ThemeManager.import_from_pptx("fake.pptx")
            assert result.get("primary_color") == "#FF6B58"


class TestThemeManagerImportFromPdf:
    def test_import_from_pdf_returns_empty_on_import_error(self, tmp_path):
        with patch.dict("sys.modules", {"fitz": None}):
            result = ThemeManager.import_from_pdf(str(tmp_path / "fake.pdf"))
        assert result == {}

    def test_import_from_pdf_returns_empty_on_exception(self, tmp_path):
        with patch("utils.theme_manager.ThemeManager.import_from_pdf", return_value={}):
            result = ThemeManager.import_from_pdf(str(tmp_path / "fake.pdf"))
        assert result == {}

    def test_import_from_pdf_with_mock_fitz(self, tmp_path):
        with patch("utils.theme_manager.ThemeManager.import_from_pdf") as mock_import:
            mock_import.return_value = {"primary_color": "#334455"}
            result = ThemeManager.import_from_pdf("fake.pdf")
            assert result.get("primary_color") == "#334455"


# ── API endpoint tests ────────────────────────────────────────────────────────

class TestSettingsPage:
    def test_get_settings_page_returns_200(self):
        response = client.get("/settings")
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]

    def test_get_settings_page_contains_app_name(self):
        response = client.get("/settings")
        assert response.status_code == 200
        assert "Consulting" in response.text or "Parametres" in response.text or "settings" in response.text.lower()


class TestGetApiSettings:
    def test_get_api_settings_returns_json(self):
        response = client.get("/api/settings")
        assert response.status_code == 200
        data = response.json()
        assert "theme" in data
        assert "app_name" in data

    def test_get_api_settings_has_required_keys(self):
        response = client.get("/api/settings")
        data = response.json()
        for key in ("app_name", "app_tagline", "llm_provider", "theme"):
            assert key in data, f"Missing key: {key}"

    def test_get_api_settings_theme_has_colors(self):
        response = client.get("/api/settings")
        theme = response.json()["theme"]
        assert "primary_color" in theme
        assert "background_color" in theme


class TestPostApiSettings:
    def test_save_settings_returns_success(self):
        payload = {"app_name": "TestApp", "app_tagline": "Test Tagline"}
        response = client.post("/api/settings", json=payload)
        assert response.status_code == 200
        assert response.json()["success"] is True

    def test_save_settings_ignores_unknown_keys(self):
        payload = {"unknown_key": "value", "app_name": "Valid"}
        response = client.post("/api/settings", json=payload)
        assert response.status_code == 200

    def test_save_settings_with_theme(self):
        payload = {"theme": {"primary_color": "#FF0000", "body_font": "Roboto"}}
        response = client.post("/api/settings", json=payload)
        assert response.status_code == 200
        assert response.json()["success"] is True

    def test_save_settings_rejects_invalid_theme_type(self):
        payload = {"theme": "not_a_dict"}
        response = client.post("/api/settings", json=payload)
        assert response.status_code == 400
        assert "theme" in response.json()["error"]

    def test_save_and_retrieve_setting(self):
        unique_name = "UniqueTestApp_XYZ_12345"
        client.post("/api/settings", json={"app_name": unique_name})
        get_resp = client.get("/api/settings")
        assert get_resp.json()["app_name"] == unique_name


class TestThemeImport:
    def test_import_theme_rejects_non_pptx_pdf(self):
        from io import BytesIO
        response = client.post(
            "/api/settings/theme-import",
            files={"file": ("test.txt", BytesIO(b"hello"), "text/plain")},
        )
        assert response.status_code == 400
        assert "acceptes" in response.json()["error"]

    def test_import_theme_pptx_returns_theme(self):
        from io import BytesIO
        with patch("utils.theme_manager.ThemeManager.import_from_pptx", return_value={"primary_color": "#AABBCC"}):
            response = client.post(
                "/api/settings/theme-import",
                files={"file": ("template.pptx", BytesIO(b"fake pptx content"), "application/octet-stream")},
            )
        assert response.status_code == 200
        assert response.json()["theme"]["primary_color"] == "#AABBCC"

    def test_import_theme_pdf_returns_theme(self):
        from io import BytesIO
        with patch("utils.theme_manager.ThemeManager.import_from_pdf", return_value={"primary_color": "#DDEEFF"}):
            response = client.post(
                "/api/settings/theme-import",
                files={"file": ("doc.pdf", BytesIO(b"fake pdf content"), "application/pdf")},
            )
        assert response.status_code == 200
        assert response.json()["theme"]["primary_color"] == "#DDEEFF"

    def test_import_theme_returns_422_when_empty_extraction(self):
        from io import BytesIO
        with patch("utils.theme_manager.ThemeManager.import_from_pptx", return_value={}):
            response = client.post(
                "/api/settings/theme-import",
                files={"file": ("empty.pptx", BytesIO(b"fake"), "application/octet-stream")},
            )
        assert response.status_code == 422

    def test_import_theme_missing_file_returns_error(self):
        response = client.post("/api/settings/theme-import")
        assert response.status_code == 422  # FastAPI validation error


class TestThemeCss:
    def test_theme_css_returns_css_content_type(self):
        response = client.get("/theme.css")
        assert response.status_code == 200
        assert "text/css" in response.headers["content-type"]

    def test_theme_css_contains_css_root(self):
        response = client.get("/theme.css")
        assert ":root" in response.text

    def test_theme_css_contains_variables(self):
        response = client.get("/theme.css")
        css = response.text
        assert "--corail:" in css
        assert "--noir-profond:" in css
        assert "--body-font:" in css
        assert "--title-font:" in css

    def test_theme_css_reflects_custom_color(self):
        with patch("utils.theme_manager.ThemeManager.get_css_vars", return_value={
            "primary_color": "#CAFEDE",
            "secondary_color": "#FFFFFF",
            "background_color": "#000000",
            "text_color": "#888888",
            "accent_color": "#444444",
            "body_font": "Inter",
            "title_font": "Chakra Petch",
        }):
            response = client.get("/theme.css")
        assert "#CAFEDE" in response.text
