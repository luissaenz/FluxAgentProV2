"""src/cli/commands/scaffold.py — Implementation of 'fap scaffold' command."""

import json
from pathlib import Path

import typer
from rich.console import Console

from src.utils.bundle_utils import create_base_manifest

app = typer.Typer(help="Scaffold new FAP bundles.")
console = Console()

@app.callback(invoke_without_command=True)
def scaffold_command(
    name: str = typer.Argument(..., help="Name of the bundle to scaffold"),
    target_dir: Path = typer.Option(Path("."), "--dir", "-d", help="Directory where to create the bundle"),
):
    """
    Create a new bundle structure (agents, skills, flows, manifest.json).
    """
    bundle_path = target_dir / name

    if bundle_path.exists():
        console.print(f"[yellow]Warning:[/yellow] Directory [bold]{bundle_path}[/bold] already exists.")
        if not typer.confirm("Do you want to scaffold inside it?"):
            raise typer.Abort()
    else:
        bundle_path.mkdir(parents=True, exist_ok=True)

    # Create subdirectories
    for folder in ["agents", "skills", "flows"]:
        (bundle_path / folder).mkdir(exist_ok=True)
        # Create a .gitkeep to ensure folder is tracked if empty
        (bundle_path / folder / ".gitkeep").touch()

    # Create manifest.json
    manifest_path = bundle_path / "manifest.json"
    if not manifest_path.exists():
        manifest = create_base_manifest(name)
        with open(manifest_path, "w", encoding="utf-8") as f:
            json.dump(manifest, f, indent=2)
        console.print("[green]Created manifest.json[/green]")
    else:
        console.print("[blue]Info:[/blue] manifest.json already exists, skipping creation.")

    console.print(f"\n[green]Successfully scaffolded bundle [bold]{name}[/bold] at {bundle_path}[/green]")
    console.print("[cyan]Structure:[/cyan]")
    console.print(f"  {name}/")
    console.print("  ├── agents/")
    console.print("  ├── skills/")
    console.print("  ├── flows/")
    console.print("  └── manifest.json")

if __name__ == "__main__":
    app()
