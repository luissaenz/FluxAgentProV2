"""MCP Tools — Static and Dynamic tool handlers for FluxAgentPro.

Each handler returns CallToolResult with TextContent (JSON serialized string).
Output passes through sanitize_output() before returning (Rule R3).
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any

from mcp.types import Tool, TextContent, CallToolResult

from .sanitizer import sanitize_output
from ..db.session import get_service_client

logger = logging.getLogger(__name__)

# ── Tool Definitions ─────────────────────────────────────────────

STATIC_TOOLS = [
    Tool(
        name="list_flows",
        description="Listar todos los flows de trabajo registrados en FluxAgentPro con su metadata (categoría, dependencias, descripción).",
        inputSchema={"type": "object", "properties": {}},
    ),
    Tool(
        name="list_agents",
        description="Listar todos los agentes activos configurados para esta organización desde el catálogo de agentes.",
        inputSchema={"type": "object", "properties": {}},
    ),
    Tool(
        name="get_agent_detail",
        description="Obtener el detalle completo de un agente específico, incluyendo su SOUL (personalidad), herramientas permitidas y configuración.",
        inputSchema={
            "type": "object",
            "required": ["agent_id"],
            "properties": {
                "agent_id": {
                    "type": "string",
                    "description": "UUID del agente a consultar",
                },
            },
        },
    ),
    Tool(
        name="get_server_time",
        description="Obtener la hora actual del servidor en formato ISO 8601 UTC.",
        inputSchema={"type": "object", "properties": {}},
    ),
    Tool(
        name="list_capabilities",
        description="Listar las capacidades y metadata del servidor MCP de FluxAgentPro (versión, organización, transporte, cantidad de tools).",
        inputSchema={"type": "object", "properties": {}},
    ),
    Tool(
        name="execute_flow",
        description="Instanciar y ejecutar un flow de trabajo por nombre.",
        inputSchema={
            "type": "object",
            "required": ["flow_type"],
            "properties": {
                "flow_type": {"type": "string", "description": "Nombre del flow a ejecutar"},
                "input_data": {"type": "object", "description": "Diccionario con los parámetros de entrada"}
            }
        }
    ),
    Tool(
        name="get_task",
        description="Consultar el estado y resultado de una tarea o ejecución de flow previa.",
        inputSchema={
            "type": "object",
            "required": ["task_id"],
            "properties": {
                "task_id": {"type": "string", "description": "UUID de la tarea a consultar"}
            }
        }
    ),
    Tool(
        name="approve_task",
        description="Aprobar una tarea que requiere validación humana (HITL).",
        inputSchema={
            "type": "object",
            "required": ["task_id"],
            "properties": {
                "task_id": {"type": "string", "description": "UUID de la tarea a aprobar"},
                "notes": {"type": "string", "description": "Notas opcionales para la auditoría"}
            }
        }
    ),
    Tool(
        name="reject_task",
        description="Rechazar una tarea que requiere validación humana (HITL).",
        inputSchema={
            "type": "object",
            "required": ["task_id"],
            "properties": {
                "task_id": {"type": "string", "description": "UUID de la tarea a rechazar"},
                "reason": {"type": "string", "description": "Razón del rechazo"}
            }
        }
    ),
    Tool(
        name="create_workflow",
        description="Generar un nuevo template de workflow a partir de una descripción en lenguaje natural.",
        inputSchema={
            "type": "object",
            "required": ["description"],
            "properties": {
                "description": {"type": "string", "description": "Descripción de lo que debe hacer el workflow"}
            }
        }
    ),
    Tool(
        name="activate_service",
        description="Activa un servicio del catálogo de integraciones para la organización actual.",
        inputSchema={
            "type": "object",
            "required": ["service_id"],
            "properties": {
                "service_id": {
                    "type": "string",
                    "description": "ID del servicio a activar (ej: google_sheets, gmail, stripe)"
                }
            }
        }
    ),
    Tool(
        name="store_credential",
        description="Almacena una credencial (API key, token OAuth, etc.) en el vault seguro. El valor se encripta.",
        inputSchema={
            "type": "object",
            "required": ["secret_name", "secret_value"],
            "properties": {
                "secret_name": {
                    "type": "string",
                    "description": "Nombre del secreto (ej: google_oauth_token, stripe_api_key)"
                },
                "secret_value": {
                    "type": "string",
                    "description": "Valor del secreto. Se almacena encriptado."
                }
            }
        }
    ),
    Tool(
        name="retry_workflow",
        description="Re-ejecuta la resolución de un workflow que estaba pendiente de integraciones.",
        inputSchema={
            "type": "object",
            "required": ["task_id"],
            "properties": {
                "task_id": {
                    "type": "string",
                    "description": "ID de la tarea del workflow que necesita re-resolución"
                }
            }
        }
    ),
]


def get_static_tools() -> list[Tool]:
    """Retorna las definiciones de tools estáticas."""
    return list(STATIC_TOOLS)


# ── Tool Handlers ────────────────────────────────────────────────

async def handle_tool_call(
    name: str,
    arguments: dict[str, Any],
    config: Any,
) -> CallToolResult:
    """Route a tool call to the correct handler.
    
    Includes dynamic flow tools by mapping them to execute_flow.
    """
    from .flow_to_tool import get_flow_tool_names
    from .handlers import (
        handle_execute_flow, handle_get_task, handle_approve_task, 
        handle_reject_task, handle_create_workflow
    )
    from .exceptions import map_exception_to_mcp_error

    # 1. Check for dynamic flow tools
    if name in get_flow_tool_names():
        try:
            res = await handle_execute_flow({"flow_type": name, "input_data": arguments}, config)
            return _make_result(res)
        except Exception as exc:
            logger.error("Error executing flow tool '%s': %s", name, exc)
            err = map_exception_to_mcp_error(exc)
            return CallToolResult(
                content=[TextContent(type="text", text=json.dumps(err.to_dict()))],
                isError=True,
            )

    # 2. Map static handlers
    handlers = {
        "list_flows": _handle_list_flows,
        "list_agents": _handle_list_agents,
        "get_agent_detail": _handle_get_agent_detail,
        "get_server_time": _handle_get_server_time,
        "list_capabilities": _handle_list_capabilities,
        "execute_flow": lambda args, cfg: handle_execute_flow(args, cfg),
        "get_task": lambda args, cfg: handle_get_task(args, cfg),
        "approve_task": lambda args, cfg: handle_approve_task(args, cfg),
        "reject_task": lambda args, cfg: handle_reject_task(args, cfg),
        "create_workflow": lambda args, cfg: handle_create_workflow(args, cfg),
        "activate_service": _handle_activate_service,
        "store_credential": _handle_store_credential,
        "retry_workflow": _handle_retry_workflow,
    }

    handler = handlers.get(name)
    if handler is None:
        return CallToolResult(
            content=[TextContent(type="text", text=json.dumps({"error": f"Tool '{name}' not found"}))],
            isError=True,
        )

    try:
        # Wrap the result in _make_result if it's raw data
        res = await handler(arguments, config)
        if isinstance(res, CallToolResult):
            return res
        return _make_result(res)
    except Exception as exc:
        logger.error("Error executing tool '%s': %s", name, exc)
        err = map_exception_to_mcp_error(exc)
        return CallToolResult(
            content=[TextContent(type="text", text=json.dumps(err.to_dict()))],
            isError=True,
        )


def _make_result(data: Any) -> CallToolResult:
    """Helper: creates CallToolResult with sanitized JSON."""
    sanitized = sanitize_output(data)
    return CallToolResult(
        content=[TextContent(
            type="text",
            text=json.dumps(sanitized, ensure_ascii=False, default=str),
        )],
    )


def _make_error(message: str) -> CallToolResult:
    """Helper: creates CallToolResult with error message."""
    return CallToolResult(
        content=[TextContent(type="text", text=json.dumps({"error": message}))],
        isError=True,
    )


# ── Individual Handlers ──────────────────────────────────────────

async def _handle_list_flows(
    arguments: dict[str, Any],
    config: Any,
) -> CallToolResult:
    """Listar flows registrados con metadata."""
    from ..flows.registry import flow_registry

    flows = []
    for flow_name in flow_registry.list_flows():
        meta = flow_registry.get_metadata(flow_name)
        flows.append({
            "name": flow_name,
            "category": meta.get("category"),
            "depends_on": meta.get("depends_on", []),
            "description": meta.get("description", ""),
        })

    return _make_result({"flows": flows, "count": len(flows)})


async def _handle_list_agents(
    arguments: dict[str, Any],
    config: Any,
) -> CallToolResult:
    """Listar agentes activos para la org."""
    try:
        svc = get_service_client()
        result = (
            svc.table("agent_catalog")
            .select("id, role, is_active, soul_json, allowed_tools, max_iter")
            .eq("org_id", config.org_id)
            .eq("is_active", True)
            .execute()
        )
        agents = result.data or []
    except Exception as exc:
        logger.error("Error consulting agent_catalog: %s", exc)
        return CallToolResult(
            content=[TextContent(type="text", text=json.dumps({"error": "DB connection error"}))],
            isError=True,
        )

    return _make_result({"agents": agents, "count": len(agents)})


async def _handle_get_agent_detail(
    arguments: dict[str, Any],
    config: Any,
) -> CallToolResult:
    """Obtener detalle de un agente específico."""
    agent_id = arguments.get("agent_id")
    if not agent_id:
        return CallToolResult(
            content=[TextContent(type="text", text=json.dumps({"error": "agent_id required"}))],
            isError=True,
        )

    try:
        svc = get_service_client()
        result = (
            svc.table("agent_catalog")
            .select("id, role, is_active, soul_json, allowed_tools, max_iter, created_at, updated_at")
            .eq("id", agent_id)
            .eq("org_id", config.org_id)
            .maybe_single()
            .execute()
        )
    except Exception as exc:
        logger.error("Error consulting agent_catalog: %s", exc)
        return CallToolResult(
            content=[TextContent(type="text", text=json.dumps({"error": "DB connection error"}))],
            isError=True,
        )

    if not result.data:
        return CallToolResult(
            content=[TextContent(type="text", text=json.dumps({"error": f"Agent '{agent_id}' not found"}))],
            isError=True,
        )

    return _make_result(result.data)


async def _handle_get_server_time(
    arguments: dict[str, Any],
    config: Any,
) -> CallToolResult:
    """Retorna la hora UTC del servidor."""
    return _make_result({
        "server_time": datetime.now(timezone.utc).isoformat(),
    })


async def _handle_list_capabilities(
    arguments: dict[str, Any],
    config: Any,
) -> CallToolResult:
    """Retorna metadata del servidor."""
    from .flow_to_tool import build_flow_tools

    static_count = len(STATIC_TOOLS)
    dynamic_count = len(build_flow_tools())

    return _make_result({
        "version": "5.0.0",
        "org_id": config.org_id,
        "transport": config.transport,
        "tools_count": static_count + dynamic_count,
        "static_tools": static_count,
        "dynamic_tools": dynamic_count,
    })


# ── Internal Handlers for Onboarding ─────────────────────────────

async def _handle_activate_service(arguments: dict, config) -> CallToolResult:
    """Activa un servicio del catálogo."""
    from ..flows.integration_resolver import IntegrationResolver

    service_id = arguments.get("service_id")
    if not service_id:
        return _make_error("service_id requerido")

    # Validar existe en catálogo
    try:
        db = get_service_client()
        svc = db.table("service_catalog").select("id, name").eq("id", service_id).maybe_single().execute()
        if not svc.data:
            return _make_error(f"Servicio '{service_id}' no encontrado en el catálogo")

        resolver = IntegrationResolver(org_id=config.org_id)
        # NOTA: MVP activa sin secret_names, usuario configura después con store_credential
        await resolver.activate_service(service_id)
        
        return _make_result({
            "status": "activated", 
            "service_id": service_id, 
            "org_id": config.org_id
        })
    except Exception as exc:
        logger.error("Error activating service: %s", exc)
        return _make_error(f"DB Error: {str(exc)}")


async def _handle_store_credential(arguments: dict, config) -> CallToolResult:
    """Almacena una credencial en Vault."""
    from ..flows.integration_resolver import IntegrationResolver

    secret_name = arguments.get("secret_name")
    secret_value = arguments.get("secret_value")
    if not secret_name or not secret_value:
        return _make_error("secret_name y secret_value requeridos")

    try:
        resolver = IntegrationResolver(org_id=config.org_id)
        await resolver.store_credential(secret_name, secret_value)
        return _make_result({
            "status": "stored",
            "secret_name": secret_name,
            "message": f"Credencial '{secret_name}' almacenada correctamente",
        })
    except Exception as exc:
        logger.error("Error storing credential: %s", exc)
        return _make_error(f"Vault Error: {str(exc)}")


async def _handle_retry_workflow(arguments: dict, config) -> CallToolResult:
    """Re-ejecuta la resolución de un workflow pendiente."""
    from ..flows.integration_resolver import IntegrationResolver
    from ..flows.architect_flow import ArchitectFlow
    from ..flows.workflow_definition import WorkflowDefinition

    task_id = arguments.get("task_id")
    if not task_id:
        return _make_error("task_id requerido")

    try:
        db = get_service_client()
        task = db.table("tasks").select("*").eq("id", task_id).eq("org_id", config.org_id).maybe_single().execute()
        
        if not task.data:
            return _make_error("Tarea no encontrada")
        
        # NOTA: tasks.status es TEXT libre, permitimos reintento de resolution_pending
        if task.data["status"] != "resolution_pending":
            return _make_error(f"Tarea en estado '{task.data['status']}', esperaba 'resolution_pending'")

        workflow_def_raw = task.data.get("result", {}).get("extracted_definition")
        if not workflow_def_raw:
            return _make_error("No se encontró definición de workflow guardada en task.result")

        # Re-resolver
        resolver = IntegrationResolver(org_id=config.org_id)
        resolution = await resolver.resolve(workflow_def_raw)

        if not resolution.is_ready:
            return _make_result({
                "status": "still_not_ready",
                "needs_activation": resolution.needs_activation,
                "not_found": resolution.not_found,
                "needs_credentials": resolution.needs_credentials,
            })

        # Persistir workflow reutilizando lógica de ArchitectFlow
        mapped_def = resolver.apply_mapping(workflow_def_raw, resolution.tool_mapping)
        workflow_def_obj = WorkflowDefinition(**mapped_def)

        # Usamos una instancia de ArchitectFlow para acceder a sus métodos de persistencia
        flow_instance = ArchitectFlow(org_id=config.org_id, user_id="mcp-system")
        
        # RESTORE STATE (Fix ID-002)
        from ..flows.architect_flow import ArchitectState
        flow_instance.state = ArchitectState.from_snapshot(task.data)
        
        from ..events.store import EventStore
        flow_instance.event_store = EventStore(
            config.org_id, 
            "mcp-system", 
            correlation_id=flow_instance.state.correlation_id
        )
        
        # LOGGING (Fix ID-004)
        await flow_instance.emit_event("flow.retry_started", {"task_id": task_id})
        
        # Asegurar flow_type único
        safe_flow_type = flow_instance._ensure_unique_flow_type(workflow_def_obj.flow_type)
        workflow_def_obj.flow_type = safe_flow_type

        # Ejecutar persistencia (Tareas atómicas del ArchitectFlow)
        template_id = await flow_instance._persist_template(workflow_def_obj)
        agents_created = await flow_instance._persist_agents(workflow_def_obj)
        flow_instance._register_dynamic_flow(safe_flow_type, workflow_def_obj)

        # Actualizar task a completed
        db.table("tasks").update({
            "status": "completed",
            "result": {
                "flow_type": safe_flow_type,
                "template_id": template_id,
                "agents_created": agents_created,
                "status": "workflow_created"
            },
        }).eq("id", task_id).execute()

        return _make_result({
            "status": "workflow_created",
            "task_id": task_id,
            "flow_type": safe_flow_type,
            "template_id": template_id,
        })
    except Exception as exc:
        logger.error("Error in retry_workflow: %s", exc)
        return _make_error(f"Resolution Error: {str(exc)}")
