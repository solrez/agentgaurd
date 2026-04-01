"""Tests for Anthropic integration (fully mocked)."""

import sys
import pytest
from unittest.mock import AsyncMock, MagicMock

from agentguard import Guard
from agentguard.core.audit import InMemoryAuditBackend
from agentguard.core.interceptor import GuardError
from agentguard.validators.base import BaseValidator, ValidationResult, ValidationStatus


class AlwaysApprove(BaseValidator):
    name = "always_approve"

    async def validate(self, action):
        return ValidationResult(status=ValidationStatus.APPROVED)


class AlwaysBlock(BaseValidator):
    name = "always_block"

    async def validate(self, action):
        return ValidationResult(status=ValidationStatus.BLOCKED, reason="Blocked", confidence=0.95)


@pytest.fixture
def mock_anthropic():
    """Mock the anthropic package."""
    mock_msg = MagicMock()
    mock_msg.type = "text"
    mock_msg.text = "Hello"

    mock_tool_use = MagicMock()
    mock_tool_use.type = "tool_use"
    mock_tool_use.name = "get_weather"
    mock_tool_use.input = {"location": "SF"}
    mock_tool_use.id = "toolu_123"

    mock_module = MagicMock()
    mock_module.AsyncAnthropic = MagicMock
    mock_module.types.Message = MagicMock

    sys.modules["anthropic"] = mock_module
    sys.modules["anthropic.types"] = mock_module.types

    yield {"text_block": mock_msg, "tool_use_block": mock_tool_use}

    sys.modules.pop("anthropic", None)
    sys.modules.pop("anthropic.types", None)
    for key in list(sys.modules.keys()):
        if "agentguard.integrations.anthropic" in key:
            sys.modules.pop(key, None)


def _make_response(blocks):
    response = MagicMock()
    response.content = blocks
    return response


@pytest.mark.asyncio
async def test_no_tool_use_passes_through(mock_anthropic):
    import importlib
    import agentguard.integrations.anthropic as anth_mod
    importlib.reload(anth_mod)

    mock_client = AsyncMock()
    mock_client.messages.create.return_value = _make_response([mock_anthropic["text_block"]])

    guard = Guard(validators=[AlwaysApprove()], audit_backend=InMemoryAuditBackend())
    guarded = anth_mod.GuardedAnthropicClient(guard, client=mock_client)

    response = await guarded.create_message(model="test", max_tokens=100, messages=[])
    assert len(response.content) == 1


@pytest.mark.asyncio
async def test_tool_use_approved(mock_anthropic):
    import importlib
    import agentguard.integrations.anthropic as anth_mod
    importlib.reload(anth_mod)

    mock_client = AsyncMock()
    mock_client.messages.create.return_value = _make_response([mock_anthropic["tool_use_block"]])

    audit = InMemoryAuditBackend()
    guard = Guard(validators=[AlwaysApprove()], audit_backend=audit)
    guarded = anth_mod.GuardedAnthropicClient(guard, client=mock_client)

    response = await guarded.create_message(model="test", max_tokens=100, messages=[])
    assert response is not None
    assert len(audit.entries) == 1
    assert audit.entries[0].target == "get_weather"


@pytest.mark.asyncio
async def test_tool_use_blocked_raises(mock_anthropic):
    import importlib
    import agentguard.integrations.anthropic as anth_mod
    importlib.reload(anth_mod)

    mock_client = AsyncMock()
    mock_client.messages.create.return_value = _make_response([mock_anthropic["tool_use_block"]])

    guard = Guard(validators=[AlwaysBlock()], audit_backend=InMemoryAuditBackend())
    guarded = anth_mod.GuardedAnthropicClient(guard, client=mock_client, raise_on_block=True)

    with pytest.raises(GuardError):
        await guarded.create_message(model="test", max_tokens=100, messages=[])


@pytest.mark.asyncio
async def test_multiple_blocks_all_checked(mock_anthropic):
    import importlib
    import agentguard.integrations.anthropic as anth_mod
    importlib.reload(anth_mod)

    tool2 = MagicMock()
    tool2.type = "tool_use"
    tool2.name = "search"
    tool2.input = {"q": "test"}
    tool2.id = "toolu_456"

    mock_client = AsyncMock()
    mock_client.messages.create.return_value = _make_response(
        [mock_anthropic["text_block"], mock_anthropic["tool_use_block"], tool2]
    )

    audit = InMemoryAuditBackend()
    guard = Guard(validators=[AlwaysApprove()], audit_backend=audit)
    guarded = anth_mod.GuardedAnthropicClient(guard, client=mock_client)

    await guarded.create_message(model="test", max_tokens=100, messages=[])
    # Should have audit entries for both tool_use blocks
    assert len(audit.entries) == 2
