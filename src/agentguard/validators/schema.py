"""Schema validator — checks agent actions against API/data schemas."""

from __future__ import annotations

from typing import Any

import yaml

from agentguard.core.action import AgentAction
from agentguard.validators.base import BaseValidator, ValidationResult, ValidationStatus


class SchemaValidator(BaseValidator):
    """Validates agent actions against known schemas.

    Supports:
    - Allowlists of valid targets (endpoints, tables, etc.)
    - Required/forbidden fields in payloads
    - Type checking on payload values
    """

    name = "schema"

    def __init__(
        self,
        allowed_targets: list[str] | None = None,
        blocked_targets: list[str] | None = None,
        required_fields: dict[str, list[str]] | None = None,
        field_types: dict[str, type] | None = None,
        schemas: dict[str, dict[str, Any]] | None = None,
    ):
        self.allowed_targets = set(allowed_targets) if allowed_targets else None
        self.blocked_targets = set(blocked_targets) if blocked_targets else set()
        self.required_fields = required_fields or {}
        self.field_types = field_types or {}
        self.schemas = schemas or {}

    @classmethod
    def from_yaml(cls, path: str) -> SchemaValidator:
        with open(path) as f:
            config = yaml.safe_load(f)
        return cls(**config)

    async def validate(self, action: AgentAction) -> ValidationResult:
        # Check blocked targets
        if action.target in self.blocked_targets:
            return ValidationResult(
                status=ValidationStatus.BLOCKED,
                reason=f"Target '{action.target}' is explicitly blocked",
                confidence=1.0,
            )

        # Check allowed targets
        if self.allowed_targets is not None and action.target not in self.allowed_targets:
            return ValidationResult(
                status=ValidationStatus.BLOCKED,
                reason=f"Target '{action.target}' is not in the allowlist",
                confidence=1.0,
            )

        # Check required fields for this action type
        required = self.required_fields.get(action.action_type.value, [])
        missing = [f for f in required if f not in action.payload]
        if missing:
            return ValidationResult(
                status=ValidationStatus.BLOCKED,
                reason=f"Missing required fields: {missing}",
                confidence=1.0,
            )

        # Check field types
        for field_name, expected_type in self.field_types.items():
            if field_name in action.payload:
                value = action.payload[field_name]
                if not isinstance(value, expected_type):
                    return ValidationResult(
                        status=ValidationStatus.BLOCKED,
                        reason=f"Field '{field_name}' expected {expected_type.__name__}, got {type(value).__name__}",
                        confidence=1.0,
                    )

        # Check against registered schemas
        if action.target in self.schemas:
            schema = self.schemas[action.target]
            schema_required = schema.get("required_fields", [])
            missing = [f for f in schema_required if f not in action.payload]
            if missing:
                return ValidationResult(
                    status=ValidationStatus.BLOCKED,
                    reason=f"Schema violation for '{action.target}': missing {missing}",
                    confidence=1.0,
                )

            allowed_fields = schema.get("allowed_fields")
            if allowed_fields:
                extra = [f for f in action.payload if f not in allowed_fields]
                if extra:
                    return ValidationResult(
                        status=ValidationStatus.BLOCKED,
                        reason=f"Schema violation for '{action.target}': unexpected fields {extra}",
                        confidence=0.9,
                    )

        return ValidationResult(
            status=ValidationStatus.APPROVED,
            reason="Schema validation passed",
        )
