"""MCP Server Stdio — Entry point para Claude Desktop.

Uso:
    python -m src.mcp.server --org-id "uuid-de-la-org"
"""

from __future__ import annotations

import argparse
import asyncio
import logging

from mcp.server import Server
from mcp.server.stdio import stdio_server

# Eager flow registration (mismos que main.py:15-17)
import src.flows.generic_flow   # noqa: F401
import src.flows.architect_flow  # noqa: F401
import src.flows.test_flows     # noqa: F401

from .config import MCPConfig
from .tools import get_static_tools, handle_tool_call
from .flow_to_tool import build_flow_tools

logger = logging.getLogger(__name__)

from contextvars import ContextVar

server = Server("FluxAgentPro-v2")

# ContextVar para manejar el config por request (especialmente para SSE)
mcp_config_var: ContextVar[MCPConfig | None] = ContextVar("mcp_config", default=None)

@server.list_tools()
async def handle_list_tools():
    """Retorna tools estáticas + dinámicas (flow-to-tool)."""
    static = get_static_tools()
    dynamic = build_flow_tools()
    return static + dynamic


@server.call_tool()
async def handle_call_tool(name: str, arguments: dict | None):
    """Route a handler apropiado."""
    config = mcp_config_var.get()
    if not config:
        # Fallback para Stdio
        config = current_config_stdio
        
    return await handle_tool_call(name, arguments or {}, config)

# Global solo para Stdio (donde solo hay un tenant por proceso)
current_config_stdio: MCPConfig | None = None

async def run_stdio_server(org_id: str):
    """Entry point del servidor MCP Stdio."""
    global current_config_stdio
    current_config_stdio = MCPConfig(org_id=org_id)
    mcp_config_var.set(current_config_stdio)

    logger.info(
        "Starting Stdio MCP Server (org_id=%s)",
        current_config_stdio.org_id,
    )

    async with stdio_server() as (read, write):
        await server.run(read, write, server.create_initialization_options())


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="FAP MCP Server")
    parser.add_argument("--org-id", required=True)
    args = parser.parse_args()
    
    logging.basicConfig(level=logging.INFO)
    asyncio.run(run_stdio_server(args.org_id))
