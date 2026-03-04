"""
Tests pour agents/video_analysis_agent.py
"""
import os
from unittest.mock import MagicMock, patch

import pytest

os.environ.setdefault("GEMINI_API_KEY", "test-gemini-key")

from agents.video_analysis_agent import (
    GeminiVideoAnalyzer,
    UnsupportedFeatureError,
    UnsupportedVideoAnalyzer,
    VideoAnalysisInterface,
    get_video_analyzer,
)


class TestUnsupportedVideoAnalyzer:
    def test_supports_video_returns_false(self):
        analyzer = UnsupportedVideoAnalyzer()
        assert analyzer.supports_video() is False

    def test_analyze_video_raises_unsupported(self):
        analyzer = UnsupportedVideoAnalyzer(provider="claude")
        with pytest.raises(UnsupportedFeatureError) as exc_info:
            analyzer.analyze_video("some_video.mp4")
        assert "Gemini" in str(exc_info.value)

    def test_analyze_video_raises_with_settings_hint(self):
        analyzer = UnsupportedVideoAnalyzer(provider="openai")
        with pytest.raises(UnsupportedFeatureError) as exc_info:
            analyzer.analyze_video("meeting.webm")
        assert "/settings" in str(exc_info.value)

    def test_provider_stored(self):
        analyzer = UnsupportedVideoAnalyzer(provider="openai")
        assert analyzer.provider == "openai"

    def test_default_provider(self):
        analyzer = UnsupportedVideoAnalyzer()
        assert analyzer.provider == "unknown"

    def test_is_video_analysis_interface(self):
        assert isinstance(UnsupportedVideoAnalyzer(), VideoAnalysisInterface)


class TestGeminiVideoAnalyzer:
    def test_supports_video_returns_true(self):
        analyzer = GeminiVideoAnalyzer(api_key="test-key")
        assert analyzer.supports_video() is True

    def test_stores_api_key(self):
        analyzer = GeminiVideoAnalyzer(api_key="my-key")
        assert analyzer.api_key == "my-key"

    def test_default_model_from_env(self, monkeypatch):
        monkeypatch.setenv("GEMINI_MODEL", "gemini-2.5-flash")
        analyzer = GeminiVideoAnalyzer(api_key="key")
        assert analyzer.model_name == "gemini-2.5-flash"

    def test_custom_model(self):
        analyzer = GeminiVideoAnalyzer(api_key="key", model="gemini-3.1-flash")
        assert analyzer.model_name == "gemini-3.1-flash"

    def test_is_video_analysis_interface(self):
        assert isinstance(GeminiVideoAnalyzer(api_key="k"), VideoAnalysisInterface)

    def test_analyze_video_delegates_to_meeting_capture(self):
        mock_agent = MagicMock()
        mock_agent.upload_video.return_value = "uploaded_file"
        mock_agent.analyze.return_value = {"transcript": "Hello world"}

        # MeetingCaptureAgent is imported lazily inside analyze_video — patch the source
        with patch("agents.meeting_capture_agent.MeetingCaptureAgent", return_value=mock_agent):
            analyzer = GeminiVideoAnalyzer(api_key="key")
            result = analyzer.analyze_video("video.mp4")

        mock_agent.upload_video.assert_called_once_with("video.mp4")
        mock_agent.analyze.assert_called_once_with("uploaded_file")
        assert result == {"transcript": "Hello world"}

    def test_analyze_video_uses_custom_model(self):
        mock_agent = MagicMock()
        mock_agent.upload_video.return_value = "f"
        mock_agent.analyze.return_value = {}

        with patch("agents.meeting_capture_agent.MeetingCaptureAgent", return_value=mock_agent) as mock_class:
            analyzer = GeminiVideoAnalyzer(api_key="key", model="gemini-custom")
            analyzer.analyze_video("v.mp4", model="gemini-override")

        mock_class.assert_called_once_with(api_key="key", model="gemini-override")

    def test_analyze_video_uses_instance_model_when_no_override(self):
        mock_agent = MagicMock()
        mock_agent.upload_video.return_value = "f"
        mock_agent.analyze.return_value = {}

        with patch("agents.meeting_capture_agent.MeetingCaptureAgent", return_value=mock_agent) as mock_class:
            analyzer = GeminiVideoAnalyzer(api_key="key", model="gemini-instance")
            analyzer.analyze_video("v.mp4")

        mock_class.assert_called_once_with(api_key="key", model="gemini-instance")


class TestGetVideoAnalyzer:
    def test_returns_gemini_analyzer_for_gemini_provider(self, monkeypatch):
        monkeypatch.setenv("LLM_PROVIDER", "gemini")
        analyzer = get_video_analyzer(api_key="my-key", provider="gemini")
        assert isinstance(analyzer, GeminiVideoAnalyzer)

    def test_returns_unsupported_for_claude(self):
        analyzer = get_video_analyzer(provider="claude")
        assert isinstance(analyzer, UnsupportedVideoAnalyzer)

    def test_returns_unsupported_for_openai(self):
        analyzer = get_video_analyzer(provider="openai")
        assert isinstance(analyzer, UnsupportedVideoAnalyzer)

    def test_reads_provider_from_env_gemini(self, monkeypatch):
        monkeypatch.setenv("LLM_PROVIDER", "gemini")
        analyzer = get_video_analyzer(api_key="k")
        assert isinstance(analyzer, GeminiVideoAnalyzer)

    def test_reads_provider_from_env_claude(self, monkeypatch):
        monkeypatch.setenv("LLM_PROVIDER", "claude")
        analyzer = get_video_analyzer()
        assert isinstance(analyzer, UnsupportedVideoAnalyzer)

    def test_reads_api_key_from_env(self, monkeypatch):
        monkeypatch.setenv("GEMINI_API_KEY", "env-key")
        monkeypatch.setenv("LLM_PROVIDER", "gemini")
        analyzer = get_video_analyzer(provider="gemini")
        assert isinstance(analyzer, GeminiVideoAnalyzer)
        assert analyzer.api_key == "env-key"

    def test_explicit_api_key_takes_priority(self, monkeypatch):
        monkeypatch.setenv("GEMINI_API_KEY", "env-key")
        analyzer = get_video_analyzer(api_key="explicit-key", provider="gemini")
        assert analyzer.api_key == "explicit-key"

    def test_unsupported_analyzer_stores_provider(self):
        analyzer = get_video_analyzer(provider="openai")
        assert isinstance(analyzer, UnsupportedVideoAnalyzer)
        assert analyzer.provider == "openai"

    def test_gemini_supports_video(self):
        analyzer = get_video_analyzer(provider="gemini", api_key="k")
        assert analyzer.supports_video() is True

    def test_unsupported_does_not_support_video(self):
        analyzer = get_video_analyzer(provider="claude")
        assert analyzer.supports_video() is False


class TestVideoAnalysisInterface:
    def test_base_supports_video_returns_false(self):
        """La méthode de base VideoAnalysisInterface.supports_video() retourne False."""
        assert VideoAnalysisInterface.supports_video() is False


class TestUnsupportedFeatureError:
    def test_is_exception(self):
        err = UnsupportedFeatureError("test message")
        assert isinstance(err, Exception)
        assert str(err) == "test message"

    def test_can_be_raised_and_caught(self):
        with pytest.raises(UnsupportedFeatureError):
            raise UnsupportedFeatureError("video not supported")
