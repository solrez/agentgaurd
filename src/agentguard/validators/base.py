"""Base validator interface and result types."""

from __future__ import annotations

from abc import ABC, abstractmethod
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field

from agentguard.core.action import AgentAction


class ValidationStatus(str, Enum):
    APPROVED = "approved"
    BLOCKED = "blocked"
    MODIFIED = "modified"
    ESCALATE = "escalate"
    SKIPPED = "skipped"


class ValidationResult(BaseModel):
    """Result from a single validator."""

    validator_name: str = ""
    status: ValidationStatus
    reason: str = ""
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    suggested_fix: dict[str, Any] | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    @property
    def passed(self) -> bool:
        return self.status in (ValidationStatus.APPROVED, ValidationStatus.SKIPPED)


class BaseValidator(ABC):
    """Base class for all validators.

    Subclass this and implement `validate` to create custom validators.
    """

    name: str = "base"

    @abstractmethod
    async def validate(self, action: AgentAction) -> ValidationResult:
        """Validate an agent action. Return a ValidationResult."""
        ...

    async def setup(self) -> None:
        """Optional setup hook called once before first validation."""

    async def teardown(self) -> None:
        """Optional cleanup hook."""

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}>"
