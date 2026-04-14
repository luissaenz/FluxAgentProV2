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
