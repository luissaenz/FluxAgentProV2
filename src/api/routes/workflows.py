"""src/api/routes/workflows.py — CRUD de workflow_templates."""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from ...db.session import get_tenant_client
from ..middleware import require_org_id

logger = logging.getLogger(__name__)

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


class WorkflowCreate(BaseModel):
    name: str
    flow_type: str
    definition: Dict[str, Any]
    status: str = "draft"


class WorkflowResponse(BaseModel):
    id: str
    flow_type: str
    status: str


@router.get("", response_model=WorkflowListResponse)
async def list_workflows(
    org_id: str = Depends(require_org_id),
    status: Optional[str] = None,
):
    """Listar todos los workflows activos de una org."""
    with get_tenant_client(org_id) as db:
        query = (
            db.table("workflow_templates")
            .select("id, name, flow_type, status, is_active, execution_count")
            .eq("org_id", org_id)
        )

        if status:
            query = query.eq("status", status)
        else:
            query = query.eq("is_active", True)

        result = query.execute()

    return WorkflowListResponse(workflows=[dict(r) for r in result.data or []])


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
        db.table("workflow_templates").update(
            {
                "is_active": False,
                "status": "archived",
            }
        ).eq("flow_type", flow_type).eq("org_id", org_id).execute()

    return {"status": "archived", "flow_type": flow_type}


@router.post("", status_code=201, response_model=WorkflowResponse)
async def create_workflow(
    payload: WorkflowCreate,
    org_id: str = Depends(require_org_id),
):
    """Create a new workflow_template from canvas definition.

    Persists the workflow definition JSON in workflow_templates table.
    Returns 201 Created or 409 Conflict if flow_type already exists for this org.
    """
    workflow_id = str(uuid4())

    with get_tenant_client(org_id) as db:
        existing = (
            db.table("workflow_templates")
            .select("id")
            .eq("org_id", org_id)
            .eq("flow_type", payload.flow_type)
            .maybe_single()
            .execute()
        )

        if existing.data:
            raise HTTPException(
                status_code=409,
                detail=f"Workflow with flow_type '{payload.flow_type}' already exists for this org",
            )

        db.table("workflow_templates").insert({
            "id": workflow_id,
            "org_id": org_id,
            "name": payload.name,
            "flow_type": payload.flow_type,
            "definition": payload.definition,
            "status": payload.status,
            "is_active": True,
        }).execute()

    logger.info("Workflow '%s' created in org '%s'", payload.flow_type, org_id)
    return WorkflowResponse(id=workflow_id, flow_type=payload.flow_type, status=payload.status)
