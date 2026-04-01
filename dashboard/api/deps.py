"""Shared dashboard dependencies."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from agentguard.core.audit import AuditEntry, FileAuditBackend


class DashboardState:
    """Holds shared state for the dashboard API."""

    def __init__(self, audit_path: str = "agentguard_audit.jsonl", config_path: str = "agentguard.yaml"):
        self.audit_path = Path(audit_path)
        self.config_path = Path(config_path)
        self.escalation_path = self.audit_path.parent / "escalation_status.json"

    def load_all_entries(self) -> list[AuditEntry]:
        if not self.audit_path.exists():
            return []
        entries = []
        for line in self.audit_path.read_text().strip().split("\n"):
            if not line:
                continue
            try:
                entries.append(AuditEntry.model_validate(json.loads(line)))
            except Exception:
                continue
        return entries

    def load_escalation_status(self) -> dict[str, dict[str, Any]]:
        if not self.escalation_path.exists():
            return {}
        try:
            return json.loads(self.escalation_path.read_text())
        except Exception:
            return {}

    def save_escalation_status(self, data: dict[str, dict[str, Any]]) -> None:
        self.escalation_path.write_text(json.dumps(data, indent=2))

    def load_config_raw(self) -> str:
        if not self.config_path.exists():
            return ""
        return self.config_path.read_text()

    def save_config_raw(self, content: str) -> None:
        self.config_path.write_text(content)
