"""MCP Tools — 5 herramientas estáticas + handlers para el servidor MCP de FAP.

Cada handler retorna CallToolResult con TextContent (JSON serializado como string).
El output pasa por sanitize_output() antes de retornar (Regla R3).
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
    }

    # Incluir flow tools dinámicas
    from .flow_to_tool import get_flow_tool_names
    for flow_name in get_flow_tool_names():
        handlers[flow_name] = _handle_flow_tool_placeholder

    handler = handlers.get(name)
    if handler is None:
        return CallToolResult(
            content=[TextContent(
                type="text",
                text=json.dumps({"error": f"Tool '{name}' not found"}),
            )],
            isError=True,
        )

    try:
        return await handler(arguments, config)
    except Exception as exc:
        logger.error("Error ejecutando tool '%s': %s", name, exc)
        return CallToolResult(
            content=[TextContent(
                type="text",
                text=json.dumps(sanitize_output(
                    {"error": f"Error ejecutando '{name}': {str(exc)}"}
                )),
            )],
            isError=True,
        )


def _make_result(data: Any) -> CallToolResult:
    """Helper: crea CallToolResult con JSON sanitizado."""
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
        logger.error("Error consultando agent_catalog: %s", exc)
        return CallToolResult(
            content=[TextContent(
                type="text",
                text=json.dumps({"error": "No se pudo conectar a la base de datos"}),
            )],
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
            content=[TextContent(
                type="text",
                text=json.dumps({"error": "agent_id es requerido"}),
            )],
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
        logger.error("Error consultando agent_catalog: %s", exc)
        return CallToolResult(
            content=[TextContent(
                type="text",
                text=json.dumps({"error": "No se pudo conectar a la base de datos"}),
            )],
            isError=True,
        )

    if not result.data:
        return CallToolResult(
            content=[TextContent(
                type="text",
                text=json.dumps({"error": f"Agente '{agent_id}' no encontrado para esta organización"}),
            )],
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


async def _handle_flow_tool_placeholder(
    arguments: dict[str, Any],
    config: Any,
) -> CallToolResult:
    """Placeholder para flow tools — Sprint 1 solo lista, no ejecuta."""
    return CallToolResult(
        content=[TextContent(
            type="text",
            text=json.dumps({
                "error": "La ejecución de flows no está habilitada en Sprint 1. "
                         "Este servidor solo permite consultar la lista de flows y agentes."
            }),
        )],
        isError=True,
    )
