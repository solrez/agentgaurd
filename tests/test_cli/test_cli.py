"""Tests for the CLI tool."""

import json
from pathlib import Path

import pytest
from click.testing import CliRunner

from agentguard.cli.main import cli


@pytest.fixture
def runner():
    return CliRunner()


@pytest.fixture
def tmp_config(tmp_path):
    config = tmp_path / "guard.yaml"
    config.write_text("""\
guard:
  sequential: false
  raise_on_block: true

validators:
  - type: schema
    allowed_targets:
      - "/api/users"
    blocked_targets:
      - "/api/admin/nuke"

  - type: safety

audit:
  type: memory
""")
    return str(config)


def test_validate_approved(runner, tmp_config):
    action_json = json.dumps({
        "action_type": "api_call",
        "target": "/api/users",
        "payload": {"method": "GET"},
    })
    result = runner.invoke(cli, ["validate", "-c", tmp_config], input=action_json)
    assert result.exit_code == 0
    output = json.loads(result.output)
    assert output["decision"] == "execute"
    assert output["should_execute"] is True


def test_validate_blocked(runner, tmp_config):
    action_json = json.dumps({
        "action_type": "api_call",
        "target": "/api/admin/nuke",
        "payload": {},
    })
    result = runner.invoke(cli, ["validate", "-c", tmp_config], input=action_json)
    assert result.exit_code == 1
    output = json.loads(result.output)
    assert output["decision"] == "block"
    assert output["should_execute"] is False


def test_validate_invalid_json(runner, tmp_config):
    result = runner.invoke(cli, ["validate", "-c", tmp_config], input="not json")
    assert result.exit_code == 2
    assert "Invalid JSON" in result.output


def test_validate_no_config(runner):
    """Without a config, uses default validators."""
    action_json = json.dumps({
        "action_type": "api_call",
        "target": "/api/test",
        "payload": {"method": "GET"},
    })
    result = runner.invoke(cli, ["validate"], input=action_json)
    assert result.exit_code == 0


def test_init_creates_config(runner, tmp_path):
    output_file = tmp_path / "test_config.yaml"
    result = runner.invoke(cli, ["init", "-o", str(output_file)])
    assert result.exit_code == 0
    assert output_file.exists()
    content = output_file.read_text()
    assert "validators:" in content
    assert "schema" in content
    assert "safety" in content
    assert "trajectory" in content
    assert "code" in content


def test_init_overwrite_prompt(runner, tmp_path):
    output_file = tmp_path / "existing.yaml"
    output_file.write_text("old content")

    # Decline overwrite
    result = runner.invoke(cli, ["init", "-o", str(output_file)], input="n\n")
    assert "Aborted" in result.output
    assert output_file.read_text() == "old content"

    # Accept overwrite
    result = runner.invoke(cli, ["init", "-o", str(output_file)], input="y\n")
    assert "Config written" in result.output
    assert "validators:" in output_file.read_text()


def test_audit_no_file(runner, tmp_path):
    result = runner.invoke(cli, ["audit", "-p", str(tmp_path / "nonexistent.jsonl")])
    assert result.exit_code == 1
    assert "not found" in result.output


def test_audit_empty_file(runner, tmp_path):
    audit_file = tmp_path / "audit.jsonl"
    audit_file.write_text("")
    result = runner.invoke(cli, ["audit", "-p", str(audit_file)])
    assert "No matching" in result.output
