"""src/cli/commands/crew.py — `fap crew` CLI for crew canvas management.

Tarea 0 DX & Tooling — Paso 07.
Subcomandos: save, load, export, validate, scaffold.
"""
from __future__ import annotations

import asyncio
import json
import logging
from pathlib import Path
from typing import Optional

import httpx
import typer
from rich.console import Console
from rich.table import Table

from src.cli.config import CLIConfig
from src.db.session import get_service_client
from src.services.bundle_schemas import AgentExportItem, ExportBundleRequest
from src.services.export_service import ExportService

logger = logging.getLogger(__name__)
console = Console()

crew_app = typer.Typer(
    help="Crew canvas management: save, load, export, validate, scaffold.",
    no_args_is_help=True,
)

PRESET_NODES: dict[str, list[dict]] = {
    "research-pipeline": [
        {"id": "r1", "type": "agentNode", "data": {"role": "researcher", "goal": "Research a given topic thoroughly", "tools": ["web_search"]}, "position": {"x": 100, "y": 100}},
        {"id": "t1", "type": "taskNode", "data": {"description": "Search and gather information", "expectedOutput": "Research summary", "assignedAgent": "researcher"}, "position": {"x": 400, "y": 100}},
    ],
    "code-review-crew": [
        {"id": "cr1", "type": "agentNode", "data": {"role": "code_reviewer", "goal": "Review code for bugs and best practices", "tools": ["code_analysis"]}, "position": {"x": 100, "y": 100}},
        {"id": "ct1", "type": "taskNode", "data": {"description": "Analyze code quality", "expectedOutput": "Code review report", "assignedAgent": "code_reviewer"}, "position": {"x": 400, "y": 100}},
    ],
    "content-creation": [
        {"id": "w1", "type": "agentNode", "data": {"role": "writer", "goal": "Write engaging content", "tools": ["web_search"]}, "position": {"x": 100, "y": 100}},
        {"id": "e1", "type": "agentNode", "data": {"role": "editor", "goal": "Edit and polish content", "tools": []}, "position": {"x": 100, "y": 250}},
        {"id": "ct1", "type": "taskNode", "data": {"description": "Draft article", "expectedOutput": "First draft", "assignedAgent": "writer"}, "position": {"x": 400, "y": 100}},
        {"id": "ct2", "type": "taskNode", "data": {"description": "Review and edit", "expectedOutput": "Final article", "assignedAgent": "editor"}, "position": {"x": 400, "y": 250}},
    ],
    "data-analysis": [
        {"id": "a1", "type": "agentNode", "data": {"role": "analyst", "goal": "Analyze data and extract insights", "tools": ["python_repl"]}, "position": {"x": 100, "y": 100}},
        {"id": "dt1", "type": "taskNode", "data": {"description": "Parse and clean dataset", "expectedOutput": "Clean data", "assignedAgent": "analyst"}, "position": {"x": 400, "y": 100}},
        {"id": "dt2", "type": "taskNode", "data": {"description": "Generate visualization report", "expectedOutput": "Charts and insights", "assignedAgent": "analyst"}, "position": {"x": 400, "y": 250}},
    ],
}

PRESET_EDGES: dict[str, list[dict]] = {
    "research-pipeline": [
        {"id": "e-r1-t1", "source": "r1", "target": "t1", "sourceHandle": "bottom", "targetHandle": "left"},
    ],
    "code-review-crew": [
        {"id": "e-cr1-ct1", "source": "cr1", "target": "ct1", "sourceHandle": "bottom", "targetHandle": "left"},
    ],
    "content-creation": [
        {"id": "e-w1-ct1", "source": "w1", "target": "ct1", "sourceHandle": "bottom", "targetHandle": "left"},
        {"id": "e-e1-ct2", "source": "e1", "target": "ct2", "sourceHandle": "bottom", "targetHandle": "left"},
    ],
    "data-analysis": [
        {"id": "e-a1-dt1", "source": "a1", "target": "dt1", "sourceHandle": "bottom", "targetHandle": "left"},
        {"id": "e-a1-dt2", "source": "a1", "target": "dt2", "sourceHandle": "bottom", "targetHandle": "left"},
    ],
}

PRESET_METADATA: dict[str, dict[str, str]] = {
    "research-pipeline": {"name": "Research Pipeline", "description": "Researcher -> Search -> Writer"},
    "code-review-crew": {"name": "Code Review Crew", "description": "Reviewer -> Analyze -> Report"},
    "content-creation": {"name": "Content Creation", "description": "Writer -> SEO -> Editor"},
    "data-analysis": {"name": "Data Analysis", "description": "Analyst -> Parse -> Visualize"},
}


def _validate_crew_graph(data: dict) -> tuple[list[str], list[str]]:
    """Validate a crew graph JSON structure.

    Returns (errors, warnings).
    """
    errors: list[str] = []
    warnings: list[str] = []

    if not isinstance(data, dict):
        errors.append("Root must be a JSON object")
        return errors, warnings

    nodes = data.get("nodes", [])
    edges = data.get("edges", [])

    if not isinstance(nodes, list):
        errors.append("'nodes' must be an array")
    if not isinstance(edges, list):
        errors.append("'edges' must be an array")

    if errors:
        return errors, warnings

    roles_seen: set[str] = set()
    agent_nodes = [n for n in nodes if n.get("type") == "agentNode"]
    task_nodes = [n for n in nodes if n.get("type") == "taskNode"]
    node_ids = {n.get("id") for n in nodes}

    for node in agent_nodes:
        role = (node.get("data") or {}).get("role")
        if not role:
            errors.append(f"AgentNode '{node.get('id')}' missing role")
            continue
        if role in roles_seen:
            errors.append(f"Duplicate role '{role}' detected")
        roles_seen.add(role)
        has_edge = any(e.get("source") == node.get("id") for e in edges)
        if not has_edge:
            warnings.append(f"Agent '{role}' has no assigned tasks")

    for node in task_nodes:
        desc = (node.get("data") or {}).get("description")
        if not desc:
            warnings.append(f"TaskNode '{node.get('id')}' has no description")

    for edge in edges:
        source = edge.get("source")
        target = edge.get("target")
        if source not in node_ids:
            errors.append(f"Edge '{edge.get('id')}' references unknown source '{source}'")
        if target not in node_ids:
            errors.append(f"Edge '{edge.get('id')}' references unknown target '{target}'")

    visited: set[str] = set()
    cycle_stack: set[str] = set()

    def dfs(node_id: str) -> bool:
        if node_id in cycle_stack:
            return True
        if node_id in visited:
            return False
        visited.add(node_id)
        cycle_stack.add(node_id)
        for e in edges:
            if e.get("source") == node_id:
                target = e.get("target")
                if target and dfs(target):
                    return True
        cycle_stack.discard(node_id)
        return False

    for nid in node_ids:
        if nid not in visited and dfs(nid):
            errors.append("Cycle detected in crew graph")
            break

    return errors, warnings


async def _save_crew_async(
    name: str,
    org_id: str,
    base_url: str,
    headers: dict[str, str],
    output: Path,
) -> None:
    url = f"{base_url.rstrip('/')}/agents?active_only=true"

    async with httpx.AsyncClient(timeout=15) as client:
        response = await client.get(url, headers=headers)

    if response.status_code != 200:
        console.print(f"[red]Error {response.status_code}:[/red] {response.text}")
        raise typer.Exit(code=1)

    data = response.json()
    agents_list = data.get("agents", [])

    nodes = []
    for i, agent in enumerate(agents_list):
        role = agent.get("role", f"agent_{i}")
        goal = (agent.get("soul_json") or {}).get("goal", "")
        tools = agent.get("allowed_tools", [])
        node_id = f"agent_{i}"
        nodes.append({
            "id": node_id,
            "type": "agentNode",
            "data": {"role": role, "goal": goal, "tools": tools},
            "position": {"x": 100, "y": 100 + i * 120},
        })

    snapshot = {
        "name": name,
        "org_id": org_id,
        "nodes": nodes,
        "edges": [],
        "metadata": {"name": name, "createdAt": ""},
    }

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(snapshot, indent=2))

    console.print(f"[bold green]OK[/bold green] Saved crew '{name}' with {len(nodes)} agent(s) to [bold]{output}[/bold]")


@crew_app.command("save")
def save_crew(
    name: str = typer.Option(..., "--name", "-n", help="Crew snapshot name"),
    org_id: Optional[str] = typer.Option(None, "--org-id", "-o", help="Organization UUID"),
    output: Path = typer.Option(Path("crew.json"), "--output", help="Output JSON file path"),
) -> None:
    """Save a crew canvas snapshot to a JSON file."""
    config = CLIConfig.load()
    if org_id is None:
        org_id = config.org_id
    if not org_id:
        console.print("[red]Error:[/red] --org-id required. Set FAP_ORG_ID in .env or pass --org-id.")
        raise typer.Exit(code=1)

    base_url = config.api_url or "http://localhost:8000"
    headers: dict[str, str] = {"X-Org-ID": org_id, "Content-Type": "application/json"}
    if config.access_token:
        headers["Authorization"] = f"Bearer {config.access_token}"

    try:
        asyncio.run(_save_crew_async(name, org_id, base_url, headers, output))
    except httpx.ConnectError:
        console.print("[red]Error:[/red] Cannot connect to API. Is the backend running?")
        raise typer.Exit(code=1)
    except typer.Exit:
        raise
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(code=1)


@crew_app.command("load")
def load_crew(
    file: Path = typer.Option(..., "--file", "-f", help="Crew JSON file to load"),
    org_id: Optional[str] = typer.Option(None, "--org-id", "-o", help="Organization UUID"),
) -> None:
    """Load a crew snapshot from JSON and display its contents."""
    config = CLIConfig.load()
    if org_id is None:
        org_id = config.org_id
    if not org_id:
        console.print("[red]Error:[/red] --org-id required. Set FAP_ORG_ID in .env or pass --org-id.")
        raise typer.Exit(code=1)

    if not file.exists():
        console.print(f"[red]Error:[/red] File not found: {file}")
        raise typer.Exit(code=1)

    try:
        data = json.loads(file.read_text())
    except json.JSONDecodeError as e:
        console.print(f"[red]Error:[/red] Invalid JSON: {e}")
        raise typer.Exit(code=1)

    name = data.get("name", file.stem)
    nodes = data.get("nodes", [])
    edges = data.get("edges", [])

    table = Table(title=f"Crew: {name}")
    table.add_column("Type", style="cyan")
    table.add_column("ID", style="dim")
    table.add_column("Details", style="green")

    for node in nodes:
        ntype = node.get("type", "unknown")
        ndata = node.get("data") or {}
        if ntype == "agentNode":
            table.add_row("Agent", node.get("id", ""), ndata.get("role", ""))
        elif ntype == "taskNode":
            table.add_row("Task", node.get("id", ""), ndata.get("description", ""))
        else:
            table.add_row("Node", node.get("id", ""), str(ndata))

    console.print(table)

    if edges:
        console.print(f"\n[dim]{len(edges)} connection(s)[/dim]")
        for edge in edges:
            console.print(f"  [dim]{edge.get('source')} -> {edge.get('target')}[/dim]")
    else:
        console.print("\n[dim]No connections[/dim]")


@crew_app.command("export")
def export_crew(
    name: str = typer.Option(..., "--name", "-n", help="Crew name for the ZIP file"),
    roles: str = typer.Option(..., "--roles", "-r", help="Comma-separated agent roles to export"),
    org_id: Optional[str] = typer.Option(None, "--org-id", "-o", help="Organization UUID"),
    output: Path = typer.Option(Path("crew.zip"), "--output", help="Output ZIP file path"),
) -> None:
    """Export crew agents as a bundle ZIP (without opening dashboard)."""
    config = CLIConfig.load()
    if org_id is None:
        org_id = config.org_id
    if not org_id:
        console.print("[red]Error:[/red] --org-id required. Set FAP_ORG_ID in .env or pass --org-id.")
        raise typer.Exit(code=1)

    role_list = [r.strip() for r in roles.split(",") if r.strip()]
    if not role_list:
        console.print("[red]Error:[/red] --roles must be a comma-separated list of agent roles.")
        raise typer.Exit(code=1)

    try:
        svc = get_service_client()
        result = (
            svc.table("agent_catalog")
            .select("*")
            .eq("org_id", org_id)
            .eq("is_active", True)
            .execute()
        )

        agents_data = result.data or []
        agents_data = [a for a in agents_data if a.get("role") in role_list]

        if not agents_data:
            found_roles = {a.get("role") for a in (result.data or [])}
            missing = set(role_list) - found_roles
            console.print(f"[yellow]! No matching agents found. Missing roles: {missing}[/yellow]")
            raise typer.Exit(code=0)

        agent_items = []
        for a in agents_data:
            agent_items.append(
                AgentExportItem(
                    role=a.get("role", "unknown"),
                    soul_json=a.get("soul_json", {}),
                    allowed_tools=a.get("allowed_tools", []),
                    max_iter=a.get("max_iter", 5),
                )
            )

        payload = ExportBundleRequest(
            bundle_name=name,
            agents=agent_items,
        )

        service = ExportService(org_id=org_id)
        zip_bytes, _filename = service.export(payload)

        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_bytes(zip_bytes)

        console.print(
            f"\n[bold green]OK[/bold green] Exported {len(agent_items)} agent(s)"
            f" to [bold]{output}[/bold] ({len(zip_bytes)} bytes)"
        )
        console.print("[yellow]Note:[/yellow] Tasks and connections not exported (bundle-schema-v2.md limitation).")

    except Exception as e:
        logger.exception("Crew export failed for org %s", org_id)
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(code=1)


@crew_app.command("validate")
def validate_crew(
    file: Path = typer.Option(..., "--file", "-f", help="Crew JSON file to validate"),
) -> None:
    """Validate a crew graph JSON for structure issues."""
    if not file.exists():
        console.print(f"[red]Error:[/red] File not found: {file}")
        raise typer.Exit(code=1)

    try:
        data = json.loads(file.read_text())
    except json.JSONDecodeError as e:
        console.print(f"[red]Error:[/red] Invalid JSON: {e}")
        raise typer.Exit(code=1)

    errors, warnings = _validate_crew_graph(data)

    if errors:
        console.print(f"\n[bold red]Validation FAILED[/bold red] — {len(errors)} error(s):")
        for err in errors:
            console.print(f"  [red]x[/red] {err}")
    else:
        console.print("\n[bold green]Validation PASSED[/bold green]")

    if warnings:
        console.print(f"\n[bold yellow]{len(warnings)} warning(s):[/bold yellow]")
        for w in warnings:
            console.print(f"  [yellow]![/yellow] {w}")

    if errors:
        raise typer.Exit(code=1)
    elif warnings:
        console.print("\n[dim]Warnings are non-blocking. Review them before export.[/dim]")


@crew_app.command("scaffold")
def scaffold_crew(
    preset: str = typer.Option(..., "--preset", "-p", help="Template preset name"),
    org_id: Optional[str] = typer.Option(None, "--org-id", "-o", help="Organization UUID"),
    output: Path = typer.Option(Path("crew.json"), "--output", help="Output JSON file path"),
) -> None:
    """Scaffold a crew canvas from a preset template."""
    config = CLIConfig.load()
    if org_id is None:
        org_id = config.org_id
    if not org_id:
        console.print("[red]Error:[/red] --org-id required. Set FAP_ORG_ID in .env or pass --org-id.")
        raise typer.Exit(code=1)

    if preset not in PRESET_NODES:
        available = ", ".join(sorted(PRESET_NODES.keys()))
        console.print(f"[red]Error:[/red] Unknown preset '{preset}'. Available: {available}")
        raise typer.Exit(code=1)

    meta = PRESET_METADATA.get(preset, {"name": preset, "description": ""})
    nodes = PRESET_NODES[preset]
    edges = PRESET_EDGES.get(preset, [])

    import datetime
    snapshot = {
        "name": preset,
        "org_id": org_id,
        "nodes": nodes,
        "edges": edges,
        "metadata": {
            "name": meta["name"],
            "description": meta["description"],
            "createdAt": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        },
    }

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(snapshot, indent=2))

    console.print(
        f"\n[bold green]OK[/bold green] Scaffolded crew '[bold]{preset}[/bold]'"
        f" ({meta['name']}) with {len(nodes)} node(s) + {len(edges)} edge(s)"
        f"\n         Output: [bold]{output}[/bold]"
    )
