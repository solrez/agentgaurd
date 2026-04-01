"""Decision engine — takes pipeline results and makes a final call."""

from __future__ import annotations

from enum import Enum
from typing import Any, Callable, Awaitable

from pydantic import BaseModel, Field

from agentguard.core.action import AgentAction
from agentguard.core.pipeline import PipelineResult
from agentguard.validators.base import ValidationStatus


class DecisionAction(str, Enum):
    EXECUTE = "execute"
    BLOCK = "block"
    MODIFY = "modify"
    ESCALATE = "escalate"


class Decision(BaseModel):
    """The final decision on whether an action should proceed."""

    action: DecisionAction
    original_action: AgentAction
    modified_action: AgentAction | None = None
    reasons: list[str] = Field(default_factory=list)
    pipeline_latency_ms: float = 0.0
    metadata: dict[str, Any] = Field(default_factory=dict)

    @property
    def should_execute(self) -> bool:
        return self.action in (DecisionAction.EXECUTE, DecisionAction.MODIFY)

    @property
    def effective_action(self) -> AgentAction:
        """The action to execute (modified if corrections were applied)."""
        if self.action == DecisionAction.MODIFY and self.modified_action:
            return self.modified_action
        return self.original_action


EscalationHandler = Callable[[AgentAction, list[str]], Awaitable[Decision]]


class DecisionEngine:
    """Makes final decisions based on pipeline results.

    Args:
        block_confidence_threshold: Minimum confidence to honor a block verdict.
        escalation_handler: Async callback for human-in-the-loop escalation.
        default_on_escalation: What to do if escalation has no handler.
    """

    def __init__(
        self,
        block_confidence_threshold: float = 0.7,
        escalation_handler: EscalationHandler | None = None,
        default_on_escalation: DecisionAction = DecisionAction.BLOCK,
    ):
        self.block_confidence_threshold = block_confidence_threshold
        self.escalation_handler = escalation_handler
        self.default_on_escalation = default_on_escalation

    async def decide(self, action: AgentAction, pipeline_result: PipelineResult) -> Decision:
        reasons: list[str] = []

        # Check for high-confidence blocks
        for result in pipeline_result.results:
            if (
                result.status == ValidationStatus.BLOCKED
                and result.confidence >= self.block_confidence_threshold
            ):
                reasons.append(f"[{result.validator_name}] {result.reason}")

        if reasons:
            return Decision(
                action=DecisionAction.BLOCK,
                original_action=action,
                reasons=reasons,
                pipeline_latency_ms=pipeline_result.latency_ms,
            )

        # Check for modifications
        fixes = pipeline_result.suggested_fixes
        if fixes and pipeline_result.has_modifications:
            merged_payload = {**action.payload}
            for fix in fixes:
                merged_payload.update(fix)

            modified = action.model_copy(update={"payload": merged_payload})
            modification_reasons = [
                f"[{r.validator_name}] {r.reason}"
                for r in pipeline_result.results
                if r.status == ValidationStatus.MODIFIED
            ]
            return Decision(
                action=DecisionAction.MODIFY,
                original_action=action,
                modified_action=modified,
                reasons=modification_reasons,
                pipeline_latency_ms=pipeline_result.latency_ms,
            )

        # Check for escalation
        if pipeline_result.needs_escalation:
            escalation_reasons = [
                f"[{r.validator_name}] {r.reason}"
                for r in pipeline_result.results
                if r.status == ValidationStatus.ESCALATE
            ]

            if self.escalation_handler:
                return await self.escalation_handler(action, escalation_reasons)

            return Decision(
                action=self.default_on_escalation,
                original_action=action,
                reasons=escalation_reasons,
                pipeline_latency_ms=pipeline_result.latency_ms,
            )

        # All clear
        return Decision(
            action=DecisionAction.EXECUTE,
            original_action=action,
            pipeline_latency_ms=pipeline_result.latency_ms,
        )
