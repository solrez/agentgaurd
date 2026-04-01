"""LangChain integration — intercept tool calls via callback handler."""

from __future__ import annotations

import json
from typing import Any

from agentguard.core.action import ActionType, AgentAction, ActionContext
from agentguard.core.interceptor import Guard, GuardError

try:
    from langchain_core.callbacks import AsyncCallbackHandler
except ImportError:
    raise ImportError(
        "The 'langchain-core' package is required for LangChain integration. "
        "Install it with: pip install agentguard[langchain]"
    )


class AgentGuardCallback(AsyncCallbackHandler):
    """LangChain callback that intercepts tool calls through AgentGuard.

    Usage:
        guard = Guard(validators=[...])
        callback = AgentGuardCallback(guard)
        agent_executor = AgentExecutor(agent=agent, tools=tools, callbacks=[callback])
    """

    name = "AgentGuardCallback"

    def __init__(self, guard: Guard, raise_on_block: bool = True):
        self.guard = guard
        self.raise_on_block = raise_on_block

    async def on_tool_start(
        self, serialized: dict[str, Any], input_str: str, **kwargs: Any
    ) -> None:
        """Intercept before tool execution."""
        action = self._build_action(serialized, input_str, kwargs)
        decision = await self.guard.verify(action)

        if not decision.should_execute and self.raise_on_block:
            raise GuardError(decision)

    def _build_action(
        self, serialized: dict[str, Any], input_str: str, kwargs: dict[str, Any]
    ) -> AgentAction:
        """Convert LangChain tool call into AgentAction."""
        tool_name = serialized.get("name", serialized.get("id", ["unknown"])[-1])

        # Try to parse input_str as JSON for structured payload
        try:
            payload = json.loads(input_str)
            if not isinstance(payload, dict):
                payload = {"input": input_str}
        except (json.JSONDecodeError, TypeError):
            payload = {"input": input_str}

        run_id = kwargs.get("run_id", "")
        parent_run_id = kwargs.get("parent_run_id", "")

        return AgentAction(
            action_type=ActionType.TOOL_CALL,
            target=tool_name,
            payload=payload,
            context=ActionContext(
                agent_id=str(parent_run_id) if parent_run_id else "",
                session_id=str(run_id) if run_id else "",
            ),
            metadata={
                "framework": "langchain",
                "serialized": serialized,
            },
        )
