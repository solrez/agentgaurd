"""Config management API routes."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request

import yaml

from dashboard.api.models.config import ConfigUpdateRequest, GuardConfig, ValidatorConfig

router = APIRouter(prefix="/api/config", tags=["config"])


def _parse_config(raw: str) -> GuardConfig:
    """Parse raw YAML into structured GuardConfig."""
    if not raw.strip():
        return GuardConfig(raw_yaml=raw)

    data = yaml.safe_load(raw) or {}

    validators = []
    for v in data.get("validators", []):
        v_type = v.pop("type", "unknown")
        validators.append(ValidatorConfig(type=v_type, enabled=True, settings=v))

    return GuardConfig(
        guard=data.get("guard", {}),
        validators=validators,
        audit=data.get("audit", {}),
        llm=data.get("llm"),
        raw_yaml=raw,
    )


@router.get("", response_model=GuardConfig)
async def get_config(request: Request):
    raw = request.app.state.dashboard.load_config_raw()
    return _parse_config(raw)


@router.put("", response_model=GuardConfig)
async def update_config(request: Request, body: ConfigUpdateRequest):
    # Validate YAML parses correctly
    try:
        yaml.safe_load(body.raw_yaml)
    except yaml.YAMLError as e:
        raise HTTPException(status_code=400, detail=f"Invalid YAML: {e}")

    request.app.state.dashboard.save_config_raw(body.raw_yaml)
    return _parse_config(body.raw_yaml)


@router.patch("/validators/{index}", response_model=ValidatorConfig)
async def update_validator(request: Request, index: int, validator: ValidatorConfig):
    raw = request.app.state.dashboard.load_config_raw()
    data = yaml.safe_load(raw) or {}

    validators_list = data.get("validators", [])
    if index < 0 or index >= len(validators_list):
        raise HTTPException(status_code=404, detail="Validator index out of range")

    # Rebuild the validator entry
    new_entry = {"type": validator.type, **validator.settings}
    validators_list[index] = new_entry
    data["validators"] = validators_list

    new_raw = yaml.dump(data, default_flow_style=False, sort_keys=False)
    request.app.state.dashboard.save_config_raw(new_raw)

    return validator
