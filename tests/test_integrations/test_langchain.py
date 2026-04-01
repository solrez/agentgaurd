"""Tests for LangChain integration (mocked, no langchain dependency needed)."""

import sys
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

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
def mock_langchain():
    """Mock langchain_core.callbacks so we can import our integration."""
    mock_module = MagicMock()
    mock_module.AsyncCallbackHandler = type("AsyncCallbackHandler", (), {
        "on_tool_start": AsyncMock(),
        "name": "MockCallback",
    })
    sys.modules["langchain_core"] = MagicMock()
    sys.modules["langchain_core.callbacks"] = mock_module
    yield mock_module
    sys.modules.pop("langchain_core", None)
    sys.modules.pop("langchain_core.callbacks", None)
    # Clear cached import
    for key in list(sys.modules.keys()):
        if "agentguard.integrations.langchain" in key:
            sys.modules.pop(key, None)


@pytest.mark.asyncio
async def test_tool_start_approved(mock_langchain):
    import importlib
    import agentguard.integrations.langchain as lc_mod
    importlib.reload(lc_mod)

    guard = Guard(validators=[AlwaysApprove()], audit_backend=InMemoryAuditBackend())
    callback = lc_mod.AgentGuardCallback(guard)

    serialized = {"name": "search_tool", "id": ["search_tool"]}
    await callback.on_tool_start(serialized, '{"query": "test"}')
    # No exception = approved


@pytest.mark.asyncio
async def test_tool_start_blocked_raises(mock_langchain):
    import importlib
    import agentguard.integrations.langchain as lc_mod
    importlib.reload(lc_mod)

    guard = Guard(validators=[AlwaysBlock()], audit_backend=InMemoryAuditBackend())
    callback = lc_mod.AgentGuardCallback(guard, raise_on_block=True)

    serialized = {"name": "dangerous_tool"}
    with pytest.raises(GuardError):
        await callback.on_tool_start(serialized, '{"action": "delete"}')


@pytest.mark.asyncio
async def test_plain_string_input(mock_langchain):
    import importlib
    import agentguard.integrations.langchain as lc_mod
    importlib.reload(lc_mod)

    guard = Guard(validators=[AlwaysApprove()], audit_backend=InMemoryAuditBackend())
    callback = lc_mod.AgentGuardCallback(guard)

    serialized = {"name": "tool"}
    # Non-JSON input string should still work
    await callback.on_tool_start(serialized, "plain text input")


@pytest.mark.asyncio
async def test_audit_entry_created(mock_langchain):
    import importlib
    import agentguard.integrations.langchain as lc_mod
    importlib.reload(lc_mod)

    audit = InMemoryAuditBackend()
    guard = Guard(validators=[AlwaysApprove()], audit_backend=audit)
    callback = lc_mod.AgentGuardCallback(guard)

    await callback.on_tool_start({"name": "my_tool"}, '{}')
    assert len(audit.entries) == 1
    assert audit.entries[0].target == "my_tool"
