"""src/cli/commands/lint_fix.py — 'fap lint-fix' command.

Runs ruff check --fix on src/ and tests/ then validates result.
DX Tooling for Paso 1 Hotfix Post-Certificacion — dogfooding obligatorio.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import typer
from rich import print

PROJECT_ROOT = Path(__file__).resolve().parents[3]


def _run_ruff(check_only: bool = False) -> subprocess.CompletedProcess:
    cmd = [sys.executable, "-m", "ruff", "check"]

    if not check_only:
        cmd.append("--fix")

    cmd.extend(["src/", "tests/"])

    result = subprocess.run(
        cmd,
        cwd=str(PROJECT_ROOT),
        capture_output=True,
        text=True,
    )

    return result


def lint_fix(
    check: bool = typer.Option(
        False,
        "--check",
        help="Only check, don't fix (exit code = error count)",
    ),
):
    """Fix I001 unsorted-imports via ruff --fix, then validate.

    Ejemplos:
        fap lint-fix              # fix + verify 0 errors
        fap lint-fix --check      # solo verificar (CI mode)
    """
    mode = "check" if check else "fix"
    print(f"\n[bold cyan]fap lint-fix --{mode}[/bold cyan]")

    result = _run_ruff(check_only=check)

    if result.stdout:
        print(result.stdout)
    if result.stderr:
        print(f"[dim]{result.stderr}[/dim]")

    if result.returncode == 0:
        print("\n[bold green]LINT PASSED (0 errors)[/bold green]")
    else:
        print(f"\n[bold red]LINT FAILED ({result.returncode} errors)[/bold red]")

    raise typer.Exit(code=result.returncode)
