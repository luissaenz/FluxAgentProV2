"""src/cli/commands/tools_list.py — `fap tools list` CLI command.

Lists available tools from ToolRegistry (local) and MCP servers.
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table

from src.cli.config import CLIConfig
from src.db.session import get_service_client

logger = logging.getLogger(__name__)

console = Console()
tools_list_app = typer.Typer(
    help="List available tools (local + MCP).",
    no_args_is_help=True,
)


@tools_list_app.command("list")
def list_tools(
    org_id: Optional[str] = typer.Option(
        None, "--org-id", "-o", help="Organization UUID"
    ),
    source: Optional[str] = typer.Option(
        None, "--source", "-s", help="Filter: local|mcp"
    ),
    json_output: bool = typer.Option(
        False, "--json", help="Output as JSON"
    ),
) -> None:
    """List all available tools from ToolRegistry and MCP servers."""
    if source is not None and source not in ("local", "mcp"):
        console.print("[red]Error:[/red] --source must be 'local' or 'mcp'")
        raise typer.Exit(code=1)

    config = CLIConfig.load()
    if org_id is None:
        org_id = config.org_id

    if not org_id:
        console.print(
            "[red]Error:[/red] --org-id required. "
            "Set FAP_ORG_ID in .env or pass --org-id."
        )
        raise typer.Exit(code=1)

    tools = _collect_tools(org_id, source)

    if json_output:
        console.print(json.dumps(tools, indent=2, ensure_ascii=False))
    else:
        _print_table(tools)

    console.print(f"\n[bold]Total:[/bold] {len(tools)} tool(s)")


def _collect_tools(org_id: str, source: Optional[str] = None) -> list[dict]:
    """Collect tools from ToolRegistry and MCP servers."""
    from src.tools.registry import tool_registry

    tools: list[dict] = []

    # Local tools
    if source in (None, "local"):
        for name in tool_registry.list_tools():
            if ":" in name:
                continue
            meta = tool_registry.get_metadata(name)
            if not meta:
                continue
            tools.append({
                "name": name,
                "description": meta.description,
                "category": meta.tags[0] if meta.tags else "general",
                "categories": meta.tags,
                "source": "local",
                "requires_approval": meta.requires_approval,
                "timeout_seconds": meta.timeout_seconds,
                "is_active": True,
            })

    # MCP servers
    if source in (None, "mcp"):
        try:
            mcp_tools = _fetch_mcp_tools(org_id)
            tools.extend(mcp_tools)
        except Exception:
            logger.exception("Failed to fetch MCP tools")

    return tools


def _fetch_mcp_tools(org_id: str) -> list[dict]:
    """Fetch MCP server tools using async pool."""
    db = get_service_client()
    result = (
        db.table("org_mcp_servers")
        .select("name")
        .eq("org_id", org_id)
        .eq("is_active", True)
        .execute()
    )
    servers = result.data or []

    async def _fetch(server_name: str) -> list[dict]:
        from src.tools.mcp_pool import MCPConnectionError, MCPPool

        try:
            pool = MCPPool.get()
            mcp_tools = await pool.get_tools(org_id, server_name, timeout=5)
            return [
                {
                    "name": f"mcp:{server_name}:{getattr(t, 'name', str(t))}",
                    "description": getattr(t, "description", ""),
                    "category": server_name,
                    "categories": ["mcp", server_name],
                    "source": "mcp",
                    "requires_approval": False,
                    "timeout_seconds": 30,
                    "is_active": True,
                }
                for t in mcp_tools
            ]
        except MCPConnectionError:
            logger.warning("MCP server '%s' unreachable — skipping", server_name)
            return []
        except Exception:
            logger.exception("MCP server '%s' error — skipping", server_name)
            return []

    async def _fetch_all():
        return await asyncio.gather(
            *[_fetch(s["name"]) for s in servers],
            return_exceptions=True,
        )

    results = asyncio.run(_fetch_all())

    tools: list[dict] = []
    for r in results:
        if isinstance(r, Exception):
            logger.warning("MCP fetch exception: %s", r)
        else:
            tools.extend(r)
    return tools


def _print_table(tools: list[dict]) -> None:
    """Print tools as a rich table."""
    table = Table(title="Available Tools")
    table.add_column("Name", style="cyan")
    table.add_column("Source", style="magenta")
    table.add_column("Category", style="green")
    table.add_column("Description")

    for t in tools:
        table.add_row(
            t["name"],
            t["source"],
            t.get("category", ""),
            t.get("description", ""),
        )

    console.print(table)
