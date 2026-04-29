"""src/cli/commands/validate.py — Implementation of 'fap validate' command."""

import sys
from pathlib import Path
from typing import Optional

import httpx
import typer
from rich import print

from src.cli.config import CLIConfig
from src.cli.utils import load_json
from src.services.bundle_manager import BundleError, BundleManager
from src.services.security_guard import SecurityError, SecurityGuard
from src.utils.bundle_utils import calculate_bundle_hashes


def get_remote_security_config(config: CLIConfig) -> Optional[dict]:
    """Fetch security configuration from the server."""
    if not config.access_token:
        print("[yellow]⚠️  Not logged in. Skipping security sync.[/yellow]")
        return None

    try:
        headers = {
            "X-Org-ID": config.org_id,
            "Authorization": f"Bearer {config.access_token}"
        }
        with httpx.Client(base_url=config.api_url, timeout=5.0) as client:
            response = client.get("/api/bundles/security-config", headers=headers)
            if response.status_code == 200:
                return response.json()
            else:
                print(f"[yellow]⚠️  Could not sync security config (Status {response.status_code}). Using local defaults.[/yellow]")
    except Exception as e:
        print(f"[yellow]⚠️  Offline or connection error: {e}. Using local defaults.[/yellow]")

    return None


def validate_bundle(
    path: Path = typer.Argument(
        Path("."), help="Path to the bundle directory or .zip file to validate"
    ),
    sync: bool = typer.Option(False, "--sync", "-s", help="Synchronize security configuration with server"),
):
    """Validate a bundle's structure, integrity, and security."""
    config = CLIConfig.load()
    remote_config = None

    if sync:
        print("[cyan]Syncing security configuration with server...[/cyan]")
        remote_config = get_remote_security_config(config)
        if remote_config:
            # Check python version compatibility
            remote_py = remote_config.get("python_version")
            local_py = f"{sys.version_info.major}.{sys.version_info.minor}"
            if remote_py and remote_py != local_py:
                print(f"[yellow]⚠️  Python version mismatch! Server: {remote_py}, Local: {local_py}[/yellow]")
                print("[yellow]   Bytecode compilation might behave differently.[/yellow]")
            else:
                print("[green]✓ Security configuration synced.[/green]")

    # Prepare SecurityGuard
    if remote_config:
        guard = SecurityGuard(
            allowed_modules=set(remote_config["allowed_modules"]),
            forbidden_modules=set(remote_config["forbidden_modules"]),
            timeout_seconds=remote_config.get("timeout_seconds", 30)
        )
    else:
        guard = SecurityGuard()

    # 1. Handle ZIP files
    if path.is_file() and path.suffix.lower() == ".zip":
        print(f"Validating ZIP bundle: [bold]{path.name}[/bold]")
        try:
            with open(path, "rb") as f:
                zip_bytes = f.read()

            # Use 'cli-validation' as placeholder org_id
            manager = BundleManager(org_id="cli-validation", security_guard=guard)
            content = manager.process_zip(zip_bytes)

            bundle_name = (
                content.manifest.bundle_info.name
                if content.manifest.bundle_info
                else "Unknown"
            )
            print(f"  [green]OK:[/green] Manifest '{bundle_name}' is valid.")
            print("  [green]OK:[/green] Integrity (SHA256) verified for all files.")
            print(
                f"  [green]OK:[/green] Security scan passed ({len(content.skills)} skills safe)."
            )
            print(f"\n[bold green]SUCCESS:[/bold green] Bundle {path.name} is valid and safe.")
            return
        except BundleError as e:
            print(f"[red]Validation failed:[/red] {e}")
            raise typer.Exit(code=1)
        except Exception as e:
            print(f"[red]Error:[/red] Unexpected failure: {e}")
            raise typer.Exit(code=1)

    # 2. Handle Directories
    if not path.is_dir():
        print(f"[red]Error:[/red] [bold]{path}[/bold] is not a directory or .zip file.")
        raise typer.Exit(code=1)

    manifest_path = path / "manifest.json"
    if not manifest_path.exists():
        print(f"[red]Error:[/red] manifest.json not found in [bold]{path}[/bold].")
        raise typer.Exit(code=1)

    try:
        manifest = load_json(manifest_path)
        print(
            f"Validating bundle directory: [bold]{manifest.get('name', 'Unknown')}[/bold]"
        )

        # 1. Integrity Check (Hashes)
        print("VALIDATING integrity...")
        actual_hashes = calculate_bundle_hashes(path)

        expected_hashes = manifest.get("hashes", {})

        if not expected_hashes:
            print(
                "[yellow]![/yellow] No hashes found in manifest. Skipping integrity check. (Run 'fap package' to generate them)"
            )
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
