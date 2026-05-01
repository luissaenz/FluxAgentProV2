"""src/cli/commands/run.py — Implementation of 'fap run' commands."""

import asyncio
import json
import time
from pathlib import Path
from typing import Any, Dict, Optional

import httpx
import typer
from RestrictedPython import compile_restricted
from rich.console import Console
from rich.live import Live
from rich.panel import Panel
from rich.spinner import Spinner

from src.cli.config import CLIConfig
from src.services.local_executor import LocalExecutor
from src.services.security_guard import SecurityError, SecurityGuard

app = typer.Typer(help="Execute skills, agents, or flows.")
console = Console()


def _load_inputs(
    input_str: Optional[str], input_file: Optional[Path]
) -> Dict[str, Any]:
    """Helper to load JSON inputs from string or file."""
    if input_file:
        try:
            return json.loads(input_file.read_text(encoding="utf-8"))
        except Exception as e:
            console.print(f"[red]Error parsing input file:[/red] {e}")
            raise typer.Exit(code=1)
    if input_str:
        try:
            return json.loads(input_str)
        except Exception as e:
            console.print(f"[red]Error parsing input string:[/red] {e}")
            raise typer.Exit(code=1)
    return {}


@app.command("skill")
def run_skill(
    file_path: Path = typer.Argument(..., help="Path to the .py skill file"),
    input_str: Optional[str] = typer.Option(
        None, "--input", "-i", help="JSON input string"
    ),
    input_file: Optional[Path] = typer.Option(
        None, "--file", "-f", help="Path to JSON input file"
    ),
    danger_no_sandbox: bool = typer.Option(
        False, "--danger-no-sandbox", help="Disable sandbox (NOT RECOMMENDED)"
    ),
):
    """Execute a skill locally in a secure sandbox."""
    if not file_path.exists():
        console.print(f"[red]Error:[/red] File [bold]{file_path}[/bold] not found.")
        raise typer.Exit(code=1)

    inputs = _load_inputs(input_str, input_file)

    try:
        source_code = file_path.read_text(encoding="utf-8")
    except Exception as e:
        console.print(f"[red]Error reading file:[/red] {e}")
        raise typer.Exit(code=1)

    if not danger_no_sandbox:
        guard = SecurityGuard()
        try:
            console.print("[cyan]Verifying security...[/cyan]")
            guard.validate_skill(source_code, file_path.name)
        except SecurityError as e:
            console.print(f"[red]SECURITY BLOCKED:[/red] {e}")
            raise typer.Exit(code=1)
    else:
        if not typer.confirm(
            "WARNING: Running without sandbox is dangerous. Continue?"
        ):
            raise typer.Abort()

    console.print(f"[cyan]Executing [bold]{file_path.name}[/bold]...[/cyan]\n")

    try:
        if not danger_no_sandbox:
            byte_code = compile_restricted(
                source_code, filename=file_path.name, mode="exec"
            )
            safe_env = guard._create_safe_builtins()

            exec_globals = {"__builtins__": safe_env, "INPUT": inputs, "result": None}
            exec(byte_code, exec_globals)
            result = exec_globals.get("result")
        else:
            exec_globals = {"INPUT": inputs, "result": None}
            exec(source_code, exec_globals)
            result = exec_globals.get("result")

        if result is not None:
            console.print(
                Panel(
                    json.dumps(result, indent=2),
                    title="[green]Execution Result[/green]",
                    expand=False,
                )
            )
        else:
            console.print(
                "[yellow]Skill finished with no 'result' variable set.[/yellow]"
            )

    except Exception as e:
        console.print(f"[red]Execution failed:[/red] {e}")
        raise typer.Exit(code=1)


@app.command("agent")
def run_agent(
    role: str = typer.Argument(..., help="Agent role to execute"),
    bundle: Optional[Path] = typer.Option(
        None, "--bundle", "-b", help="Path to local bundle directory"
    ),
    input_str: Optional[str] = typer.Option(
        None, "--input", "-i", help="JSON input string"
    ),
    input_file: Optional[Path] = typer.Option(
        None, "--file", "-f", help="Path to JSON input file"
    ),
    timeout: int = typer.Option(60, "--timeout", help="Execution timeout in seconds"),
):
    """Execute an agent either locally (with --bundle) or remotely."""
    inputs = _load_inputs(input_str, input_file)

    if bundle:
        asyncio.run(_run_local_agent(role, bundle, inputs))
    else:
        asyncio.run(_run_remote_agent(role, inputs, timeout))


@app.command("flow")
def run_flow(
    flow_type: str = typer.Argument(..., help="Flow type to execute"),
    bundle: Optional[Path] = typer.Option(
        None, "--bundle", "-b", help="Path to local bundle directory"
    ),
    input_str: Optional[str] = typer.Option(
        None, "--input", "-i", help="JSON input string"
    ),
    input_file: Optional[Path] = typer.Option(
        None, "--file", "-f", help="Path to JSON input file"
    ),
    timeout: int = typer.Option(60, "--timeout", help="Execution timeout in seconds"),
):
    """Execute a flow either locally (with --bundle) or remotely."""
    inputs = _load_inputs(input_str, input_file)

    if bundle:
        asyncio.run(_run_local_flow(flow_type, bundle, inputs))
    else:
        asyncio.run(_run_remote_flow(flow_type, inputs, timeout))


# --- Internal Implementations ---


async def _run_local_agent(role: str, bundle_path: Path, inputs: Dict[str, Any]):
    """Execute an agent from a local bundle."""
    console.print(
        f"[cyan]Loading local bundle from [bold]{bundle_path}[/bold]...[/cyan]"
    )
    executor = LocalExecutor(bundle_path)
    try:
        executor.prepare()
        with executor.mock_persistence():
            from src.crews.base_crew import BaseCrew

            crew = BaseCrew(org_id=executor.org_id, role=role)
            console.print(f"[cyan]Executing agent [bold]{role}[/bold]...[/cyan]")
            result = crew.run(task_description="Execute assigned task", inputs=inputs)
            _display_result(result.raw if hasattr(result, "raw") else result)
    except Exception as e:
        console.print(f"[red]Local execution failed:[/red] {e}")
        raise typer.Exit(code=1)
    finally:
        executor.cleanup()


async def _run_local_flow(flow_type: str, bundle_path: Path, inputs: Dict[str, Any]):
    """Execute a flow from a local bundle."""
    console.print(
        f"[cyan]Loading local bundle from [bold]{bundle_path}[/bold]...[/cyan]"
    )
    executor = LocalExecutor(bundle_path)
    try:
        executor.prepare()
        with executor.mock_persistence():
            console.print(f"[cyan]Executing flow [bold]{flow_type}[/bold]...[/cyan]")
            # Transient registration happened in executor.prepare()
            from src.flows.registry import flow_registry

            flow = flow_registry.create(flow_type, org_id=executor.org_id)
            result = await flow.execute(input_data=inputs)
            _display_result(result.output_data)
    except Exception as e:
        console.print(f"[red]Local execution failed:[/red] {e}")
        raise typer.Exit(code=1)
    finally:
        executor.cleanup()


async def _run_remote_agent(role: str, inputs: Dict[str, Any], timeout: int):
    """Execute an agent via the remote API."""
    config = CLIConfig.load()
    if not config.api_url or not config.org_id:
        console.print("[red]Error:[/red] CLI not configured. Run 'fap login' first.")
        raise typer.Exit(code=1)

    async with httpx.AsyncClient(timeout=timeout) as client:
        # SUPUESTO: El endpoint para ejecutar agentes remotos es /api/agents/{role}/run
        url = f"{config.api_url}/api/agents/{role}/run"
        headers = {"X-Org-ID": config.org_id}
        if config.access_token:
            headers["Authorization"] = f"Bearer {config.access_token}"

        try:
            response = await client.post(url, json=inputs, headers=headers)
            response.raise_for_status()
            task_id = response.json().get("task_id")
            if not task_id:
                _display_result(response.json())
                return

            await _poll_task(client, config.api_url, task_id, headers, timeout)
        except Exception as e:
            console.print(f"[red]Remote execution failed:[/red] {e}")
            raise typer.Exit(code=1)


async def _run_remote_flow(flow_type: str, inputs: Dict[str, Any], timeout: int):
    """Execute a flow via the remote API."""
    config = CLIConfig.load()
    if not config.api_url or not config.org_id:
        console.print("[red]Error:[/red] CLI not configured. Run 'fap login' first.")
        raise typer.Exit(code=1)

    async with httpx.AsyncClient(timeout=timeout) as client:
        url = f"{config.api_url}/api/flows/{flow_type}/run"
        headers = {"X-Org-ID": config.org_id}
        if config.access_token:
            headers["Authorization"] = f"Bearer {config.access_token}"

        try:
            response = await client.post(url, json=inputs, headers=headers)
            response.raise_for_status()
            task_id = response.json().get("task_id")
            if not task_id:
                _display_result(response.json())
                return

            await _poll_task(client, config.api_url, task_id, headers, timeout)
        except Exception as e:
            console.print(f"[red]Remote execution failed:[/red] {e}")
            raise typer.Exit(code=1)


async def _poll_task(
    client: httpx.AsyncClient, api_url: str, task_id: str, headers: dict, timeout: int
):
    """Poll for task completion with rich spinner."""
    start_time = time.time()
    url = f"{api_url}/api/tasks/{task_id}"

    with Live(
        Spinner("dots", text=f"Executing task {task_id}..."), refresh_per_second=10
    ) as live:
        while time.time() - start_time < timeout:
            resp = await client.get(url, headers=headers)
            resp.raise_for_status()
            data = resp.json()
            status = data.get("status")

            if status == "completed":
                live.update("[green]Task completed![/green]")
                _display_result(data.get("result"))
                return
            elif status == "failed":
                live.update("[red]Task failed![/red]")
                console.print(f"[red]Error:[/red] {data.get('error')}")
                raise typer.Exit(code=1)

            await asyncio.sleep(2)

        live.update("[yellow]Timeout reached.[/yellow]")
        console.print(
            f"[yellow]Task {task_id} is still running (timeout={timeout}s).[/yellow]"
        )


def _display_result(result: Any):
    """Format and display the execution result."""
    if result is None:
        return

    try:
        if isinstance(result, str):
            # Check if it's a JSON string
            try:
                formatted = json.dumps(json.loads(result), indent=2)
            except Exception:
                formatted = result
        else:
            formatted = json.dumps(result, indent=2)

        console.print(
            Panel(
                formatted, title="[green]Result[/green]", expand=False, padding=(1, 2)
            )
        )
    except Exception:
        console.print(f"[green]Result:[/green] {result}")


if __name__ == "__main__":
    app()
