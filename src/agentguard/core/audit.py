"""Audit logging — records every action decision for observability and compliance."""

from __future__ import annotations

import json
import time
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from agentguard.core.action import AgentAction
from agentguard.core.decision import Decision


class AuditEntry(BaseModel):
    """A single audit log entry."""

    timestamp: float = Field(default_factory=time.time)
    trace_id: str = ""
    agent_id: str = ""
    action_type: str = ""
    target: str = ""
    decision: str = ""
    reasons: list[str] = Field(default_factory=list)
    validators_run: list[str] = Field(default_factory=list)
    pipeline_latency_ms: float = 0.0
    metadata: dict[str, Any] = Field(default_factory=dict)

    @classmethod
    def from_decision(cls, action: AgentAction, decision: Decision, validators: list[str]) -> AuditEntry:
        return cls(
            trace_id=action.id,
            agent_id=action.context.agent_id,
            action_type=action.action_type.value,
            target=action.target,
            decision=decision.action.value,
            reasons=decision.reasons,
            validators_run=validators,
            pipeline_latency_ms=decision.pipeline_latency_ms,
        )


class AuditBackend(ABC):
    @abstractmethod
    async def log(self, entry: AuditEntry) -> None: ...

    async def query(self, **filters: Any) -> list[AuditEntry]:
        return []


class FileAuditBackend(AuditBackend):
    """Writes audit entries as JSON lines to a file."""

    def __init__(self, path: str | Path = "agentguard_audit.jsonl"):
        self.path = Path(path)

    async def log(self, entry: AuditEntry) -> None:
        with open(self.path, "a") as f:
            f.write(entry.model_dump_json() + "\n")

    async def query(self, **filters: Any) -> list[AuditEntry]:
        if not self.path.exists():
            return []

        entries = []
        for line in self.path.read_text().strip().split("\n"):
            if not line:
                continue
            entry = AuditEntry.model_validate(json.loads(line))
            match = all(getattr(entry, k, None) == v for k, v in filters.items())
            if match:
                entries.append(entry)
        return entries


class InMemoryAuditBackend(AuditBackend):
    """In-memory audit backend for testing."""

    def __init__(self) -> None:
        self.entries: list[AuditEntry] = []

    async def log(self, entry: AuditEntry) -> None:
        self.entries.append(entry)

    async def query(self, **filters: Any) -> list[AuditEntry]:
        return [
            e
            for e in self.entries
            if all(getattr(e, k, None) == v for k, v in filters.items())
        ]


class AuditLogger:
    """Manages audit logging across backends."""

    def __init__(self, backends: list[AuditBackend] | None = None):
        self.backends = backends or []

    async def log(self, entry: AuditEntry) -> None:
        for backend in self.backends:
            await backend.log(entry)

    async def log_decision(
        self, action: AgentAction, decision: Decision, validators: list[str]
    ) -> AuditEntry:
        entry = AuditEntry.from_decision(action, decision, validators)
        await self.log(entry)
        return entry
