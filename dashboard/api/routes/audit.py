"""Audit log API routes."""

from __future__ import annotations

import asyncio
import time

from fastapi import APIRouter, Query, Request
from fastapi.responses import StreamingResponse

from dashboard.api.models.audit import AuditEntryResponse, AuditListResponse

router = APIRouter(prefix="/api/audit", tags=["audit"])


@router.get("", response_model=AuditListResponse)
async def list_entries(
    request: Request,
    agent_id: str | None = None,
    target: str | None = None,
    decision: str | None = None,
    action_type: str | None = None,
    start_time: float | None = None,
    end_time: float | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=200),
    sort: str = Query(default="desc", pattern="^(asc|desc)$"),
):
    state = request.app.state.dashboard
    entries = state.load_all_entries()

    # Apply filters
    if agent_id:
        entries = [e for e in entries if e.agent_id == agent_id]
    if target:
        entries = [e for e in entries if e.target == target]
    if decision:
        entries = [e for e in entries if e.decision == decision]
    if action_type:
        entries = [e for e in entries if e.action_type == action_type]
    if start_time is not None:
        entries = [e for e in entries if e.timestamp >= start_time]
    if end_time is not None:
        entries = [e for e in entries if e.timestamp <= end_time]

    # Sort
    entries.sort(key=lambda e: e.timestamp, reverse=(sort == "desc"))

    total = len(entries)
    start = (page - 1) * page_size
    page_entries = entries[start : start + page_size]

    return AuditListResponse(
        entries=[AuditEntryResponse.model_validate(e.model_dump()) for e in page_entries],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/stream")
async def stream_entries(request: Request):
    """SSE endpoint that tails the audit JSONL file for new entries."""
    state = request.app.state.dashboard

    async def event_generator():
        last_size = state.audit_path.stat().st_size if state.audit_path.exists() else 0

        while True:
            await asyncio.sleep(1)

            if not state.audit_path.exists():
                continue

            current_size = state.audit_path.stat().st_size
            if current_size > last_size:
                with open(state.audit_path) as f:
                    f.seek(last_size)
                    new_data = f.read()
                last_size = current_size

                for line in new_data.strip().split("\n"):
                    if line:
                        yield f"data: {line}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@router.get("/{trace_id}", response_model=AuditEntryResponse | None)
async def get_entry(request: Request, trace_id: str):
    state = request.app.state.dashboard
    entries = state.load_all_entries()
    for entry in entries:
        if entry.trace_id == trace_id:
            return AuditEntryResponse.model_validate(entry.model_dump())
    return None
