"""src/cli/commands/bundle_validate_payload.py — `fap bundle validate-payload` CLI.

Valida un payload JSON contra el schema ExportBundleRequest sin ejecutar el endpoint.
Muestra summary (agentes, skills, tamaño estimado) y errores de validación.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Annotated, Optional

import typer
from pydantic import ValidationError
from rich.console import Console
from rich.table import Table

from src.services.bundle_schemas import ExportBundleRequest

console = Console()


def validate_payload(
    file: Annotated[Optional[Path], typer.Option("--file", help="JSON payload file")] = None,
    stdin: Annotated[bool, typer.Option("--stdin", help="Read from stdin")] = False,
    json_output: Annotated[bool, typer.Option("--json", help="JSON output")] = False,
) -> None:
    """Validate a JSON export payload against ExportBundleRequest schema."""
    if file is None and not stdin:
        console.print("[red]Error:[/red] Provide --file or --stdin")
        raise typer.Exit(code=1)

    if file is not None and stdin:
        console.print("[red]Error:[/red] Use --file OR --stdin, not both")
        raise typer.Exit(code=1)

    try:
        if stdin:
            raw = sys.stdin.read()
        else:
            raw = file.read_text(encoding="utf-8")
    except Exception as e:
        console.print(f"[red]Error reading input:[/red] {e}")
        raise typer.Exit(code=1)

    try:
        data = json.loads(raw)
    except json.JSONDecodeError as e:
        console.print(f"[red]Invalid JSON:[/red] {e}")
        raise typer.Exit(code=1)

    errors: list[str] = []
    warnings: list[str] = []

    try:
        payload = ExportBundleRequest(**data)
    except ValidationError as e:
        for err in e.errors():
            loc = " -> ".join(str(x) for x in err["loc"])
            errors.append(f"[bold]{loc}[/bold]: {err['msg']}")
        if json_output:
            console.print_json(json.dumps({"valid": False, "errors": errors, "warnings": warnings}))
        else:
            console.print(f"\n[red]Schema validation FAILED — {len(errors)} error(s)[/red]\n")
            table = Table(title="Validation Errors", show_lines=True)
            table.add_column("#", justify="right", style="dim")
            table.add_column("Field", style="red")
            table.add_column("Error")
            for i, err_msg in enumerate(errors, 1):
                table.add_row(str(i), "", err_msg)
            console.print(table)
        raise typer.Exit(code=1)

    agent_count = len(payload.agents)
    skill_count = len(payload.skills) if payload.skills else 0
    bundle_name = payload.bundle_name or "(default)"

    agent_goals_ok = 0
    agent_backstories_ok = 0
    for agent in payload.agents:
        goal = agent.soul_json.get("goal", "")
        backstory = agent.soul_json.get("backstory", "")
        if isinstance(goal, str) and len(goal) >= 10:
            agent_goals_ok += 1
        else:
            warnings.append(f"Agent [bold]{agent.role}[/bold]: goal < 10 chars or missing")
        if isinstance(backstory, str) and len(backstory) >= 10:
            agent_backstories_ok += 1
        else:
            warnings.append(f"Agent [bold]{agent.role}[/bold]: backstory < 10 chars or missing")

    est_size = (
        len(raw)
        + (agent_count * 200)
        + (skill_count * 1000)
    )

    if agent_count > 10:
        warnings.append(f"Agent count {agent_count} is close to max limit (15)")

    if json_output:
        result = {
            "valid": True,
            "bundle_name": bundle_name,
            "agents": agent_count,
            "agents_goal_ok": agent_goals_ok,
            "agents_backstory_ok": agent_backstories_ok,
            "skills": skill_count,
            "estimated_size_bytes": est_size,
            "warnings": warnings,
            "errors": [],
        }
        console.print_json(json.dumps(result))
    else:
        console.print("\n[bold green]Schema valid[/bold green]")
        console.print(f"  Bundle name: [bold]{bundle_name}[/bold]")
        console.print(f"  Agents: [bold]{agent_count}[/bold]")
        console.print(f"  Skills: [bold]{skill_count}[/bold]")
        console.print(f"  Estimated ZIP size: [bold]{est_size:,}[/bold] bytes")

        table = Table(title="Agent Details", show_lines=False)
        table.add_column("Role", style="cyan")
        table.add_column("Goal OK", justify="center")
        table.add_column("Backstory OK", justify="center")
        table.add_column("Tools", justify="right")
        table.add_column("Max Iter", justify="right")

        for agent in payload.agents:
            goal = agent.soul_json.get("goal", "")
            backstory = agent.soul_json.get("backstory", "")

            table.add_row(
                agent.role,
                "[green]✓[/green]" if (isinstance(goal, str) and len(goal) >= 10) else "[red]✗[/red]",
                "[green]✓[/green]" if (isinstance(backstory, str) and len(backstory) >= 10) else "[red]✗[/red]",
                str(len(agent.allowed_tools)),
                str(agent.max_iter),
            )

        console.print(table)

        if warnings:
            console.print(f"\n[yellow]Warnings ({len(warnings)}):[/yellow]")
            for w in warnings:
                console.print(f"  [yellow]![/yellow] {w}")

    if errors:
        raise typer.Exit(code=1)
