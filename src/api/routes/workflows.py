"""src/api/routes/workflows.py — CRUD de workflow_templates."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional

from ...db.session import get_tenant_client
from ..middleware import require_org_id

router = APIRouter(prefix="/workflows", tags=["workflows"])


class WorkflowSummary(BaseModel):
    id: str
    name: str
    flow_type: str
    status: str
    is_active: bool
    execution_count: int


class WorkflowListResponse(BaseModel):
    workflows: list[WorkflowSummary]


@router.get("/", response_model=WorkflowListResponse)
async def list_workflows(
    org_id: str = Depends(require_org_id),
    status: Optional[str] = None,
):
    """Listar todos los workflows activos de una org."""
    with get_tenant_client(org_id) as db:
        query = db.table("workflow_templates").select(
            "id, name, flow_type, status, is_active, execution_count"
        ).eq("org_id", org_id)

        if status:
            query = query.eq("status", status)
        else:
            query = query.eq("is_active", True)

        result = query.execute()

    return WorkflowListResponse(
        workflows=[dict(r) for r in result.data or []]
    )


@router.get("/{flow_type}")
async def get_workflow(
    flow_type: str,
    org_id: str = Depends(require_org_id),
):
    """Obtener definición completa de un workflow."""
    with get_tenant_client(org_id) as db:
        result = (
            db.table("workflow_templates")
            .select("*")
            .eq("flow_type", flow_type)
            .eq("org_id", org_id)
            .maybe_single()
            .execute()
        )

    if not result.data:
        raise HTTPException(404, f"Workflow '{flow_type}' no encontrado")

    return result.data


@router.delete("/{flow_type}")
async def archive_workflow(
    flow_type: str,
    org_id: str = Depends(require_org_id),
):
    """Desactivar (soft-delete) un workflow."""
    with get_tenant_client(org_id) as db:
        db.table("workflow_templates").update({
            "is_active": False,
            "status": "archived",
        }).eq("flow_type", flow_type).eq("org_id", org_id).execute()

    return {"status": "archived", "flow_type": flow_type}
