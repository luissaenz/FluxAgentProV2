"""Routes: Approvals — Procesar decisiones de supervisor (HITL).

Phase 5: Updated to support both legacy (org_id in body) and
dashboard (JWT + X-Org-ID header) authentication modes.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, BackgroundTasks, Depends, Request
from pydantic import BaseModel, field_validator
from typing import Optional
import logging
import asyncio

from ...db.session import get_service_client, get_tenant_client
from ...events.store import EventStore, EventStoreError
from ...flows.registry import flow_registry
from ..middleware import require_org_id, verify_org_membership

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/approvals", tags=["approvals"])


def _run_async_in_background(coro):
    """Wrapper para ejecutar coroutines async en background tasks síncronos."""
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # Si hay un loop corriendo, crear una tarea
            asyncio.ensure_future(coro)
        else:
            # Si no hay loop, ejecutar directamente
            loop.run_until_complete(coro)
    except RuntimeError:
        # No hay loop, crear uno nuevo
        asyncio.run(coro)


class ApprovalRequest(BaseModel):
    """Payload for processing an approval decision."""
    action: str  # "approve" or "reject"
    notes: Optional[str] = None

    @field_validator("action")
    @classmethod
    def validate_action(cls, v: str) -> str:
        if v not in ("approve", "reject"):
            raise ValueError("action must be 'approve' or 'reject'")
        return v


class ApprovalDecision(BaseModel):
    """Legacy payload (backward compatibility with Phase 2-4)."""
    org_id: str
    decision: str  # "approved" | "rejected"
    decided_by: str
    notes: str = ""

    @field_validator("decision")
    @classmethod
    def validate_decision(cls, v: str) -> str:
        if v not in ("approved", "rejected"):
            raise ValueError("decision must be 'approved' or 'rejected'")
        return v


@router.get("")
async def list_approvals(
    org_id: str = Depends(require_org_id),
    status: Optional[str] = "pending",
) -> list:
    """List pending_approvals for the current org."""
    db = get_service_client()

    query = (
        db.table("pending_approvals")
        .select("*")
        .eq("org_id", org_id)
    )

    if status:
        query = query.eq("status", status)

    result = query.order("created_at", desc=True).execute()
    return result.data or []


@router.post("/{task_id}")
async def process_approval(
    task_id: str,
    request: Request,
    background: BackgroundTasks,
    auth: dict = Depends(verify_org_membership),
) -> dict:
    """
    Process supervisor approval/rejection decision.

    Accepts both new format (ApprovalRequest with action) and
    legacy format (ApprovalDecision with decision) for backward compatibility.
    """
    org_id = auth["org_id"]
    user_id = auth["user_id"]
    body = await request.json()

    # Determine format: new (action) vs legacy (decision)
    if "action" in body:
        action = body["action"]
        if action not in ("approve", "reject"):
            raise HTTPException(status_code=422, detail="action must be 'approve' or 'reject'")
        decision = "approved" if action == "approve" else "rejected"
        decided_by = user_id
        notes = body.get("notes", "")
        effective_org_id = org_id
    elif "decision" in body:
        decision = body["decision"]
        if decision not in ("approved", "rejected"):
            raise HTTPException(status_code=422, detail="decision must be 'approved' or 'rejected'")
        decided_by = body.get("decided_by", "unknown")
        notes = body.get("notes", "")
        effective_org_id = body.get("org_id", org_id)
    else:
        raise HTTPException(status_code=422, detail="Must provide 'action' or 'decision'")

    with get_tenant_client(org_id) as db:
        # 1. Verify approval exists and is pending
        approval = (
            db.table("pending_approvals")
            .select("*")
            .eq("task_id", task_id)
            .eq("status", "pending")
            .maybe_single()
            .execute()
        )

        if not approval.data:
            raise HTTPException(
                status_code=404,
                detail="Approval not found or already processed",
            )

        flow_type = approval.data["flow_type"]

        # 2. Mark approval as resolved
        db.table("pending_approvals").update({
            "status": decision,
            "decided_by": decided_by,
        }).eq("task_id", task_id).execute()

    # 3. Emit event (blocking — Rule R6)
    try:
        EventStore.append_sync(
            org_id=effective_org_id,
            aggregate_type="flow",
            aggregate_id=task_id,
            event_type=f"approval.{decision}",
            payload={"decided_by": decided_by, "notes": notes},
            actor=f"user:{decided_by}",
        )
    except EventStoreError as e:
        logger.error("Failed to emit approval event: %s", e)
        raise HTTPException(status_code=500, detail="Could not record event")

    # 4. Resume flow in background
    flow_class = flow_registry.get(flow_type)
    if not flow_class:
        raise HTTPException(
            status_code=400,
            detail=f"Flow type '{flow_type}' not found in registry",
        )

    flow = flow_class(org_id=effective_org_id)
    background.add_task(
        _run_async_in_background,
        flow.resume(
            task_id=task_id,
            decision=decision,
            decided_by=decided_by,
        ),
    )

    return {
        "status": decision,
        "task_id": task_id,
        "decision": decision,
    }
