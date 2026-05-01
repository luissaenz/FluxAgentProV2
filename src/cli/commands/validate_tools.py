"""src/cli/commands/validate_tools.py — Implementation of 'fap validate-tools' command."""

import logging
from pathlib import Path
from typing import Optional

import typer
from rich import print

from src.cli.config import CLIConfig
from src.cli.utils import load_json

logger = logging.getLogger(__name__)

validate_tools_app = typer.Typer(
    help="Validate allowed_tools in bundles and agent configs.",
    no_args_is_help=True,
)


def _parse_mcp_prefix(tool_name: str) -> tuple[str, str] | None:
    """Parse mcp:server:tool format. Returns (server, tool_name) or None."""
    if not tool_name.startswith("mcp:"):
        return None
    parts = tool_name.split(":", 2)
    if len(parts) != 3 or not parts[1] or not parts[2]:
        return None
    return parts[1], parts[2]


def _validate_regular_tool(tool_name: str, org_id: str | None) -> tuple[bool, str]:
    """Validate a regular tool against the tool_registry."""
    from src.tools.registry import tool_registry

    try:
        tool_cls = tool_registry.get(tool_name, org_id=org_id)
        return True, f"Tool '{tool_name}' found: {tool_cls.__name__}"
    except ValueError as e:
        return False, f"Tool '{tool_name}' NOT found: {e}"


def _validate_mcp_tool(
    tool_name: str, org_id: str | None, server: str, mcp_tool_name: str
) -> tuple[bool, str]:
    """Validate an MCP tool by connecting to the server and checking tool existence."""
    if not org_id:
        return False, "org_id required for MCP tool validation"

    try:
        from src.db.session import get_service_client
    except ImportError:
        return False, "Database session not available"

    svc = get_service_client()
    config = (
        svc.table("org_mcp_servers")
        .select("*")
        .eq("org_id", org_id)
        .eq("name", server)
        .eq("is_active", True)
        .maybe_single()
        .execute()
    )

    if not config.data:
        return False, f"MCP server '{server}' not configured for org '{org_id}'"

    try:
        from crewai_tools import MCPServerAdapter
        from mcp import StdioServerParameters
    except ImportError:
        return False, "crewai-tools not installed. Run: pip install fluxagentpro-v2[crew]"

    env = {}
    if config.data.get("secret_name"):
        env["API_TOKEN"] = "SECRET_PLACEHOLDER"

    params = StdioServerParameters(
        command=config.data["command"],
        args=config.data.get("args", []),
        env=env or None,
    )

    try:
        adapter = MCPServerAdapter(params)
        with adapter:
            tools = adapter.tools
            for tool in tools:
                if hasattr(tool, "name") and tool.name == mcp_tool_name:
                    return True, f"MCP tool '{server}:{mcp_tool_name}' found"
            return False, f"MCP tool '{mcp_tool_name}' not found in server '{server}'"
    except Exception as e:
        return False, f"MCP server '{server}' connection failed: {e}"


def validate_tools_command(
    bundle_path: Optional[str] = typer.Option(
        None, "--bundle", "-b", help="Path to bundle manifest.json"
    ),
    agent_role: Optional[str] = typer.Option(
        None, "--agent-role", "-r", help="Agent role to validate in agent_catalog"
    ),
    org_id: Optional[str] = typer.Option(
        None, "--org-id", "-o", help="Organization ID for tool resolution"
    ),
    tool: Optional[str] = typer.Option(
        None, "--tool", "-t", help="Single tool string to validate"
    ),
) -> None:
    """Validate allowed_tools against tool_registry and org_mcp_servers."""
    config = CLIConfig.load()
    if org_id is None:
        org_id = config.org_id

    results: list[tuple[str, bool, str]] = []

    if tool:
        results.append(_validate_single_tool(tool, org_id))
    elif bundle_path:
        results.extend(_validate_bundle_tools(bundle_path, org_id))
    elif agent_role:
        results.extend(_validate_agent_tools(agent_role, org_id))
    else:
        print("[red]Error:[/red] Provide --bundle, --agent-role, or --tool")
        raise typer.Exit(code=1)

    _print_results(results)

    has_errors = any(not valid for _, valid, _ in results)
    if has_errors:
        raise typer.Exit(code=1)


def _validate_single_tool(tool_name: str, org_id: str | None) -> tuple[str, bool, str]:
    """Validate a single tool string."""
    mcp_parts = _parse_mcp_prefix(tool_name)
    if mcp_parts:
        server, mcp_tool_name = mcp_parts
        valid, msg = _validate_mcp_tool(tool_name, org_id, server, mcp_tool_name)
    else:
        valid, msg = _validate_regular_tool(tool_name, org_id)
    return tool_name, valid, msg


def _validate_bundle_tools(
    bundle_path: str, org_id: str | None
) -> list[tuple[str, bool, str]]:
    """Validate all allowed_tools from a bundle manifest."""
    manifest_file = Path(bundle_path)
    if manifest_file.is_dir():
        manifest_file = manifest_file / "manifest.json"

    if not manifest_file.exists():
        print(f"[red]Error:[/red] Manifest not found: {manifest_file}")
        raise typer.Exit(code=1)

    manifest = load_json(manifest_file)
    results: list[tuple[str, bool, str]] = []

    agents = manifest.get("agents", [])
    for agent in agents:
        allowed_tools = agent.get("allowed_tools", [])
        for tool_name in allowed_tools:
            results.append(_validate_single_tool(tool_name, org_id))

    if not results:
        print("[yellow]No allowed_tools found in bundle manifest[/yellow]")

    return results


def _validate_agent_tools(
    agent_role: str, org_id: str | None
) -> list[tuple[str, bool, str]]:
    """Validate allowed_tools for an agent role from agent_catalog."""
    if not org_id:
        print("[red]Error:[/red] --org-id required with --agent-role")
        raise typer.Exit(code=1)

    from src.db.session import get_service_client

    svc = get_service_client()
    result = (
        svc.table("agent_catalog")
        .select("role, allowed_tools")
        .eq("org_id", org_id)
        .eq("role", agent_role)
        .eq("is_active", True)
        .maybe_single()
        .execute()
    )

    if not result.data:
        print(f"[red]Error:[/red] No active agent with role '{agent_role}' for org '{org_id}'")
        raise typer.Exit(code=1)

    allowed_tools = result.data.get("allowed_tools", []) or []
    results: list[tuple[str, bool, str]] = []
    for tool_name in allowed_tools:
        results.append(_validate_single_tool(tool_name, org_id))

    return results


def _print_results(results: list[tuple[str, bool, str]]) -> None:
    """Print validation results in a formatted way."""
    print("\n[bold]Tool Validation Results:[/bold]\n")
    for tool_name, valid, msg in results:
        status = "[green]✓[/green]" if valid else "[red]✗[/red]"
        print(f"  {status} {tool_name}: {msg}")

    total = len(results)
    valid_count = sum(1 for _, v, _ in results if v)
    invalid_count = total - valid_count

    print(f"\n[bold]Summary:[/bold] {valid_count}/{total} tools valid")
    if invalid_count > 0:
        print(f"[bold red]{invalid_count} tool(s) invalid[/bold red]")
    else:
        print("[bold green]All tools valid![/bold green]")
