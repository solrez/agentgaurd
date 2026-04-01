"""Basic usage example for AgentGuard."""

import asyncio

from agentguard import Guard, AgentAction, ActionContext
from agentguard.core.action import ActionType
from agentguard.core.audit import InMemoryAuditBackend
from agentguard.validators.schema import SchemaValidator
from agentguard.validators.safety import SafetyScorer
from agentguard.validators.rate_limit import RateLimiter


async def main():
    # 1. Create a guard with validators
    guard = Guard(
        validators=[
            SchemaValidator(
                allowed_targets=["/api/users", "/api/orders"],
                blocked_targets=["/api/admin/nuke"],
            ),
            SafetyScorer(),
            RateLimiter(max_actions_per_minute=10),
        ],
        audit_backend=InMemoryAuditBackend(),
        raise_on_block=False,
    )

    # 2. Verify a safe action
    safe_action = AgentAction(
        action_type=ActionType.API_CALL,
        target="/api/users",
        payload={"method": "GET", "user_id": 123},
        context=ActionContext(agent_id="my-agent", goal="Look up user info"),
    )

    decision = await guard.verify(safe_action)
    print(f"Safe action: {decision.action.value}")
    # Output: Safe action: execute

    # 3. Verify a dangerous action
    dangerous_action = AgentAction(
        action_type=ActionType.DB_QUERY,
        target="/api/admin/nuke",
        payload={"query": "DROP TABLE users"},
    )

    decision = await guard.verify(dangerous_action)
    print(f"Dangerous action: {decision.action.value}")
    print(f"Reasons: {decision.reasons}")
    # Output: Dangerous action: block
    # Output: Reasons: [...]

    # 4. Use as a decorator
    @guard.protect(action_type=ActionType.API_CALL, target="/api/users")
    async def get_user(user_id: int = 0):
        return {"id": user_id, "name": "Alice"}

    result = await get_user(user_id=42)
    print(f"Decorated call result: {result}")

    # 5. Verify an unknown target (not in allowlist)
    unknown_action = AgentAction(
        action_type=ActionType.API_CALL,
        target="/api/hallucinated-endpoint",
        payload={"method": "POST", "data": "fake"},
    )

    decision = await guard.verify(unknown_action)
    print(f"Unknown target: {decision.action.value}")
    print(f"Reasons: {decision.reasons}")
    # Output: Unknown target: block (not in allowlist)


if __name__ == "__main__":
    asyncio.run(main())
