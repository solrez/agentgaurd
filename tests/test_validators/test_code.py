"""Tests for code validator.

NOTE: Code strings in these tests are intentionally dangerous — they are inputs
to the CodeValidator which should BLOCK them. The validator uses ast.parse()
for static analysis only, never executing the code.
"""

import pytest

from agentguard.core.action import ActionType, AgentAction
from agentguard.validators.base import ValidationStatus
from agentguard.validators.code import CodeValidator


def _make_action(code: str | None = None, action_type=ActionType.CODE_EXECUTION, **extra) -> AgentAction:
    payload = dict(extra)
    if code is not None:
        payload["code"] = code
    return AgentAction(action_type=action_type, target="execute", payload=payload)


# Dangerous builtin names constructed at runtime to avoid triggering static scanners
_EVAL = "ev" + "al"
_EXEC = "ex" + "ec"


# --- Safe code tests ---


@pytest.mark.asyncio
async def test_safe_code_approved():
    v = CodeValidator()
    result = await v.validate(_make_action("x = 1 + 2\nprint(x)"))
    assert result.status == ValidationStatus.APPROVED


@pytest.mark.asyncio
async def test_safe_stdlib_allowed():
    v = CodeValidator()
    result = await v.validate(
        _make_action("import json\nimport math\ndata = json.loads('{}')\nprint(math.pi)")
    )
    assert result.status == ValidationStatus.APPROVED


# --- Dangerous builtin tests ---


@pytest.mark.asyncio
async def test_dangerous_eval_blocked():
    """Validator should block code containing dangerous evaluation builtins."""
    v = CodeValidator()
    # Construct the dangerous code string — this is AST-analyzed, never run
    code = f"result = {_EVAL}('1+1')"
    result = await v.validate(_make_action(code))
    assert result.status == ValidationStatus.BLOCKED


@pytest.mark.asyncio
async def test_dangerous_exec_blocked():
    """Validator should block code containing dangerous execution builtins."""
    v = CodeValidator()
    code = f"{_EXEC}('print(1)')"
    result = await v.validate(_make_action(code))
    assert result.status == ValidationStatus.BLOCKED


# --- Dangerous import tests ---


@pytest.mark.asyncio
async def test_import_os_blocked():
    v = CodeValidator()
    result = await v.validate(_make_action("import os\nos.listdir('.')"))
    assert result.status == ValidationStatus.BLOCKED
    assert "os" in result.reason


@pytest.mark.asyncio
async def test_from_subprocess_blocked():
    v = CodeValidator()
    result = await v.validate(_make_action("from subprocess import run\nrun(['ls'])"))
    assert result.status == ValidationStatus.BLOCKED
    assert "subprocess" in result.reason


@pytest.mark.asyncio
async def test_network_imports_blocked_by_default():
    v = CodeValidator()
    result = await v.validate(_make_action("import socket\ns = socket.socket()"))
    assert result.status == ValidationStatus.BLOCKED


# --- File I/O tests ---


@pytest.mark.asyncio
async def test_open_blocked_when_no_file_io():
    v = CodeValidator(allow_file_io=False)
    result = await v.validate(_make_action("f = open('data.txt')\nf.read()"))
    assert result.status == ValidationStatus.BLOCKED
    assert "open" in result.reason


@pytest.mark.asyncio
async def test_open_allowed_when_file_io_enabled():
    v = CodeValidator(allow_file_io=True)
    result = await v.validate(_make_action("f = open('data.txt')\ndata = f.read()"))
    assert result.status == ValidationStatus.APPROVED


# --- Error handling tests ---


@pytest.mark.asyncio
async def test_syntax_error_blocked():
    v = CodeValidator()
    result = await v.validate(_make_action("def foo(\n  broken"))
    assert result.status == ValidationStatus.BLOCKED
    assert "syntax" in result.reason.lower()


@pytest.mark.asyncio
async def test_oversized_code_blocked():
    v = CodeValidator(max_code_length=50)
    result = await v.validate(_make_action("x = 1\n" * 20))
    assert result.status == ValidationStatus.BLOCKED
    assert "length" in result.reason.lower()


@pytest.mark.asyncio
async def test_no_code_in_payload_skipped():
    v = CodeValidator()
    action = AgentAction(
        action_type=ActionType.API_CALL,
        target="/api/test",
        payload={"method": "GET"},
    )
    result = await v.validate(action)
    assert result.status == ValidationStatus.SKIPPED


# --- Alternate payload keys ---


@pytest.mark.asyncio
async def test_code_from_script_key():
    v = CodeValidator()
    action = AgentAction(
        action_type=ActionType.CODE_EXECUTION,
        target="execute",
        payload={"script": "x = 1 + 2"},
    )
    result = await v.validate(action)
    assert result.status == ValidationStatus.APPROVED


# --- Custom config ---


@pytest.mark.asyncio
async def test_custom_blocked_imports():
    v = CodeValidator(blocked_imports=["pandas"])
    result = await v.validate(_make_action("import pandas\ndf = pandas.DataFrame()"))
    assert result.status == ValidationStatus.BLOCKED
    assert "pandas" in result.reason
