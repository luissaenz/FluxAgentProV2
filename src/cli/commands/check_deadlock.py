"""src/cli/commands/check_deadlock.py — 'fap check-deadlock' command.

DX Tooling: Detects asyncio.run_coroutine_threadsafe().result() pattern in
Python source files — the sync->async bridge that causes deadlocks when
called from within the same event loop.

Usage:
    fap check-deadlock --path src/
    fap check-deadlock --check  (exit 1 if patterns found)
"""

from __future__ import annotations

import re
from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

console = Console()

DEADLOCK_PATTERN = re.compile(
    r"run_coroutine_threadsafe\s*\(.*?\)\s*\.result\s*\(", re.DOTALL
)


def check_deadlock(
    path: str = typer.Option(
        "src/",
        "--path",
        help="Directory to scan for deadlock patterns",
    ),
    check: bool = typer.Option(
        False,
        "--check",
        help="Exit with code 1 if deadlock patterns are found",
    ),
) -> None:
    """Scan Python files for run_coroutine_threadsafe().result() anti-pattern.

    This pattern causes deadlocks when called from within the same event loop
    that the coroutine is scheduled on.
    """
    scan_path = Path(path)
    if not scan_path.exists():
        console.print(f"[red]Error:[/red] Path '{path}' does not exist")
        raise typer.Exit(code=1)

    py_files = list(scan_path.rglob("*.py"))
    matches: list[tuple[str, int, str]] = []

    base_path = Path.cwd()
    for py_file in py_files:
        try:
            content = py_file.read_text(encoding="utf-8")
            for match in DEADLOCK_PATTERN.finditer(content):
                start_pos = match.start()
                line_num = content[:start_pos].count("\n") + 1
                matched_text = match.group(0)
                first_line = matched_text.split("\n")[0].strip()
                try:
                    rel_path = str(py_file.resolve().relative_to(base_path))
                except ValueError:
                    rel_path = str(py_file)
                matches.append((rel_path, line_num, first_line))
        except (UnicodeDecodeError, PermissionError):
            continue

    if not matches:
        console.print("\n[green]No deadlock patterns found.[/green]")
        console.print(
            "[dim]Scanned {} Python files in '{}'.[/dim]".format(len(py_files), path)
        )
        return

    table = Table(title="Deadlock Pattern Detection")
    table.add_column("File", style="cyan")
    table.add_column("Line", style="yellow")
    table.add_column("Code", style="white")

    for file_path, line_num, code_line in matches:
        table.add_row(file_path, str(line_num), code_line)

    console.print(table)
    console.print(
        f"\n[red]Found {len(matches)} potential deadlock pattern(s) in {path}[/red]"
    )
    console.print(
        "[dim]Use 'await pool.get_tools()' instead of "
        "run_coroutine_threadsafe().result()[/dim]"
    )

    if check:
        raise typer.Exit(code=1)


if __name__ == "__main__":
    typer.run(check_deadlock)
