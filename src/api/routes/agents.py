"""Endpoints para detalle de agentes con metricas y creacion via POST."""

from __future__ import annotations

import logging
from typing import Any, Dict, List
from uuid import uuid4

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from pydantic import BaseModel

from ...crews.base_crew import BaseCrew
from ...db.session import get_tenant_client
from ..middleware import require_org_id, verify_org_membership

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/agents", tags=["agents"])


class AgentCreate(BaseModel):
    role: str
    soul_json: Dict[str, Any]
    allowed_tools: List[str] = []
    max_iter: int = 3


class AgentResponse(BaseModel):
    id: str
    org_id: str
    role: str
    soul_json: Dict[str, Any]
    allowed_tools: List[str] = []
    max_iter: int
    created_at: str | None = None


class RunAgentRequest(BaseModel):
    """Request para ejecutar un agente."""

    input_data: Dict[str, Any] = {}


class RunAgentResponse(BaseModel):
    """Respuesta al ejecutar un agente."""

    task_id: str
    status: str


@router.post("", response_model=AgentResponse, status_code=201)
async def create_agent(
    payload: AgentCreate,
    org_id: str = Depends(require_org_id),
):
    """Create or upsert an agent in agent_catalog via POST.

    Uses TenantClient for RLS compliance (D4 fix vs plan).
    Upserts via on_conflict='org_id,role' to allow re-saving.
    Returns 409 on duplicate role within same org.
    """
    with get_tenant_client(org_id) as db:
        existing = (
            db.table("agent_catalog")
            .select("id")
            .eq("org_id", org_id)
            .eq("role", payload.role)
            .maybe_single()
            .execute()
        )

        if existing.data:
            result = (
                db.table("agent_catalog")
                .update({
                    "soul_json": payload.soul_json,
                    "allowed_tools": payload.allowed_tools,
                    "max_iter": payload.max_iter,
                    "is_active": True,
                })
                .eq("id", existing.data["id"])
                .execute()
            )
            logger.info("Agent '%s' updated in org '%s'", payload.role, org_id)
            return AgentResponse(**result.data[0])

        result = (
            db.table("agent_catalog")
            .insert({
                "org_id": org_id,
                "role": payload.role,
                "soul_json": payload.soul_json,
                "allowed_tools": payload.allowed_tools,
                "max_iter": payload.max_iter,
                "is_active": True,
            })
            .execute()
        )

        logger.info("Agent '%s' created in org '%s'", payload.role, org_id)
        return AgentResponse(**result.data[0])


@router.get("/by-role/{role}")
async def get_agent_by_role(
    role: str,
    org_id: str = Depends(require_org_id),
):
    """Get agent config by role name. Returns agent_catalog record."""
    with get_tenant_client(org_id) as db:
        result = (
            db.table("agent_catalog")
            .select("*")
            .eq("org_id", org_id)
            .eq("role", role)
            .eq("is_active", True)
            .maybe_single()
            .execute()
        )

        if not result.data:
            raise HTTPException(status_code=404, detail=f"Agent '{role}' not found")

        return result.data


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
                agent_role,
                org_id,
                exc,
            )

        # Fallbacks finales: Garantizar que el frontend siempre tenga claves consistentes
        if not agent.get("display_name"):
            agent["display_name"] = (
                agent_role.replace("-", " ").title() if agent_role else "Unknown Agent"
            )

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

    total_tokens = sum(t.get("tokens_used", 0) for t in (tokens_result.data or []))

    status_counts: dict = {}
    for t in tasks_result.data or []:
        s = t.get("status", "unknown")
        status_counts[s] = status_counts.get(s, 0) + 1

    # Credenciales — solo nombres de secrets asociados a las tools del agente
    secret_refs: list = []
    allowed_tools = agent.get("allowed_tools") or []
    if allowed_tools:
        try:
            from ...tools.registry import tool_registry

            for tool_name in allowed_tools:
                # SUPUESTO: Pass org_id for tenant-aware metadata lookup
                tool_meta = tool_registry.get(tool_name, org_id=org_id)
                if tool_meta:
                    secret_refs.append(
                        {
                            "tool": tool_name,
                            "description": tool_meta.description
                            if hasattr(tool_meta, "description")
                            else None,
                        }
                    )
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


@router.post("/{role}/run", response_model=RunAgentResponse)
async def run_agent(
    role: str,
    request: RunAgentRequest,
    background_tasks: BackgroundTasks,
    auth: dict = Depends(verify_org_membership),
):
    """
    Ejecutar un agente específico por su rol.
    Retorna un task_id para polling.
    """
    org_id = auth["org_id"]

    # 1. Generate task_id and correlation_id for persistence
    task_id = str(uuid4())
    correlation_id = f"manual-agent-{role}-{org_id[:8]}-{uuid4().hex[:6]}"

    # 2. Create initial task record in 'pending' state
    with get_tenant_client(org_id) as db:
        db.table("tasks").insert(
            {
                "id": task_id,
                "org_id": org_id,
                "flow_type": f"agent:{role}",
                "status": "pending",
                "payload": request.input_data,
                "correlation_id": correlation_id,
            }
        ).execute()

    # 3. Start execution in background
    async def _execute():
        try:
            # Initialize BaseCrew
            crew = BaseCrew(org_id=org_id, role=role)

            # Mark as running
            with get_tenant_client(org_id) as db:
                db.table("tasks").update({"status": "running"}).eq(
                    "id", task_id
                ).execute()

            # Execute
            result = await crew.run_async(
                task_description="Execute assigned task", inputs=request.input_data
            )

            # Update to completed
            with get_tenant_client(org_id) as db:
                db.table("tasks").update(
                    {
                        "status": "completed",
                        "result": str(result),
                        "tokens_used": crew.get_last_tokens_used(),
                    }
                ).eq("id", task_id).execute()

        except Exception as e:
            import logging

            logging.getLogger(__name__).error("Agent execution failed: %s", e)
            # Update to failed
            with get_tenant_client(org_id) as db:
                db.table("tasks").update({"status": "failed", "error": str(e)}).eq(
                    "id", task_id
                ).execute()

    background_tasks.add_task(_execute)

    return RunAgentResponse(task_id=task_id, status="accepted")
