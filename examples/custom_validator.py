"""Example: Building a custom validator.

Shows how to create domain-specific validation logic
that integrates with the AgentGuard pipeline.
"""

import asyncio

from agentguard import Guard, AgentAction, ActionContext
from agentguard.core.action import ActionType
from agentguard.core.audit import InMemoryAuditBackend
from agentguard.validators.base import BaseValidator, ValidationResult, ValidationStatus


class BusinessHoursValidator(BaseValidator):
    """Only allow certain actions during business hours."""

    name = "business_hours"

    def __init__(self, restricted_types: list[str] | None = None):
        self.restricted_types = set(restricted_types or ["send_message", "db_query"])

    async def validate(self, action: AgentAction) -> ValidationResult:
        from datetime import datetime

        hour = datetime.now().hour

        if action.action_type.value in self.restricted_types and (hour < 9 or hour >= 17):
            return ValidationResult(
                status=ValidationStatus.ESCALATE,
                reason=f"Action '{action.action_type.value}' requires approval outside business hours (9-17)",
                confidence=0.9,
            )

        return ValidationResult(status=ValidationStatus.APPROVED)


class PII_Detector(BaseValidator):
    """Block actions that contain potential PII in payloads."""

    name = "pii_detector"

    PII_PATTERNS = ["ssn", "social_security", "credit_card", "password", "secret"]

    async def validate(self, action: AgentAction) -> ValidationResult:
        payload_str = str(action.payload).lower()

        for pattern in self.PII_PATTERNS:
            if pattern in payload_str:
                return ValidationResult(
                    status=ValidationStatus.BLOCKED,
                    reason=f"Potential PII detected in payload: '{pattern}'",
                    confidence=0.85,
                )

        return ValidationResult(status=ValidationStatus.APPROVED)


async def main():
    guard = Guard(
        validators=[
            BusinessHoursValidator(),
            PII_Detector(),
        ],
        audit_backend=InMemoryAuditBackend(),
        raise_on_block=False,
    )

    # Safe action
    action1 = AgentAction(
        action_type=ActionType.API_CALL,
        target="/api/users",
        payload={"name": "Alice", "email": "alice@example.com"},
    )
    decision1 = await guard.verify(action1)
    print(f"Normal action: {decision1.action.value}")

    # Action with PII — gets blocked
    action2 = AgentAction(
        action_type=ActionType.API_CALL,
        target="/api/users",
        payload={"name": "Bob", "ssn": "123-45-6789"},
    )
    decision2 = await guard.verify(action2)
    print(f"PII action: {decision2.action.value}")
    print(f"Reason: {decision2.reasons}")


if __name__ == "__main__":
    asyncio.run(main())
