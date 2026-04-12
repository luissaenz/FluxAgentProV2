"""Endpoints para gestion de tickets (solicitudes de trabajo)."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List

from fastapi import APIRouter, HTTPException, Depends, Query, Body
from pydantic import BaseModel, Field

from ..middleware import require_org_id
from ...db.session import get_tenant_client
from ...flows.registry import flow_registry
from .webhooks import execute_flow

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
    title: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = None
    flow_type: Optional[str] = None
    priority: Optional[str] = Field(None, pattern="^(low|medium|high|urgent)$")
    status: Optional[str] = None
    input_data: Optional[Dict[str, Any]] = None
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
        created_at=row["created_at"].isoformat() if isinstance(row.get("created_at"), datetime) else str(row.get("created_at", "")),
        updated_at=row["updated_at"].isoformat() if isinstance(row.get("updated_at"), datetime) else str(row.get("updated_at", "")),
        resolved_at=row["resolved_at"].isoformat() if isinstance(row.get("resolved_at"), datetime) else None,
    )


def _append_error_note(db, ticket_id: str, error_msg: str, error_type: str, correlation_id: Optional[str] = None) -> None:
    """Append error information to ticket notes, preserving existing content."""
    now = datetime.now(timezone.utc).isoformat()

    # Fetch current notes
    result = db.table("tickets").select("notes").eq("id", ticket_id).maybe_single().execute()
    current_notes = result.data.get("notes", "") if result.data else ""

    # Format new error entry
    prefix = f"[{now}]"
    if correlation_id:
        prefix += f" [Trace: {correlation_id}]"
    new_note = f"{prefix} {error_type}: {error_msg}"

    # Preserve existing notes, append new error
    updated_notes = new_note if not current_notes else f"{current_notes}\n{new_note}"

    db.table("tickets").update({
        "notes": updated_notes,
        "updated_at": now,
    }).eq("id", ticket_id).execute()


def _handle_blocked_ticket(
    db, ticket_id: str, result: Dict[str, Any]
) -> None:
    """Mark ticket as blocked with error details. Preserves existing notes.

    Single UPDATE to avoid race condition (ID-002 fix).
    Explicit defaults for safety when result is empty dict (ID-003 fix).
    """
    error_msg = result.get("error") or "Unknown error"
    error_type = result.get("error_type") or "Exception"
    task_id = result.get("task_id")

    _append_error_note(db, ticket_id, error_msg, error_type, result.get("correlation_id"))

    now = datetime.now(timezone.utc).isoformat()
    update_data: Dict[str, Any] = {
        "status": "blocked",
        "updated_at": now,
    }
    if task_id:
        update_data["task_id"] = task_id

    db.table("tickets").update(update_data).eq("id", ticket_id).execute()


def _handle_done_ticket(
    db, ticket_id: str, task_id: str
) -> None:
    """Mark ticket as done with linked task_id."""
    now = datetime.now(timezone.utc).isoformat()
    db.table("tickets").update({
        "task_id": task_id,
        "status": "done",
        "resolved_at": now,
        "updated_at": now,
    }).eq("id", ticket_id).execute()


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
    ticket_input: TicketCreate,
    org_id: str = Depends(require_org_id),
):
    """Crea un nuevo ticket."""
    # Validar flow_type si se proporciona
    if ticket_input.flow_type and not flow_registry.has(ticket_input.flow_type):
        raise HTTPException(
            status_code=400,
            detail=(
                f"Flow type '{ticket_input.flow_type}' not found. "
                f"Available: {flow_registry.list_flows()}"
            ),
        )

    ticket_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()

    ticket_data: Dict[str, Any] = {
        "id": ticket_id,
        "org_id": org_id,
        "title": ticket_input.title,
        "description": ticket_input.description,
        "flow_type": ticket_input.flow_type,
        "priority": ticket_input.priority,
        "status": "backlog",
        "input_data": ticket_input.input_data,
        "created_at": now,
        "updated_at": now,
    }
    if ticket_input.assigned_to:
        ticket_data["assigned_to"] = ticket_input.assigned_to

    with get_tenant_client(org_id) as db:
        result = db.table("tickets").insert(ticket_data).execute()

    if not result.data:
        raise HTTPException(status_code=500, detail="Failed to create ticket")

    return _to_ticket_response(result.data[0])


@router.patch("/{ticket_id}", response_model=TicketResponse)
async def update_ticket(
    ticket_id: str,
    ticket_update: TicketUpdate,
    org_id: str = Depends(require_org_id),
):
    """Actualiza un ticket (estado, notas, asignacion)."""
    # print(f"DEBUG: Updating ticket {ticket_id} with body: {ticket_update}")
    update_data: Dict[str, Any] = ticket_update.model_dump(exclude_unset=True)
    update_data["updated_at"] = datetime.now(timezone.utc).isoformat()

    if update_data.get("status") in ("done", "cancelled"):
        update_data["resolved_at"] = datetime.now(timezone.utc).isoformat()

    # Validar flow_type si se proporciona en la actualización
    if "flow_type" in update_data and update_data["flow_type"]:
        if not flow_registry.has(update_data["flow_type"]):
            raise HTTPException(
                status_code=400,
                detail=f"Flow type '{update_data['flow_type']}' not found."
            )

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
    input_data = ticket.get("input_data") or {}

    # Auto-mapping para GenericFlow si falta 'text'
    if ticket["flow_type"] == "generic_flow" and "text" not in input_data:
        input_data["text"] = ticket.get("description") or ticket.get("title") or ""

    try:
        result = await execute_flow(
            flow_type=ticket["flow_type"],
            org_id=org_id,
            input_data=input_data,
            correlation_id=correlation_id,
            callback_url=None,
        )
    except Exception as infra_exc:
        # Error de infraestructura (DB, red, etc)
        with get_tenant_client(org_id) as db:
            _handle_blocked_ticket(db, ticket_id, {
                "error": str(infra_exc),
                "error_type": type(infra_exc).__name__,
                "correlation_id": correlation_id,
            })
        raise HTTPException(
            status_code=500,
            detail=f"Flow execution infrastructure error: {str(infra_exc)}",
        )

    # Procesar resultado de execute_flow (Criterios ID-001, ID-002, ID-003)
    if result is None or not result or result.get("error"):
        with get_tenant_client(org_id) as db:
            _handle_blocked_ticket(db, ticket_id, result or {})
        
        raise HTTPException(
            status_code=500,
            detail={
                "message": "Flow execution failed",
                "ticket_id": ticket_id,
                "task_id": result.get("task_id") if result else None,
                "status": "blocked",
                "error": (result.get("error") if result else "Unknown error") or "Unknown error",
            }
        )

    # Éxito (ID-002)
    task_id = result.get("task_id")
    with get_tenant_client(org_id) as db:
        _handle_done_ticket(db, ticket_id, task_id)
        
        # Recuperar ticket actualizado para devolver objeto completo (ID-005)
        updated_ticket = (
            db.table("tickets")
            .select("*")
            .eq("id", ticket_id)
            .maybe_single()
            .execute()
        )

    if not updated_ticket.data:
        # Fallback si no se encuentra (no debería pasar)
        return {
            "ticket_id": ticket_id,
            "task_id": task_id,
            "status": "done",
        }

    return _to_ticket_response(updated_ticket.data)


@router.delete("/{ticket_id}", status_code=204)
async def delete_ticket(
    ticket_id: str,
    org_id: str = Depends(require_org_id),
):
    """Elimina un ticket (Hard delete)."""
    with get_tenant_client(org_id) as db:
        # Primero verificamos si existe
        check = db.table("tickets").select("id").eq("id", ticket_id).maybe_single().execute()
        if not check.data:
            raise HTTPException(status_code=404, detail="Ticket not found")

        # Eliminamos
        db.table("tickets").delete().eq("id", ticket_id).execute()

    return None
