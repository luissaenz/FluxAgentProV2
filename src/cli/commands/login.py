"""src/cli/commands/login.py — Implementation of 'fap login' command."""

import httpx
import typer
from rich import print

from src.cli.config import CLIConfig


def login(
    api_url: str = typer.Option(None, "--url", "-u", help="Backend API URL"),
    org_id: str = typer.Option(None, "--org", "-o", help="Organization ID"),
    token: str = typer.Option(None, "--token", "-t", help="Access Token"),
):
    """Authenticate the CLI with the FluxAgentPro server."""
    config = CLIConfig.load()

    # Interactively ask for missing fields if not provided via flags
    if not api_url:
        api_url = typer.prompt("API URL", default=config.api_url)
    
    if not org_id:
        org_id = typer.prompt("Organization ID", default=config.org_id or "")

    if not token:
        token = typer.prompt("Access Token", hide_input=True)

    print(f"\n[cyan]Authenticating with {api_url}...[/cyan]")

    # Validate credentials
    try:
        # Note: We use a simple GET to verify connectivity and token.
        # In this step, we use /api/bundles/security-config as verification.
        headers = {"X-Org-ID": org_id, "Authorization": f"Bearer {token}"}
        
        with httpx.Client(base_url=api_url, timeout=10.0) as client:
            response = client.get("/api/bundles/security-config", headers=headers)
            
            if response.status_code == 401:
                print("[red]Error:[/red] Invalid token or unauthorized.")
                raise typer.Exit(code=1)
            elif response.status_code == 404:
                # If endpoint doesn't exist yet or URL is wrong
                print(f"[red]Error:[/red] Endpoint not found at {api_url}. Is the server running?")
                raise typer.Exit(code=1)
            elif response.status_code != 200:
                print(f"[red]Error:[/red] Server returned status {response.status_code}: {response.text}")
                raise typer.Exit(code=1)

            # If successful, save config
            config.api_url = api_url
            config.org_id = org_id
            config.access_token = token
            config.save()

            print(f"[green]SUCCESS:[/green] Authenticated correctly for Org [bold]{org_id}[/bold].")
            print("Configuration saved to [bold]~/.fap/config.json[/bold]")

    except httpx.ConnectError:
        print(f"[red]Error:[/red] Could not connect to [bold]{api_url}[/bold]. Check your connection and the URL.")
        raise typer.Exit(code=1)
    except Exception as e:
        print(f"[red]Error during authentication:[/red] {str(e)}")
        raise typer.Exit(code=1)
