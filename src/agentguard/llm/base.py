"""Base LLM provider interface."""

from __future__ import annotations

from abc import ABC, abstractmethod

from pydantic import BaseModel


class LLMResponse(BaseModel):
    """Standardized response from an LLM provider."""

    content: str
    model: str = ""
    usage: dict[str, int] = {}


class LLMProvider(ABC):
    """Minimal abstraction over LLM providers for internal validator use."""

    @abstractmethod
    async def complete(
        self, system_prompt: str, user_prompt: str, max_tokens: int = 1024
    ) -> LLMResponse:
        """Send a prompt and return the response."""
        ...


def get_provider(
    provider: str = "anthropic",
    model: str | None = None,
    api_key: str | None = None,
) -> LLMProvider:
    """Factory function to create an LLM provider.

    Args:
        provider: "anthropic" or "openai"
        model: Model name override. Defaults to provider's default.
        api_key: API key. Defaults to reading from environment.
    """
    if provider == "anthropic":
        from agentguard.llm.anthropic_provider import AnthropicProvider

        return AnthropicProvider(model=model, api_key=api_key)
    elif provider == "openai":
        from agentguard.llm.openai_provider import OpenAIProvider

        return OpenAIProvider(model=model, api_key=api_key)
    else:
        raise ValueError(f"Unknown provider: {provider}. Use 'anthropic' or 'openai'.")
