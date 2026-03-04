"""
Tests pour config/consultant.py — ConsultantConfig singleton et get_consultant_info()
Phase 5 - Coverage improvement
"""
import os
from unittest.mock import patch

import pytest

os.environ.setdefault("AUTH_PASSWORD", "testpass")
os.environ.setdefault("SECRET_KEY", "testsecret")
os.environ.setdefault("GEMINI_API_KEY", "test-gemini-key")
os.environ.setdefault("ANTHROPIC_API_KEY", "test-anthropic-key")
os.environ.setdefault("CONSULTANT_NAME", "Test Consultant")
os.environ.setdefault("CONSULTANT_TITLE", "Senior Consultant")
os.environ.setdefault("COMPANY_NAME", "TestCo")


@pytest.fixture(autouse=True)
def reset_config():
    from config.consultant import ConsultantConfig
    ConsultantConfig.reset()
    ConsultantConfig._instance = None
    yield
    ConsultantConfig.reset()
    ConsultantConfig._instance = None


class TestConsultantConfigSingleton:
    def test_new_returns_instance(self):
        from config.consultant import ConsultantConfig
        instance = ConsultantConfig()
        assert isinstance(instance, ConsultantConfig)

    def test_new_returns_same_instance_on_second_call(self):
        from config.consultant import ConsultantConfig
        inst1 = ConsultantConfig()
        inst2 = ConsultantConfig()
        assert inst1 is inst2

    def test_get_returns_dict(self):
        from config.consultant import ConsultantConfig
        result = ConsultantConfig.get()
        assert isinstance(result, dict)

    def test_get_caches_result(self):
        from config.consultant import ConsultantConfig
        result1 = ConsultantConfig.get()
        result2 = ConsultantConfig.get()
        assert result1 is result2

    def test_reset_clears_cache(self):
        from config.consultant import ConsultantConfig
        ConsultantConfig.get()
        assert ConsultantConfig._config is not None
        ConsultantConfig.reset()
        assert ConsultantConfig._config is None

    def test_get_after_reset_reloads(self):
        from config.consultant import ConsultantConfig
        ConsultantConfig.get()
        ConsultantConfig.reset()
        result = ConsultantConfig.get()
        assert isinstance(result, dict)


class TestConsultantConfigValues:
    def test_name_from_env(self):
        from config.consultant import ConsultantConfig
        with patch.dict(os.environ, {"CONSULTANT_NAME": "Jean Dupont"}, clear=False):
            ConsultantConfig.reset()
            result = ConsultantConfig.get()
        assert result["name"] == "Jean Dupont"

    def test_title_from_env(self):
        from config.consultant import ConsultantConfig
        with patch.dict(os.environ, {"CONSULTANT_NAME": "X", "CONSULTANT_TITLE": "Data Expert"}, clear=False):
            ConsultantConfig.reset()
            result = ConsultantConfig.get()
        assert result["title"] == "Data Expert"

    def test_company_from_env(self):
        from config.consultant import ConsultantConfig
        with patch.dict(os.environ, {"CONSULTANT_NAME": "X", "COMPANY_NAME": "Accenture"}, clear=False):
            ConsultantConfig.reset()
            result = ConsultantConfig.get()
        assert result["company"] == "Accenture"

    def test_app_name_from_env(self):
        from config.consultant import ConsultantConfig
        with patch.dict(os.environ, {"CONSULTANT_NAME": "X", "APP_NAME": "MyApp"}, clear=False):
            ConsultantConfig.reset()
            result = ConsultantConfig.get()
        assert result["app_name"] == "MyApp"

    def test_app_name_default(self):
        from config.consultant import ConsultantConfig
        env = {k: v for k, v in os.environ.items() if k != "APP_NAME"}
        env["CONSULTANT_NAME"] = "X"
        with patch.dict(os.environ, env, clear=True):
            ConsultantConfig.reset()
            result = ConsultantConfig.get()
        assert result["app_name"] == "Consulting Tools"

    def test_raises_value_error_when_no_name(self):
        from config.consultant import ConsultantConfig
        env = {k: v for k, v in os.environ.items() if k != "CONSULTANT_NAME"}
        # Patch load_dotenv at the dotenv module level so it doesn't re-read .env
        with patch("dotenv.load_dotenv"):
            with patch.dict(os.environ, env, clear=True):
                ConsultantConfig.reset()
                with pytest.raises(ValueError, match="CONSULTANT_NAME"):
                    ConsultantConfig.get()

    def test_has_all_required_keys(self):
        from config.consultant import ConsultantConfig
        result = ConsultantConfig.get()
        for key in ("name", "email", "title", "company", "app_name", "app_tagline", "profile", "linkedin_email"):
            assert key in result


class TestGetConsultantInfo:
    def test_returns_dict(self):
        from config.consultant import get_consultant_info
        result = get_consultant_info()
        assert isinstance(result, dict)

    def test_returns_name(self):
        from config.consultant import get_consultant_info
        result = get_consultant_info()
        assert "name" in result
        assert result["name"] == "Test Consultant"
