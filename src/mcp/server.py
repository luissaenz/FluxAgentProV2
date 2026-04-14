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

server = Server("FluxAgentPro-v2")
config: MCPConfig  # se asigna en main()


@server.list_tools()
async def handle_list_tools():
    """Retorna tools estáticas + dinámicas (flow-to-tool)."""
    static = get_static_tools()
    dynamic = build_flow_tools()
    return static + dynamic


@server.call_tool()
async def handle_call_tool(name: str, arguments: dict | None):
    """Route a handler apropiado."""
    return await handle_tool_call(name, arguments or {}, config)


async def main():
    """Entry point del servidor MCP Stdio."""
    global config

    parser = argparse.ArgumentParser(description="FAP MCP Server")
    parser.add_argument(
        "--org-id",
        required=True,
        help="UUID de la organización",
    )
    args = parser.parse_args()

    config = MCPConfig(org_id=args.org_id)

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    logger.info(
        "MCP Server starting (org_id=%s, transport=%s)",
        config.org_id,
        config.transport,
    )

    async with stdio_server() as (read, write):
        await server.run(read, write, server.create_initialization_options())


if __name__ == "__main__":
    asyncio.run(main())
