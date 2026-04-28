"""MCP Tools — 5 herramientas estáticas + handlers para el servidor MCP de FAP.

Cada handler retorna CallToolResult con TextContent (JSON serializado como string).
El output pasa por sanitize_output() antes de retornar (Regla R3).
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any

from mcp.types import CallToolResult, TextContent, Tool

from ..db.session import get_service_client
from .exceptions import (
    InternalError,
    InvalidParams,
    MethodNotFound,
    mcp_error_to_response,
)
from .sanitizer import sanitize_output

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
        name="get_task",
        description="Consultar el estado detallado de una tarea/flow en ejecución mediante su task_id.",
        inputSchema={
            "type": "object",
            "required": ["task_id"],
            "properties": {
                "task_id": {
                    "type": "string",
                    "description": "UUID de la tarea a consultar",
                }
            },
        },
    ),
    Tool(
        name="approve_task",
        description="Aprobar una tarea que se encuentra pausada esperando intervención humana (HITL).",
        inputSchema={
            "type": "object",
            "required": ["task_id"],
            "properties": {
                "task_id": {
                    "type": "string",
                    "description": "UUID de la tarea a aprobar",
                }
            },
        },
    ),
    Tool(
        name="reject_task",
        description="Rechazar una tarea que se encuentra pausada esperando intervención humana (HITL).",
        inputSchema={
            "type": "object",
            "required": ["task_id"],
            "properties": {
                "task_id": {
                    "type": "string",
                    "description": "UUID de la tarea a rechazar",
                }
            },
        },
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
    """Route una llamada a tool al handler correcto.

    Args:
        name: Nombre de la tool invocada.
        arguments: Argumentos recibidos del agente.
        config: MCPConfig con org_id y transport.

    Returns:
        CallToolResult con el resultado o error.
    """
    handlers = {
        "list_flows": _handle_list_flows,
        "list_agents": _handle_list_agents,
        "get_agent_detail": _handle_get_agent_detail,
        "get_server_time": _handle_get_server_time,
        "list_capabilities": _handle_list_capabilities,
        "get_task": _handle_get_task,
        "approve_task": _handle_approve_task,
        "reject_task": _handle_reject_task,
    }

    # 1. Intentar obtener handler estático
    handler = handlers.get(name)

    # 2. Si no es estático, verificar si es un flow dinámico
    is_flow = False
    if handler is None:
        from .flow_to_tool import get_flow_tool_names

        if name in get_flow_tool_names():
            is_flow = True
        else:
            raise MethodNotFound(f"Tool '{name}' not found")

    try:
        # 3. Despachar
        if is_flow:
            return await _handle_execute_flow_with_name(name, arguments, config)

        return await handler(arguments, config)
    except Exception as exc:
        # Usar el helper centralizado para formatear el error
        error_resp = mcp_error_to_response(exc)
        return CallToolResult(
            content=[
                TextContent(
                    type="text",
                    text=json.dumps(sanitize_output(error_resp["error"])),
                )
            ],
            isError=True,
        )


def _make_result(data: Any) -> CallToolResult:
    """Helper: crea CallToolResult con JSON sanitizado."""
    sanitized = sanitize_output(data)
    return CallToolResult(
        content=[
            TextContent(
                type="text",
                text=json.dumps(sanitized, ensure_ascii=False, default=str),
            )
        ],
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
        flows.append(
            {
                "name": flow_name,
                "category": meta.get("category"),
                "depends_on": meta.get("depends_on", []),
                "description": meta.get("description", ""),
            }
        )

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
        raise InternalError(f"Database connection error: {str(exc)}") from exc

    return _make_result({"agents": agents, "count": len(agents)})


async def _handle_get_agent_detail(
    arguments: dict[str, Any],
    config: Any,
) -> CallToolResult:
    """Obtener detalle de un agente específico."""
    agent_id = arguments.get("agent_id")
    if not agent_id:
        raise InvalidParams("agent_id is required")

    try:
        svc = get_service_client()
        result = (
            svc.table("agent_catalog")
            .select(
                "id, role, is_active, soul_json, allowed_tools, max_iter, created_at, updated_at"
            )
            .eq("id", agent_id)
            .eq("org_id", config.org_id)
            .maybe_single()
            .execute()
        )
    except Exception as exc:
        raise InternalError(f"Database connection error: {str(exc)}") from exc

    if not result.data:
        raise MethodNotFound(f"Agent '{agent_id}' not found for this organization")

    return _make_result(result.data)


async def _handle_get_server_time(
    arguments: dict[str, Any],
    config: Any,
) -> CallToolResult:
    """Retorna la hora UTC del servidor."""
    return _make_result(
        {
            "server_time": datetime.now(timezone.utc).isoformat(),
        }
    )


async def _handle_list_capabilities(
    arguments: dict[str, Any],
    config: Any,
) -> CallToolResult:
    """Retorna metadata del servidor."""
    from .flow_to_tool import build_flow_tools

    static_count = len(STATIC_TOOLS)
    dynamic_count = len(build_flow_tools())

    return _make_result(
        {
            "version": "5.0.0",
            "org_id": config.org_id,
            "transport": config.transport,
            "tools_count": static_count + dynamic_count,
            "static_tools": static_count,
            "dynamic_tools": dynamic_count,
        }
    )


async def _handle_get_task(
    arguments: dict[str, Any],
    config: Any,
) -> CallToolResult:
    """Consultar estado de una tarea."""
    from .handlers import handle_get_task

    task_id = arguments.get("task_id")
    if not task_id:
        raise InvalidParams("task_id is required")

    # Mock claims for internal MCP call (Stdio doesn't have JWT, uses org_id from config)
    claims = {"sub": "mcp-stdio-user", "role": "service_role"}

    res = await handle_get_task(config.org_id, task_id, claims)
    return _make_result(res)


async def _handle_approve_task(
    arguments: dict[str, Any],
    config: Any,
) -> CallToolResult:
    """Aprobar tarea HITL."""
    from .handlers import handle_approve_task

    task_id = arguments.get("task_id")
    if not task_id:
        raise InvalidParams("task_id is required")

    claims = {"sub": "mcp-stdio-user", "role": "service_role"}
    res = await handle_approve_task(config.org_id, task_id, claims)
    return _make_result(res)


async def _handle_reject_task(
    arguments: dict[str, Any],
    config: Any,
) -> CallToolResult:
    """Rechazar tarea HITL."""
    from .handlers import handle_reject_task

    task_id = arguments.get("task_id")
    if not task_id:
        raise InvalidParams("task_id is required")

    claims = {"sub": "mcp-stdio-user", "role": "service_role"}
    res = await handle_reject_task(config.org_id, task_id, claims)
    return _make_result(res)


async def _handle_execute_flow_with_name(
    name: str,
    arguments: dict[str, Any],
    config: Any,
) -> CallToolResult:
    """Handler real que conoce el nombre del flujo."""
    from .handlers import handle_execute_flow

    claims = {"sub": "mcp-stdio-user", "role": "service_role"}
    res = await handle_execute_flow(
        org_id=config.org_id, flow_type=name, input_data=arguments, claims=claims
    )
    return _make_result(res)
