"""src/cli/commands/agent_run.py — `fap agent run` CLI command.

Runs an agent via POST /agents/{role}/run and polls GET /tasks/{task_id}
until completion or timeout. Dogfooding: validates backend flow before UI.
"""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Optional
from urllib.parse import quote

import httpx
import typer
from rich.console import Console
from rich.text import Text

from src.cli.config import CLIConfig

logger = logging.getLogger(__name__)
console = Console()


def _display_result(task_data: dict, elapsed: float) -> None:
    status = task_data.get("status", "unknown")
    tokens = task_data.get("tokens_used", 0) or 0
    result = task_data.get("result")
    error = task_data.get("error")

    if status == "completed":
        console.print(
            Text(f"[OK] Completed in {elapsed:.1f}s | Tokens: {tokens}", style="bold green")
        )
        if result:
            if isinstance(result, str):
                truncated = result[:2000]
                console.print(f"\n{truncated}")
                if len(result) > 2000:
                    console.print(Text("... (truncated)", style="dim"))
            elif isinstance(result, dict):
                console.print(result)
    elif status == "failed":
        console.print(Text(f"[FAIL] Failed after {elapsed:.1f}s", style="bold red"))
        if error:
            detail = error.get("detail") if isinstance(error, dict) else str(error)
            console.print(f"  Error: {detail}")
    else:
        console.print(Text(f"[?] Unknown status: {status}", style="bold yellow"))


async def _run_agent_async(
    role: str,
    message: str,
    org_id: str,
    base_url: str,
    headers: dict[str, str],
    watch: bool,
    timeout: int,
) -> None:
    encoded_role = quote(role, safe='')
    run_url = f"{base_url.rstrip('/')}/agents/{encoded_role}/run"

    async with httpx.AsyncClient(timeout=15) as client:
        response = await client.post(
            run_url,
            json={"input_data": {"message": message}},
            headers=headers,
        )

    if response.status_code not in (200, 201, 202):
        detail = response.json().get("detail", response.text) if response.text else "Unknown error"
        console.print(f"[red]Error {response.status_code}:[/red] {detail}")
        raise typer.Exit(code=1)

    data = response.json()
    task_id = data.get("task_id")
    if not task_id:
        console.print("[red]Error:[/red] No task_id in response")
        raise typer.Exit(code=1)

    if watch:
        console.print(Text(f"[*] Starting agent '{role}' (task: {task_id})", style="bold cyan"))
    else:
        console.print(Text(f"[*] Running agent '{role}'...", style="bold cyan"))

    poll_url = f"{base_url.rstrip('/')}/tasks/{task_id}"
    start_time = time.time()
    attempt = 0
    max_attempts = max(1, timeout // 2)

    while attempt < max_attempts:
        elapsed = time.time() - start_time
        if elapsed > timeout:
            console.print(Text("[yellow]Timeout:[/yellow] Agent is taking too long. Use --timeout to increase."))
            raise typer.Exit(code=1)

        async with httpx.AsyncClient(timeout=10) as poll_client:
            poll_response = await poll_client.get(poll_url, headers=headers)

        if poll_response.status_code == 404:
            attempt += 1
            if watch:
                console.print(Text(f"  [{attempt}/{max_attempts}] waiting for task...", style="dim"))
            await asyncio.sleep(2)
            continue

        if poll_response.status_code != 200:
            detail = poll_response.json().get("detail", poll_response.text) if poll_response.text else "Unknown"
            console.print(f"[red]Polling error {poll_response.status_code}:[/red] {detail}")
            raise typer.Exit(code=1)

        task_data = poll_response.json()
        status = task_data.get("status", "")

        if watch:
            tokens = task_data.get("tokens_used", 0) or 0
            console.print(
                Text(f"  [{attempt + 1}/{max_attempts}] status={status} tokens={tokens}", style="dim")
            )

        if status in ("completed", "failed", "cancelled", "rejected"):
            _display_result(task_data, elapsed)
            if status == "completed":
                raise typer.Exit(code=0)
            else:
                raise typer.Exit(code=1)

        attempt += 1
        await asyncio.sleep(2)

    console.print(Text("[yellow]Timeout:[/yellow] Agent did not complete within the timeout."))
    raise typer.Exit(code=1)


def run_agent(
    role: str = typer.Option(..., "--role", "-r", help="Agent role name"),
    message: str = typer.Option(..., "--message", "-m", help="Message to send to the agent"),
    org_id: Optional[str] = typer.Option(
        None, "--org-id", "-o", help="Organization UUID"
    ),
    watch: bool = typer.Option(
        False, "--watch", "-w", help="Show real-time polling progress"
    ),
    timeout: int = typer.Option(
        120, "--timeout", "-t", help="Polling timeout in seconds", min=1, max=600
    ),
) -> None:
    """Run an agent with a message and wait for the result."""
    config = CLIConfig.load()
    if org_id is None:
        org_id = config.org_id

    if not org_id:
        console.print("[red]Error:[/red] --org-id required. Set FAP_ORG_ID in .env or pass --org-id.")
        raise typer.Exit(code=1)

    base_url = config.api_url
    if not base_url:
        base_url = "http://localhost:8000"

    headers: dict[str, str] = {"X-Org-ID": org_id, "Content-Type": "application/json"}
    if config.access_token:
        headers["Authorization"] = f"Bearer {config.access_token}"

    try:
        asyncio.run(_run_agent_async(role, message, org_id, base_url, headers, watch, timeout))
    except typer.Exit:
        raise
    except httpx.ConnectError:
        console.print("[red]Error:[/red] Cannot connect to API. Is the backend running?")
        raise typer.Exit(code=1)
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(code=1)
