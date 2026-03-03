import os
import unittest
from unittest.mock import MagicMock, patch

from utils.llm_client import LLMClient


class TestLLMClientAgnostic(unittest.TestCase):
    def setUp(self):
        # Reset environment
        if "LLM_PROVIDER" in os.environ:
            del os.environ["LLM_PROVIDER"]
        if "USE_GEMINI" in os.environ:
            del os.environ["USE_GEMINI"]

    @patch("utils.llm_client.Anthropic")
    def test_init_claude(self, mock_anthropic):
        client = LLMClient(api_key="test-key", provider="claude")
        self.assertEqual(client.provider, "claude")
        mock_anthropic.assert_called_once_with(api_key="test-key")

    @patch("utils.llm_client.genai.configure")
    def test_init_gemini(self, mock_configure):
        client = LLMClient(api_key="test-key", provider="gemini")
        self.assertEqual(client.provider, "gemini")
        mock_configure.assert_called_once_with(api_key="test-key")

    @patch("utils.llm_client.OpenAI")
    def test_init_openai(self, mock_openai):
        client = LLMClient(api_key="test-key", provider="openai")
        self.assertEqual(client.provider, "openai")
        mock_openai.assert_called_once_with(api_key="test-key")

    @patch("utils.llm_client.OpenAI")
    def test_generate_openai(self, mock_openai_class):
        mock_openai_instance = MagicMock()
        mock_openai_class.return_value = mock_openai_instance

        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "OpenAI response"
        mock_openai_instance.chat.completions.create.return_value = mock_response

        client = LLMClient(api_key="test-key", provider="openai")
        response = client.generate("Hello")

        self.assertEqual(response, "OpenAI response")
        mock_openai_instance.chat.completions.create.assert_called_once()

    @patch("utils.llm_client.OpenAI")
    @patch("utils.llm_client.genai.configure")
    def test_env_provider_selection(self, mock_genai, mock_openai):
        with patch.dict(os.environ, {"LLM_PROVIDER": "openai", "OPENAI_API_KEY": "test-key"}):
            client = LLMClient()
            self.assertEqual(client.provider, "openai")

        with patch.dict(os.environ, {"LLM_PROVIDER": "gemini", "GEMINI_API_KEY": "test-key"}):
            client = LLMClient()
            self.assertEqual(client.provider, "gemini")


if __name__ == "__main__":
    unittest.main()
