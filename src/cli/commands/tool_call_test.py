"""src/cli/commands/tool_call_test.py — 'fap test-tool-call' command.

DX Tooling: Verify an agent calls a specific tool during real execution.
Supports dry-run mode (config check without LLM) and full LLM execution.

Patron: src/cli/commands/check_env.py
"""

from __future__ import annotations

import json as json_mod
import logging
from uuid import uuid4

import typer
from rich.console import Console
from rich.table import Table

from src.tools.registry import tool_registry

console = Console()
logger = logging.getLogger(__name__)


def test_tool_call(
    agent_role: str = typer.Option(
        "presupuestador",
        "--agent",
        help="Agent role from agent_catalog",
    ),
    tool_name: str = typer.Option(
        "excel_reader",
        "--tool",
        help="Tool name to verify",
    ),
    file: str = typer.Option(
        "precios_bebidas.xlsx",
        "--file",
        help="Excel file to read",
    ),
    task: str = typer.Option(
        "Calcula el costo de 100 cocteles usando el archivo precios_bebidas.xlsx",
        "--task",
        help="Task description for the agent",
    ),
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        help="Only verify config without executing LLM",
    ),
    json_output: bool = typer.Option(
        False,
        "--json",
        help="Output in machine-readable JSON format",
    ),
    force_llm: bool = typer.Option(
        False,
        "--llm",
        help="Force use of real LLM (Groq)",
    ),
) -> None:
    """Verify an agent can call a specific tool during execution.

    Checks tool registration, agent config, and optionally runs the agent
    with a real LLM to verify tool calling works end-to-end.
    """
    results: dict[str, str | bool | list[str]] = {
        "tool_registered": False,
        "tool_name": tool_name,
        "agent_role": agent_role,
    }

    console.print(
        f"\n[bold cyan]fap test-tool-call --agent {agent_role} --tool {tool_name} --file {file}[/bold cyan]"
    )
    console.print("[dim]Verificando tool calling...[/dim]\n")

    is_groq_available = False
    try:
        from src.config import get_settings

        s = get_settings()
        is_groq_available = bool(s.groq_api_key)
    except Exception:
        pass

    try:
        tool_registry.get(tool_name)
        results["tool_registered"] = True
        console.print(f"[green]OK[/green] Tool '{tool_name}' registrada en tool_registry")
    except ValueError:
        results["tool_registered"] = False
        console.print(f"[red]ERROR:[/red] Tool '{tool_name}' no encontrada en tool_registry")
        if not dry_run:
            raise typer.Exit(code=1)

    if not is_groq_available and not dry_run and not force_llm:
        console.print("[yellow]WARNING:[/yellow] GROQ_API_KEY no configurada. Usar --dry-run o --llm para forzar")
        if not json_output:
            console.print("[dim]Ejecutando solo verificacion de config (dry-run mode)[/dim]")

    if dry_run or (not is_groq_available and not force_llm):
        table = Table(title="Tool Call Test (Dry Run)")
        table.add_column("Check", style="cyan")
        table.add_column("Resultado", style="green")

        table.add_row(
            f"Tool '{tool_name}' registrada",
            "[green]OK[/green]" if results["tool_registered"] else "[red]FAIL[/red]",
        )
        table.add_row("GROQ_API_KEY presente", "[green]OK[/green]" if is_groq_available else "[yellow]NO[/yellow]")
        table.add_row("Agent role", agent_role)

        console.print(table)

        if json_output:
            results["dry_run"] = True
            results["groq_available"] = is_groq_available
            console.print(json_mod.dumps(results, indent=2))

        if not results["tool_registered"]:
            raise typer.Exit(code=1)
        raise typer.Exit(code=0)

    if not is_groq_available and force_llm:
        console.print("[red]ERROR:[/red] GROQ_API_KEY no configurada. No se puede forzar LLM real")
        raise typer.Exit(code=1)

    from src.crews.base_crew import BaseCrew

    org_id = str(uuid4())
    crew = BaseCrew(org_id=org_id, role=agent_role)

    import asyncio

    try:
        result = asyncio.run(
            crew.run_async(
                task_description=task,
                inputs={},
                expected_output="JSON with calculation based on tool data",
            )
        )
    except Exception as e:
        console.print(f"[red]ERROR durante ejecucion:[/red] {e}")
        raise typer.Exit(code=1)

    raw = str(result)
    console.print(f"\n[bold]Resultado del agente:[/bold]\n{raw[:500]}")

    tool_calls = crew.get_last_tool_calls()
    calls_made = tool_calls.get(tool_name, 0)
    results["tool_calls"] = calls_made

    console.print(f"\n[bold]Tool calls:[/bold] {tool_name} fue llamada {calls_made} vez/veces")

    table = Table(title="Tool Call Test Result")
    table.add_column("Metrica", style="cyan")
    table.add_column("Valor", style="green")

    table.add_row("Tool calls", str(calls_made))
    table.add_row("Ejecucion", "[green]OK[/green]")
    console.print(table)

    if json_output:
        results["execution_success"] = True
        results["raw_output_preview"] = raw[:200]
        console.print(json_mod.dumps(results, indent=2))

    if calls_made == 0:
        console.print(
            "[yellow]WARNING:[/yellow] El LLM no llamo la tool. "
            "Verificar soul_json backstory y tool description."
        )
        raise typer.Exit(code=1)

    raise typer.Exit(code=0)
