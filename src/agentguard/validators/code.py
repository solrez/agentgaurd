"""Code validator — static analysis for generated code using Python's ast module."""

from __future__ import annotations

import ast
from typing import Any

from agentguard.core.action import AgentAction, ActionType
from agentguard.validators.base import BaseValidator, ValidationResult, ValidationStatus

# Imports that are dangerous if used in agent-generated code
DEFAULT_BLOCKED_IMPORTS = {
    "os",
    "subprocess",
    "shutil",
    "socket",
    "http",
    "urllib",
    "requests",
    "ctypes",
    "marshal",
    "signal",
}

DEFAULT_BLOCKED_CALLS = {
    "eval",
    "exec",
    "compile",
    "__import__",
    "globals",
    "locals",
    "breakpoint",
}

FILESYSTEM_IMPORTS = {"pathlib", "io", "tempfile"}
NETWORK_IMPORTS = {"socket", "http", "urllib", "requests", "httpx", "aiohttp"}


class _DangerousPatternVisitor(ast.NodeVisitor):
    """AST visitor that collects dangerous code patterns."""

    def __init__(
        self,
        blocked_imports: set[str],
        blocked_calls: set[str],
        allow_file_io: bool,
        allow_network: bool,
        allow_subprocess: bool,
    ):
        self.blocked_imports = blocked_imports
        self.blocked_calls = blocked_calls
        self.allow_file_io = allow_file_io
        self.allow_network = allow_network
        self.allow_subprocess = allow_subprocess
        self.violations: list[str] = []

    def visit_Import(self, node: ast.Import) -> None:
        for alias in node.names:
            module = alias.name.split(".")[0]
            if self._is_blocked_import(module):
                self.violations.append(f"Blocked import: '{alias.name}' (line {node.lineno})")
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        if node.module:
            module = node.module.split(".")[0]
            if self._is_blocked_import(module):
                self.violations.append(
                    f"Blocked import: 'from {node.module}' (line {node.lineno})"
                )
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call) -> None:
        func_name = self._get_call_name(node)
        if func_name:
            # Check direct dangerous calls
            base_name = func_name.split(".")[-1]
            if base_name in self.blocked_calls:
                self.violations.append(
                    f"Blocked call: '{func_name}()' (line {node.lineno})"
                )

            # Check module-level dangerous calls
            if "." in func_name:
                module = func_name.split(".")[0]
                if self._is_blocked_import(module):
                    self.violations.append(
                        f"Blocked call: '{func_name}()' (line {node.lineno})"
                    )

            # Check open() when file I/O is blocked
            if not self.allow_file_io and base_name == "open":
                self.violations.append(
                    f"File I/O blocked: 'open()' (line {node.lineno})"
                )

        self.generic_visit(node)

    def _get_call_name(self, node: ast.Call) -> str | None:
        if isinstance(node.func, ast.Name):
            return node.func.id
        elif isinstance(node.func, ast.Attribute):
            parts = []
            current = node.func
            while isinstance(current, ast.Attribute):
                parts.append(current.attr)
                current = current.value
            if isinstance(current, ast.Name):
                parts.append(current.id)
            return ".".join(reversed(parts))
        return None

    def _is_blocked_import(self, module: str) -> bool:
        if module in self.blocked_imports:
            return True
        if not self.allow_file_io and module in FILESYSTEM_IMPORTS:
            return True
        if not self.allow_network and module in NETWORK_IMPORTS:
            return True
        if not self.allow_subprocess and module == "subprocess":
            return True
        return False


class CodeValidator(BaseValidator):
    """Validates generated code via static analysis.

    Uses Python's ast module to detect dangerous patterns:
    - Dangerous builtins (eval, exec, compile, etc.)
    - Blocked imports (os, subprocess, etc.)
    - File I/O, network access, subprocess calls (configurable)
    - Syntax errors
    """

    name = "code"

    def __init__(
        self,
        blocked_imports: list[str] | None = None,
        blocked_calls: list[str] | None = None,
        max_code_length: int = 50_000,
        allow_network: bool = False,
        allow_file_io: bool = False,
        allow_subprocess: bool = False,
    ):
        extra_imports = set(blocked_imports) if blocked_imports else set()
        extra_calls = set(blocked_calls) if blocked_calls else set()
        self._blocked_imports = DEFAULT_BLOCKED_IMPORTS | extra_imports
        self._blocked_calls = DEFAULT_BLOCKED_CALLS | extra_calls
        self.max_code_length = max_code_length
        self.allow_network = allow_network
        self.allow_file_io = allow_file_io
        self.allow_subprocess = allow_subprocess

    def _extract_code(self, action: AgentAction) -> str | None:
        """Extract code string from the action payload."""
        for key in ("code", "script", "source"):
            if key in action.payload:
                return str(action.payload[key])

        if action.action_type == ActionType.CODE_EXECUTION:
            # Try to find any string value that looks like code
            for value in action.payload.values():
                if isinstance(value, str) and len(value) > 10:
                    return value
        return None

    async def validate(self, action: AgentAction) -> ValidationResult:
        code = self._extract_code(action)
        if code is None:
            return ValidationResult(
                status=ValidationStatus.SKIPPED,
                reason="No code found in action payload",
            )

        # Check code length
        if len(code) > self.max_code_length:
            return ValidationResult(
                status=ValidationStatus.BLOCKED,
                reason=f"Code length {len(code)} exceeds maximum {self.max_code_length}",
                confidence=1.0,
            )

        # Parse AST
        try:
            tree = ast.parse(code)
        except SyntaxError as e:
            return ValidationResult(
                status=ValidationStatus.BLOCKED,
                reason=f"Code has syntax errors: {e}",
                confidence=1.0,
            )

        # Walk AST for dangerous patterns
        visitor = _DangerousPatternVisitor(
            blocked_imports=self._blocked_imports,
            blocked_calls=self._blocked_calls,
            allow_file_io=self.allow_file_io,
            allow_network=self.allow_network,
            allow_subprocess=self.allow_subprocess,
        )
        visitor.visit(tree)

        if visitor.violations:
            return ValidationResult(
                status=ValidationStatus.BLOCKED,
                reason=f"Code safety violations: {'; '.join(visitor.violations)}",
                confidence=0.95,
                metadata={"violations": visitor.violations},
            )

        return ValidationResult(
            status=ValidationStatus.APPROVED,
            reason="Code passed static analysis",
        )
