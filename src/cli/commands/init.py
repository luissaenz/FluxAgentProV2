"""src/cli/commands/init.py — Implementation of 'fap init' command."""

import os
from pathlib import Path

import typer
from rich import print

from src.cli.utils import create_manifest_base, save_json


def init_bundle(
    name: str = typer.Argument(..., help="Name of the bundle to create"),
    author: str = typer.Option("dev@org.com", help="Author of the bundle"),
    path: Path = typer.Option(Path("."), help="Path where the bundle folder will be created"),
):
    """Initialize a new FAP Bundle structure."""
    bundle_path = path / name

    if bundle_path.exists():
        print(f"[red]Error:[/red] Path [bold]{bundle_path}[/bold] already exists.")
        raise typer.Exit(code=1)

    # Create directory structure
    subdirs = ["agents", "flows", "skills", "context"]
    try:
        os.makedirs(bundle_path)
        for sd in subdirs:
            os.makedirs(bundle_path / sd)

        # Create initial manifest
        manifest = create_manifest_base(name, author)
        save_json(bundle_path / "manifest.json", manifest)

        print(f"[green]SUCCESS:[/green] Bundle [bold]{name}[/bold] initialized successfully at {bundle_path}")
        print("\nStructure created:")
        for sd in subdirs:
            print(f"  - {sd}/")
        print("  - manifest.json")
        print("\nNext steps:")
        print("  1. Add your files to the subdirectories.")
        print(f"  2. Run [cyan]fap validate {name}[/cyan] to check for errors.")
        print(f"  3. Run [cyan]fap package {name}[/cyan] to create the ZIP.")

    except Exception as e:
        print(f"[red]Error:[/red] Could not create bundle structure: {e}")
        raise typer.Exit(code=1)
