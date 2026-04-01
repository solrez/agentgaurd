"""Tests for OpenAI integration (fully mocked)."""

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
def mock_openai():
    """Mock the openai package."""
    mock_module = MagicMock()
    mock_module.AsyncOpenAI = MagicMock
    mock_module.types.chat.ChatCompletion = MagicMock

    sys.modules["openai"] = mock_module
    sys.modules["openai.types"] = mock_module.types
    sys.modules["openai.types.chat"] = mock_module.types.chat

    yield
    sys.modules.pop("openai", None)
    sys.modules.pop("openai.types", None)
    sys.modules.pop("openai.types.chat", None)
    for key in list(sys.modules.keys()):
        if "agentguard.integrations.openai_agents" in key:
            sys.modules.pop(key, None)


def _make_response(tool_calls=None):
    """Create a mock ChatCompletion response."""
    choice = MagicMock()
    choice.message.tool_calls = tool_calls
    response = MagicMock()
    response.choices = [choice]
    return response


def _make_tool_call(name="get_data", arguments='{"key": "value"}', call_id="call_123"):
    tc = MagicMock()
    tc.function.name = name
    tc.function.arguments = arguments
    tc.id = call_id
    return tc


@pytest.mark.asyncio
async def test_no_tool_calls_passes_through(mock_openai):
    import importlib
    import agentguard.integrations.openai_agents as oai_mod
    importlib.reload(oai_mod)

    mock_client = AsyncMock()
    mock_client.chat.completions.create.return_value = _make_response(tool_calls=None)

    guard = Guard(validators=[AlwaysApprove()], audit_backend=InMemoryAuditBackend())
    guarded = oai_mod.GuardedOpenAIClient(guard, client=mock_client)

    response = await guarded.create_chat_completion(model="gpt-4o", messages=[])
    assert response is not None


@pytest.mark.asyncio
async def test_tool_call_approved(mock_openai):
    import importlib
    import agentguard.integrations.openai_agents as oai_mod
    importlib.reload(oai_mod)

    mock_client = AsyncMock()
    mock_client.chat.completions.create.return_value = _make_response(
        tool_calls=[_make_tool_call()]
    )

    audit = InMemoryAuditBackend()
    guard = Guard(validators=[AlwaysApprove()], audit_backend=audit)
    guarded = oai_mod.GuardedOpenAIClient(guard, client=mock_client)

    await guarded.create_chat_completion(model="gpt-4o", messages=[])
    assert len(audit.entries) == 1
    assert audit.entries[0].target == "get_data"


@pytest.mark.asyncio
async def test_tool_call_blocked_raises(mock_openai):
    import importlib
    import agentguard.integrations.openai_agents as oai_mod
    importlib.reload(oai_mod)

    mock_client = AsyncMock()
    mock_client.chat.completions.create.return_value = _make_response(
        tool_calls=[_make_tool_call()]
    )

    guard = Guard(validators=[AlwaysBlock()], audit_backend=InMemoryAuditBackend())
    guarded = oai_mod.GuardedOpenAIClient(guard, client=mock_client, raise_on_block=True)

    with pytest.raises(GuardError):
        await guarded.create_chat_completion(model="gpt-4o", messages=[])


@pytest.mark.asyncio
async def test_invalid_json_arguments_handled(mock_openai):
    import importlib
    import agentguard.integrations.openai_agents as oai_mod
    importlib.reload(oai_mod)

    mock_client = AsyncMock()
    mock_client.chat.completions.create.return_value = _make_response(
        tool_calls=[_make_tool_call(arguments="not valid json")]
    )

    audit = InMemoryAuditBackend()
    guard = Guard(validators=[AlwaysApprove()], audit_backend=audit)
    guarded = oai_mod.GuardedOpenAIClient(guard, client=mock_client)

    await guarded.create_chat_completion(model="gpt-4o", messages=[])
    assert len(audit.entries) == 1


@pytest.mark.asyncio
async def test_multiple_tool_calls(mock_openai):
    import importlib
    import agentguard.integrations.openai_agents as oai_mod
    importlib.reload(oai_mod)

    mock_client = AsyncMock()
    mock_client.chat.completions.create.return_value = _make_response(
        tool_calls=[
            _make_tool_call(name="tool_a", call_id="c1"),
            _make_tool_call(name="tool_b", call_id="c2"),
        ]
    )

    audit = InMemoryAuditBackend()
    guard = Guard(validators=[AlwaysApprove()], audit_backend=audit)
    guarded = oai_mod.GuardedOpenAIClient(guard, client=mock_client)

    await guarded.create_chat_completion(model="gpt-4o", messages=[])
    assert len(audit.entries) == 2
