"""src/cli/commands/validate_architect.py — Implementation of 'fap validate-architect-output' command."""

import json
from pathlib import Path
from typing import Optional

import typer
from rich import print
from rich.console import Console
from rich.table import Table

from src.db.session import get_service_client
from src.flows.workflow_definition import WorkflowDefinition

console = Console()


def _load_json(path: Path) -> Optional[dict]:
    """Load JSON from file path."""
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        print(f"[red]Error:[/red] JSON inválido en '{path}': {e}")
        return None
    except Exception as e:
        print(f"[red]Error:[/red] No se pudo leer '{path}': {e}")
        return None


def _validate_structural(data: dict) -> list[str]:
    """Validate structural schema with WorkflowDefinition."""
    errors = []
    try:
        WorkflowDefinition(**data)
    except Exception as e:
        errors.append(f"Schema inválido: {e}")
    return errors


def _validate_mcp_tools(data: dict, org_id: str) -> list[str]:
    """Validate MCP tool references against org_mcp_servers."""
    errors = []
    mcp_tools = [
        tool
        for agent in data.get("agents", [])
        for tool in agent.get("allowed_tools", [])
        if tool.startswith("mcp:")
    ]

    if not mcp_tools:
        return errors

    # SUPUESTO: El formato es mcp:server_name:tool_name
    servers: dict[str, set[str]] = {}
    for tool in mcp_tools:
        parts = tool.split(":")
        if len(parts) < 3:
            errors.append(f"MCP tool '{tool}' formato inválido (esperado mcp:server:tool)")
            continue
        server_name = parts[1]
        if server_name not in servers:
            servers[server_name] = set()
        servers[server_name].add(parts[2])

    if not org_id or org_id == "cli-validation":
        for server_name in servers:
            errors.append(
                f"[yellow]WARN: MCP server '{server_name}': No se puede validar sin --org-id[/yellow]"
            )
        return errors

    svc = get_service_client()
    for server_name in servers:
        config = (
            svc.table("org_mcp_servers")
            .select("id, name, is_active")
            .eq("org_id", org_id)
            .eq("name", server_name)
            .eq("is_active", True)
            .maybe_single()
            .execute()
        )
        if not config.data:
            errors.append(
                f"[red]✗ MCP server '{server_name}' no configurado o inactivo para org '{org_id}'[/red]"
            )
        else:
            print(f"[green]✓ MCP server '{server_name}' verificado[/green]")

    return errors


def _validate_service_connectors(data: dict, org_id: str) -> list[str]:
    """Validate service_connector references against service_tools."""
    errors = []
    has_sc = False
    for agent in data.get("agents", []):
        if "service_connector" in agent.get("allowed_tools", []):
            has_sc = True
            break

    if not has_sc:
        return errors

    if not org_id or org_id == "cli-validation":
        errors.append(
            "[yellow]WARN: service_connector referenciado: No se puede validar sin --org-id[/yellow]"
        )
        return errors

    svc = get_service_client()
    active_integrations = (
        svc.table("org_service_integrations")
        .select("service_id, status")
        .eq("org_id", org_id)
        .eq("status", "active")
        .execute()
    )
    if not active_integrations.data:
        errors.append(
            "[red]✗ No hay integraciones activas para esta org (service_connector no podrá ejecutarse)[/red]"
        )
    else:
        active_service_ids = {r["service_id"] for r in active_integrations.data}
        tools_with_config = (
            svc.table("service_tools")
            .select("id, name, service_id")
            .in_("service_id", list(active_service_ids))
            .execute()
        )
        if tools_with_config.data:
            print(f"[green]✓ {len(tools_with_config.data)} service_tools disponibles para org[/green]")
        else:
            errors.append(
                "[yellow]WARN: service_connector referenciado pero no hay service_tools activas[/yellow]"
            )

    return errors


def _validate_tools_registry(data: dict) -> list[str]:
    """Validate regular tools against tool registry."""
    errors = []
    from src.tools.registry import TOOL_REGISTRY

    regular_tools = [
        tool
        for agent in data.get("agents", [])
        for tool in agent.get("allowed_tools", [])
        if not tool.startswith("mcp:") and tool != "service_connector"
    ]

    if not regular_tools:
        return errors

    registered_tools = set(TOOL_REGISTRY.keys())
    for tool in regular_tools:
        if tool not in registered_tools:
            errors.append(f"[yellow]WARN: Tool '{tool}' no está en TOOL_REGISTRY (puede no estar registrada aún)[/yellow]")
        else:
            print(f"[green]✓ Tool '{tool}' encontrada en registry[/green]")

    return errors


def validate_architect_data(data: dict, org_id: str = "", strict: bool = False) -> dict:
    """Validate architect JSON data against schemas and registries.

    Args:
        data: Parsed JSON dict with workflow definition.
        org_id: Organization UUID for DB-dependent checks. Empty = skip DB.
        strict: If True, DB resource errors are hard errors (for strict CLI validation).
                If False, DB resource errors are downgraded to warnings (for test-scenarios).

    Returns:
        dict with keys: valid (bool), errors (list[str]), warnings (list[str])
    """
    all_errors: list[str] = []
    all_warnings: list[str] = []

    # 1. Structural validation
    struct_errors = _validate_structural(data)
    all_errors.extend(struct_errors)

    # 2. MCP tools validation
    if any(
        tool.startswith("mcp:")
        for agent in data.get("agents", [])
        for tool in agent.get("allowed_tools", [])
    ):
        try:
            mcp_errors = _validate_mcp_tools(data, org_id)
            for err in mcp_errors:
                if "WARN" in err or "\u26a0" in err:
                    all_warnings.append(err)
                elif not strict and "[red]" in err:
                    all_warnings.append(err)
                else:
                    all_errors.append(err)
        except Exception as e:
            all_warnings.append(f"MCP validation skipped: {e}")

    # 3. Service connector validation
    if any(
        "service_connector" in agent.get("allowed_tools", [])
        for agent in data.get("agents", [])
    ):
        try:
            sc_errors = _validate_service_connectors(data, org_id)
            for err in sc_errors:
                if "WARN" in err or "\u26a0" in err:
                    all_warnings.append(err)
                elif not strict and "[red]" in err:
                    all_warnings.append(err)
                else:
                    all_errors.append(err)
        except Exception as e:
            all_warnings.append(f"Service connector validation skipped: {e}")

    # 4. Registry validation
    try:
        tool_warnings = _validate_tools_registry(data)
        all_warnings.extend(tool_warnings)
    except Exception as e:
        all_warnings.append(f"Registry validation skipped: {e}")

    return {
        "valid": len(all_errors) == 0,
        "errors": all_errors,
        "warnings": all_warnings,
    }


def validate_architect_output(
    json_path: Path = typer.Argument(..., help="Path al archivo JSON generado por el Architect"),
    org_id: Optional[str] = typer.Option(None, "--org-id", "-o", help="UUID de la organización para validar MCP servers"),
):
    """Validar JSON generado por el Architect contra schemas y registries."""

    if not json_path.exists():
        print(f"[red]Error:[/red] Archivo no encontrado: {json_path}")
        raise typer.Exit(code=1)

    data = _load_json(json_path)
    if not data:
        raise typer.Exit(code=1)

    all_errors: list[str] = []
    all_warnings: list[str] = []

    # 1. Validación estructural
    print("\n[cyan]Validando schema estructural...[/cyan]")
    struct_errors = _validate_structural(data)
    if struct_errors:
        all_errors.extend(struct_errors)
    else:
        print("[green]✓ Schema estructural válido[/green]")

    # 2. Validación de MCP tools
    if any(
        tool.startswith("mcp:")
        for agent in data.get("agents", [])
        for tool in agent.get("allowed_tools", [])
    ):
        print("\n[cyan]Validando MCP tools...[/cyan]")
        mcp_errors = _validate_mcp_tools(data, org_id)
        for err in mcp_errors:
            if "WARN" in err or "\u26a0" in err:
                all_warnings.append(err)
            else:
                all_errors.append(err)
    else:
        print("(Sin MCP tools referenciadas)")

    # 3. Validación de service_connector
    if any(
        "service_connector" in agent.get("allowed_tools", [])
        for agent in data.get("agents", [])
    ):
        print("\n[cyan]Validando service_connector...[/cyan]")
        sc_errors = _validate_service_connectors(data, org_id)
        for err in sc_errors:
            if "WARN" in err or "\u26a0" in err:
                all_warnings.append(err)
            else:
                all_errors.append(err)
    else:
        print("(Sin service_connector referenciado)")

    # 4. Validación de tools del registry
    print("\n[cyan]Validando tools del registry...[/cyan]")
    tool_warnings = _validate_tools_registry(data)
    all_warnings.extend(tool_warnings)
    if not tool_warnings:
        print("(Sin warnings de registry)")

    # Resumen
    print("\n" + "=" * 60)
    if all_errors:
        print("[bold red]VALIDACIÓN FALLIDA:[/bold red]")
        for err in all_errors:
            print(f"  {err}")
    else:
        print("[bold green]VALIDACIÓN EXITOSA:[/bold green] JSON válido")

    if all_warnings:
        print("\n[bold yellow]WARNINGS:[/bold yellow]")
        for warn in all_warnings:
            print(f"  {warn}")

    if all_errors:
        raise typer.Exit(code=1)

    # Mostrar resumen del workflow
    name = data.get("name", "Unknown")
    flow_type = data.get("flow_type", "Unknown")
    agents_count = len(data.get("agents", []))
    steps_count = len(data.get("steps", []))

    table = Table(title="Resumen del Workflow")
    table.add_column("Campo", style="cyan")
    table.add_column("Valor", style="green")
    table.add_row("Name", name)
    table.add_row("flow_type", flow_type)
    table.add_row("Agents", str(agents_count))
    table.add_row("Steps", str(steps_count))
    console.print(table)

    raise typer.Exit(code=0)
