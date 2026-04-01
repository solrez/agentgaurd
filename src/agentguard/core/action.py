"""Core action types that represent what an agent is about to do."""

from __future__ import annotations

import time
import uuid
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class ActionType(str, Enum):
    API_CALL = "api_call"
    DB_QUERY = "db_query"
    FILE_WRITE = "file_write"
    FILE_READ = "file_read"
    SEND_MESSAGE = "send_message"
    CODE_EXECUTION = "code_execution"
    TOOL_CALL = "tool_call"
    HTTP_REQUEST = "http_request"
    CUSTOM = "custom"


class RiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ActionContext(BaseModel):
    """The surrounding context for an agent action."""

    agent_id: str = ""
    session_id: str = Field(default_factory=lambda: uuid.uuid4().hex[:12])
    goal: str = ""
    conversation_history: list[dict[str, Any]] = Field(default_factory=list)
    previous_actions: list[str] = Field(default_factory=list)
    grounding_docs: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class AgentAction(BaseModel):
    """Represents a single action an agent is about to take."""

    id: str = Field(default_factory=lambda: uuid.uuid4().hex[:16])
    action_type: ActionType
    target: str
    payload: dict[str, Any] = Field(default_factory=dict)
    context: ActionContext = Field(default_factory=ActionContext)
    metadata: dict[str, Any] = Field(default_factory=dict)
    timestamp: float = Field(default_factory=time.time)

    @property
    def risk_level(self) -> RiskLevel:
        """Infer a baseline risk level from the action type."""
        high_risk = {ActionType.DB_QUERY, ActionType.CODE_EXECUTION, ActionType.FILE_WRITE}
        medium_risk = {ActionType.API_CALL, ActionType.HTTP_REQUEST, ActionType.SEND_MESSAGE}

        if self.action_type in high_risk:
            return RiskLevel.HIGH
        if self.action_type in medium_risk:
            return RiskLevel.MEDIUM
        return RiskLevel.LOW
