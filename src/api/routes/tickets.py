"""Endpoints para gestion de tickets (solicitudes de trabajo)."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List

from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel, Field

from ..middleware import require_org_id
from ...db.session import get_tenant_client
from ...flows.registry import flow_registry

router = APIRouter(prefix="/tickets", tags=["tickets"])


# ── Request/Response models ─────────────────────────────────


class TicketCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None
    flow_type: Optional[str] = None
    priority: str = Field(default="medium", pattern="^(low|medium|high|urgent)$")
    input_data: Optional[Dict[str, Any]] = None
    assigned_to: Optional[str] = None


class TicketUpdate(BaseModel):
    status: Optional[str] = None
    notes: Optional[str] = None
    assigned_to: Optional[str] = None


class TicketResponse(BaseModel):
    id: str
    org_id: str
    title: str
    description: Optional[str] = None
    flow_type: Optional[str] = None
    priority: str
    status: str
    input_data: Optional[Dict[str, Any]] = None
    task_id: Optional[str] = None
    created_by: Optional[str] = None
    assigned_to: Optional[str] = None
    notes: Optional[str] = None
    created_at: str
    updated_at: str
    resolved_at: Optional[str] = None


class TicketsListResponse(BaseModel):
    items: List[TicketResponse]
    total: int


# ── Helpers ─────────────────────────────────────────────────


def _to_ticket_response(row: dict) -> TicketResponse:
    return TicketResponse(
        id=row["id"],
        org_id=str(row["org_id"]),
        title=row["title"],
        description=row.get("description"),
        flow_type=row.get("flow_type"),
        priority=row.get("priority", "medium"),
        status=row.get("status", "backlog"),
        input_data=row.get("input_data"),
        task_id=row.get("task_id"),
        created_by=row.get("created_by"),
        assigned_to=row.get("assigned_to"),
        notes=row.get("notes"),
        created_at=str(row["created_at"]),
        updated_at=str(row["updated_at"]),
        resolved_at=str(row["resolved_at"]) if row.get("resolved_at") else None,
    )


# ── Routes ──────────────────────────────────────────────────


@router.get("", response_model=TicketsListResponse)
async def list_tickets(
    org_id: str = Depends(require_org_id),
    status: Optional[str] = Query(None),
    flow_type: Optional[str] = Query(None),
    priority: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    """Lista tickets con filtros opcionales."""
    with get_tenant_client(org_id) as db:
        query = db.table("tickets").select("*", count="exact")

        if status:
            query = query.eq("status", status)
        if flow_type:
            query = query.eq("flow_type", flow_type)
        if priority:
            query = query.eq("priority", priority)

        result = (
            query.order("created_at", desc=True)
            .range(offset, offset + limit - 1)
            .execute()
        )

    return TicketsListResponse(
        items=[_to_ticket_response(t) for t in (result.data or [])],
        total=result.count or 0,
    )


@router.get("/{ticket_id}", response_model=TicketResponse)
async def get_ticket(
    ticket_id: str,
    org_id: str = Depends(require_org_id),
):
    """Obtiene un ticket por ID."""
    with get_tenant_client(org_id) as db:
        result = (
            db.table("tickets")
            .select("*")
            .eq("id", ticket_id)
            .maybe_single()
            .execute()
        )

    if result.data is None:
        raise HTTPException(status_code=404, detail="Ticket not found")

    return _to_ticket_response(result.data)


@router.post("", response_model=TicketResponse, status_code=201)
async def create_ticket(
    body: TicketCreate,
    org_id: str = Depends(require_org_id),
):
    """Crea un nuevo ticket."""
    # Validar flow_type si se proporciona
    if body.flow_type and not flow_registry.has(body.flow_type):
        raise HTTPException(
            status_code=400,
            detail=(
                f"Flow type '{body.flow_type}' not found. "
                f"Available: {flow_registry.list_flows()}"
            ),
        )

    ticket_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()

    ticket_data: Dict[str, Any] = {
        "id": ticket_id,
        "org_id": org_id,
        "title": body.title,
        "description": body.description,
        "flow_type": body.flow_type,
        "priority": body.priority,
        "status": "backlog",
        "input_data": body.input_data,
        "created_at": now,
        "updated_at": now,
    }
    if body.assigned_to:
        ticket_data["assigned_to"] = body.assigned_to

    with get_tenant_client(org_id) as db:
        result = db.table("tickets").insert(ticket_data).execute()

    if not result.data:
        raise HTTPException(status_code=500, detail="Failed to create ticket")

    return _to_ticket_response(result.data[0])


@router.patch("/{ticket_id}", response_model=TicketResponse)
async def update_ticket(
    ticket_id: str,
    body: TicketUpdate,
    org_id: str = Depends(require_org_id),
):
    """Actualiza un ticket (estado, notas, asignacion)."""
    update_data: Dict[str, Any] = body.model_dump(exclude_none=True)
    update_data["updated_at"] = datetime.now(timezone.utc).isoformat()

    if update_data.get("status") in ("done", "cancelled"):
        update_data["resolved_at"] = datetime.now(timezone.utc).isoformat()

    with get_tenant_client(org_id) as db:
        result = (
            db.table("tickets")
            .update(update_data)
            .eq("id", ticket_id)
            .execute()
        )

    if not result.data:
        raise HTTPException(status_code=404, detail="Ticket not found")

    return _to_ticket_response(result.data[0])


@router.post("/{ticket_id}/execute")
async def execute_ticket(
    ticket_id: str,
    org_id: str = Depends(require_org_id),
):
    """
    Ejecuta el Flow asociado a un ticket.
    - Verifica que el ticket existe y tiene flow_type
    - Cambia status a in_progress
    - Dispara el Flow directamente y espera resultado
    - Al completar, vincula task_id al ticket y actualiza status
    """
    from .webhooks import execute_flow

    with get_tenant_client(org_id) as db:
        ticket_result = (
            db.table("tickets")
            .select("*")
            .eq("id", ticket_id)
            .maybe_single()
            .execute()
        )

    if not ticket_result.data:
        raise HTTPException(status_code=404, detail="Ticket not found")

    ticket = ticket_result.data
    if not ticket.get("flow_type"):
        raise HTTPException(
            status_code=400,
            detail="Ticket has no flow_type to execute",
        )

    if ticket.get("status") in ("in_progress", "done"):
        raise HTTPException(
            status_code=409,
            detail=f"Ticket is already {ticket['status']}",
        )

    if not flow_registry.has(ticket["flow_type"]):
        raise HTTPException(
            status_code=404,
            detail=f"Flow type '{ticket['flow_type']}' not found",
        )

    # Cambiar a in_progress
    now = datetime.now(timezone.utc).isoformat()
    with get_tenant_client(org_id) as db:
        db.table("tickets").update({
            "status": "in_progress",
            "updated_at": now,
        }).eq("id", ticket_id).execute()

    # Ejecutar el Flow
    correlation_id = f"ticket-{ticket_id}"
    task_id = None

    try:
        task_id = await execute_flow(
            flow_type=ticket["flow_type"],
            org_id=org_id,
            input_data=ticket.get("input_data") or {},
            correlation_id=correlation_id,
            callback_url=None,
        )
    except Exception as exc:
        # Si falla, marcar ticket como blocked
        with get_tenant_client(org_id) as db:
            db.table("tickets").update({
                "status": "blocked",
                "notes": f"Execution error: {str(exc)}",
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }).eq("id", ticket_id).execute()
        raise HTTPException(
            status_code=500,
            detail=f"Flow execution failed: {str(exc)}",
        )

    # Vincular task_id y actualizar status
    final_status = "done"
    with get_tenant_client(org_id) as db:
        db.table("tickets").update({
            "task_id": task_id,
            "status": final_status,
            "resolved_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }).eq("id", ticket_id).execute()

    return {
        "ticket_id": ticket_id,
        "task_id": task_id,
        "status": final_status,
    }


@router.delete("/{ticket_id}", response_model=TicketResponse)
async def delete_ticket(
    ticket_id: str,
    org_id: str = Depends(require_org_id),
):
    """Elimina un ticket (soft-delete: status = cancelled)."""
    now = datetime.now(timezone.utc).isoformat()
    with get_tenant_client(org_id) as db:
        result = (
            db.table("tickets")
            .update({
                "status": "cancelled",
                "resolved_at": now,
                "updated_at": now,
            })
            .eq("id", ticket_id)
            .execute()
        )

    if not result.data:
        raise HTTPException(status_code=404, detail="Ticket not found")

    return _to_ticket_response(result.data[0])
