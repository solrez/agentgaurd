"""Anthropic LLM provider."""

from __future__ import annotations

from agentguard.llm.base import LLMProvider, LLMResponse

DEFAULT_MODEL = "claude-sonnet-4-20250514"


class AnthropicProvider(LLMProvider):
    """LLM provider using the Anthropic SDK."""

    def __init__(
        self,
        model: str | None = None,
        api_key: str | None = None,
        client: object | None = None,
    ):
        self.model = model or DEFAULT_MODEL

        if client is not None:
            self.client = client
        else:
            try:
                import anthropic
            except ImportError:
                raise ImportError(
                    "The 'anthropic' package is required for the Anthropic provider. "
                    "Install it with: pip install agentguard[anthropic]"
                )
            self.client = anthropic.AsyncAnthropic(api_key=api_key)

    async def complete(
        self, system_prompt: str, user_prompt: str, max_tokens: int = 1024
    ) -> LLMResponse:
        response = await self.client.messages.create(
            model=self.model,
            max_tokens=max_tokens,
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}],
        )

        content = ""
        for block in response.content:
            if block.type == "text":
                content += block.text

        return LLMResponse(
            content=content,
            model=response.model,
            usage={
                "input_tokens": response.usage.input_tokens,
                "output_tokens": response.usage.output_tokens,
            },
        )
