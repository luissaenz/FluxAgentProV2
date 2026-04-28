"""src/cli/commands/package.py — Implementation of 'fap package' command."""

import os
import zipfile
from pathlib import Path

import typer
from rich import print

from src.cli.utils import calculate_dir_hashes, load_json, save_json


def package_bundle(
    path: Path = typer.Argument(
        Path("."), help="Path to the bundle directory to package"
    ),
    output: Path = typer.Option(
        None, "--output", "-o", help="Custom name/path for the output ZIP file"
    ),
):
    """Update manifest hashes and create a deployable ZIP bundle."""
    if not path.is_dir():
        print(f"[red]Error:[/red] [bold]{path}[/bold] is not a directory.")
        raise typer.Exit(code=1)

    manifest_path = path / "manifest.json"
    if not manifest_path.exists():
        print(f"[red]Error:[/red] manifest.json not found in [bold]{path}[/bold].")
        raise typer.Exit(code=1)

    try:
        manifest = load_json(manifest_path)
        bundle_name = manifest.get("name", "bundle")

        # 1. Update Hashes
        print(f"PACKAGING bundle: [bold]{bundle_name}[/bold]")
        print("GENERATING hashes...")
        new_hashes = calculate_dir_hashes(path)
        manifest["hashes"] = new_hashes
        save_json(manifest_path, manifest)
        print("[green]OK:[/green] Manifest updated.")

        # 2. Create ZIP
        zip_filename = output if output else Path(f"{bundle_name}.zip")
        print(f"ZIP: Creating [bold]{zip_filename}[/bold]...")

        with zipfile.ZipFile(zip_filename, "w", zipfile.ZIP_DEFLATED) as zf:
            # We want to walk the directory and add everything relative to 'path'
            for root, _dirs, files in os.walk(path):
                for f in files:
                    file_path = Path(root) / f
                    # Calculate arcname (path inside the zip)
                    arcname = file_path.relative_to(path)
                    zf.write(file_path, arcname)

        size_mb = os.path.getsize(zip_filename) / (1024 * 1024)
        print(
            f"[bold green]OK:[/bold green] [cyan]{zip_filename}[/cyan] created successfully ({size_mb:.2f} MB)."
        )
        print("\nYou can now import this bundle using:")
        print("  [white]POST /api/bundles/import[/white]")

    except Exception as e:
        print(f"[red]Error:[/red] Packaging failed: {e}")
        raise typer.Exit(code=1)
