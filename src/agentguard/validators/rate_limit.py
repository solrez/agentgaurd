"""Rate limiter — prevents agents from executing too many actions too quickly."""

from __future__ import annotations

import time
from collections import defaultdict

from agentguard.core.action import AgentAction
from agentguard.validators.base import BaseValidator, ValidationResult, ValidationStatus


class RateLimiter(BaseValidator):
    """Rate-limits actions by target, action type, or agent.

    Uses a sliding window approach.
    """

    name = "rate_limit"

    def __init__(
        self,
        max_actions_per_minute: int = 60,
        max_actions_per_target_per_minute: int = 10,
        window_seconds: float = 60.0,
    ):
        self.max_per_minute = max_actions_per_minute
        self.max_per_target = max_actions_per_target_per_minute
        self.window = window_seconds
        self._global_log: list[float] = []
        self._target_logs: dict[str, list[float]] = defaultdict(list)

    async def validate(self, action: AgentAction) -> ValidationResult:
        now = time.time()
        cutoff = now - self.window

        # Clean and check global rate
        self._global_log = [t for t in self._global_log if t > cutoff]
        if len(self._global_log) >= self.max_per_minute:
            return ValidationResult(
                status=ValidationStatus.BLOCKED,
                reason=f"Global rate limit exceeded: {len(self._global_log)}/{self.max_per_minute} per {self.window}s",
                confidence=1.0,
            )

        # Clean and check per-target rate
        target_log = self._target_logs[action.target]
        self._target_logs[action.target] = [t for t in target_log if t > cutoff]
        if len(self._target_logs[action.target]) >= self.max_per_target:
            return ValidationResult(
                status=ValidationStatus.BLOCKED,
                reason=f"Rate limit for '{action.target}' exceeded: {len(self._target_logs[action.target])}/{self.max_per_target} per {self.window}s",
                confidence=1.0,
            )

        # Record this action
        self._global_log.append(now)
        self._target_logs[action.target].append(now)

        return ValidationResult(
            status=ValidationStatus.APPROVED,
            reason="Rate limit check passed",
        )
