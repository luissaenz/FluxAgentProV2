"""src/cli/commands/dev.py — Implementation of 'fap dev' command."""

import threading
import time
from pathlib import Path
from typing import Optional

import typer
from rich import print
from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

from src.cli.commands.package import package_bundle
from src.cli.commands.publish import publish_bundle
from src.services.security_guard import SecurityError, SecurityGuard


class BundleEventHandler(FileSystemEventHandler):
    """Handle file system events for bundle directory with debounce and validation."""

    def __init__(self, bundle_path: Path, debounce_seconds: float = 0.5):
        self.bundle_path = bundle_path
        self.debounce_seconds = debounce_seconds
        self.timer: Optional[threading.Timer] = None
        self.lock = threading.Lock()
        self.guard = SecurityGuard()

        # Files to ignore to prevent infinite loops (manifest is updated by package_bundle)
        self.ignored_patterns = {".zip", ".git", "__pycache__", "manifest.json"}

    def on_any_event(self, event):
        if event.is_directory:
            return

        path = Path(event.src_path)

        # Filter by name/extension
        if (
            path.suffix.lower() in self.ignored_patterns
            or path.name in self.ignored_patterns
        ):
            return

        # Also ignore hidden files or files in ignored directories
        if any(part.startswith(".") or part == "__pycache__" for part in path.parts):
            return

        # Check if it's within the valid bundle structure
        try:
            rel_path = path.relative_to(self.bundle_path)
            valid_subdirs = {"agents", "flows", "skills", "context"}

            # We only trigger on changes inside the valid subdirectories
            if rel_path.parts[0] not in valid_subdirs:
                return
        except (ValueError, IndexError):
            return

        self._schedule_update()

    def _schedule_update(self):
        with self.lock:
            if self.timer:
                self.timer.cancel()
            self.timer = threading.Timer(self.debounce_seconds, self._do_update)
            self.timer.start()

    def _do_update(self):
        # SUPUESTO: Usamos un lock para evitar que múltiples eventos disparen
        # publicaciones concurrentes si una subida lenta está en proceso.
        with self.lock:
            print("\n[cyan]Change detected. Syncing...[/cyan]")

            try:
                # 1. Validation AST (Local fail-fast)
                print("Validating [bold]AST[/bold]...")
                skills_dir = self.bundle_path / "skills"
                if skills_dir.exists():
                    for skill_file in skills_dir.glob("*.py"):
                        with open(skill_file, "r", encoding="utf-8") as f:
                            content = f.read()
                        # NOTE: SecurityGuard is used here to catch errors before network overhead
                        self.guard.validate_skill(content, filename=skill_file.name)

                # 2. Package (Update hashes and create ZIP)
                # We call package_bundle directly and use its return value
                zip_path = package_bundle(path=self.bundle_path)

                if not zip_path or not zip_path.exists():
                    print("[red]Error:[/red] Could not find generated ZIP.")
                    return

                # NOTE: Injected force=True as per Analysis Final §79
                publish_bundle(zip_path=zip_path, force=True)

                print("[bold green]✓ Hot-reload successful![/bold green]")

            except SecurityError as e:
                print(f"[red]STOPPED:[/red] Security validation failed: {e}")
                print(
                    "[yellow]Bundle NOT published. Fix the error to resume sync.[/yellow]"
                )
            except typer.Exit as e:
                # Typer exit usually means one of the sub-commands printed its own error
                exit_code = getattr(e, "exit_code", 0)
                if exit_code != 0:
                    print("[red]Sync aborted due to error in sub-command.[/red]")
            except Exception as e:
                print(f"[red]Error during sync:[/red] {e}")


def dev_command(
    path: Path = typer.Argument(
        Path("."), help="Path to the bundle directory to watch"
    ),
    debounce: float = typer.Option(
        0.5, "--debounce", "-d", help="Debounce time in seconds"
    ),
):
    """Watch for changes and automatically publish the bundle (Hot-Reload)."""
    path = Path(path).absolute()

    if not path.is_dir():
        print(f"[red]Error:[/red] [bold]{path}[/bold] is not a directory.")
        raise typer.Exit(code=1)

    manifest_path = path / "manifest.json"
    if not manifest_path.exists():
        print(f"[red]Error:[/red] manifest.json not found in [bold]{path}[/bold].")
        raise typer.Exit(code=1)

    print(f"[bold green]Watcher started[/bold green] on [bold]{path.absolute()}[/bold]")
    print(
        "[dim]Monitoring agents/, flows/, skills/, context/. Press Ctrl+C to stop.[/dim]\n"
    )

    event_handler = BundleEventHandler(path, debounce_seconds=debounce)
    observer = Observer()
    observer.schedule(event_handler, str(path), recursive=True)
    observer.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
        print("\n[yellow]Watcher stopped.[/yellow]")

    observer.join()
