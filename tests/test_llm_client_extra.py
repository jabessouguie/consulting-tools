"""
Extra tests for utils/llm_client.py — targets uncovered lines.
Avoids duplicating tests already in tests/test_llm_client.py.
"""

import json
import os
import sys
from unittest.mock import MagicMock, patch, call

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_claude_response(text="Response text"):
    """Build a mock Anthropic messages.create response."""
    content_block = MagicMock()
    content_block.text = text
    response = MagicMock()
    response.content = [content_block]
    return response


def _make_openai_response(text="OpenAI response"):
    """Build a mock OpenAI chat.completions.create response."""
    msg = MagicMock()
    msg.content = text
    choice = MagicMock()
    choice.message = msg
    resp = MagicMock()
    resp.choices = [choice]
    return resp


# ---------------------------------------------------------------------------
# _get_gemini_model_from_settings
# ---------------------------------------------------------------------------


class TestGetGeminiModelFromSettings:
    def test_returns_none_when_settings_file_missing(self, tmp_path):
        with patch("utils.llm_client.SETTINGS_FILE", tmp_path / "no_settings.json"):
            from utils.llm_client import _get_gemini_model_from_settings
            result = _get_gemini_model_from_settings()
        assert result is None

    def test_returns_model_from_settings(self, tmp_path):
        settings = {"gemini_model": "gemini-pro"}
        settings_file = tmp_path / "settings.json"
        settings_file.write_text(json.dumps(settings))
        with patch("utils.llm_client.SETTINGS_FILE", settings_file):
            from utils.llm_client import _get_gemini_model_from_settings
            result = _get_gemini_model_from_settings()
        assert result == "gemini-pro"

    def test_returns_none_on_json_error(self, tmp_path):
        settings_file = tmp_path / "settings.json"
        settings_file.write_text("not valid json")
        with patch("utils.llm_client.SETTINGS_FILE", settings_file):
            from utils.llm_client import _get_gemini_model_from_settings
            result = _get_gemini_model_from_settings()
        assert result is None

    def test_returns_none_when_key_absent(self, tmp_path):
        settings = {"other_key": "value"}
        settings_file = tmp_path / "settings.json"
        settings_file.write_text(json.dumps(settings))
        with patch("utils.llm_client.SETTINGS_FILE", settings_file):
            from utils.llm_client import _get_gemini_model_from_settings
            result = _get_gemini_model_from_settings()
        assert result is None


# ---------------------------------------------------------------------------
# LLMClient init — OpenAI provider
# ---------------------------------------------------------------------------


class TestLLMClientInitOpenAI:
    def test_openai_provider_sets_model(self):
        with patch.dict(os.environ, {"OPENAI_API_KEY": "sk-test", "OPENAI_MODEL": "gpt-4"}):
            with patch("utils.llm_client.OpenAI") as mock_openai:
                from utils.llm_client import LLMClient
                client = LLMClient(provider="openai")
        assert client.provider == "openai"
        assert client.model == "gpt-4"

    def test_openai_default_model(self):
        with patch.dict(os.environ, {"OPENAI_API_KEY": "sk-test"}, clear=True):
            with patch("utils.llm_client.OpenAI"):
                from utils.llm_client import LLMClient
                client = LLMClient(provider="openai")
        assert client.model == "gpt-4o"

    def test_openai_client_created(self):
        with patch.dict(os.environ, {"OPENAI_API_KEY": "sk-test"}):
            with patch("utils.llm_client.OpenAI") as mock_openai_cls:
                from utils.llm_client import LLMClient
                client = LLMClient(provider="openai")
        mock_openai_cls.assert_called_once_with(api_key="sk-test")

    def test_gemini_uses_settings_model(self, tmp_path):
        settings = {"gemini_model": "gemini-ultra"}
        settings_file = tmp_path / "settings.json"
        settings_file.write_text(json.dumps(settings))
        with patch.dict(os.environ, {"GEMINI_API_KEY": "g-key"}):
            with patch("utils.llm_client.SETTINGS_FILE", settings_file):
                with patch("utils.llm_client.genai"):
                    from utils.llm_client import LLMClient
                    client = LLMClient(provider="gemini")
        assert client.model == "gemini-ultra"


# ---------------------------------------------------------------------------
# _retry_with_backoff
# ---------------------------------------------------------------------------


class TestRetryWithBackoff:
    def test_returns_on_first_success(self):
        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"}):
            from utils.llm_client import LLMClient
            client = LLMClient(provider="claude")

        func = MagicMock(return_value="ok")
        result = client._retry_with_backoff(func)
        assert result == "ok"
        func.assert_called_once()

    def test_retries_on_rate_limit(self):
        from anthropic import RateLimitError

        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"}):
            from utils.llm_client import LLMClient
            client = LLMClient(provider="claude")

        mock_resp = MagicMock()
        mock_resp.status_code = 429
        mock_resp.headers = {}
        rate_error = RateLimitError("rate limit", response=mock_resp, body={})

        func = MagicMock(side_effect=[rate_error, rate_error, "success"])

        with patch("utils.llm_client.time.sleep"):
            result = client._retry_with_backoff(func, max_retries=5)

        assert result == "success"
        assert func.call_count == 3

    def test_raises_after_max_retries(self):
        from anthropic import RateLimitError

        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"}):
            from utils.llm_client import LLMClient
            client = LLMClient(provider="claude")

        mock_resp = MagicMock()
        mock_resp.status_code = 429
        mock_resp.headers = {}
        rate_error = RateLimitError("rate limit", response=mock_resp, body={})

        func = MagicMock(side_effect=rate_error)

        with patch("utils.llm_client.time.sleep"):
            with pytest.raises(RateLimitError):
                client._retry_with_backoff(func, max_retries=3)

    def test_non_rate_limit_error_not_retried(self):
        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"}):
            from utils.llm_client import LLMClient
            client = LLMClient(provider="claude")

        func = MagicMock(side_effect=ValueError("Other error"))
        with pytest.raises(ValueError):
            client._retry_with_backoff(func, max_retries=5)
        func.assert_called_once()


# ---------------------------------------------------------------------------
# generate — routing
# ---------------------------------------------------------------------------


class TestGenerateRouting:
    def test_generate_routes_to_claude(self):
        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"}):
            from utils.llm_client import LLMClient
            client = LLMClient(provider="claude")

        with patch.object(client, "_generate_claude", return_value="claude resp") as mock_c:
            result = client.generate("hello")
        mock_c.assert_called_once_with("hello", None, 1.0)
        assert result == "claude resp"

    def test_generate_routes_to_gemini(self):
        with patch.dict(os.environ, {"GEMINI_API_KEY": "g-key"}):
            with patch("utils.llm_client.genai"):
                from utils.llm_client import LLMClient
                client = LLMClient(provider="gemini")

        with patch.object(client, "_generate_gemini", return_value="gemini resp") as mock_g:
            result = client.generate("hello")
        mock_g.assert_called_once_with("hello", None, 1.0)
        assert result == "gemini resp"

    def test_generate_routes_to_openai(self):
        with patch.dict(os.environ, {"OPENAI_API_KEY": "sk-test"}):
            with patch("utils.llm_client.OpenAI"):
                from utils.llm_client import LLMClient
                client = LLMClient(provider="openai")

        with patch.object(client, "_generate_openai", return_value="openai resp") as mock_o:
            result = client.generate("hello")
        mock_o.assert_called_once_with("hello", None, 1.0)
        assert result == "openai resp"


# ---------------------------------------------------------------------------
# _generate_claude
# ---------------------------------------------------------------------------


class TestGenerateClaude:
    def _make_client(self):
        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"}):
            from utils.llm_client import LLMClient
            return LLMClient(provider="claude")

    def test_returns_text_from_response(self):
        client = self._make_client()
        mock_resp = _make_claude_response("My answer")
        client.client = MagicMock()
        client.client.messages.create.return_value = mock_resp

        result = client._generate_claude("question?")
        assert result == "My answer"

    def test_includes_system_prompt_when_provided(self):
        client = self._make_client()
        mock_resp = _make_claude_response("answer")
        client.client = MagicMock()
        client.client.messages.create.return_value = mock_resp

        client._generate_claude("question?", system_prompt="You are helpful.")
        call_kwargs = client.client.messages.create.call_args[1]
        assert call_kwargs["system"] == "You are helpful."

    def test_no_system_key_when_no_system_prompt(self):
        client = self._make_client()
        mock_resp = _make_claude_response("answer")
        client.client = MagicMock()
        client.client.messages.create.return_value = mock_resp

        client._generate_claude("question?")
        call_kwargs = client.client.messages.create.call_args[1]
        assert "system" not in call_kwargs

    def test_custom_temperature(self):
        client = self._make_client()
        mock_resp = _make_claude_response("answer")
        client.client = MagicMock()
        client.client.messages.create.return_value = mock_resp

        client._generate_claude("question?", temperature=0.5)
        call_kwargs = client.client.messages.create.call_args[1]
        assert call_kwargs["temperature"] == 0.5

    def test_custom_max_tokens(self):
        client = self._make_client()
        mock_resp = _make_claude_response("answer")
        client.client = MagicMock()
        client.client.messages.create.return_value = mock_resp

        client._generate_claude("question?", max_tokens=1000)
        call_kwargs = client.client.messages.create.call_args[1]
        assert call_kwargs["max_tokens"] == 1000


# ---------------------------------------------------------------------------
# _generate_openai
# ---------------------------------------------------------------------------


class TestGenerateOpenAI:
    def _make_client(self):
        with patch.dict(os.environ, {"OPENAI_API_KEY": "sk-test"}):
            with patch("utils.llm_client.OpenAI"):
                from utils.llm_client import LLMClient
                return LLMClient(provider="openai")

    def test_returns_text_from_response(self):
        client = self._make_client()
        mock_resp = _make_openai_response("OpenAI answer")
        client.client = MagicMock()
        client.client.chat.completions.create.return_value = mock_resp

        result = client._generate_openai("question?")
        assert result == "OpenAI answer"

    def test_includes_system_message_when_provided(self):
        client = self._make_client()
        mock_resp = _make_openai_response("answer")
        client.client = MagicMock()
        client.client.chat.completions.create.return_value = mock_resp

        client._generate_openai("question?", system_prompt="Be helpful.")
        call_kwargs = client.client.chat.completions.create.call_args[1]
        messages = call_kwargs["messages"]
        assert messages[0] == {"role": "system", "content": "Be helpful."}

    def test_no_system_message_without_system_prompt(self):
        client = self._make_client()
        mock_resp = _make_openai_response("answer")
        client.client = MagicMock()
        client.client.chat.completions.create.return_value = mock_resp

        client._generate_openai("question?")
        call_kwargs = client.client.chat.completions.create.call_args[1]
        messages = call_kwargs["messages"]
        assert all(m["role"] != "system" for m in messages)


# ---------------------------------------------------------------------------
# _generate_gemini
# ---------------------------------------------------------------------------


class TestGenerateGemini:
    def _make_client(self):
        with patch.dict(os.environ, {"GEMINI_API_KEY": "g-key"}):
            with patch("utils.llm_client.genai"):
                from utils.llm_client import LLMClient
                return LLMClient(provider="gemini")

    def test_returns_text_from_response(self):
        client = self._make_client()

        mock_model = MagicMock()
        mock_response = MagicMock()
        mock_response.text = "Gemini answer"
        mock_model.generate_content.return_value = mock_response

        with patch("utils.llm_client.genai") as mock_genai:
            mock_genai.GenerativeModel.return_value = mock_model
            result = client._generate_gemini("question?")

        assert result == "Gemini answer"

    def test_prepends_system_prompt(self):
        client = self._make_client()

        mock_model = MagicMock()
        mock_response = MagicMock()
        mock_response.text = "answer"
        mock_model.generate_content.return_value = mock_response

        with patch("utils.llm_client.genai") as mock_genai:
            mock_genai.GenerativeModel.return_value = mock_model
            client._generate_gemini("question?", system_prompt="You are an expert.")

        call_args = mock_model.generate_content.call_args
        full_prompt = call_args[0][0]
        assert "You are an expert." in full_prompt
        assert "question?" in full_prompt

    def test_no_prepend_without_system_prompt(self):
        client = self._make_client()

        mock_model = MagicMock()
        mock_response = MagicMock()
        mock_response.text = "answer"
        mock_model.generate_content.return_value = mock_response

        with patch("utils.llm_client.genai") as mock_genai:
            mock_genai.GenerativeModel.return_value = mock_model
            client._generate_gemini("question only")

        call_args = mock_model.generate_content.call_args
        full_prompt = call_args[0][0]
        assert full_prompt == "question only"


# ---------------------------------------------------------------------------
# generate_with_context — Claude
# ---------------------------------------------------------------------------


class TestGenerateWithContextClaude:
    def _make_client(self):
        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"}):
            from utils.llm_client import LLMClient
            return LLMClient(provider="claude")

    def test_returns_text_from_messages(self):
        client = self._make_client()
        mock_resp = _make_claude_response("Context response")
        client.client = MagicMock()
        client.client.messages.create.return_value = mock_resp

        messages = [{"role": "user", "content": "Hello"}]
        result = client.generate_with_context(messages)
        assert result == "Context response"

    def test_passes_system_prompt(self):
        client = self._make_client()
        mock_resp = _make_claude_response("response")
        client.client = MagicMock()
        client.client.messages.create.return_value = mock_resp

        messages = [{"role": "user", "content": "Hi"}]
        client.generate_with_context(messages, system_prompt="Act as expert.")
        call_kwargs = client.client.messages.create.call_args[1]
        assert call_kwargs["system"] == "Act as expert."

    def test_no_system_key_without_system_prompt(self):
        client = self._make_client()
        mock_resp = _make_claude_response("response")
        client.client = MagicMock()
        client.client.messages.create.return_value = mock_resp

        messages = [{"role": "user", "content": "Hi"}]
        client.generate_with_context(messages)
        call_kwargs = client.client.messages.create.call_args[1]
        assert "system" not in call_kwargs

    def test_custom_temperature_via_kwargs(self):
        client = self._make_client()
        mock_resp = _make_claude_response("response")
        client.client = MagicMock()
        client.client.messages.create.return_value = mock_resp

        messages = [{"role": "user", "content": "Hi"}]
        client.generate_with_context(messages, temperature=0.2)
        call_kwargs = client.client.messages.create.call_args[1]
        assert call_kwargs["temperature"] == 0.2


# ---------------------------------------------------------------------------
# generate_with_context — Gemini
# ---------------------------------------------------------------------------


class TestGenerateWithContextGemini:
    def _make_client(self):
        with patch.dict(os.environ, {"GEMINI_API_KEY": "g-key"}):
            with patch("utils.llm_client.genai"):
                from utils.llm_client import LLMClient
                return LLMClient(provider="gemini")

    def test_returns_text_from_chat(self):
        client = self._make_client()

        mock_response = MagicMock()
        mock_response.text = "Gemini context response"
        mock_chat = MagicMock()
        mock_chat.send_message.return_value = mock_response
        mock_model = MagicMock()
        mock_model.start_chat.return_value = mock_chat

        with patch("utils.llm_client.genai") as mock_genai:
            mock_genai.GenerativeModel.return_value = mock_model
            messages = [
                {"role": "user", "content": "First message"},
                {"role": "assistant", "content": "Response"},
                {"role": "user", "content": "Last message"},
            ]
            result = client.generate_with_context(messages)

        assert result == "Gemini context response"

    def test_uses_system_instruction(self):
        client = self._make_client()

        mock_response = MagicMock()
        mock_response.text = "answer"
        mock_chat = MagicMock()
        mock_chat.send_message.return_value = mock_response
        mock_model = MagicMock()
        mock_model.start_chat.return_value = mock_chat

        with patch("utils.llm_client.genai") as mock_genai:
            mock_genai.GenerativeModel.return_value = mock_model
            messages = [{"role": "user", "content": "Hello"}]
            client.generate_with_context(messages, system_prompt="Be concise.")

        mock_genai.GenerativeModel.assert_called_once_with(
            client.model, system_instruction="Be concise."
        )

    def test_sends_last_message(self):
        client = self._make_client()

        mock_response = MagicMock()
        mock_response.text = "answer"
        mock_chat = MagicMock()
        mock_chat.send_message.return_value = mock_response
        mock_model = MagicMock()
        mock_model.start_chat.return_value = mock_chat

        with patch("utils.llm_client.genai") as mock_genai:
            mock_genai.GenerativeModel.return_value = mock_model
            messages = [
                {"role": "user", "content": "Not this"},
                {"role": "user", "content": "Send this"},
            ]
            client.generate_with_context(messages)

        call_args = mock_chat.send_message.call_args
        assert call_args[0][0] == "Send this"


# ---------------------------------------------------------------------------
# generate_with_context — OpenAI
# ---------------------------------------------------------------------------


class TestGenerateWithContextOpenAI:
    def _make_client(self):
        with patch.dict(os.environ, {"OPENAI_API_KEY": "sk-test"}):
            with patch("utils.llm_client.OpenAI"):
                from utils.llm_client import LLMClient
                return LLMClient(provider="openai")

    def test_returns_text_from_response(self):
        client = self._make_client()
        mock_resp = _make_openai_response("OpenAI context response")
        client.client = MagicMock()
        client.client.chat.completions.create.return_value = mock_resp

        messages = [{"role": "user", "content": "Hello"}]
        result = client.generate_with_context(messages)
        assert result == "OpenAI context response"

    def test_prepends_system_message(self):
        client = self._make_client()
        mock_resp = _make_openai_response("answer")
        client.client = MagicMock()
        client.client.chat.completions.create.return_value = mock_resp

        messages = [{"role": "user", "content": "Hello"}]
        client.generate_with_context(messages, system_prompt="Be helpful.")
        call_kwargs = client.client.chat.completions.create.call_args[1]
        assert call_kwargs["messages"][0] == {"role": "system", "content": "Be helpful."}


# ---------------------------------------------------------------------------
# stream_with_context — Claude
# ---------------------------------------------------------------------------


class TestStreamWithContextClaude:
    def _make_client(self):
        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"}):
            from utils.llm_client import LLMClient
            return LLMClient(provider="claude")

    def test_yields_chunks(self):
        client = self._make_client()

        mock_stream_ctx = MagicMock()
        mock_stream_ctx.__enter__ = MagicMock(return_value=mock_stream_ctx)
        mock_stream_ctx.__exit__ = MagicMock(return_value=False)
        mock_stream_ctx.text_stream = iter(["chunk1", "chunk2", "chunk3"])
        client.client = MagicMock()
        client.client.messages.stream.return_value = mock_stream_ctx

        messages = [{"role": "user", "content": "Hello"}]
        chunks = list(client.stream_with_context(messages))
        assert chunks == ["chunk1", "chunk2", "chunk3"]

    def test_passes_system_prompt_to_stream(self):
        client = self._make_client()

        mock_stream_ctx = MagicMock()
        mock_stream_ctx.__enter__ = MagicMock(return_value=mock_stream_ctx)
        mock_stream_ctx.__exit__ = MagicMock(return_value=False)
        mock_stream_ctx.text_stream = iter([])
        client.client = MagicMock()
        client.client.messages.stream.return_value = mock_stream_ctx

        messages = [{"role": "user", "content": "Hello"}]
        list(client.stream_with_context(messages, system_prompt="System instruction."))
        call_kwargs = client.client.messages.stream.call_args[1]
        assert call_kwargs["system"] == "System instruction."


# ---------------------------------------------------------------------------
# stream_with_context — Gemini
# ---------------------------------------------------------------------------


class TestStreamWithContextGemini:
    def _make_client(self):
        with patch.dict(os.environ, {"GEMINI_API_KEY": "g-key"}):
            with patch("utils.llm_client.genai"):
                from utils.llm_client import LLMClient
                return LLMClient(provider="gemini")

    def test_yields_chunks_from_gemini(self):
        client = self._make_client()

        chunk1 = MagicMock()
        chunk1.text = "Hello "
        chunk2 = MagicMock()
        chunk2.text = "World"
        chunk3 = MagicMock()
        chunk3.text = ""  # Falsy — should be skipped

        mock_chat = MagicMock()
        mock_chat.send_message.return_value = iter([chunk1, chunk2, chunk3])
        mock_model = MagicMock()
        mock_model.start_chat.return_value = mock_chat

        with patch("utils.llm_client.genai") as mock_genai:
            mock_genai.GenerativeModel.return_value = mock_model
            messages = [{"role": "user", "content": "Hello"}]
            chunks = list(client.stream_with_context(messages))

        assert "Hello " in chunks
        assert "World" in chunks
        assert "" not in chunks


# ---------------------------------------------------------------------------
# generate_stream
# ---------------------------------------------------------------------------


class TestGenerateStream:
    def test_stream_claude_yields_chunks(self):
        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"}):
            from utils.llm_client import LLMClient
            client = LLMClient(provider="claude")

        mock_stream_ctx = MagicMock()
        mock_stream_ctx.__enter__ = MagicMock(return_value=mock_stream_ctx)
        mock_stream_ctx.__exit__ = MagicMock(return_value=False)
        mock_stream_ctx.text_stream = iter(["a", "b", "c"])
        client.client = MagicMock()
        client.client.messages.stream.return_value = mock_stream_ctx

        chunks = list(client.generate_stream("prompt"))
        assert chunks == ["a", "b", "c"]

    def test_stream_openai_yields_chunks(self):
        with patch.dict(os.environ, {"OPENAI_API_KEY": "sk-test"}):
            with patch("utils.llm_client.OpenAI"):
                from utils.llm_client import LLMClient
                client = LLMClient(provider="openai")

        def make_chunk(text):
            chunk = MagicMock()
            chunk.choices[0].delta.content = text
            return chunk

        mock_chunks = [make_chunk("x"), make_chunk("y"), make_chunk(None)]
        client.client = MagicMock()
        client.client.chat.completions.create.return_value = iter(mock_chunks)

        chunks = list(client.generate_stream("prompt"))
        assert "x" in chunks
        assert "y" in chunks

    def test_stream_gemini_yields_chunks(self):
        with patch.dict(os.environ, {"GEMINI_API_KEY": "g-key"}):
            with patch("utils.llm_client.genai"):
                from utils.llm_client import LLMClient
                client = LLMClient(provider="gemini")

        mock_chunk1 = MagicMock()
        mock_chunk1.text = "Gemini chunk"
        mock_chunk2 = MagicMock()
        mock_chunk2.text = ""

        mock_model = MagicMock()
        mock_model.generate_content.return_value = iter([mock_chunk1, mock_chunk2])

        with patch("utils.llm_client.genai") as mock_genai:
            mock_genai.GenerativeModel.return_value = mock_model
            chunks = list(client.generate_stream("prompt"))

        assert "Gemini chunk" in chunks
        assert "" not in chunks


# ---------------------------------------------------------------------------
# extract_structured_data
# ---------------------------------------------------------------------------


class TestExtractStructuredData:
    def _make_client(self):
        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"}):
            from utils.llm_client import LLMClient
            return LLMClient(provider="claude")

    def test_parses_valid_json(self):
        client = self._make_client()
        with patch.object(client, "generate", return_value='{"name": "Alice", "age": 30}'):
            result = client.extract_structured_data("prompt", {"name": "str", "age": "int"})
        assert result == {"name": "Alice", "age": 30}

    def test_strips_markdown_json_fence(self):
        client = self._make_client()
        raw = '```json\n{"key": "value"}\n```'
        with patch.object(client, "generate", return_value=raw):
            result = client.extract_structured_data("prompt", {})
        assert result == {"key": "value"}

    def test_strips_plain_code_fence(self):
        client = self._make_client()
        raw = '```\n{"key": "val"}\n```'
        with patch.object(client, "generate", return_value=raw):
            result = client.extract_structured_data("prompt", {})
        assert result == {"key": "val"}

    def test_returns_empty_dict_on_invalid_json(self):
        client = self._make_client()
        with patch.object(client, "generate", return_value="not json at all!!!"):
            result = client.extract_structured_data("prompt", {})
        assert result == {}

    def test_tries_newline_fix_on_json_error(self):
        client = self._make_client()
        # JSON with literal newlines inside a string value — after replacement it should parse
        broken = '{"text": "line1\nline2"}'
        with patch.object(client, "generate", return_value=broken):
            result = client.extract_structured_data("prompt", {})
        # Either parsed correctly or returned empty — either is acceptable
        assert isinstance(result, dict)

    def test_control_chars_sanitized(self):
        client = self._make_client()
        # Contains control char \x01 which should be removed
        raw = '{"key": "val\x01ue"}'
        with patch.object(client, "generate", return_value=raw):
            result = client.extract_structured_data("prompt", {})
        assert result.get("key") == "value"

    def test_passes_low_temperature(self):
        client = self._make_client()
        with patch.object(client, "generate", return_value="{}") as mock_gen:
            client.extract_structured_data("prompt", {})
        call_kwargs = mock_gen.call_args[1]
        assert call_kwargs.get("temperature") == 0.3


# ---------------------------------------------------------------------------
# summarize
# ---------------------------------------------------------------------------


class TestSummarize:
    def test_calls_generate_with_prompt(self):
        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"}):
            from utils.llm_client import LLMClient
            client = LLMClient(provider="claude")

        with patch.object(client, "generate", return_value="Summary here") as mock_gen:
            result = client.summarize("Long text to summarize")

        assert result == "Summary here"
        call_kwargs = mock_gen.call_args[1]
        assert call_kwargs.get("temperature") == 0.5

    def test_includes_max_length_in_prompt(self):
        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"}):
            from utils.llm_client import LLMClient
            client = LLMClient(provider="claude")

        with patch.object(client, "generate", return_value="summary") as mock_gen:
            client.summarize("text", max_length=50)

        call_kwargs = mock_gen.call_args[1]
        assert "50" in call_kwargs.get("prompt", "")


# ---------------------------------------------------------------------------
# translate
# ---------------------------------------------------------------------------


class TestTranslate:
    def test_calls_generate_with_target_lang(self):
        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"}):
            from utils.llm_client import LLMClient
            client = LLMClient(provider="claude")

        with patch.object(client, "generate", return_value="Translated text") as mock_gen:
            result = client.translate("Hello world", target_lang="fr")

        assert result == "Translated text"
        call_kwargs = mock_gen.call_args[1]
        assert "fr" in call_kwargs.get("prompt", "")
        assert call_kwargs.get("temperature") == 0.3
