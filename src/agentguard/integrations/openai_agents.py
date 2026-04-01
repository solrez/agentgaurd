"""OpenAI integration — intercept function/tool calls before execution."""

from __future__ import annotations

import json
from typing import Any

from agentguard.core.action import ActionType, AgentAction, ActionContext
from agentguard.core.interceptor import Guard, GuardError

try:
    from openai import AsyncOpenAI
    from openai.types.chat import ChatCompletion
except ImportError:
    raise ImportError(
        "The 'openai' package is required for the OpenAI integration. "
        "Install it with: pip install agentguard[openai]"
    )


class GuardedOpenAIClient:
    """Wraps openai.AsyncOpenAI to intercept tool_calls in chat completions.

    Usage:
        guard = Guard(validators=[...])
        client = GuardedOpenAIClient(guard)
        response = await client.create_chat_completion(
            model="gpt-4o",
            messages=[{"role": "user", "content": "..."}],
            tools=[...],
        )
    """

    def __init__(
        self,
        guard: Guard,
        client: AsyncOpenAI | None = None,
        raise_on_block: bool = True,
        agent_id: str = "",
    ):
        self.guard = guard
        self.client = client or AsyncOpenAI()
        self.raise_on_block = raise_on_block
        self.agent_id = agent_id

    async def create_chat_completion(self, **kwargs: Any) -> ChatCompletion:
        """Call chat.completions.create then intercept any tool_calls."""
        response = await self.client.chat.completions.create(**kwargs)
        await self._intercept_tool_calls(response)
        return response

    async def _intercept_tool_calls(self, response: ChatCompletion) -> None:
        """For each tool_call in the response, run it through the guard."""
        for choice in response.choices:
            tool_calls = choice.message.tool_calls
            if not tool_calls:
                continue

            for tool_call in tool_calls:
                func = tool_call.function
                try:
                    payload = json.loads(func.arguments) if func.arguments else {}
                except json.JSONDecodeError:
                    payload = {"raw_arguments": func.arguments}

                action = AgentAction(
                    action_type=ActionType.TOOL_CALL,
                    target=func.name,
                    payload=payload if isinstance(payload, dict) else {"value": payload},
                    context=ActionContext(agent_id=self.agent_id),
                    metadata={
                        "framework": "openai",
                        "tool_call_id": tool_call.id,
                    },
                )

                decision = await self.guard.verify(action)
                if not decision.should_execute and self.raise_on_block:
                    raise GuardError(decision)
