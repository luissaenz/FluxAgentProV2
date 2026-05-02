"""src/cli/commands/check_env.py — 'fap check-env' command.

DX Tooling: Verifica que variables de entorno requeridas esten presentes
antes de ejecutar tests de integracion real. Elimina ciclo falla-intenta.

ADAPTADO: analisis-FINAL.md referencia src/cli/commands/baseline_check.py
que no existe. Patron real tomado de src/cli/baseline.py (Rich table + exit code).
"""

from __future__ import annotations

import os
from pathlib import Path

import typer
from dotenv import load_dotenv
from rich.console import Console
from rich.table import Table

console = Console()

_PROFILES: dict[str, list[dict[str, str]]] = {
    "integration": [
        {"var": "SUPABASE_URL", "label": "Supabase URL", "critical": True},
        {"var": "SUPABASE_SERVICE_KEY", "label": "Supabase Service Key", "critical": True},
    ],
}


def _load_full_profile() -> list[dict[str, str]]:
    env_example = Path(__file__).resolve().parents[3] / ".env.example"
    if not env_example.exists():
        console.print(f"[yellow]Warning: .env.example not found at {env_example}[/yellow]")
        return _PROFILES["integration"]

    vars_list: list[dict[str, str]] = []
    for line in env_example.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        var_name = line.split("=", 1)[0].strip()
        vars_list.append({"var": var_name, "label": var_name, "critical": False})

    for critical_var in _PROFILES["integration"]:
        for v in vars_list:
            if v["var"] == critical_var["var"]:
                v["critical"] = True
                break
        else:
            vars_list.append(critical_var)

    return vars_list


def check_env(
    profile: str = typer.Option(
        "integration",
        "--profile",
        help="Perfil de verificacion: integration (default) | full",
    ),
) -> None:
    """Verifica variables de entorno requeridas antes de ejecutar tests.

    Perfiles:
    - integration: SUPABASE_URL + SUPABASE_SERVICE_KEY
    - full: todas las variables definidas en .env.example
    """
    load_dotenv()

    if profile == "full":
        vars_to_check = _load_full_profile()
    elif profile == "integration":
        vars_to_check = _PROFILES["integration"]
    else:
        console.print(f"[red]Error:[/red] Perfil desconocido '{profile}'")
        console.print("Perfiles disponibles: integration, full")
        raise typer.Exit(code=1)

    console.print(
        f"\n[bold cyan]fap check-env --profile {profile}[/bold cyan]"
    )
    console.print("[dim]Verificando variables de entorno...[/dim]\n")

    table = Table(title=f"Check-Env: {profile}")
    table.add_column("Variable", style="cyan")
    table.add_column("Estado", style="green")
    table.add_column("Valor", style="white")

    missing_critical = False

    for entry in vars_to_check:
        var_name = entry["var"]
        label = entry["label"]
        critical = entry.get("critical", False)

        value = os.getenv(var_name)
        if value:
            display = value[:20] + "..." if len(value) > 20 else value
            table.add_row(label, "[green]OK[/green]", display)
        else:
            table.add_row(label, "[red]MISSING[/red]", "")
            if critical:
                missing_critical = True

    console.print(table)

    if missing_critical:
        console.print(
            "\n[red]ERROR: Faltan variables criticas. "
            "Configura .env antes de continuar.[/red]"
        )
        raise typer.Exit(code=1)

    console.print("\n[green]Todas las variables requeridas presentes.[/green]")


if __name__ == "__main__":
    typer.run(check_env)
