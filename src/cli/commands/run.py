"""src/cli/commands/run.py — Implementation of 'fap run' command."""

import json
from pathlib import Path
from typing import Optional

import typer
from RestrictedPython import compile_restricted, safe_builtins
from rich import print
from rich.console import Console
from rich.panel import Panel

from src.services.security_guard import SecurityError, SecurityGuard

console = Console()

def run_skill(
    file_path: Path = typer.Argument(..., help="Path to the .py skill file"),
    input_str: Optional[str] = typer.Option(None, "--input", "-i", help="JSON input string"),
    input_file: Optional[Path] = typer.Option(None, "--file", "-f", help="Path to JSON input file"),
    danger_no_sandbox: bool = typer.Option(False, "--danger-no-sandbox", help="Disable sandbox (NOT RECOMMENDED)"),
):
    """Execute a skill locally in a secure sandbox."""
    if not file_path.exists():
        print(f"[red]Error:[/red] File [bold]{file_path}[/bold] not found.")
        raise typer.Exit(code=1)

    # 1. Prepare inputs
    inputs = {}
    if input_file:
        try:
            inputs = json.loads(input_file.read_text())
        except Exception as e:
            print(f"[red]Error parsing input file:[/red] {e}")
            raise typer.Exit(code=1)
    elif input_str:
        try:
            inputs = json.loads(input_str)
        except Exception as e:
            print(f"[red]Error parsing input string:[/red] {e}")
            raise typer.Exit(code=1)

    # 2. Read code
    try:
        source_code = file_path.read_text(encoding="utf-8")
    except Exception as e:
        print(f"[red]Error reading file:[/red] {e}")
        raise typer.Exit(code=1)

    # 3. Security Validation (Skip if danger-no-sandbox)
    if not danger_no_sandbox:
        guard = SecurityGuard()
        try:
            print("[cyan]Verifying security...[/cyan]")
            guard.validate_skill(source_code, file_path.name)
        except SecurityError as e:
            print(f"[red]SECURITY BLOCKED:[/red] {e}")
            raise typer.Exit(code=1)
    else:
        # Confirm if not already confirmed by flag
        if not typer.confirm("⚠️  WARNING: Running without sandbox is dangerous. Continue?"):
            raise typer.Abort()

    # 4. Execution
    print(f"[cyan]Executing [bold]{file_path.name}[/bold]...[/cyan]\n")
    
    try:
        if not danger_no_sandbox:
            # Sandbox execution logic
            # RestrictedPython compilation
            byte_code = compile_restricted(source_code, filename=file_path.name, mode="exec")
            
            # Safe environment
            # Injected variables: INPUT
            # Note: We provide a controlled __import__ that is backed by SecurityGuard validation
            safe_env = safe_builtins.copy()
            safe_env["__import__"] = __import__ 
            
            exec_globals = {
                "__builtins__": safe_env,
                "INPUT": inputs,
                "result": None # We expect the script to set 'result'
            }
            
            exec(byte_code, exec_globals)
            result = exec_globals.get("result")
        else:
            # Direct execution
            # Injected variables: INPUT
            exec_globals = {"INPUT": inputs, "result": None}
            exec(source_code, exec_globals)
            result = exec_globals.get("result")

        # 5. Output result
        if result is not None:
            console.print(Panel(
                json.dumps(result, indent=2),
                title="[green]Execution Result[/green]",
                expand=False
            ))
        else:
            print("[yellow]Skill finished with no 'result' variable set.[/yellow]")

    except Exception as e:
        print(f"[red]Execution failed:[/red] {e}")
        raise typer.Exit(code=1)
