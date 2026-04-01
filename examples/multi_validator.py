"""Example: Full validation pipeline with multiple validators.

Demonstrates how validators compose together to catch
different failure modes.
"""

import asyncio

from agentguard import Guard, AgentAction, ActionContext
from agentguard.core.action import ActionType
from agentguard.core.audit import InMemoryAuditBackend
from agentguard.validators.schema import SchemaValidator
from agentguard.validators.safety import SafetyScorer
from agentguard.validators.rate_limit import RateLimiter
from agentguard.validators.policy import PolicyEnforcer
from agentguard.validators.code import CodeValidator
from agentguard.validators.trajectory import TrajectoryValidator


async def main():
    # Build a comprehensive guard
    policy = PolicyEnforcer()
    policy.block_target("production-db", reason="Direct production access forbidden")
    policy.require_field("api_key", reason="All API calls must include api_key")

    guard = Guard(
        validators=[
            SchemaValidator(
                allowed_targets=["/api/users", "/api/orders", "/api/products"],
                blocked_targets=["/api/admin/delete-all"],
                required_fields={"api_call": ["method"]},
            ),
            SafetyScorer(),
            RateLimiter(max_actions_per_minute=30, max_actions_per_target_per_minute=5),
            policy,
            CodeValidator(allow_file_io=False, allow_network=False),
            TrajectoryValidator(max_steps=10, max_repeated_actions=3),
        ],
        audit_backend=InMemoryAuditBackend(),
        raise_on_block=False,
    )

    test_cases = [
        ("Valid API call", ActionType.API_CALL, "/api/users", {"method": "GET", "api_key": "abc123"}),
        ("Hallucinated endpoint", ActionType.API_CALL, "/api/nonexistent", {"method": "GET", "api_key": "abc123"}),
        ("Blocked admin target", ActionType.API_CALL, "/api/admin/delete-all", {"method": "DELETE", "api_key": "abc123"}),
        ("Missing required field", ActionType.API_CALL, "/api/users", {"api_key": "abc123"}),
        ("Dangerous SQL", ActionType.DB_QUERY, "/api/users", {"query": "DROP TABLE users", "api_key": "abc123"}),
        ("Production DB access", ActionType.DB_QUERY, "production-db", {"query": "SELECT 1", "api_key": "abc123"}),
        ("Safe code", ActionType.CODE_EXECUTION, "execute", {"code": "x = 1 + 2\nprint(x)", "api_key": "abc123"}),
        # NOTE: Unsafe code string below is a test input for CodeValidator — never executed
        ("Unsafe code", ActionType.CODE_EXECUTION, "execute", {"code": "import subprocess\nsubprocess.run(['ls'])", "api_key": "abc123"}),
    ]

    print("AgentGuard Multi-Validator Pipeline Demo")
    print("=" * 60)

    for label, action_type, target, payload in test_cases:
        action = AgentAction(
            action_type=action_type,
            target=target,
            payload=payload,
            context=ActionContext(agent_id="demo-agent", session_id="demo-session"),
        )
        decision = await guard.verify(action)

        status = "PASS" if decision.should_execute else "BLOCK"
        icon = "+" if decision.should_execute else "x"
        reasons = "; ".join(decision.reasons) if decision.reasons else ""
        print(f"  [{icon}] {label:30s} -> {status}")
        if reasons:
            print(f"      {reasons}")

    print("=" * 60)
    print(f"Pipeline: {len(guard.pipeline.validators)} validators active")


if __name__ == "__main__":
    asyncio.run(main())
