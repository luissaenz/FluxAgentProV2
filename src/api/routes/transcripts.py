"""Transcripts de ejecucion de Flows.

Optimized snapshot endpoint that delivers a filtered, sync-ready transcript
with hand-off metadata for Realtime streaming (Paso 3.3).
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException, Depends, Query

from ..middleware import require_org_id
from ...db.session import get_tenant_client

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/transcripts", tags=["transcripts"])

# ── Constants ──────────────────────────────────────────────────────────

TERMINAL_STATES = {"done", "failed", "cancelled", "blocked"}

DEFAULT_EVENT_TYPES = ["flow_step", "agent_thought", "tool_output"]


@router.get("/{task_id}")
async def get_flow_transcript(
    task_id: str,
    org_id: str = Depends(require_org_id),
    types: str | None = Query(
        None,
        description="Comma-separated event types to include. Default: flow_step,agent_thought,tool_output",
    ),
    after_sequence: int = Query(
        0,
        ge=0,
        description="Return only events with sequence > this value",
    ),
    limit: int = Query(500, ge=1, le=1000),
):
    """
    Transcript snapshot de un Flow run con metadata de sincronizacion.

    Retorna:
    - Estado consolidado de la tarea (status, flow_type, is_running)
    - Eventos de dominio filtrados (por defecto: flow_step, agent_thought, tool_output)
    - Metadata de sync (last_sequence, has_more) para hand-off con Realtime

    Nunca incluye valores de secretos — los payloads ya estan saneados en DB.
    """
    # Resolve event types filter
    event_types = DEFAULT_EVENT_TYPES
    if types:
        event_types = [t.strip() for t in types.split(",") if t.strip()]
        if not event_types:
            # SUPUESTO: si el usuario pasa types="" o types=",,", usar defaults
            event_types = DEFAULT_EVENT_TYPES

    # ── Step 1: Verify task exists and belongs to org ──────────────────
    try:
        with get_tenant_client(org_id) as db:
            task_result = (
                db.table("tasks")
                .select("id, flow_type, status")
                .eq("id", task_id)
                .maybe_single()
                .execute()
            )
    except Exception as exc:
        logger.error("DB error verifying task %s for org %s: %s", task_id, org_id, exc)
        raise HTTPException(
            status_code=503,
            detail="Transcript temporarily unavailable — could not verify task",
        ) from exc

    if not task_result.data:
        raise HTTPException(status_code=404, detail="Task not found")

    task = task_result.data
    task_status = task.get("status", "")

    # ── Step 2: Fetch domain events with filters ───────────────────────
    try:
        with get_tenant_client(org_id) as db:
            query_builder = (
                db.table("domain_events")
                .select("id, event_type, payload, sequence, created_at")
                .eq("aggregate_id", task_id)
                .in_("event_type", event_types)
                .order("sequence", desc=False)
            )

            if after_sequence > 0:
                query_builder = query_builder.gt("sequence", after_sequence)

            # Fetch limit + 1 to detect has_more
            query_builder = query_builder.limit(limit + 1)
            events_result = query_builder.execute()
    except Exception as exc:
        logger.error("DB error fetching events for task %s: %s", task_id, exc)
        raise HTTPException(
            status_code=503,
            detail="Transcript temporarily unavailable — could not fetch events",
        ) from exc

    # ── Step 3: Build response with sync metadata ──────────────────────
    raw_events = events_result.data or []

    # Truncate to limit if has_more
    has_more = len(raw_events) > limit
    if has_more:
        raw_events = raw_events[:limit]

    # Build clean event list
    events = []
    last_sequence = after_sequence
    for evt in raw_events:
        events.append({
            "id": evt.get("id"),
            "event_type": evt.get("event_type"),
            "payload": evt.get("payload"),
            "sequence": evt.get("sequence"),
            "created_at": evt.get("created_at"),
        })
        seq = evt.get("sequence")
        if seq is not None:
            last_sequence = seq

    # Derive is_running from terminal states
    is_running = task_status.lower() not in TERMINAL_STATES if task_status else False

    return {
        "task_id": task_id,
        "flow_type": task.get("flow_type"),
        "status": task_status,
        "is_running": is_running,
        "sync": {
            "last_sequence": last_sequence,
            "has_more": has_more,
        },
        "events": events,
    }
