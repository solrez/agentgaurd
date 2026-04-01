"""Tests for safety scorer."""

import pytest

from agentguard.core.action import ActionType, AgentAction
from agentguard.validators.base import ValidationStatus
from agentguard.validators.safety import SafetyPolicy, SafetyScorer
from agentguard.core.action import RiskLevel


def _make_action(action_type=ActionType.API_CALL, target="/api/test", **payload) -> AgentAction:
    return AgentAction(action_type=action_type, target=target, payload=payload)


@pytest.mark.asyncio
async def test_safe_action_approved():
    scorer = SafetyScorer()
    result = await scorer.validate(_make_action())
    assert result.status == ValidationStatus.APPROVED


@pytest.mark.asyncio
async def test_dangerous_sql_blocked():
    scorer = SafetyScorer()
    result = await scorer.validate(
        _make_action(action_type=ActionType.DB_QUERY, query="DROP TABLE users")
    )
    assert result.status == ValidationStatus.BLOCKED


@pytest.mark.asyncio
async def test_rm_rf_blocked():
    scorer = SafetyScorer()
    result = await scorer.validate(
        _make_action(action_type=ActionType.CODE_EXECUTION, command="rm -rf /")
    )
    assert result.status == ValidationStatus.BLOCKED


@pytest.mark.asyncio
async def test_blocked_action_type():
    policy = SafetyPolicy(blocked_action_types=[ActionType.CODE_EXECUTION])
    scorer = SafetyScorer(policy=policy)
    result = await scorer.validate(
        _make_action(action_type=ActionType.CODE_EXECUTION, command="echo hello")
    )
    assert result.status == ValidationStatus.BLOCKED


@pytest.mark.asyncio
async def test_payload_size_limit():
    policy = SafetyPolicy(max_payload_size_bytes=100)
    scorer = SafetyScorer(policy=policy)
    result = await scorer.validate(_make_action(data="x" * 200))
    assert result.status == ValidationStatus.BLOCKED
    assert "size" in result.reason.lower()


@pytest.mark.asyncio
async def test_risk_elevation_for_destructive_keywords():
    policy = SafetyPolicy(max_risk_level=RiskLevel.MEDIUM)
    scorer = SafetyScorer(policy=policy)
    result = await scorer.validate(
        _make_action(action_type=ActionType.API_CALL, operation="delete all records")
    )
    assert result.status == ValidationStatus.BLOCKED


@pytest.mark.asyncio
async def test_risk_elevation_for_production_target():
    policy = SafetyPolicy(max_risk_level=RiskLevel.MEDIUM)
    scorer = SafetyScorer(policy=policy)
    result = await scorer.validate(
        _make_action(action_type=ActionType.API_CALL, target="production-db")
    )
    assert result.status == ValidationStatus.BLOCKED
