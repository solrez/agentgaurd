"""Example: Guarding Anthropic Claude tool_use calls.

This wraps the Anthropic client so every tool_use block in Claude's
response gets verified before your code executes it.
"""

import asyncio

from agentguard import Guard
from agentguard.core.audit import InMemoryAuditBackend
from agentguard.validators.schema import SchemaValidator
from agentguard.validators.safety import SafetyScorer
from agentguard.integrations.anthropic import GuardedAnthropicClient


async def main():
    # Define what tools are allowed and what's dangerous
    guard = Guard(
        validators=[
            SchemaValidator(
                allowed_targets=["get_weather", "search_docs", "send_email"],
                blocked_targets=["delete_account", "run_sql"],
            ),
            SafetyScorer(),
        ],
        audit_backend=InMemoryAuditBackend(),
    )

    # Wrap the Anthropic client
    client = GuardedAnthropicClient(guard)

    # Now use it exactly like normal — AgentGuard checks every tool_use
    response = await client.create_message(
        model="claude-sonnet-4-20250514",
        max_tokens=1024,
        messages=[{"role": "user", "content": "What's the weather in SF?"}],
        tools=[
            {
                "name": "get_weather",
                "description": "Get current weather for a city",
                "input_schema": {
                    "type": "object",
                    "properties": {"city": {"type": "string"}},
                    "required": ["city"],
                },
            }
        ],
    )

    print("Response:", response)


if __name__ == "__main__":
    asyncio.run(main())
