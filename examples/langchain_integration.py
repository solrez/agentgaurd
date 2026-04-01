"""Example: Guarding LangChain agent tool calls.

Uses AgentGuardCallback to intercept every tool invocation
in a LangChain agent.
"""

from agentguard import Guard
from agentguard.core.audit import InMemoryAuditBackend
from agentguard.validators.schema import SchemaValidator
from agentguard.validators.safety import SafetyScorer
from agentguard.validators.rate_limit import RateLimiter

# AgentGuard setup
guard = Guard(
    validators=[
        SchemaValidator(
            allowed_targets=["search", "calculator", "weather"],
        ),
        SafetyScorer(),
        RateLimiter(max_actions_per_minute=20),
    ],
    audit_backend=InMemoryAuditBackend(),
)

# LangChain integration
# from agentguard.integrations.langchain import AgentGuardCallback
# from langchain.agents import AgentExecutor, create_react_agent
#
# callback = AgentGuardCallback(guard)
# agent_executor = AgentExecutor(
#     agent=agent,
#     tools=tools,
#     callbacks=[callback],  # Every tool call goes through AgentGuard
# )
#
# result = agent_executor.invoke({"input": "What's 25 * 4?"})

print("LangChain integration example — uncomment with actual LangChain setup")
print(f"Guard configured with {len(guard.pipeline.validators)} validators")
