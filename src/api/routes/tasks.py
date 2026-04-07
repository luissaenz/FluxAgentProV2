"""GET /tasks — Polling and listing endpoints for task status.

Phase 5: Extended with pagination, flow_type filter, and total count.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import logging

from ..middleware import verify_org_membership
from ...db.session import get_tenant_client

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/tasks", tags=["tasks"])


# ── response models ──────────────────────────────────────────────


class TaskResponse(BaseModel):
    task_id: str
    org_id: str
    flow_type: str
    status: str
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    tokens_used: int = 0
    created_at: str
    updated_at: str


class PaginatedTasksResponse(BaseModel):
    items: List[TaskResponse]
    total: int


# ── helpers ──────────────────────────────────────────────────────


def _task_to_response(t: dict) -> TaskResponse:
    return TaskResponse(
        task_id=t["id"],
        org_id=str(t["org_id"]),
        flow_type=t["flow_type"],
        status=t["status"],
        result=t.get("result"),
        error=t.get("error"),
        tokens_used=t.get("tokens_used", 0) or 0,
        created_at=str(t["created_at"]),
        updated_at=str(t["updated_at"]),
    )


# ── routes ──────────────────────────────────────────────────────


@router.get("/{task_id}", response_model=TaskResponse)
async def get_task(
    task_id: str,
    auth: dict = Depends(verify_org_membership),
):
    """Return the current state of a single task (used for polling)."""
    org_id = auth["org_id"]
    with get_tenant_client(org_id) as db:
        result = db.table("tasks").select("*").eq("id", task_id).execute()

        if not result.data:
            raise HTTPException(status_code=404, detail="Task not found")

        return _task_to_response(result.data[0])


@router.get("", response_model=PaginatedTasksResponse)
async def list_tasks(
    auth: dict = Depends(verify_org_membership),
    status: Optional[str] = None,
    flow_type: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
):
    """List tasks for an organisation with pagination and filters."""
    org_id = auth["org_id"]
    with get_tenant_client(org_id) as db:
        query = (
            db.table("tasks")
            .select("*")
            .eq("org_id", org_id)  # Explicitly filter by org_id
            .order("created_at", desc=True)
        )

        if status:
            query = query.eq("status", status)
        if flow_type:
            query = query.eq("flow_type", flow_type)

        result = query.range(offset, offset + limit - 1).execute()
        items = result.data or []
        total = len(items)

        return PaginatedTasksResponse(
            items=[_task_to_response(t) for t in items],
            total=total,
        )
