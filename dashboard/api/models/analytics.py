"""Analytics API response models."""

from __future__ import annotations

from pydantic import BaseModel


class OverviewMetrics(BaseModel):
    total_actions: int
    block_rate: float
    avg_latency_ms: float
    active_agents: int
    actions_last_hour: int


class DecisionDistribution(BaseModel):
    decision: str
    count: int


class TimeseriesPoint(BaseModel):
    timestamp: str
    count: int


class TopTarget(BaseModel):
    target: str
    block_count: int
    total_count: int
    block_rate: float


class ValidatorEffectiveness(BaseModel):
    validator_name: str
    times_run: int
    blocks_triggered: int


class LatencyBucket(BaseModel):
    range_label: str
    count: int
