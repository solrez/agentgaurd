"""Tests for semantic checker (mocked LLM, no API calls)."""

import pytest
from unittest.mock import AsyncMock

from agentguard.core.action import ActionType, AgentAction, ActionContext
from agentguard.llm.base import LLMResponse
from agentguard.validators.base import ValidationStatus
from agentguard.validators.semantic import SemanticChecker


def _make_provider(content: str) -> AsyncMock:
    provider = AsyncMock()
    provider.complete.return_value = LLMResponse(content=content, model="test")
    return provider


def _make_action(target="/api/users", grounding_docs=None, **payload) -> AgentAction:
    return AgentAction(
        action_type=ActionType.API_CALL,
        target=target,
        payload=payload,
        context=ActionContext(grounding_docs=grounding_docs or []),
    )


@pytest.mark.asyncio
async def test_grounded_action_approved():
    provider = _make_provider('{"grounded": true, "confidence": 0.95, "reason": "Endpoint exists"}')
    checker = SemanticChecker(llm_provider=provider, grounding_docs=["API has /api/users endpoint"])

    result = await checker.validate(_make_action(target="/api/users"))
    assert result.status == ValidationStatus.APPROVED


@pytest.mark.asyncio
async def test_ungrounded_high_confidence_blocked():
    provider = _make_provider(
        '{"grounded": false, "confidence": 0.9, "reason": "Endpoint not in docs"}'
    )
    checker = SemanticChecker(llm_provider=provider, grounding_docs=["API has /api/users only"])

    result = await checker.validate(_make_action(target="/api/fake"))
    assert result.status == ValidationStatus.BLOCKED
    assert "Hallucination" in result.reason


@pytest.mark.asyncio
async def test_ungrounded_low_confidence_escalated():
    provider = _make_provider(
        '{"grounded": false, "confidence": 0.4, "reason": "Uncertain"}'
    )
    checker = SemanticChecker(llm_provider=provider, grounding_docs=["Some docs"])

    result = await checker.validate(_make_action())
    assert result.status == ValidationStatus.ESCALATE


@pytest.mark.asyncio
async def test_no_grounding_docs_skipped():
    provider = _make_provider("")
    checker = SemanticChecker(llm_provider=provider)

    result = await checker.validate(_make_action())
    assert result.status == ValidationStatus.SKIPPED
    assert "No grounding" in result.reason


@pytest.mark.asyncio
async def test_malformed_llm_response_escalated():
    provider = _make_provider("I'm not sure about this action.")
    checker = SemanticChecker(llm_provider=provider, grounding_docs=["Some docs"])

    result = await checker.validate(_make_action())
    assert result.status == ValidationStatus.ESCALATE
    assert "parse" in result.reason.lower()


@pytest.mark.asyncio
async def test_llm_error_escalated():
    provider = AsyncMock()
    provider.complete.side_effect = RuntimeError("API error")
    checker = SemanticChecker(llm_provider=provider, grounding_docs=["Some docs"])

    result = await checker.validate(_make_action())
    assert result.status == ValidationStatus.ESCALATE
    assert "failed" in result.reason.lower()


@pytest.mark.asyncio
async def test_docs_from_action_context():
    provider = _make_provider('{"grounded": true, "confidence": 0.9, "reason": "ok"}')
    checker = SemanticChecker(llm_provider=provider)

    # Docs come from action context, not constructor
    action = _make_action(grounding_docs=["User table has id, name, email"])
    result = await checker.validate(action)
    assert result.status == ValidationStatus.APPROVED


@pytest.mark.asyncio
async def test_markdown_wrapped_json_parsed():
    provider = _make_provider('```json\n{"grounded": true, "confidence": 0.9, "reason": "ok"}\n```')
    checker = SemanticChecker(llm_provider=provider, grounding_docs=["docs"])

    result = await checker.validate(_make_action())
    assert result.status == ValidationStatus.APPROVED
