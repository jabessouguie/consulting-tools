"""
Tests unitaires pour LLMClient
"""

import os
import sys
from unittest.mock import patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.llm_client import LLMClient  # noqa: E402


class TestLLMClient:
    """Tests pour LLMClient"""

    def test_init_with_claude_key(self):
        """Test initialisation avec clé Claude"""
        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"}):  # pragma: allowlist secret
            client = LLMClient(provider="claude")
            assert client.provider == "claude"
            assert client.api_key == "test-key"
            assert client.model == "claude-opus-4-6"

    def test_init_with_gemini_key(self):
        """Test initialisation avec clé Gemini"""
        with patch.dict(
            os.environ, {"GEMINI_API_KEY": "test-gemini-key"}
        ):  # pragma: allowlist secret
            client = LLMClient(provider="gemini")
            assert client.provider == "gemini"
            assert client.api_key == "test-gemini-key"

    def test_init_defaults_to_claude(self):
        """Test que le provider par défaut est claude"""
        with patch.dict(
            os.environ,
            {"ANTHROPIC_API_KEY": "test-key", "USE_GEMINI": "false"},
            clear=True,  # pragma: allowlist secret
        ):
            client = LLMClient()
            assert client.provider == "claude"

    def test_init_with_max_tokens(self):
        """Test initialisation avec max_tokens personnalisé"""
        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"}):  # pragma: allowlist secret
            client = LLMClient(provider="claude", max_tokens=2000)
            assert client.max_tokens == 2000

    def test_init_with_custom_model(self):
        """Test initialisation avec modèle personnalisé"""
        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"}):  # pragma: allowlist secret
            client = LLMClient(provider="claude", model="claude-3-opus-20240229")
            assert client.model == "claude-3-opus-20240229"

    def test_provider_detection_from_env(self):
        """Test détection automatique du provider depuis l'environnement"""
        with patch.dict(os.environ, {"USE_GEMINI": "true", "GEMINI_API_KEY": "test-key"}):
            client = LLMClient()
            assert client.provider == "gemini"

    def test_missing_api_key_uses_none(self):
        """Test que l'absence de clé API définit api_key à None"""
        with patch.dict(os.environ, {}, clear=True):
            client = LLMClient(provider="claude")
            assert client.api_key is None

    def test_default_max_tokens(self):
        """Test que max_tokens par défaut est 4096"""
        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"}):  # pragma: allowlist secret
            client = LLMClient()
            assert client.max_tokens == 4096

    def test_custom_api_key_parameter(self):
        """Test fourniture de clé API via paramètre"""
        client = LLMClient(api_key="custom-key", provider="claude")
        assert client.api_key == "custom-key"

    def test_claude_client_created(self):
        """Test que le client Anthropic est créé pour Claude"""
        with patch.dict(
            os.environ,
            {"ANTHROPIC_API_KEY": "test-key", "USE_GEMINI": "false"},
            clear=True,  # pragma: allowlist secret
        ):
            client = LLMClient(provider="claude")
            assert client.client is not None
            assert client.provider == "claude"
