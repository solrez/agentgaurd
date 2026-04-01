"""Config API response models."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class ValidatorConfig(BaseModel):
    type: str
    enabled: bool = True
    settings: dict[str, Any] = Field(default_factory=dict)


class GuardConfig(BaseModel):
    guard: dict[str, Any] = Field(default_factory=dict)
    validators: list[ValidatorConfig] = Field(default_factory=list)
    audit: dict[str, Any] = Field(default_factory=dict)
    llm: dict[str, Any] | None = None
    raw_yaml: str = ""


class ConfigUpdateRequest(BaseModel):
    raw_yaml: str
