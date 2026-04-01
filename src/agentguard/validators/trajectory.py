"""Trajectory validator — tracks multi-step workflows and catches cascading errors."""

from __future__ import annotations

import json
import logging
import time
from collections import defaultdict

from pydantic import BaseModel, Field

from agentguard.core.action import AgentAction
from agentguard.llm.base import LLMProvider
from agentguard.validators.base import BaseValidator, ValidationResult, ValidationStatus

logger = logging.getLogger(__name__)

DRIFT_SYSTEM_PROMPT = """You are an agent trajectory analyzer. Given an agent's original goal, \
its action history so far, and the next proposed action, determine if the agent is still \
on track toward its goal.

Respond ONLY with valid JSON:
{"on_track": true, "drift_score": 0.1, "reason": "Brief explanation"}

Rules:
- "on_track": true if the action advances the goal, false if it's drifting.
- "drift_score": 0.0 (perfectly on track) to 1.0 (completely off track).
- "reason": Brief explanation."""


class TrajectoryStep(BaseModel):
    action_type: str
    target: str
    timestamp: float = Field(default_factory=time.time)
    was_blocked: bool = False


class SessionTrajectory(BaseModel):
    session_id: str
    goal: str = ""
    steps: list[TrajectoryStep] = Field(default_factory=list)
    consecutive_blocks: int = 0


class TrajectoryValidator(BaseValidator):
    """Tracks multi-step agent workflows and detects problems.

    Heuristic checks (no LLM):
    - Max step count exceeded
    - Repeated identical actions (possible infinite loop)
    - Cascading errors (consecutive blocks)

    Optional semantic drift detection (requires LLM):
    - Checks if current action aligns with original goal
    """

    name = "trajectory"

    def __init__(
        self,
        max_steps: int = 20,
        max_repeated_actions: int = 3,
        error_cascade_threshold: int = 2,
        drift_detection: bool = False,
        llm_provider: LLMProvider | None = None,
        drift_block_threshold: float = 0.9,
        drift_escalate_threshold: float = 0.7,
    ):
        self.max_steps = max_steps
        self.max_repeated_actions = max_repeated_actions
        self.error_cascade_threshold = error_cascade_threshold
        self.drift_detection = drift_detection
        self.llm_provider = llm_provider
        self.drift_block_threshold = drift_block_threshold
        self.drift_escalate_threshold = drift_escalate_threshold
        self._sessions: dict[str, SessionTrajectory] = {}

    def _get_session(self, action: AgentAction) -> SessionTrajectory:
        session_id = action.context.session_id
        if session_id not in self._sessions:
            self._sessions[session_id] = SessionTrajectory(
                session_id=session_id,
                goal=action.context.goal,
            )
        session = self._sessions[session_id]
        if not session.goal and action.context.goal:
            session.goal = action.context.goal
        return session

    async def validate(self, action: AgentAction) -> ValidationResult:
        session = self._get_session(action)

        # Check max steps
        if len(session.steps) >= self.max_steps:
            return ValidationResult(
                status=ValidationStatus.ESCALATE,
                reason=f"Agent has taken {len(session.steps)} steps (max: {self.max_steps})",
                confidence=0.9,
            )

        # Check repeated actions
        if session.steps:
            current_key = (action.action_type.value, action.target)
            repeat_count = 0
            for step in reversed(session.steps):
                if (step.action_type, step.target) == current_key:
                    repeat_count += 1
                else:
                    break

            if repeat_count >= self.max_repeated_actions:
                return ValidationResult(
                    status=ValidationStatus.BLOCKED,
                    reason=f"Repeated action detected ({repeat_count}x): {action.action_type.value} → {action.target}",
                    confidence=0.95,
                )

        # Check error cascade
        if session.consecutive_blocks >= self.error_cascade_threshold:
            return ValidationResult(
                status=ValidationStatus.BLOCKED,
                reason=f"Cascading errors: {session.consecutive_blocks} consecutive blocks",
                confidence=0.9,
            )

        # Optional: semantic drift detection
        if self.drift_detection and self.llm_provider and session.goal:
            drift_result = await self._check_drift(action, session)
            if drift_result is not None:
                # Record step before returning
                session.steps.append(
                    TrajectoryStep(action_type=action.action_type.value, target=action.target)
                )
                session.consecutive_blocks = 0
                return drift_result

        # Record step
        session.steps.append(
            TrajectoryStep(action_type=action.action_type.value, target=action.target)
        )
        session.consecutive_blocks = 0

        return ValidationResult(
            status=ValidationStatus.APPROVED,
            reason=f"Trajectory check passed (step {len(session.steps)})",
            metadata={"step_count": len(session.steps)},
        )

    def record_block(self, session_id: str) -> None:
        """Call this when an action is blocked to track cascading errors."""
        if session_id in self._sessions:
            session = self._sessions[session_id]
            session.consecutive_blocks += 1
            if session.steps:
                session.steps[-1].was_blocked = True

    async def _check_drift(
        self, action: AgentAction, session: SessionTrajectory
    ) -> ValidationResult | None:
        """Use LLM to check if the action drifts from the goal."""
        history = "\n".join(
            f"  {i+1}. {s.action_type} → {s.target}" for i, s in enumerate(session.steps[-10:])
        )

        user_prompt = (
            f"## Original Goal\n{session.goal}\n\n"
            f"## Action History (last {min(len(session.steps), 10)} steps)\n{history}\n\n"
            f"## Proposed Next Action\n"
            f"Type: {action.action_type.value}\n"
            f"Target: {action.target}\n"
            f"Payload: {json.dumps(action.payload, default=str)}"
        )

        try:
            response = await self.llm_provider.complete(
                system_prompt=DRIFT_SYSTEM_PROMPT,
                user_prompt=user_prompt,
                max_tokens=256,
            )
            data = json.loads(response.content.strip())
            drift_score = float(data.get("drift_score", 0.0))
            reason = data.get("reason", "")

            if drift_score >= self.drift_block_threshold:
                return ValidationResult(
                    status=ValidationStatus.BLOCKED,
                    reason=f"Severe goal drift ({drift_score:.2f}): {reason}",
                    confidence=drift_score,
                )
            if drift_score >= self.drift_escalate_threshold:
                return ValidationResult(
                    status=ValidationStatus.ESCALATE,
                    reason=f"Goal drift detected ({drift_score:.2f}): {reason}",
                    confidence=drift_score,
                )
        except Exception as e:
            logger.warning(f"Drift detection error: {e}")

        return None

    def reset_session(self, session_id: str) -> None:
        """Clear a session's trajectory history."""
        self._sessions.pop(session_id, None)

    def reset_all(self) -> None:
        """Clear all session trajectories."""
        self._sessions.clear()
