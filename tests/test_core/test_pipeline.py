"""Tests for the validator pipeline."""

import pytest

from agentguard.core.action import ActionType, AgentAction
from agentguard.core.pipeline import ValidatorPipeline
from agentguard.validators.base import BaseValidator, ValidationResult, ValidationStatus


class AlwaysApprove(BaseValidator):
    name = "always_approve"

    async def validate(self, action):
        return ValidationResult(status=ValidationStatus.APPROVED, reason="Always approved")


class AlwaysBlock(BaseValidator):
    name = "always_block"

    async def validate(self, action):
        return ValidationResult(
            status=ValidationStatus.BLOCKED, reason="Always blocked", confidence=0.95
        )


class AlwaysEscalate(BaseValidator):
    name = "always_escalate"

    async def validate(self, action):
        return ValidationResult(status=ValidationStatus.ESCALATE, reason="Needs review")


class RaisesError(BaseValidator):
    name = "raises_error"

    async def validate(self, action):
        raise RuntimeError("Validator crashed")


def _make_action(**kwargs) -> AgentAction:
    defaults = {"action_type": ActionType.API_CALL, "target": "/api/test"}
    defaults.update(kwargs)
    return AgentAction(**defaults)


@pytest.mark.asyncio
async def test_all_approve():
    pipeline = ValidatorPipeline([AlwaysApprove(), AlwaysApprove()])
    result = await pipeline.run(_make_action())
    assert result.all_passed
    assert not result.blocked
    assert len(result.results) == 2


@pytest.mark.asyncio
async def test_one_blocks():
    pipeline = ValidatorPipeline([AlwaysApprove(), AlwaysBlock()])
    result = await pipeline.run(_make_action())
    assert not result.all_passed
    assert result.blocked
    assert len(result.block_reasons) == 1


@pytest.mark.asyncio
async def test_sequential_fail_fast():
    pipeline = ValidatorPipeline(
        [AlwaysBlock(), AlwaysApprove()], sequential=True, fail_fast=True
    )
    result = await pipeline.run(_make_action())
    assert result.blocked
    # Should have stopped after the first block
    assert len(result.results) == 1


@pytest.mark.asyncio
async def test_escalation():
    pipeline = ValidatorPipeline([AlwaysApprove(), AlwaysEscalate()])
    result = await pipeline.run(_make_action())
    assert result.needs_escalation
    assert not result.blocked


@pytest.mark.asyncio
async def test_validator_error_becomes_escalation():
    pipeline = ValidatorPipeline([RaisesError()])
    result = await pipeline.run(_make_action())
    assert result.needs_escalation
    assert "Validator error" in result.results[0].reason


@pytest.mark.asyncio
async def test_empty_pipeline():
    pipeline = ValidatorPipeline([])
    result = await pipeline.run(_make_action())
    assert result.all_passed
    assert len(result.results) == 0


@pytest.mark.asyncio
async def test_latency_tracked():
    pipeline = ValidatorPipeline([AlwaysApprove()])
    result = await pipeline.run(_make_action())
    assert result.latency_ms >= 0
