"""Analytics API routes."""

from __future__ import annotations

import time
from collections import Counter, defaultdict
from datetime import datetime, timezone

from fastapi import APIRouter, Query, Request

from dashboard.api.models.analytics import (
    DecisionDistribution,
    LatencyBucket,
    OverviewMetrics,
    TimeseriesPoint,
    TopTarget,
    ValidatorEffectiveness,
)

router = APIRouter(prefix="/api/analytics", tags=["analytics"])


def _filter_by_time(entries, start_time=None, end_time=None):
    if start_time is not None:
        entries = [e for e in entries if e.timestamp >= start_time]
    if end_time is not None:
        entries = [e for e in entries if e.timestamp <= end_time]
    return entries


@router.get("/overview", response_model=OverviewMetrics)
async def overview(
    request: Request,
    start_time: float | None = None,
    end_time: float | None = None,
):
    entries = _filter_by_time(request.app.state.dashboard.load_all_entries(), start_time, end_time)

    total = len(entries)
    blocks = sum(1 for e in entries if e.decision == "block")
    block_rate = blocks / total if total > 0 else 0.0
    avg_latency = sum(e.pipeline_latency_ms for e in entries) / total if total > 0 else 0.0
    active_agents = len({e.agent_id for e in entries if e.agent_id})

    one_hour_ago = time.time() - 3600
    actions_last_hour = sum(1 for e in entries if e.timestamp >= one_hour_ago)

    return OverviewMetrics(
        total_actions=total,
        block_rate=round(block_rate, 4),
        avg_latency_ms=round(avg_latency, 2),
        active_agents=active_agents,
        actions_last_hour=actions_last_hour,
    )


@router.get("/decisions", response_model=list[DecisionDistribution])
async def decisions(
    request: Request,
    start_time: float | None = None,
    end_time: float | None = None,
):
    entries = _filter_by_time(request.app.state.dashboard.load_all_entries(), start_time, end_time)
    counts = Counter(e.decision for e in entries)
    return [DecisionDistribution(decision=d, count=c) for d, c in counts.most_common()]


@router.get("/timeline", response_model=list[TimeseriesPoint])
async def timeline(
    request: Request,
    start_time: float | None = None,
    end_time: float | None = None,
):
    entries = _filter_by_time(request.app.state.dashboard.load_all_entries(), start_time, end_time)

    # Bucket by hour
    buckets: dict[str, int] = defaultdict(int)
    for e in entries:
        dt = datetime.fromtimestamp(e.timestamp, tz=timezone.utc)
        key = dt.strftime("%Y-%m-%dT%H:00:00Z")
        buckets[key] += 1

    return [TimeseriesPoint(timestamp=k, count=v) for k, v in sorted(buckets.items())]


@router.get("/top-targets", response_model=list[TopTarget])
async def top_targets(
    request: Request,
    start_time: float | None = None,
    end_time: float | None = None,
    limit: int = Query(default=10, ge=1, le=50),
):
    entries = _filter_by_time(request.app.state.dashboard.load_all_entries(), start_time, end_time)

    target_stats: dict[str, dict[str, int]] = defaultdict(lambda: {"total": 0, "blocks": 0})
    for e in entries:
        target_stats[e.target]["total"] += 1
        if e.decision == "block":
            target_stats[e.target]["blocks"] += 1

    results = []
    for target, stats in target_stats.items():
        results.append(
            TopTarget(
                target=target,
                block_count=stats["blocks"],
                total_count=stats["total"],
                block_rate=round(stats["blocks"] / stats["total"], 4) if stats["total"] > 0 else 0,
            )
        )

    results.sort(key=lambda t: t.block_count, reverse=True)
    return results[:limit]


@router.get("/validators", response_model=list[ValidatorEffectiveness])
async def validators(
    request: Request,
    start_time: float | None = None,
    end_time: float | None = None,
):
    entries = _filter_by_time(request.app.state.dashboard.load_all_entries(), start_time, end_time)

    validator_stats: dict[str, dict[str, int]] = defaultdict(lambda: {"runs": 0, "blocks": 0})
    for e in entries:
        for v in e.validators_run:
            validator_stats[v]["runs"] += 1
            if e.decision == "block":
                validator_stats[v]["blocks"] += 1

    return [
        ValidatorEffectiveness(
            validator_name=name,
            times_run=stats["runs"],
            blocks_triggered=stats["blocks"],
        )
        for name, stats in sorted(validator_stats.items(), key=lambda x: x[1]["blocks"], reverse=True)
    ]


@router.get("/latency", response_model=list[LatencyBucket])
async def latency(
    request: Request,
    start_time: float | None = None,
    end_time: float | None = None,
):
    entries = _filter_by_time(request.app.state.dashboard.load_all_entries(), start_time, end_time)

    bucket_ranges = [
        ("0-5ms", 0, 5),
        ("5-10ms", 5, 10),
        ("10-25ms", 10, 25),
        ("25-50ms", 25, 50),
        ("50-100ms", 50, 100),
        ("100-500ms", 100, 500),
        ("500ms+", 500, float("inf")),
    ]

    counts = {label: 0 for label, _, _ in bucket_ranges}
    for e in entries:
        for label, low, high in bucket_ranges:
            if low <= e.pipeline_latency_ms < high:
                counts[label] += 1
                break

    return [LatencyBucket(range_label=label, count=counts[label]) for label, _, _ in bucket_ranges]
