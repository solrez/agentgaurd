"""Tests for LLM providers (fully mocked, no API calls)."""

import pytest
from unittest.mock import AsyncMock, MagicMock

from agentguard.llm.base import LLMResponse, get_provider
from agentguard.llm.anthropic_provider import AnthropicProvider
from agentguard.llm.openai_provider import OpenAIProvider


# --- Anthropic Provider Tests ---


@pytest.mark.asyncio
async def test_anthropic_provider_complete():
    mock_client = AsyncMock()
    mock_response = MagicMock()
    mock_response.content = [MagicMock(type="text", text="The action is valid.")]
    mock_response.model = "claude-sonnet-4-20250514"
    mock_response.usage.input_tokens = 100
    mock_response.usage.output_tokens = 20
    mock_client.messages.create.return_value = mock_response

    provider = AnthropicProvider(client=mock_client)
    result = await provider.complete("system prompt", "user prompt", max_tokens=512)

    assert isinstance(result, LLMResponse)
    assert result.content == "The action is valid."
    assert result.model == "claude-sonnet-4-20250514"
    assert result.usage["input_tokens"] == 100
    assert result.usage["output_tokens"] == 20

    mock_client.messages.create.assert_called_once_with(
        model="claude-sonnet-4-20250514",
        max_tokens=512,
        system="system prompt",
        messages=[{"role": "user", "content": "user prompt"}],
    )


@pytest.mark.asyncio
async def test_anthropic_provider_custom_model():
    mock_client = AsyncMock()
    mock_response = MagicMock()
    mock_response.content = [MagicMock(type="text", text="ok")]
    mock_response.model = "claude-opus-4-20250514"
    mock_response.usage.input_tokens = 50
    mock_response.usage.output_tokens = 10
    mock_client.messages.create.return_value = mock_response

    provider = AnthropicProvider(model="claude-opus-4-20250514", client=mock_client)
    result = await provider.complete("sys", "usr")

    assert result.model == "claude-opus-4-20250514"
    call_kwargs = mock_client.messages.create.call_args
    assert call_kwargs.kwargs["model"] == "claude-opus-4-20250514"


# --- OpenAI Provider Tests ---


@pytest.mark.asyncio
async def test_openai_provider_complete():
    mock_client = AsyncMock()
    mock_choice = MagicMock()
    mock_choice.message.content = "Looks good."
    mock_response = MagicMock()
    mock_response.choices = [mock_choice]
    mock_response.model = "gpt-4o"
    mock_response.usage.prompt_tokens = 80
    mock_response.usage.completion_tokens = 15
    mock_client.chat.completions.create.return_value = mock_response

    provider = OpenAIProvider(client=mock_client)
    result = await provider.complete("system prompt", "user prompt", max_tokens=256)

    assert isinstance(result, LLMResponse)
    assert result.content == "Looks good."
    assert result.model == "gpt-4o"
    assert result.usage["input_tokens"] == 80
    assert result.usage["output_tokens"] == 15

    mock_client.chat.completions.create.assert_called_once_with(
        model="gpt-4o",
        max_tokens=256,
        messages=[
            {"role": "system", "content": "system prompt"},
            {"role": "user", "content": "user prompt"},
        ],
    )


@pytest.mark.asyncio
async def test_openai_provider_no_usage():
    mock_client = AsyncMock()
    mock_choice = MagicMock()
    mock_choice.message.content = "ok"
    mock_response = MagicMock()
    mock_response.choices = [mock_choice]
    mock_response.model = "gpt-4o"
    mock_response.usage = None
    mock_client.chat.completions.create.return_value = mock_response

    provider = OpenAIProvider(client=mock_client)
    result = await provider.complete("sys", "usr")

    assert result.usage == {}


# --- Factory Tests ---


def test_get_provider_unknown():
    with pytest.raises(ValueError, match="Unknown provider"):
        get_provider("gemini")


def test_get_provider_anthropic():
    # Test direct construction with mock client (avoids needing SDK installed)
    mock_client = MagicMock()
    provider = AnthropicProvider(client=mock_client)
    assert provider.model == "claude-sonnet-4-20250514"
    assert provider.client is mock_client


def test_get_provider_openai():
    mock_client = MagicMock()
    provider = OpenAIProvider(client=mock_client)
    assert provider.model == "gpt-4o"
