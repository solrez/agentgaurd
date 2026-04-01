"""OpenAI LLM provider."""

from __future__ import annotations

from agentguard.llm.base import LLMProvider, LLMResponse

DEFAULT_MODEL = "gpt-4o"


class OpenAIProvider(LLMProvider):
    """LLM provider using the OpenAI SDK."""

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
                import openai
            except ImportError:
                raise ImportError(
                    "The 'openai' package is required for the OpenAI provider. "
                    "Install it with: pip install agentguard[openai]"
                )
            self.client = openai.AsyncOpenAI(api_key=api_key)

    async def complete(
        self, system_prompt: str, user_prompt: str, max_tokens: int = 1024
    ) -> LLMResponse:
        response = await self.client.chat.completions.create(
            model=self.model,
            max_tokens=max_tokens,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        )

        choice = response.choices[0]
        content = choice.message.content or ""

        usage = {}
        if response.usage:
            usage = {
                "input_tokens": response.usage.prompt_tokens,
                "output_tokens": response.usage.completion_tokens,
            }

        return LLMResponse(
            content=content,
            model=response.model or self.model,
            usage=usage,
        )
