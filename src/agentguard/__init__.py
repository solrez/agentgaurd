"""AgentGuard — Real-time verification layer for AI agents."""

from agentguard.core.action import ActionContext, AgentAction
from agentguard.core.audit import AuditEntry, AuditLogger, FileAuditBackend, InMemoryAuditBackend
from agentguard.core.decision import Decision, DecisionEngine
from agentguard.core.interceptor import Guard, GuardError
from agentguard.core.pipeline import ValidatorPipeline
from agentguard.validators.base import BaseValidator, ValidationResult, ValidationStatus

__version__ = "0.1.0"

__all__ = [
    "Guard",
    "GuardError",
    "AgentAction",
    "ActionContext",
    "ValidatorPipeline",
    "DecisionEngine",
    "Decision",
    "AuditLogger",
    "AuditEntry",
    "FileAuditBackend",
    "InMemoryAuditBackend",
    "BaseValidator",
    "ValidationResult",
    "ValidationStatus",
]
