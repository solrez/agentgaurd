"""Tests for the main Guard (interceptor)."""

import pytest

from agentguard import Guard, AgentAction, ActionContext
from agentguard.core.action import ActionType
from agentguard.core.audit import InMemoryAuditBackend
from agentguard.core.decision import DecisionAction
from agentguard.core.interceptor import GuardError
from agentguard.validators.base import BaseValidator, ValidationResult, ValidationStatus


class AlwaysApprove(BaseValidator):
    name = "always_approve"

    async def validate(self, action):
        return ValidationResult(status=ValidationStatus.APPROVED)


class AlwaysBlock(BaseValidator):
    name = "always_block"

    async def validate(self, action):
        return ValidationResult(
            status=ValidationStatus.BLOCKED, reason="Nope", confidence=0.95
        )


@pytest.mark.asyncio
async def test_guard_approves():
    audit = InMemoryAuditBackend()
    guard = Guard(validators=[AlwaysApprove()], audit_backend=audit)

    action = AgentAction(action_type=ActionType.API_CALL, target="/api/test")
    decision = await guard.verify(action)

    assert decision.should_execute
    assert decision.action == DecisionAction.EXECUTE
    assert len(audit.entries) == 1
    assert audit.entries[0].decision == "execute"


@pytest.mark.asyncio
async def test_guard_blocks():
    audit = InMemoryAuditBackend()
    guard = Guard(validators=[AlwaysBlock()], audit_backend=audit)

    action = AgentAction(action_type=ActionType.API_CALL, target="/api/test")
    decision = await guard.verify(action)

    assert not decision.should_execute
    assert decision.action == DecisionAction.BLOCK
    assert len(decision.reasons) > 0
    assert len(audit.entries) == 1


@pytest.mark.asyncio
async def test_guard_decorator_allows():
    guard = Guard(
        validators=[AlwaysApprove()],
        audit_backend=InMemoryAuditBackend(),
    )

    @guard.protect(action_type=ActionType.TOOL_CALL, target="get_user")
    async def get_user(user_id: int = 0):
        return {"id": user_id}

    result = await get_user(user_id=42)
    assert result == {"id": 42}


@pytest.mark.asyncio
async def test_guard_decorator_blocks_raises():
    guard = Guard(
        validators=[AlwaysBlock()],
        audit_backend=InMemoryAuditBackend(),
        raise_on_block=True,
    )

    @guard.protect(action_type=ActionType.TOOL_CALL, target="danger")
    async def danger(x: int = 0):
        return x

    with pytest.raises(GuardError):
        await danger(x=1)


@pytest.mark.asyncio
async def test_guard_decorator_blocks_returns_none():
    guard = Guard(
        validators=[AlwaysBlock()],
        audit_backend=InMemoryAuditBackend(),
        raise_on_block=False,
    )

    @guard.protect(action_type=ActionType.TOOL_CALL, target="danger")
    async def danger(x: int = 0):
        return x

    result = await danger(x=1)
    assert result is None


@pytest.mark.asyncio
async def test_audit_records_all_decisions():
    audit = InMemoryAuditBackend()
    guard = Guard(validators=[AlwaysApprove()], audit_backend=audit)

    for i in range(5):
        action = AgentAction(action_type=ActionType.API_CALL, target=f"/api/{i}")
        await guard.verify(action)

    assert len(audit.entries) == 5
