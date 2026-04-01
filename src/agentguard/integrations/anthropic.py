"""Anthropic integration — intercept tool_use blocks before execution."""

from __future__ import annotations

from typing import Any

from agentguard.core.action import ActionType, AgentAction, ActionContext
from agentguard.core.interceptor import Guard, GuardError

try:
    from anthropic import AsyncAnthropic
    from anthropic.types import Message
except ImportError:
    raise ImportError(
        "The 'anthropic' package is required for the Anthropic integration. "
        "Install it with: pip install agentguard[anthropic]"
    )


class GuardedAnthropicClient:
    """Wraps anthropic.AsyncAnthropic to intercept tool_use blocks.

    Usage:
        guard = Guard(validators=[...])
        client = GuardedAnthropicClient(guard)
        response = await client.create_message(
            model="claude-sonnet-4-20250514",
            max_tokens=1024,
            messages=[{"role": "user", "content": "..."}],
            tools=[...],
        )
    """

    def __init__(
        self,
        guard: Guard,
        client: AsyncAnthropic | None = None,
        raise_on_block: bool = True,
        agent_id: str = "",
    ):
        self.guard = guard
        self.client = client or AsyncAnthropic()
        self.raise_on_block = raise_on_block
        self.agent_id = agent_id

    async def create_message(self, **kwargs: Any) -> Message:
        """Call messages.create then intercept any tool_use in the response."""
        response = await self.client.messages.create(**kwargs)
        await self._intercept_tool_use(response)
        return response

    async def _intercept_tool_use(self, response: Message) -> None:
        """For each tool_use content block, run it through the guard."""
        for block in response.content:
            if block.type != "tool_use":
                continue

            action = AgentAction(
                action_type=ActionType.TOOL_CALL,
                target=block.name,
                payload=block.input if isinstance(block.input, dict) else {},
                context=ActionContext(agent_id=self.agent_id),
                metadata={
                    "framework": "anthropic",
                    "tool_use_id": block.id,
                },
            )

            decision = await self.guard.verify(action)
            if not decision.should_execute and self.raise_on_block:
                raise GuardError(decision)
