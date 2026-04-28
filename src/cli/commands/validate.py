"""src/cli/commands/validate.py — Implementation of 'fap validate' command."""

from pathlib import Path

import typer
from rich import print

from src.cli.utils import calculate_dir_hashes, load_json
from src.services.bundle_manager import BundleError, BundleManager
from src.services.security_guard import SecurityError, SecurityGuard


def validate_bundle(
    path: Path = typer.Argument(Path("."), help="Path to the bundle directory or .zip file to validate"),
):
    """Validate a bundle's structure, integrity, and security."""
    
    # 1. Handle ZIP files (Paso 13 Critical Gap)
    if path.is_file() and path.suffix.lower() == ".zip":
        typer.echo(f"Validating ZIP bundle: {path.name}")
        try:
            with open(path, "rb") as f:
                zip_bytes = f.read()
            
            # Use 'cli-validation' as placeholder org_id
            manager = BundleManager(org_id="cli-validation")
            content = manager.process_zip(zip_bytes)
            
            bundle_name = content.manifest.bundle_info.name if content.manifest.bundle_info else "Unknown"
            typer.echo(f"  OK: Manifest '{bundle_name}' is valid.")
            typer.echo("  OK: Integrity (SHA256) verified for all files.")
            typer.echo(f"  OK: Security scan passed ({len(content.skills)} skills safe).")
            typer.echo(f"SUCCESS: Bundle {path.name} is valid and safe.")
            return
        except BundleError as e:
            typer.echo(f"Validation failed: {e}", err=True)
            raise typer.Exit(code=1)
        except Exception as e:
            typer.echo(f"Error: Unexpected failure: {e}", err=True)
            raise typer.Exit(code=1)

    # 2. Handle Directories (Existing logic)
    if not path.is_dir():
        print(f"[red]Error:[/red] [bold]{path}[/bold] is not a directory or .zip file.")
        raise typer.Exit(code=1)

    manifest_path = path / "manifest.json"
    if not manifest_path.exists():
        print(f"[red]Error:[/red] manifest.json not found in [bold]{path}[/bold].")
        raise typer.Exit(code=1)

    try:
        manifest = load_json(manifest_path)
        print(f"Validating bundle directory: [bold]{manifest.get('name', 'Unknown')}[/bold]")

        # 1. Integrity Check (Hashes)
        print("VALIDATING integrity...")
        actual_hashes = calculate_dir_hashes(path)
        expected_hashes = manifest.get("hashes", {})
        
        if not expected_hashes:
            print("[yellow]![/yellow] No hashes found in manifest. Skipping integrity check. (Run 'fap package' to generate them)")
        else:
            mismatches = []
            for rel_path, expected_hash in expected_hashes.items():
                if rel_path not in actual_hashes:
                    mismatches.append(f"File missing: {rel_path}")
                elif actual_hashes[rel_path] != expected_hash:
                    mismatches.append(f"Hash mismatch: {rel_path}")
            
            if mismatches:
                print("[red]✗ Integrity check failed:[/red]")
                for m in mismatches:
                    print(f"  - {m}")
                raise typer.Exit(code=1)
            print("[green]OK.[/green] Integrity check successful.")

        # 2. Security Check (Skills)
        print("SCANNING security...")
        skills_dir = path / "skills"
        if skills_dir.exists():
            guard = SecurityGuard()
            skills_found = 0
            for skill_file in skills_dir.glob("*.py"):
                skills_found += 1
                with open(skill_file, "r", encoding="utf-8") as f:
                    content = f.read()
                try:
                    guard.validate_skill(content, filename=skill_file.name)
                    print(f"  [green]OK:[/green] {skill_file.name} is safe.")
                except SecurityError as e:
                    print(f"  [red]FAILED:[/red] [bold]{skill_file.name}:[/bold] {e}")
                    raise typer.Exit(code=1)
            
            if skills_found == 0:
                print("  (No python skills found)")
        else:
            print("  (No skills directory found)")

        print("\n[bold green]SUCCESS:[/bold green] Bundle directory is valid and safe.")

    except typer.Exit:
        raise
    except Exception as e:
        print(f"[red]Error:[/red] Validation failed: {e}")
        raise typer.Exit(code=1)

