"""Guard — the main entry point for AgentGuard."""

from __future__ import annotations

import asyncio
import functools
from typing import Any, Callable, Sequence

from agentguard.core.action import ActionType, AgentAction, ActionContext
from agentguard.core.audit import AuditBackend, AuditLogger, FileAuditBackend
from agentguard.core.decision import Decision, DecisionAction, DecisionEngine, EscalationHandler
from agentguard.core.pipeline import ValidatorPipeline
from agentguard.validators.base import BaseValidator


class GuardError(Exception):
    """Raised when an action is blocked by AgentGuard."""

    def __init__(self, decision: Decision):
        self.decision = decision
        reasons = "; ".join(decision.reasons) if decision.reasons else "Action blocked"
        super().__init__(f"AgentGuard blocked action: {reasons}")


class Guard:
    """Main AgentGuard interface.

    Usage:
        guard = Guard(validators=[SchemaValidator(...), SafetyScorer()])

        # As a decorator
        @guard.protect
        async def call_api(endpoint, data):
            ...

        # Manual verification
        decision = await guard.verify(action)
        if decision.should_execute:
            execute(decision.effective_action)
    """

    def __init__(
        self,
        validators: Sequence[BaseValidator] | None = None,
        sequential: bool = False,
        fail_fast: bool = True,
        block_confidence_threshold: float = 0.7,
        escalation_handler: EscalationHandler | None = None,
        default_on_escalation: DecisionAction = DecisionAction.BLOCK,
        audit_backend: AuditBackend | None = None,
        raise_on_block: bool = True,
    ):
        self.pipeline = ValidatorPipeline(
            validators=validators or [],
            sequential=sequential,
            fail_fast=fail_fast,
        )
        self.decision_engine = DecisionEngine(
            block_confidence_threshold=block_confidence_threshold,
            escalation_handler=escalation_handler,
            default_on_escalation=default_on_escalation,
        )
        self.audit = AuditLogger(
            backends=[audit_backend] if audit_backend else [FileAuditBackend()]
        )
        self.raise_on_block = raise_on_block

    async def verify(self, action: AgentAction) -> Decision:
        """Verify an action through the full pipeline. Returns a Decision."""
        pipeline_result = await self.pipeline.run(action)
        decision = await self.decision_engine.decide(action, pipeline_result)

        validator_names = [v.name for v in self.pipeline.validators]
        await self.audit.log_decision(action, decision, validator_names)

        return decision

    def protect(
        self,
        func: Callable | None = None,
        *,
        action_type: ActionType = ActionType.TOOL_CALL,
        target: str = "",
    ) -> Callable:
        """Decorator that guards a function call.

        The function's kwargs become the action payload. If the action is blocked,
        raises GuardError (or returns None if raise_on_block=False).
        """

        def decorator(fn: Callable) -> Callable:
            @functools.wraps(fn)
            async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
                action = AgentAction(
                    action_type=action_type,
                    target=target or fn.__name__,
                    payload=kwargs,
                    context=ActionContext(),
                )
                decision = await self.verify(action)

                if not decision.should_execute:
                    if self.raise_on_block:
                        raise GuardError(decision)
                    return None

                effective = decision.effective_action
                return await fn(*args, **effective.payload)

            @functools.wraps(fn)
            def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
                return asyncio.get_event_loop().run_until_complete(
                    async_wrapper(*args, **kwargs)
                )

            if asyncio.iscoroutinefunction(fn):
                return async_wrapper
            return sync_wrapper

        if func is not None:
            return decorator(func)
        return decorator

    def wrap_tool(self, tool_fn: Callable, **guard_kwargs: Any) -> Callable:
        """Wrap a tool function with guard protection."""
        return self.protect(tool_fn, **guard_kwargs)

    async def teardown(self) -> None:
        await self.pipeline.teardown()
