"""Routes: Approvals — Procesar decisiones de supervisor (HITL)."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel, field_validator
import logging

from ...db.session import get_service_client
from ...events.store import EventStore, EventStoreError
from ...flows.registry import flow_registry

logger = logging.getLogger(__name__)
router = APIRouter()


class ApprovalDecision(BaseModel):
    """Payload para procesar una decisión de aprobación."""
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


@router.post("/{task_id}")
async def process_approval(
    task_id: str,
    body: ApprovalDecision,
    background: BackgroundTasks,
) -> dict:
    """
    Procesar la decisión del supervisor sobre una aprobación pendiente.

    SECUENCIA:
    1. Verificar que la aprobación existe y está pendiente
    2. Marcar la aprobación como resuelta (approved | rejected)
    3. Registrar evento approval.{decision}
    4. Reanudar el Flow en background

    Args:
        task_id: UUID de la tarea que fue pausada
        body: Decisión del supervisor

    Returns:
        {"status": "ok", "task_id": ..., "decision": ...}

    Raises:
        HTTPException 404: Si la aprobación no existe o ya fue procesada
        HTTPException 400: Si el flow_type no está registrado
    """
    svc = get_service_client()

    # 1. Verificar que la aprobación existe y está pendiente
    approval = (
        svc.table("pending_approvals")
        .select("*")
        .eq("task_id", task_id)
        .eq("status", "pending")
        .maybe_single()
        .execute()
    )

    if not approval.data:
        raise HTTPException(
            status_code=404,
            detail="Aprobación no encontrada o ya procesada"
        )

    flow_type = approval.data["flow_type"]

    # 2. Marcar aprobación como resuelta
    svc.table("pending_approvals").update({
        "status": body.decision,
        "decided_by": body.decided_by,
    }).eq("task_id", task_id).execute()

    # 3. Registrar evento (bloqueante — Regla R6)
    try:
        EventStore.append_sync(
            org_id=body.org_id,
            aggregate_type="flow",
            aggregate_id=task_id,
            event_type=f"approval.{body.decision}",
            payload={
                "decided_by": body.decided_by,
                "notes": body.notes,
            },
            actor=f"user:{body.decided_by}"
        )
    except EventStoreError as e:
        logger.error("Failed to emit approval event: %s", e)
        raise HTTPException(status_code=500, detail="No se pudo registrar el evento")

    # 4. Reanudar el Flow en background
    flow_class = flow_registry.get(flow_type)

    if not flow_class:
        raise HTTPException(
            status_code=400,
            detail=f"Flow type '{flow_type}' not found in registry"
        )

    # Crear instancia con org_id del body
    flow = flow_class(org_id=body.org_id)

    background.add_task(
        flow.resume,
        task_id=task_id,
        decision=body.decision,
        decided_by=body.decided_by,
    )

    return {
        "status": "ok",
        "task_id": task_id,
        "decision": body.decision,
    }
