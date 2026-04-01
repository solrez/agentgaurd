# AgentGuard

**Real-time verification layer for AI agents.** Intercept, validate, and correct agent actions before they execute — preventing hallucination-driven failures in production.

> No one verifies what agents *do* before they do it. AgentGuard changes that.

---

## The Problem

AI agents hallucinate. They fabricate API endpoints, generate dangerous queries, loop endlessly, and act on confidence they don't deserve. In demos, this is funny. In production, it's catastrophic.

**Existing tools watch.** AgentGuard **prevents.**

## How It Works

AgentGuard sits between your agent's decision and the real world:

```
Agent decides → AgentGuard intercepts → Validators check → Execute or Block
```

Every tool call, API request, database query, or code execution gets verified through a pipeline of validators before it touches anything real.

## Install

```bash
pip install agentguard
```

With framework integrations:
```bash
pip install agentguard[anthropic]    # Claude tool_use
pip install agentguard[openai]       # OpenAI function calling
pip install agentguard[langchain]    # LangChain callbacks
pip install agentguard[dashboard]    # Management dashboard
```

## Quick Start

```python
import asyncio
from agentguard import Guard, AgentAction
from agentguard.core.action import ActionType
from agentguard.validators import SchemaValidator, SafetyScorer

guard = Guard(
    validators=[
        SchemaValidator(allowed_targets=["/api/users", "/api/orders"]),
        SafetyScorer(),
    ]
)

# This gets through
safe = AgentAction(action_type=ActionType.API_CALL, target="/api/users", payload={"method": "GET"})
decision = asyncio.run(guard.verify(safe))
print(decision.action)  # "execute"

# This gets blocked — target not in allowlist
hallucinated = AgentAction(action_type=ActionType.API_CALL, target="/api/fake-endpoint", payload={})
decision = asyncio.run(guard.verify(hallucinated))
print(decision.action)  # "block"
print(decision.reasons) # ["[schema] Target '/api/fake-endpoint' is not in the allowlist"]
```

## Framework Integrations

### Anthropic (Claude)

```python
from agentguard.integrations.anthropic import GuardedAnthropicClient

guard = Guard(validators=[SchemaValidator(...), SafetyScorer()])
client = GuardedAnthropicClient(guard)

# Use exactly like AsyncAnthropic — tool_use blocks get verified automatically
response = await client.create_message(
    model="claude-sonnet-4-20250514",
    messages=[{"role": "user", "content": "Delete all inactive users"}],
    tools=[...],
)
# If Claude hallucinates a tool → GuardError raised before execution
```

### OpenAI

```python
from agentguard.integrations.openai_agents import GuardedOpenAIClient

guard = Guard(validators=[...])
client = GuardedOpenAIClient(guard)

response = await client.create_chat_completion(
    model="gpt-4o",
    messages=[...],
    tools=[...],
)
```

### LangChain

```python
from agentguard.integrations.langchain import AgentGuardCallback

guard = Guard(validators=[...])
agent_executor = AgentExecutor(
    agent=agent,
    tools=tools,
    callbacks=[AgentGuardCallback(guard)]
)
```

### Decorator Pattern

```python
@guard.protect(action_type="api_call", target="/api/users")
async def call_api(endpoint="", data=None):
    return requests.post(endpoint, json=data)
# Blocked calls raise GuardError or return None
```

## Built-in Validators

| Validator | What It Catches | Needs LLM? |
|-----------|----------------|------------|
| **SchemaValidator** | Hallucinated endpoints, missing fields, wrong types | No |
| **SafetyScorer** | `DROP TABLE`, `rm -rf`, destructive patterns, payload bombs | No |
| **RateLimiter** | Runaway agents, infinite loops, API abuse | No |
| **PolicyEnforcer** | Custom org rules — block targets, require fields | No |
| **TrajectoryValidator** | Repeated actions, cascading errors, goal drift | Optional |
| **CodeValidator** | Dangerous imports (`os`, `subprocess`), `eval`/`exec`, unsafe code | No |
| **SemanticChecker** | Fabricated data, claims not grounded in source docs | Yes |

## Configuration

Define your guard in YAML:

```yaml
guard:
  block_confidence_threshold: 0.7
  default_on_escalation: block

validators:
  - type: schema
    allowed_targets: ["/api/users", "/api/orders"]
    blocked_targets: ["/api/admin/nuke"]

  - type: safety
    policy:
      max_risk_level: high
      blocked_patterns: ["DROP\\s+TABLE", "rm\\s+-rf"]

  - type: rate_limit
    max_per_minute: 60
    max_per_target: 10

  - type: trajectory
    max_steps: 20
    max_repeated_actions: 3

  - type: code
    allow_file_io: false
    allow_network: false
```

Load it:
```python
from agentguard.config.loader import guard_from_config
guard = guard_from_config("agentguard.yaml")
```

## CLI

```bash
# Generate a starter config
agentguard init

# Validate a single action
echo '{"action_type":"api_call","target":"/api/test"}' | agentguard validate -c agentguard.yaml

# Query audit logs
agentguard audit --decision block --limit 10

# Launch the management dashboard
agentguard dashboard
```

## Dashboard

Full management UI with real-time monitoring, analytics, config editing, and escalation approval.

```bash
pip install agentguard[dashboard]
agentguard dashboard
```

**Features:**
- Real-time activity feed with decision badges
- Analytics — block rate, latency distribution, validator effectiveness
- Config editor — modify guard settings and validators via UI
- Escalation queue — approve/reject actions that need human review

## Custom Validators

Build your own:

```python
from agentguard.validators.base import BaseValidator, ValidationResult, ValidationStatus

class MyValidator(BaseValidator):
    name = "my_validator"

    async def validate(self, action):
        if "production" in action.target:
            return ValidationResult(
                status=ValidationStatus.BLOCKED,
                reason="Production access requires approval",
                confidence=1.0,
            )
        return ValidationResult(status=ValidationStatus.APPROVED)

guard = Guard(validators=[MyValidator(), SafetyScorer()])
```

## Architecture

```
┌─────────────┐     ┌──────────────────────┐     ┌─────────────┐
│   Agent      │────▶│     AgentGuard        │────▶│  External   │
│  (any        │     │  Interceptor          │     │  World      │
│  framework)  │◀────│  → Validator Pipeline  │◀────│  (APIs,     │
│              │     │  → Decision Engine     │     │   DBs,      │
└──────────────┘     │  → Audit Logger        │     │   Tools)    │
                     └──────────────────────┘     └─────────────┘
```

## Why AgentGuard?

| | Guardrails AI | Lakera | Galileo | AgentGuard |
|---|---|---|---|---|
| **Focus** | Output format | Input security | Observability | **Action verification** |
| **When** | After generation | Before LLM | After execution | **Before execution** |
| **Prevents damage** | No | Partially | No | **Yes** |
| **Agent-native** | No | No | No | **Yes** |

## License

MIT

## Contributing

Contributions welcome. See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.
