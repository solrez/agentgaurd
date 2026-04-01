"""Configuration loader — build a Guard from YAML config."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from agentguard.core.action import ActionType
from agentguard.core.audit import FileAuditBackend, InMemoryAuditBackend
from agentguard.core.decision import DecisionAction
from agentguard.core.interceptor import Guard
from agentguard.validators.base import BaseValidator
from agentguard.validators.policy import PolicyEnforcer
from agentguard.validators.rate_limit import RateLimiter
from agentguard.validators.safety import SafetyPolicy, SafetyScorer
from agentguard.validators.code import CodeValidator
from agentguard.validators.schema import SchemaValidator
from agentguard.validators.trajectory import TrajectoryValidator


def _build_llm_provider(config: dict[str, Any]):
    """Build an LLM provider from config if specified."""
    llm_config = config.get("llm")
    if not llm_config:
        return None
    from agentguard.llm.base import get_provider

    return get_provider(
        provider=llm_config.get("provider", "anthropic"),
        model=llm_config.get("model"),
        api_key=llm_config.get("api_key"),
    )


def load_config(path: str | Path) -> dict[str, Any]:
    with open(path) as f:
        return yaml.safe_load(f)


def build_validators(config: dict[str, Any]) -> list[BaseValidator]:
    validators: list[BaseValidator] = []

    for v_config in config.get("validators", []):
        v_type = v_config.get("type")

        if v_type == "schema":
            validators.append(
                SchemaValidator(
                    allowed_targets=v_config.get("allowed_targets"),
                    blocked_targets=v_config.get("blocked_targets"),
                    required_fields=v_config.get("required_fields"),
                    schemas=v_config.get("schemas"),
                )
            )
        elif v_type == "safety":
            policy_config = v_config.get("policy", {})
            policy = SafetyPolicy(
                max_risk_level=policy_config.get("max_risk_level", "high"),
                blocked_patterns=policy_config.get("blocked_patterns"),
                blocked_action_types=[
                    ActionType(a) for a in policy_config.get("blocked_action_types", [])
                ],
                max_payload_size_bytes=policy_config.get("max_payload_size_bytes", 1_000_000),
            )
            validators.append(SafetyScorer(policy=policy))

        elif v_type == "rate_limit":
            validators.append(
                RateLimiter(
                    max_actions_per_minute=v_config.get("max_per_minute", 60),
                    max_actions_per_target_per_minute=v_config.get("max_per_target", 10),
                    window_seconds=v_config.get("window_seconds", 60.0),
                )
            )
        elif v_type == "policy":
            enforcer = PolicyEnforcer()
            for rule in v_config.get("rules", []):
                rule_type = rule.get("type")
                if rule_type == "block_target":
                    enforcer.block_target(rule["value"], reason=rule.get("reason", ""))
                elif rule_type == "block_action_type":
                    enforcer.block_action_type(
                        ActionType(rule["value"]), reason=rule.get("reason", "")
                    )
                elif rule_type == "require_field":
                    enforcer.require_field(rule["value"], reason=rule.get("reason", ""))
            validators.append(enforcer)

        elif v_type == "trajectory":
            llm_provider = None
            if v_config.get("drift_detection"):
                llm_provider = _build_llm_provider(config)
            validators.append(
                TrajectoryValidator(
                    max_steps=v_config.get("max_steps", 20),
                    max_repeated_actions=v_config.get("max_repeated_actions", 3),
                    error_cascade_threshold=v_config.get("error_cascade_threshold", 2),
                    drift_detection=v_config.get("drift_detection", False),
                    llm_provider=llm_provider,
                )
            )

        elif v_type == "code":
            validators.append(
                CodeValidator(
                    blocked_imports=v_config.get("blocked_imports"),
                    blocked_calls=v_config.get("blocked_calls"),
                    max_code_length=v_config.get("max_code_length", 50_000),
                    allow_network=v_config.get("allow_network", False),
                    allow_file_io=v_config.get("allow_file_io", False),
                    allow_subprocess=v_config.get("allow_subprocess", False),
                )
            )

        elif v_type == "semantic":
            from agentguard.validators.semantic import SemanticChecker

            validators.append(
                SemanticChecker(
                    provider=v_config.get("provider", "anthropic"),
                    model=v_config.get("model"),
                    api_key=v_config.get("api_key"),
                    grounding_docs=v_config.get("grounding_docs"),
                    confidence_threshold=v_config.get("confidence_threshold", 0.7),
                )
            )

    return validators


def guard_from_config(path: str | Path) -> Guard:
    """Build a Guard instance from a YAML config file."""
    config = load_config(path)
    validators = build_validators(config)

    guard_config = config.get("guard", {})

    audit_config = config.get("audit", {})
    audit_type = audit_config.get("type", "file")
    if audit_type == "file":
        audit_backend = FileAuditBackend(path=audit_config.get("path", "agentguard_audit.jsonl"))
    elif audit_type == "memory":
        audit_backend = InMemoryAuditBackend()
    else:
        audit_backend = FileAuditBackend()

    escalation_default = guard_config.get("default_on_escalation", "block")
    default_action = DecisionAction(escalation_default)

    return Guard(
        validators=validators,
        sequential=guard_config.get("sequential", False),
        fail_fast=guard_config.get("fail_fast", True),
        block_confidence_threshold=guard_config.get("block_confidence_threshold", 0.7),
        default_on_escalation=default_action,
        audit_backend=audit_backend,
        raise_on_block=guard_config.get("raise_on_block", True),
    )
