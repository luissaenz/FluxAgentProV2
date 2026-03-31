"""GET /tasks — Polling and listing endpoints for task status."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import logging

from ..middleware import require_org_id
from ...db.session import get_tenant_client

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/tasks", tags=["tasks"])


# ── response model ──────────────────────────────────────────────

class TaskResponse(BaseModel):
    task_id: str
    org_id: str
    flow_type: str
    status: str
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    created_at: str
    updated_at: str


# ── routes ──────────────────────────────────────────────────────

@router.get("/{task_id}", response_model=TaskResponse)
async def get_task(
    task_id: str,
    org_id: str = Depends(require_org_id),
):
    """Return the current state of a single task (used for polling)."""
    with get_tenant_client(org_id) as db:
        result = db.table("tasks").select("*").eq("id", task_id).execute()

        if not result.data:
            raise HTTPException(status_code=404, detail="Task not found")

        task = result.data[0]
        return TaskResponse(
            task_id=task["id"],
            org_id=str(task["org_id"]),
            flow_type=task["flow_type"],
            status=task["status"],
            result=task.get("result"),
            error=task.get("error"),
            created_at=str(task["created_at"]),
            updated_at=str(task["updated_at"]),
        )


@router.get("", response_model=List[TaskResponse])
async def list_tasks(
    org_id: str = Depends(require_org_id),
    status: Optional[str] = None,
    limit: int = 50,
):
    """List tasks for an organisation, optionally filtered by status."""
    with get_tenant_client(org_id) as db:
        query = (
            db.table("tasks")
            .select("*")
            .order("created_at", desc=True)
            .limit(limit)
        )

        if status:
            query = query.eq("status", status)

        result = query.execute()
        return [
            TaskResponse(
                task_id=t["id"],
                org_id=str(t["org_id"]),
                flow_type=t["flow_type"],
                status=t["status"],
                result=t.get("result"),
                error=t.get("error"),
                created_at=str(t["created_at"]),
                updated_at=str(t["updated_at"]),
            )
            for t in result.data
        ]
