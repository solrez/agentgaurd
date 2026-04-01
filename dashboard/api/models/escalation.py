"""Escalation API response models."""

from __future__ import annotations

from datetime import datetime, timezone

from pydantic import BaseModel, Field, computed_field


class EscalationEntry(BaseModel):
    trace_id: str
    timestamp: float
    agent_id: str
    action_type: str
    target: str
    reasons: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
    status: str = "pending"

    @computed_field
    @property
    def timestamp_iso(self) -> str:
        return datetime.fromtimestamp(self.timestamp, tz=timezone.utc).isoformat()


class EscalationAction(BaseModel):
    action: str  # "approve" or "reject"
    reason: str = ""


from typing import Any
