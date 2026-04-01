"""Escalation queue API routes."""

from __future__ import annotations

import time

from fastapi import APIRouter, HTTPException, Request

from dashboard.api.models.audit import AuditEntryResponse
from dashboard.api.models.escalation import EscalationAction, EscalationEntry

router = APIRouter(prefix="/api/escalation", tags=["escalation"])


@router.get("", response_model=list[EscalationEntry])
async def list_escalations(request: Request, status_filter: str = "pending"):
    state = request.app.state.dashboard
    entries = state.load_all_entries()
    escalation_status = state.load_escalation_status()

    escalated = [e for e in entries if e.decision == "escalate"]

    results = []
    for e in escalated:
        stored = escalation_status.get(e.trace_id, {})
        entry_status = stored.get("status", "pending")

        if status_filter != "all" and entry_status != status_filter:
            continue

        results.append(
            EscalationEntry(
                trace_id=e.trace_id,
                timestamp=e.timestamp,
                agent_id=e.agent_id,
                action_type=e.action_type,
                target=e.target,
                reasons=e.reasons,
                metadata=e.metadata,
                status=entry_status,
            )
        )

    results.sort(key=lambda x: x.timestamp, reverse=True)
    return results


@router.post("/{trace_id}", response_model=EscalationEntry)
async def resolve_escalation(request: Request, trace_id: str, body: EscalationAction):
    if body.action not in ("approve", "reject"):
        raise HTTPException(status_code=400, detail="Action must be 'approve' or 'reject'")

    state = request.app.state.dashboard
    entries = state.load_all_entries()

    entry = next((e for e in entries if e.trace_id == trace_id), None)
    if entry is None:
        raise HTTPException(status_code=404, detail="Entry not found")
    if entry.decision != "escalate":
        raise HTTPException(status_code=400, detail="Entry is not an escalation")

    escalation_status = state.load_escalation_status()
    new_status = "approved" if body.action == "approve" else "rejected"
    escalation_status[trace_id] = {
        "status": new_status,
        "reason": body.reason,
        "resolved_at": time.time(),
    }
    state.save_escalation_status(escalation_status)

    return EscalationEntry(
        trace_id=entry.trace_id,
        timestamp=entry.timestamp,
        agent_id=entry.agent_id,
        action_type=entry.action_type,
        target=entry.target,
        reasons=entry.reasons,
        metadata=entry.metadata,
        status=new_status,
    )


@router.get("/count")
async def pending_count(request: Request):
    state = request.app.state.dashboard
    entries = state.load_all_entries()
    escalation_status = state.load_escalation_status()

    escalated = [e for e in entries if e.decision == "escalate"]
    pending = sum(
        1 for e in escalated if escalation_status.get(e.trace_id, {}).get("status", "pending") == "pending"
    )
    return {"count": pending}
