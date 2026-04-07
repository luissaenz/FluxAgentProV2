"""Transcripts de ejecucion de Flows."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Depends, Query

from ..middleware import require_org_id
from ...db.session import get_tenant_client

router = APIRouter(prefix="/transcripts", tags=["transcripts"])


@router.get("/{task_id}")
async def get_flow_transcript(
    task_id: str,
    org_id: str = Depends(require_org_id),
    limit: int = Query(200, ge=1, le=1000),
):
    """
    Transcript historico de un Flow run.

    Retorna eventos de dominio filtrados por aggregate_id = task_id.

    NUNCA incluye valores de secretos — los payloads ya estan en DB
    sin secretos (la redaccion se hace al almacenar, no al leer).
    """
    # Verificar que la task existe y pertenece al org
    with get_tenant_client(org_id) as db:
        task_result = (
            db.table("tasks")
            .select("id, flow_type, status")
            .eq("id", task_id)
            .maybe_single()
            .execute()
        )

    if not task_result.data:
        raise HTTPException(status_code=404, detail="Task not found")

    task = task_result.data

    # Obtener eventos del Flow run
    with get_tenant_client(org_id) as db:
        events_result = (
            db.table("domain_events")
            .select("id, event_type, aggregate_type, aggregate_id, payload, sequence, created_at")
            .eq("aggregate_id", task_id)
            .order("sequence", desc=False)
            .limit(limit)
            .execute()
        )

    events = []
    for evt in (events_result.data or []):
        events.append({
            "id": evt.get("id"),
            "event_type": evt.get("event_type"),
            "aggregate_type": evt.get("aggregate_type"),
            "aggregate_id": evt.get("aggregate_id"),
            "payload": evt.get("payload"),
            "sequence": evt.get("sequence"),
            "created_at": evt.get("created_at"),
        })

    return {
        "task_id": task_id,
        "flow_type": task.get("flow_type"),
        "status": task.get("status"),
        "events": events,
    }
