"""Audit API response models."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, Field, computed_field


class AuditEntryResponse(BaseModel):
    timestamp: float
    trace_id: str
    agent_id: str
    action_type: str
    target: str
    decision: str
    reasons: list[str] = Field(default_factory=list)
    validators_run: list[str] = Field(default_factory=list)
    pipeline_latency_ms: float = 0.0
    metadata: dict[str, Any] = Field(default_factory=dict)

    @computed_field
    @property
    def timestamp_iso(self) -> str:
        return datetime.fromtimestamp(self.timestamp, tz=timezone.utc).isoformat()


class AuditListResponse(BaseModel):
    entries: list[AuditEntryResponse]
    total: int
    page: int
    page_size: int
