"""Endpoints para detalle de agentes con metricas."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from ..middleware import require_org_id
from ...db.session import get_tenant_client

router = APIRouter(prefix="/agents", tags=["agents"])


@router.get("/{agent_id}/detail")
async def get_agent_detail(
    agent_id: str,
    org_id: str = Depends(require_org_id),
):
    """
    Detalle completo de un agente.

    Incluye: datos del catalog, metricas de tokens, tareas recientes,
    y referencias a credenciales en Vault (solo nombres, nunca valores).
    """
    from fastapi import HTTPException

    with get_tenant_client(org_id) as db:
        # 1. Registro base del catálogo
        agent_result = (
            db.table("agent_catalog")
            .select("*")
            .eq("id", agent_id)
            .eq("org_id", org_id)
            .maybe_single()
            .execute()
        )

        if not agent_result.data:
            raise HTTPException(status_code=404, detail="Agent not found")

        agent = agent_result.data
        agent_role = agent.get("role", "")

        # 2. Enriquecimiento con Metadata (SOUL)
        # Se maneja como opcional para no bloquear métricas críticas en caso de error
        try:
            metadata_result = (
                db.table("agent_metadata")
                .select("display_name, soul_narrative, avatar_url")
                .eq("org_id", org_id)
                .eq("agent_role", agent_role)
                .maybe_single()
                .execute()
            )

            if metadata_result and metadata_result.data:
                # Inyectar metadata en el objeto del agente
                agent.update(metadata_result.data)
            
        except Exception as exc:
            import logging
            logging.getLogger(__name__).warning(
                "Error al recuperar metadata SOUL para el rol '%s' en la organización '%s'. "
                "Causa probable: tabla agent_metadata no migrada o error de conectividad. Detalle: %s", 
                agent_role, org_id, exc
            )
        
        # Fallbacks finales: Garantizar que el frontend siempre tenga claves consistentes
        if not agent.get("display_name"):
            agent["display_name"] = agent_role.replace("-", " ").title() if agent_role else "Unknown Agent"
            
        agent.setdefault("soul_narrative", None)
        agent.setdefault("avatar_url", None)

    # Tareas donde este agente participó
    with get_tenant_client(org_id) as db:
        tasks_result = (
            db.table("tasks")
            .select("id, flow_type, status, tokens_used, created_at, updated_at, error")
            .eq("assigned_agent_role", agent_role)
            .order("created_at", desc=True)
            .limit(50)
            .execute()
        )

        # Agregados de tokens para este agente
        tokens_result = (
            db.table("tasks")
            .select("tokens_used")
            .eq("assigned_agent_role", agent_role)
            .execute()
        )

    total_tokens = sum(
        t.get("tokens_used", 0)
        for t in (tokens_result.data or [])
    )

    status_counts: dict = {}
    for t in (tasks_result.data or []):
        s = t.get("status", "unknown")
        status_counts[s] = status_counts.get(s, 0) + 1

    # Credenciales — solo nombres de secrets asociados a las tools del agente
    secret_refs: list = []
    allowed_tools = agent.get("allowed_tools") or []
    if allowed_tools:
        try:
            from ...tools.registry import tool_registry
            for tool_name in allowed_tools:
                tool_meta = tool_registry.get(tool_name)
                if tool_meta:
                    secret_refs.append({
                        "tool": tool_name,
                        "description": tool_meta.description if hasattr(tool_meta, 'description') else None,
                    })
        except Exception:
            pass  # Si no se puede cargar el registry, continuar sin refs

    return {
        "agent": agent,
        "metrics": {
            "total_tokens": total_tokens,
            "tasks_by_status": status_counts,
            "recent_tasks": tasks_result.data or [],
        },
        "credentials": secret_refs,
    }
