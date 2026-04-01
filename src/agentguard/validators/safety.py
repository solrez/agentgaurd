"""Safety scorer — risk-scores actions and enforces safety policies."""

from __future__ import annotations

import re
from typing import Any

from agentguard.core.action import AgentAction, ActionType, RiskLevel
from agentguard.validators.base import BaseValidator, ValidationResult, ValidationStatus


class SafetyPolicy:
    """Defines what risk levels are acceptable."""

    def __init__(
        self,
        max_risk_level: RiskLevel = RiskLevel.HIGH,
        blocked_patterns: list[str] | None = None,
        require_confirmation_above: RiskLevel = RiskLevel.CRITICAL,
        blocked_action_types: list[ActionType] | None = None,
        max_payload_size_bytes: int = 1_000_000,
    ):
        self.max_risk_level = max_risk_level
        self.blocked_patterns = [re.compile(p, re.IGNORECASE) for p in (blocked_patterns or [])]
        self.require_confirmation_above = require_confirmation_above
        self.blocked_action_types = set(blocked_action_types or [])
        self.max_payload_size_bytes = max_payload_size_bytes


RISK_ORDER = {RiskLevel.LOW: 0, RiskLevel.MEDIUM: 1, RiskLevel.HIGH: 2, RiskLevel.CRITICAL: 3}

# Default patterns that indicate dangerous operations
DEFAULT_BLOCKED_PATTERNS = [
    r"DROP\s+TABLE",
    r"DELETE\s+FROM\s+\w+\s*$",  # DELETE without WHERE
    r"TRUNCATE\s+TABLE",
    r"rm\s+-rf\s+/",
    r"FORMAT\s+C:",
    r"sudo\s+rm",
]


class SafetyScorer(BaseValidator):
    """Scores actions for risk and enforces safety policies."""

    name = "safety"

    def __init__(self, policy: SafetyPolicy | None = None):
        self.policy = policy or SafetyPolicy(blocked_patterns=DEFAULT_BLOCKED_PATTERNS)

    async def validate(self, action: AgentAction) -> ValidationResult:
        # Check blocked action types
        if action.action_type in self.policy.blocked_action_types:
            return ValidationResult(
                status=ValidationStatus.BLOCKED,
                reason=f"Action type '{action.action_type.value}' is blocked by policy",
                confidence=1.0,
            )

        # Check risk level
        risk = self._compute_risk(action)
        if RISK_ORDER[risk] > RISK_ORDER[self.policy.max_risk_level]:
            return ValidationResult(
                status=ValidationStatus.BLOCKED,
                reason=f"Action risk level '{risk.value}' exceeds maximum '{self.policy.max_risk_level.value}'",
                confidence=0.9,
            )

        # Check if escalation needed
        if RISK_ORDER[risk] >= RISK_ORDER[self.policy.require_confirmation_above]:
            return ValidationResult(
                status=ValidationStatus.ESCALATE,
                reason=f"Action risk level '{risk.value}' requires human confirmation",
                confidence=0.9,
            )

        # Check payload for dangerous patterns
        payload_str = str(action.payload)
        for pattern in self.policy.blocked_patterns:
            if pattern.search(payload_str):
                return ValidationResult(
                    status=ValidationStatus.BLOCKED,
                    reason=f"Payload matches blocked pattern: {pattern.pattern}",
                    confidence=0.95,
                )

        # Check payload size
        payload_size = len(str(action.payload).encode())
        if payload_size > self.policy.max_payload_size_bytes:
            return ValidationResult(
                status=ValidationStatus.BLOCKED,
                reason=f"Payload size {payload_size} exceeds limit {self.policy.max_payload_size_bytes}",
                confidence=1.0,
            )

        return ValidationResult(
            status=ValidationStatus.APPROVED,
            reason=f"Safety check passed (risk: {risk.value})",
            metadata={"risk_level": risk.value},
        )

    def _compute_risk(self, action: AgentAction) -> RiskLevel:
        """Compute risk level based on action type and payload heuristics."""
        base_risk = action.risk_level

        # Elevate risk for destructive keywords in payload
        payload_str = str(action.payload).lower()
        destructive_keywords = ["delete", "drop", "remove", "destroy", "overwrite", "truncate"]
        if any(kw in payload_str for kw in destructive_keywords):
            if RISK_ORDER[base_risk] < RISK_ORDER[RiskLevel.HIGH]:
                return RiskLevel.HIGH

        # Elevate risk for sensitive targets
        sensitive_targets = ["production", "prod", "master", "main", "admin"]
        if any(t in action.target.lower() for t in sensitive_targets):
            if RISK_ORDER[base_risk] < RISK_ORDER[RiskLevel.HIGH]:
                return RiskLevel.HIGH

        return base_risk
