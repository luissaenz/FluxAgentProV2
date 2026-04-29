"""src/cli/commands/publish.py — Implementation of 'fap publish' command."""

from pathlib import Path

import httpx
import typer
from rich import print

from src.cli.config import CLIConfig


def publish_bundle(
    zip_path: Path = typer.Argument(..., help="Path to the .zip bundle to publish"),
    force: bool = typer.Option(False, "--force", "-f", help="Force overwrite existing bundle version"),
):
    """Publish a bundle to the FluxAgentPro server."""
    if not zip_path.exists() or zip_path.suffix.lower() != ".zip":
        print(f"[red]Error:[/red] [bold]{zip_path}[/bold] is not a valid ZIP file.")
        raise typer.Exit(code=1)

    import os
    if os.getenv("FAP_MOCK_SERVER") == "1":
        print("[yellow]MOCK MODE:[/yellow] Simulating successful publication...")
        print(f"\n[bold green]SUCCESS:[/bold green] Bundle [bold]{zip_path.name}[/bold] published (MOCK)!")
        return

    config = CLIConfig.load()
    if not config.access_token or not config.org_id:
        print("[red]Error:[/red] Not authenticated. Run [bold]fap login[/bold] first.")
        raise typer.Exit(code=1)

    print(f"Publishing [bold]{zip_path.name}[/bold] to [bold]{config.api_url}[/bold]...")

    headers = {
        "X-Org-ID": config.org_id,
        "Authorization": f"Bearer {config.access_token}"
    }

    try:
        with open(zip_path, "rb") as f:
            files = {"file": (zip_path.name, f, "application/zip")}

            params = {"force": "true" if force else "false"}
            with httpx.Client(base_url=config.api_url, timeout=60.0) as client:
                response = client.post("/api/bundles/import", headers=headers, files=files, params=params)

                if response.status_code == 201:
                    result = response.json()
                    print(f"\n[bold green]SUCCESS:[/bold green] Bundle [bold]{zip_path.name}[/bold] published!")
                    print(f"Bundle ID: [cyan]{result.get('bundle_id')}[/cyan]")
                    print(f"Summary: {result.get('summary', 'Import successful')}")
                elif response.status_code == 401:
                    print("[red]Error:[/red] Authentication failed (401). Try logging in again.")
                else:
                    # In case of validation errors (400), we show the detail
                    print(f"[red]Error {response.status_code}:[/red] {response.text}")
                    raise typer.Exit(code=1)

    except httpx.ConnectError:
        print(f"[red]Error:[/red] Could not connect to [bold]{config.api_url}[/bold].")
        raise typer.Exit(code=1)
    except Exception as e:
        print(f"[red]Error during publishing:[/red] {e}")
        raise typer.Exit(code=1)
