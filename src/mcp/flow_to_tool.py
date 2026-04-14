"""Flow-to-Tool translator — genera Tool MCP por cada flow registrado.

Combina dos fuentes:
1. FlowRegistry.get_metadata(flow_name) → nombre, category, description, depends_on
2. FLOW_INPUT_SCHEMAS.get(flow_name) → JSON Schema de input (vacío si no existe)
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from mcp.types import Tool

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


def build_flow_tools() -> list[Tool]:
    """Genera un Tool MCP por cada flow registrado en FlowRegistry.

    Post-desacople, FLOW_INPUT_SCHEMAS está vacío — todos los flows
    se generan con schema vacío, lo cual es aceptable para Sprint 1
    (solo consulta, no ejecución).
    """
    from src.flows.registry import flow_registry
    from src.api.routes.flows import FLOW_INPUT_SCHEMAS

    tools = []
    for flow_name in flow_registry.list_flows():
        meta = flow_registry.get_metadata(flow_name)
        schema = FLOW_INPUT_SCHEMAS.get(
            flow_name, {"type": "object", "properties": {}}
        )
        description = (
            meta.get("description")
            or f"Ejecutar flow de trabajo: {flow_name}"
        )

        tools.append(Tool(
            name=flow_name,
            description=description,
            inputSchema=schema,
        ))

    if not tools:
        logger.warning(
            "FlowRegistry vacío — no se generaron flow tools. "
            "Verificar que los imports eager estén presentes en server.py."
        )

    return tools


def get_flow_tool_names() -> list[str]:
    """Retorna los nombres de los flow tools registrados.

    Útil para que tools.py pueda routear las flow tools
    sin reconstruir los objetos Tool completos.
    """
    from src.flows.registry import flow_registry
    return flow_registry.list_flows()
