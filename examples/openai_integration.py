"""Example: Guarding OpenAI function calling.

Wraps the OpenAI client to intercept tool_calls before execution.
"""

import asyncio

from agentguard import Guard
from agentguard.core.audit import InMemoryAuditBackend
from agentguard.validators.schema import SchemaValidator
from agentguard.validators.safety import SafetyScorer
from agentguard.integrations.openai_agents import GuardedOpenAIClient


async def main():
    guard = Guard(
        validators=[
            SchemaValidator(
                allowed_targets=["get_stock_price", "send_notification"],
                blocked_targets=["execute_trade"],  # Too risky for autonomous
            ),
            SafetyScorer(),
        ],
        audit_backend=InMemoryAuditBackend(),
    )

    client = GuardedOpenAIClient(guard)

    response = await client.create_chat_completion(
        model="gpt-4o",
        messages=[{"role": "user", "content": "What's AAPL trading at?"}],
        tools=[
            {
                "type": "function",
                "function": {
                    "name": "get_stock_price",
                    "description": "Get current stock price",
                    "parameters": {
                        "type": "object",
                        "properties": {"symbol": {"type": "string"}},
                        "required": ["symbol"],
                    },
                },
            }
        ],
    )

    print("Response:", response)


if __name__ == "__main__":
    asyncio.run(main())
