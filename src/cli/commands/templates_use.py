"""src/cli/commands/templates_use.py — `fap templates use` CLI command.

Creates an agent from a system template via POST /agents.
Dogfooding: validates template-to-agent mapping before UI construction.
"""

from __future__ import annotations

import json
import logging
import uuid as _uuid
from typing import Optional

import httpx
import typer
from rich.console import Console
from rich.table import Table

from src.cli.config import CLIConfig
from src.db.session import get_service_client

logger = logging.getLogger(__name__)
console = Console()


def _map_provider(provider: Optional[str]) -> str:
    valid = {"groq", "openai", "anthropic", "openrouter"}
    return provider if provider in valid else "groq"


def use_template(
    template_name: str = typer.Argument(..., help="Template name or UUID"),
    org_id: str = typer.Option(
        ..., "--org-id", "-o", help="Organization UUID"
    ),
    role: Optional[str] = typer.Option(
        None, "--role", "-r", help="Override template role"
    ),
    goal: Optional[str] = typer.Option(
        None, "--goal", "-g", help="Override template goal"
    ),
    backstory: Optional[str] = typer.Option(
        None, "--backstory", "-b", help="Override template backstory"
    ),
    tools: Optional[list[str]] = typer.Option(
        None, "--tools", "-t", help="Additional tools (repeatable)"
    ),
    max_iter: Optional[int] = typer.Option(
        None, "--max-iter", "-m", help="Override max iterations (1-10)"
    ),
    dry_run: bool = typer.Option(
        False, "--dry-run", help="Print payload without inserting"
    ),
) -> None:
    """Create an agent from a system template."""

    try:
        db = get_service_client()
    except Exception as e:
        console.print(
            f"[red]Error:[/red] Cannot connect to Supabase: {e}"
        )
        raise typer.Exit(code=1)

    is_uuid = False
    try:
        _uuid.UUID(template_name)
        is_uuid = True
    except (ValueError, AttributeError):
        is_uuid = False

    try:
        if is_uuid:
            result = (
                db.table("agent_templates")
                .select("*")
                .eq("id", template_name)
                .eq("is_system", True)
                .maybe_single()
                .execute()
            )
        else:
            result = (
                db.table("agent_templates")
                .select("*")
                .eq("name", template_name)
                .eq("is_system", True)
                .maybe_single()
                .execute()
            )
    except Exception as e:
        console.print(
            f"[red]Error:[/red] Query failed: {e}"
        )
        raise typer.Exit(code=1)

    if not result.data:
        console.print(
            f"[red]Error:[/red] Template [bold]'{template_name}'[/bold] not found."
        )
        raise typer.Exit(code=1)

    template = result.data
    soul = template.get("soul_json") or {}

    final_role = role or soul.get("role") or template.get("name", "")
    final_goal = goal or soul.get("goal") or ""
    final_backstory = (
        backstory or soul.get("backstory") or template.get("description") or ""
    )

    suggested_tools = list(template.get("suggested_tools") or [])
    if tools:
        for t in tools:
            if t not in suggested_tools:
                suggested_tools.append(t)

    final_max_iter = max_iter or template.get("max_iter") or 3

    soul_json = {
        "goal": final_goal,
        "backstory": final_backstory,
        "llm_provider": _map_provider(soul.get("llm_provider")),
        "llm_model": soul.get("llm_model") or "llama-3.1-70b-versatile",
        "verbose": bool(soul.get("verbose", False)),
        "reasoning": bool(soul.get("reasoning", False)),
        "inject_date": bool(soul.get("inject_date", False)),
        "memory": bool(soul.get("memory", False)),
    }

    payload = {
        "role": final_role,
        "soul_json": soul_json,
        "allowed_tools": suggested_tools,
        "max_iter": final_max_iter,
    }

    if dry_run:
        console.print(
            f"[bold cyan]--dry-run mode:[/bold cyan] "
            f"Creating agent from template [bold]'{template['name']}'[/bold]\n"
        )
        console.print_json(json.dumps(payload))
        console.print("\n[dim]Not sent (--dry-run).[/dim]")
        return

    config = CLIConfig.load()
    base_url = config.api_url
    if not base_url:
        base_url = "http://localhost:8000"

    headers: dict[str, str] = {
        "X-Org-ID": org_id,
        "Content-Type": "application/json",
    }
    if config.access_token:
        headers["Authorization"] = f"Bearer {config.access_token}"

    url = f"{base_url.rstrip('/')}/agents"

    try:
        with httpx.Client(timeout=15) as client:
            response = client.post(url, json=payload, headers=headers)

        if response.status_code in (200, 201):
            data = response.json()
            table = Table(title="Agent Created from Template")
            table.add_column("Field", style="cyan")
            table.add_column("Value", style="green")
            table.add_row("Template", template["name"])
            table.add_row("Agent ID", data.get("id", ""))
            table.add_row("Role", data.get("role", ""))
            table.add_row("Org", data.get("org_id", ""))
            table.add_row("Max Iter", str(data.get("max_iter", "")))
            table.add_row(
                "Tools", ", ".join(data.get("allowed_tools", [])) or "(none)"
            )
            console.print(table)
        elif response.status_code == 409:
            detail = response.json().get("detail", "Role already exists")
            console.print(f"[yellow]Conflict:[/yellow] {detail}")
        else:
            detail = (
                response.json().get("detail", response.text)
                if response.text
                else "Unknown error"
            )
            console.print(f"[red]Error {response.status_code}:[/red] {detail}")
            raise typer.Exit(code=1)
    except httpx.ConnectError:
        console.print(
            "[red]Error:[/red] Cannot connect to API. Is the backend running?"
        )
        raise typer.Exit(code=1)
