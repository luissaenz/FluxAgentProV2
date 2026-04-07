"""Metricas del sistema agentino para el dashboard."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from ..middleware import require_org_id
from ...db.session import get_tenant_client

router = APIRouter(prefix="/flow-metrics", tags=["flow-metrics"])


@router.get("")
async def get_overview_metrics(org_id: str = Depends(require_org_id)):
    """
    Metricas globales para el Overview (SectionCards).

    Retorna SOLO datos del sistema agentino:
    - Conteos de tasks por status
    - Total de tokens consumidos
    - Aprobaciones pendientes
    - Ultimos 10 eventos

    NUNCA retorna payload ni result (datos de operatoria).
    """
    with get_tenant_client(org_id) as db:
        tasks_result = db.table("tasks").select("status, tokens_used").execute()

        approvals_result = (
            db.table("pending_approvals")
            .select("id", count="exact")
            .eq("status", "pending")
            .execute()
        )

        events_result = (
            db.table("domain_events")
            .select("event_type, aggregate_type, aggregate_id, created_at, payload")
            .order("created_at", desc=True)
            .limit(10)
            .execute()
        )

    status_counts: dict = {}
    total_tokens = 0
    for row in tasks_result.data or []:
        s = row.get("status", "unknown")
        status_counts[s] = status_counts.get(s, 0) + 1
        total_tokens += row.get("tokens_used", 0) or 0

    return {
        "tasks": {
            "total": sum(status_counts.values()),
            "by_status": status_counts,
        },
        "tokens": {
            "total": total_tokens,
        },
        "approvals": {
            "pending": approvals_result.count or 0,
        },
        "events": {
            "recent": events_result.data or [],
        },
    }


@router.get("/by-type")
async def get_metrics_by_flow_type(org_id: str = Depends(require_org_id)):
    """
    Metricas por flow_type (usa vista v_flow_metrics).
    Para enriquecer Overview con seccion de flows activos.
    """
    with get_tenant_client(org_id) as db:
        result = db.table("v_flow_metrics").select("*").execute()

    return result.data or []


@router.get("/by-type/{flow_type}/runs")
async def get_flow_runs(
    flow_type: str,
    org_id: str = Depends(require_org_id),
    limit: int = 20,
    offset: int = 0,
):
    """
    Historial de ejecuciones de un flow type.
    Solo datos del sistema agentino — NO incluye payload ni result.
    """
    with get_tenant_client(org_id) as db:
        result = (
            db.table("tasks")
            .select(
                "id, flow_type, status, tokens_used, "
                "created_at, updated_at, error, correlation_id"
            )
            .eq("flow_type", flow_type)
            .order("created_at", desc=True)
            .range(offset, offset + limit - 1)
            .execute()
        )

    return result.data or []


@router.get("/by-agent")
async def get_metrics_by_agent(org_id: str = Depends(require_org_id)):
    """
    Métricas de tokens por agente (role en agent_catalog).
    Relaciona agent_catalog con tasks via agent_role del template.
    """
    with get_tenant_client(org_id) as db:
        # Get all agents
        agents_result = db.table("agent_catalog").select("id, role").execute()

        # Get tasks with tokens aggregated by flow_type (proxy for agent)
        tasks_result = db.table("tasks").select("flow_type, tokens_used").execute()

    # Aggregate by flow_type prefix (e.g., "bartenders_preventa" -> agent)
    tokens_by_flow: dict = {}
    for row in tasks_result.data or []:
        ft = row.get("flow_type", "")
        tokens = row.get("tokens_used", 0) or 0
        tokens_by_flow[ft] = tokens_by_flow.get(ft, 0) + tokens

    # Map to agents
    agent_tokens = []
    for agent in agents_result.data or []:
        role = agent.get("role", "")
        # Find matching flow types (heuristic)
        matching_tokens = sum(
            v for k, v in tokens_by_flow.items() if role.lower() in k.lower()
        )
        agent_tokens.append(
            {
                "agent_role": role,
                "agent_id": agent.get("id"),
                "tokens_used": matching_tokens,
            }
        )

    return agent_tokens
