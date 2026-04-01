"""Tests for trajectory validator."""

import pytest
from unittest.mock import AsyncMock

from agentguard.core.action import ActionType, AgentAction, ActionContext
from agentguard.llm.base import LLMResponse
from agentguard.validators.base import ValidationStatus
from agentguard.validators.trajectory import TrajectoryValidator


def _make_action(
    target="/api/test", session_id="sess-1", goal="Complete the task", action_type=ActionType.API_CALL
) -> AgentAction:
    return AgentAction(
        action_type=action_type,
        target=target,
        context=ActionContext(session_id=session_id, goal=goal),
    )


@pytest.mark.asyncio
async def test_normal_progression_approved():
    tv = TrajectoryValidator(max_steps=10)
    result = await tv.validate(_make_action(target="/api/step1"))
    assert result.status == ValidationStatus.APPROVED
    assert "step 1" in result.reason


@pytest.mark.asyncio
async def test_max_steps_exceeded():
    tv = TrajectoryValidator(max_steps=3)
    for i in range(3):
        await tv.validate(_make_action(target=f"/api/step{i}"))

    result = await tv.validate(_make_action(target="/api/step3"))
    assert result.status == ValidationStatus.ESCALATE
    assert "3 steps" in result.reason


@pytest.mark.asyncio
async def test_repeated_action_blocked():
    tv = TrajectoryValidator(max_repeated_actions=3)
    for _ in range(3):
        await tv.validate(_make_action(target="/api/same"))

    result = await tv.validate(_make_action(target="/api/same"))
    assert result.status == ValidationStatus.BLOCKED
    assert "Repeated" in result.reason


@pytest.mark.asyncio
async def test_error_cascade_blocked():
    tv = TrajectoryValidator(error_cascade_threshold=2)
    await tv.validate(_make_action())

    # Simulate 2 consecutive blocks
    tv.record_block("sess-1")
    tv.record_block("sess-1")

    result = await tv.validate(_make_action(target="/api/another"))
    assert result.status == ValidationStatus.BLOCKED
    assert "Cascading" in result.reason


@pytest.mark.asyncio
async def test_session_isolation():
    tv = TrajectoryValidator(max_steps=2)

    # Session 1 fills up
    await tv.validate(_make_action(target="/api/a", session_id="s1"))
    await tv.validate(_make_action(target="/api/b", session_id="s1"))

    # Session 1 should be at max
    result = await tv.validate(_make_action(target="/api/c", session_id="s1"))
    assert result.status == ValidationStatus.ESCALATE

    # Session 2 should still be fine
    result = await tv.validate(_make_action(target="/api/a", session_id="s2"))
    assert result.status == ValidationStatus.APPROVED


@pytest.mark.asyncio
async def test_different_actions_not_repeated():
    tv = TrajectoryValidator(max_repeated_actions=2)
    await tv.validate(_make_action(target="/api/a"))
    await tv.validate(_make_action(target="/api/b"))
    await tv.validate(_make_action(target="/api/a"))

    result = await tv.validate(_make_action(target="/api/b"))
    assert result.status == ValidationStatus.APPROVED


@pytest.mark.asyncio
async def test_reset_session():
    tv = TrajectoryValidator(max_steps=2)
    await tv.validate(_make_action(session_id="s1"))
    await tv.validate(_make_action(session_id="s1"))

    tv.reset_session("s1")

    result = await tv.validate(_make_action(session_id="s1"))
    assert result.status == ValidationStatus.APPROVED


@pytest.mark.asyncio
async def test_drift_detection_blocks():
    provider = AsyncMock()
    provider.complete.return_value = LLMResponse(
        content='{"on_track": false, "drift_score": 0.95, "reason": "Completely off goal"}'
    )

    tv = TrajectoryValidator(
        drift_detection=True,
        llm_provider=provider,
        drift_block_threshold=0.9,
    )
    await tv.validate(_make_action(target="/api/step1"))

    result = await tv.validate(_make_action(target="/api/random"))
    assert result.status == ValidationStatus.BLOCKED
    assert "drift" in result.reason.lower()


@pytest.mark.asyncio
async def test_drift_detection_escalates():
    provider = AsyncMock()
    provider.complete.return_value = LLMResponse(
        content='{"on_track": false, "drift_score": 0.75, "reason": "Slightly off"}'
    )

    tv = TrajectoryValidator(
        drift_detection=True,
        llm_provider=provider,
        drift_escalate_threshold=0.7,
        drift_block_threshold=0.9,
    )
    await tv.validate(_make_action(target="/api/step1"))

    result = await tv.validate(_make_action(target="/api/random"))
    assert result.status == ValidationStatus.ESCALATE
