"""src/cli/commands/agent_create.py — `fap agent create` CLI command.

Creates an agent via POST /agents with full soul_json payload.
Validates backend flow before UI construction (dogfooding).
"""

from __future__ import annotations

import json
import logging
from typing import Optional

import httpx
import typer
from rich.console import Console
from rich.table import Table

from src.cli.config import CLIConfig

logger = logging.getLogger(__name__)
console = Console()

agent_app = typer.Typer(
    help="Agent management: create, list, validate.",
    no_args_is_help=True,
)


@agent_app.command("create")
def create_agent(
    role: str = typer.Option(..., "--role", "-r", help="Agent role name"),
    goal: str = typer.Option(..., "--goal", "-g", help="Agent goal description"),
    backstory: str = typer.Option(..., "--backstory", "-b", help="Agent backstory"),
    org_id: Optional[str] = typer.Option(
        None, "--org-id", "-o", help="Organization UUID"
    ),
    tools: Optional[list[str]] = typer.Option(
        None, "--tools", "-t", help="Allowed tools (repeatable: --tools tool1 --tools tool2)"
    ),
    max_iter: int = typer.Option(3, "--max-iter", "-m", help="Max iterations (1-10)", min=1, max=10),
    llm_provider: str = typer.Option(
        "groq", "--llm-provider", "--provider", help="LLM provider"
    ),
    llm_model: str = typer.Option(
        "llama-3.1-70b-versatile", "--llm-model", "--model", help="LLM model"
    ),
    verbose: bool = typer.Option(False, "--verbose/--no-verbose", help="Verbose mode"),
    reasoning: bool = typer.Option(False, "--reasoning/--no-reasoning", help="Reasoning mode"),
    inject_date: bool = typer.Option(False, "--inject-date/--no-inject-date", help="Inject current date"),
    memory: bool = typer.Option(False, "--memory/--no-memory", help="Enable memory"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Print payload without inserting"),
) -> None:
    """Create an agent via POST /agents."""

    config = CLIConfig.load()
    if org_id is None:
        org_id = config.org_id

    if not org_id:
        console.print("[red]Error:[/red] --org-id required. Set FAP_ORG_ID in .env or pass --org-id.")
        raise typer.Exit(code=1)

    soul_json = {
        "goal": goal,
        "backstory": backstory,
        "llm_provider": llm_provider,
        "llm_model": llm_model,
        "verbose": verbose,
        "reasoning": reasoning,
        "inject_date": inject_date,
        "memory": memory,
    }

    allowed_tools = tools or []

    payload = {
        "role": role,
        "soul_json": soul_json,
        "allowed_tools": allowed_tools,
        "max_iter": max_iter,
    }

    if dry_run:
        console.print("[bold cyan]--dry-run mode: previewing payload[/bold cyan]\n")
        console.print_json(json.dumps(payload))
        console.print("\n[dim]Not sent (--dry-run).[/dim]")
        return

    base_url = config.api_url
    if not base_url:
        base_url = "http://localhost:8000"

    headers: dict[str, str] = {"X-Org-ID": org_id, "Content-Type": "application/json"}

    if config.access_token:
        headers["Authorization"] = f"Bearer {config.access_token}"

    url = f"{base_url.rstrip('/')}/agents"

    try:
        with httpx.Client(timeout=15) as client:
            response = client.post(url, json=payload, headers=headers)

        if response.status_code == 200 or response.status_code == 201:
            data = response.json()
            table = Table(title="Agent Created")
            table.add_column("Field", style="cyan")
            table.add_column("Value", style="green")
            table.add_row("ID", data.get("id", ""))
            table.add_row("Role", data.get("role", ""))
            table.add_row("Org", data.get("org_id", ""))
            table.add_row("Max Iter", str(data.get("max_iter", "")))
            table.add_row("Tools", ", ".join(data.get("allowed_tools", [])) or "(none)")
            console.print(table)
        elif response.status_code == 409:
            detail = response.json().get("detail", "Role already exists")
            console.print(f"[yellow]Conflict:[/yellow] {detail}")
        else:
            detail = response.json().get("detail", response.text) if response.text else "Unknown error"
            console.print(f"[red]Error {response.status_code}:[/red] {detail}")
            raise typer.Exit(code=1)
    except httpx.ConnectError:
        console.print("[red]Error:[/red] Cannot connect to API. Is the backend running?")
        raise typer.Exit(code=1)
