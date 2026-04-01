"""AgentGuard CLI — validate actions, query audit logs, and generate configs."""

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

import click

from agentguard.core.action import AgentAction
from agentguard.core.audit import FileAuditBackend


@click.group()
@click.version_option(package_name="agentguard")
def cli():
    """AgentGuard — Real-time verification layer for AI agents."""


@cli.command()
@click.argument("json_input", type=click.File("r"), default="-")
@click.option("--config", "-c", type=click.Path(exists=True), help="Guard config YAML file")
def validate(json_input, config):
    """Validate a single agent action from JSON.

    Reads JSON from a file or stdin. Returns the decision as JSON.
    Exit code 0 = execute/modify, exit code 1 = block/escalate.
    """
    try:
        data = json.load(json_input)
    except json.JSONDecodeError as e:
        click.echo(f"Error: Invalid JSON input: {e}", err=True)
        sys.exit(2)

    try:
        action = AgentAction.model_validate(data)
    except Exception as e:
        click.echo(f"Error: Invalid action format: {e}", err=True)
        sys.exit(2)

    if config:
        from agentguard.config.loader import guard_from_config

        guard = guard_from_config(config)
    else:
        # Try default config
        default_config = Path("agentguard.yaml")
        if default_config.exists():
            from agentguard.config.loader import guard_from_config

            guard = guard_from_config(default_config)
        else:
            from agentguard import Guard
            from agentguard.core.audit import InMemoryAuditBackend
            from agentguard.validators.safety import SafetyScorer
            from agentguard.validators.schema import SchemaValidator

            guard = Guard(
                validators=[SchemaValidator(), SafetyScorer()],
                audit_backend=InMemoryAuditBackend(),
            )

    decision = asyncio.run(guard.verify(action))

    output = {
        "decision": decision.action.value,
        "should_execute": decision.should_execute,
        "reasons": decision.reasons,
        "latency_ms": round(decision.pipeline_latency_ms, 2),
    }
    click.echo(json.dumps(output, indent=2))

    if not decision.should_execute:
        sys.exit(1)


@cli.command()
@click.option("--path", "-p", default="agentguard_audit.jsonl", help="Audit log file path")
@click.option("--agent-id", help="Filter by agent ID")
@click.option("--target", help="Filter by target")
@click.option(
    "--decision",
    "decision_filter",
    type=click.Choice(["execute", "block", "modify", "escalate"]),
    help="Filter by decision",
)
@click.option("--limit", "-n", default=20, help="Max entries to show")
def audit(path, agent_id, target, decision_filter, limit):
    """Query audit logs."""
    audit_path = Path(path)
    if not audit_path.exists():
        click.echo(f"Audit file not found: {path}", err=True)
        sys.exit(1)

    backend = FileAuditBackend(path=audit_path)

    filters = {}
    if agent_id:
        filters["agent_id"] = agent_id
    if target:
        filters["target"] = target
    if decision_filter:
        filters["decision"] = decision_filter

    entries = asyncio.run(backend.query(**filters))

    if not entries:
        click.echo("No matching audit entries found.")
        return

    # Show most recent first, limited
    entries = list(reversed(entries))[:limit]

    for entry in entries:
        reasons = ", ".join(entry.reasons) if entry.reasons else "-"
        click.echo(
            f"[{entry.decision:>8}] {entry.action_type:>15} → {entry.target:<30} "
            f"({entry.pipeline_latency_ms:.1f}ms) {reasons}"
        )

    click.echo(f"\nShowing {len(entries)} of {len(entries)} matching entries.")


@cli.command()
@click.option("--output", "-o", default="agentguard.yaml", help="Output file path")
def init(output):
    """Generate a starter AgentGuard config file."""
    template = """\
# AgentGuard Configuration
# Docs: https://github.com/agentguard/agentguard

guard:
  # Run validators in parallel (false) or sequentially (true)
  sequential: false
  # Stop on first block in sequential mode
  fail_fast: true
  # Minimum confidence to honor a block verdict (0.0 - 1.0)
  block_confidence_threshold: 0.7
  # What to do when a validator escalates and there's no handler
  default_on_escalation: block
  # Raise GuardError on block (true) or return None (false)
  raise_on_block: true

validators:
  # Schema validator — check targets and payload structure
  - type: schema
    allowed_targets:
      - "/api/users"
      - "/api/orders"
      - "/api/products"
    blocked_targets:
      - "/api/admin/danger"
    # required_fields:
    #   api_call:
    #     - method
    #     - url

  # Safety scorer — risk scoring and dangerous pattern detection
  - type: safety
    policy:
      max_risk_level: high
      blocked_patterns:
        - "DROP\\\\s+TABLE"
        - "DELETE\\\\s+FROM\\\\s+\\\\w+\\\\s*$"
        - "rm\\\\s+-rf\\\\s+/"
      max_payload_size_bytes: 1000000

  # Rate limiter — prevent runaway agents
  - type: rate_limit
    max_per_minute: 60
    max_per_target: 10
    window_seconds: 60

  # Policy enforcer — custom rules
  - type: policy
    rules:
      - type: block_target
        value: "production-db"
        reason: "Direct production database access is not allowed"

  # Trajectory validator — multi-step workflow tracking
  - type: trajectory
    max_steps: 20
    max_repeated_actions: 3
    error_cascade_threshold: 2
    drift_detection: false

  # Code validator — static analysis for generated code
  - type: code
    allow_file_io: false
    allow_network: false
    allow_subprocess: false
    max_code_length: 50000

  # Semantic checker (requires LLM) — uncomment to enable
  # - type: semantic
  #   provider: anthropic
  #   model: claude-sonnet-4-20250514
  #   confidence_threshold: 0.7
  #   grounding_docs:
  #     - "Your grounding context here"

# LLM configuration (for semantic checker and trajectory drift detection)
# llm:
#   provider: anthropic
#   model: claude-sonnet-4-20250514

audit:
  type: file
  path: "./agentguard_audit.jsonl"
"""
    output_path = Path(output)
    if output_path.exists():
        if not click.confirm(f"{output} already exists. Overwrite?"):
            click.echo("Aborted.")
            return

    output_path.write_text(template)
    click.echo(f"Config written to {output}")


@cli.command()
@click.option("--host", default="127.0.0.1", help="Host to bind to")
@click.option("--port", default=8321, help="Port to bind to")
@click.option("--config", "-c", default="agentguard.yaml", help="Guard config YAML file")
@click.option("--audit-path", default="agentguard_audit.jsonl", help="Audit log file path")
@click.option("--no-browser", is_flag=True, help="Don't open browser automatically")
def dashboard(host, port, config, audit_path, no_browser):
    """Launch the AgentGuard management dashboard."""
    try:
        import uvicorn
    except ImportError:
        click.echo("Dashboard requires extra dependencies. Install with:", err=True)
        click.echo("  pip install agentguard[dashboard]", err=True)
        sys.exit(1)

    # Add project root to path so dashboard package is importable
    import importlib.util
    from pathlib import Path as _Path

    # Find the dashboard package relative to the agentguard install
    dashboard_candidates = [
        _Path.cwd() / "dashboard",
        _Path(__file__).resolve().parents[3] / "dashboard",
    ]
    for candidate in dashboard_candidates:
        if (candidate / "api" / "main.py").exists():
            sys.path.insert(0, str(candidate.parent))
            break

    from dashboard.api.main import create_app

    app = create_app(config_path=config, audit_path=audit_path)

    click.echo(f"AgentGuard Dashboard starting at http://{host}:{port}")

    if not no_browser:
        import webbrowser
        import threading
        threading.Timer(1.0, lambda: webbrowser.open(f"http://{host}:{port}")).start()

    uvicorn.run(app, host=host, port=port, log_level="info")
