"""Tests for schema validator."""

import pytest

from agentguard.core.action import ActionType, AgentAction
from agentguard.validators.base import ValidationStatus
from agentguard.validators.schema import SchemaValidator


def _make_action(target="/api/users", **payload) -> AgentAction:
    return AgentAction(action_type=ActionType.API_CALL, target=target, payload=payload)


@pytest.mark.asyncio
async def test_allowed_target():
    v = SchemaValidator(allowed_targets=["/api/users", "/api/orders"])
    result = await v.validate(_make_action(target="/api/users"))
    assert result.status == ValidationStatus.APPROVED


@pytest.mark.asyncio
async def test_blocked_target():
    v = SchemaValidator(blocked_targets=["/api/admin"])
    result = await v.validate(_make_action(target="/api/admin"))
    assert result.status == ValidationStatus.BLOCKED
    assert "blocked" in result.reason.lower()


@pytest.mark.asyncio
async def test_unknown_target_not_in_allowlist():
    v = SchemaValidator(allowed_targets=["/api/users"])
    result = await v.validate(_make_action(target="/api/hallucinated"))
    assert result.status == ValidationStatus.BLOCKED
    assert "allowlist" in result.reason.lower()


@pytest.mark.asyncio
async def test_no_allowlist_means_all_allowed():
    v = SchemaValidator()
    result = await v.validate(_make_action(target="/literally/anything"))
    assert result.status == ValidationStatus.APPROVED


@pytest.mark.asyncio
async def test_required_fields_present():
    v = SchemaValidator(required_fields={"api_call": ["method", "url"]})
    result = await v.validate(_make_action(method="GET", url="/users"))
    assert result.status == ValidationStatus.APPROVED


@pytest.mark.asyncio
async def test_required_fields_missing():
    v = SchemaValidator(required_fields={"api_call": ["method", "url"]})
    result = await v.validate(_make_action(method="GET"))
    assert result.status == ValidationStatus.BLOCKED
    assert "url" in result.reason


@pytest.mark.asyncio
async def test_field_type_check():
    v = SchemaValidator(field_types={"user_id": int})
    result = await v.validate(_make_action(user_id="not_an_int"))
    assert result.status == ValidationStatus.BLOCKED
    assert "user_id" in result.reason


@pytest.mark.asyncio
async def test_schema_required_fields():
    v = SchemaValidator(
        schemas={
            "/api/users": {
                "required_fields": ["name", "email"],
                "allowed_fields": ["name", "email", "role"],
            }
        }
    )
    result = await v.validate(_make_action(target="/api/users", name="Alice", email="a@b.com"))
    assert result.status == ValidationStatus.APPROVED


@pytest.mark.asyncio
async def test_schema_extra_fields_blocked():
    v = SchemaValidator(
        schemas={
            "/api/users": {
                "required_fields": ["name"],
                "allowed_fields": ["name", "email"],
            }
        }
    )
    result = await v.validate(
        _make_action(target="/api/users", name="Alice", hacked_field="evil")
    )
    assert result.status == ValidationStatus.BLOCKED
    assert "unexpected" in result.reason.lower()
