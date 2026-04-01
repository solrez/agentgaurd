"""Policy enforcer — custom org-level rules for agent actions."""

from __future__ import annotations

from typing import Any, Callable

import yaml

from agentguard.core.action import AgentAction, ActionType
from agentguard.validators.base import BaseValidator, ValidationResult, ValidationStatus


class PolicyRule:
    """A single policy rule that can approve or block actions."""

    def __init__(
        self,
        name: str,
        condition: Callable[[AgentAction], bool],
        action: ValidationStatus = ValidationStatus.BLOCKED,
        reason: str = "",
    ):
        self.name = name
        self.condition = condition
        self.action = action
        self.reason = reason

    def evaluate(self, agent_action: AgentAction) -> ValidationResult | None:
        if self.condition(agent_action):
            return ValidationResult(
                status=self.action,
                reason=self.reason or f"Policy rule '{self.name}' triggered",
                confidence=1.0,
            )
        return None


class PolicyEnforcer(BaseValidator):
    """Enforces custom policy rules on agent actions."""

    name = "policy"

    def __init__(self, rules: list[PolicyRule] | None = None):
        self.rules = rules or []

    def add_rule(self, rule: PolicyRule) -> None:
        self.rules.append(rule)

    def block_action_type(self, action_type: ActionType, reason: str = "") -> None:
        self.add_rule(
            PolicyRule(
                name=f"block_{action_type.value}",
                condition=lambda a, at=action_type: a.action_type == at,
                action=ValidationStatus.BLOCKED,
                reason=reason or f"Action type '{action_type.value}' is not allowed",
            )
        )

    def block_target(self, target: str, reason: str = "") -> None:
        self.add_rule(
            PolicyRule(
                name=f"block_target_{target}",
                condition=lambda a, t=target: a.target == t,
                action=ValidationStatus.BLOCKED,
                reason=reason or f"Target '{target}' is not allowed",
            )
        )

    def require_field(self, field: str, reason: str = "") -> None:
        self.add_rule(
            PolicyRule(
                name=f"require_{field}",
                condition=lambda a, f=field: f not in a.payload,
                action=ValidationStatus.BLOCKED,
                reason=reason or f"Required field '{field}' is missing",
            )
        )

    @classmethod
    def from_yaml(cls, path: str) -> PolicyEnforcer:
        with open(path) as f:
            config = yaml.safe_load(f)

        enforcer = cls()
        for rule_config in config.get("rules", []):
            rule_type = rule_config.get("type")
            if rule_type == "block_action_type":
                enforcer.block_action_type(
                    ActionType(rule_config["value"]),
                    reason=rule_config.get("reason", ""),
                )
            elif rule_type == "block_target":
                enforcer.block_target(
                    rule_config["value"],
                    reason=rule_config.get("reason", ""),
                )
            elif rule_type == "require_field":
                enforcer.require_field(
                    rule_config["value"],
                    reason=rule_config.get("reason", ""),
                )
        return enforcer

    async def validate(self, action: AgentAction) -> ValidationResult:
        for rule in self.rules:
            result = rule.evaluate(action)
            if result is not None and not result.passed:
                return result

        return ValidationResult(
            status=ValidationStatus.APPROVED,
            reason="All policy rules passed",
        )
