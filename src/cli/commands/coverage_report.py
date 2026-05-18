"""src/cli/commands/coverage_report.py — `fap coverage report` CLI command.

DX Tooling (Tarea 0, Paso 15): ejecuta pytest con coverage y muestra
tabla Rich con % por módulo, umbrales, y reporte HTML opcional.

Uso:
    fap coverage report
    fap coverage report --module src/api/routes/tools
    fap coverage report --threshold 80
    fap coverage report --html
    fap coverage report --diff
"""

from __future__ import annotations

import json
import logging
import subprocess
import sys
from pathlib import Path
from typing import Any, Optional

import typer
from rich.console import Console
from rich.table import Table

logger = logging.getLogger(__name__)
console = Console()

coverage_app = typer.Typer(
    help="Coverage reports: run pytest with coverage and visualize results.",
    no_args_is_help=True,
)

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
DEFAULT_THRESHOLD = 75.0


def _run_coverage(
    module: Optional[str] = None,
    threshold: float = DEFAULT_THRESHOLD,
    html: bool = False,
) -> dict[str, Any]:
    """Run pytest with coverage and return parsed results."""
    cmd = [
        sys.executable,
        "-m",
        "pytest",
        "--cov=src",
        "--cov-report=term-missing",
        "--cov-report=json",
        "-q",
        "--no-header",
    ]

    if module:
        cmd[4] = f"--cov={module}"

    if html:
        cmd.append("--cov-report=html")

    tests_dir = PROJECT_ROOT / "tests"
    cmd.append(str(tests_dir))

    console.print(f"[dim]Running: {' '.join(cmd)}[/dim]\n")

    result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)

    if result.returncode != 0 and "FAILED" in result.stdout:
        console.print("[red]Tests failed:[/red]")
        console.print(result.stdout)

    json_path = PROJECT_ROOT / "coverage.json"

    cov_data: dict[str, Any] = {"modules": {}, "totals": {}}
    if json_path.exists():
        try:
            raw = json.loads(json_path.read_text(encoding="utf-8"))
            files = raw.get("files", {})
            module_totals: dict[str, dict[str, float]] = {}
            total_covered = 0
            total_statements = 0

            for filepath, fdata in files.items():
                if not filepath.startswith("src/"):
                    continue
                parts = filepath.split("/")
                mod_key = "/".join(parts[:3]) if len(parts) > 3 else "/".join(parts[:2])

                if mod_key not in module_totals:
                    module_totals[mod_key] = {"covered": 0, "statements": 0}
                summary = fdata.get("summary", {})
                module_totals[mod_key]["statements"] += summary.get("num_statements", 0)
                module_totals[mod_key]["covered"] += summary.get("covered_lines", 0)

            for mod_key, mtotals in sorted(module_totals.items()):
                stmts = mtotals["statements"]
                cov_lines = mtotals["covered"]
                pct = (cov_lines / stmts * 100) if stmts > 0 else 0.0
                cov_data["modules"][mod_key] = {
                    "statements": stmts,
                    "covered": cov_lines,
                    "percent": round(pct, 1),
                    "pass": pct >= threshold,
                }
                total_covered += cov_lines
                total_statements += stmts

            total_pct = (total_covered / total_statements * 100) if total_statements > 0 else 0.0
            cov_data["totals"] = {
                "statements": total_statements,
                "covered": total_covered,
                "percent": round(total_pct, 1),
                "pass": total_pct >= threshold,
            }

            json_path.unlink(missing_ok=True)

        except (json.JSONDecodeError, KeyError) as exc:
            console.print(f"[yellow]Warning: Could not parse coverage.json: {exc}[/yellow]")

    cov_data["stdout"] = result.stdout
    cov_data["returncode"] = result.returncode
    cov_data["html_dir"] = str(PROJECT_ROOT / "htmlcov") if html else None

    return cov_data


def _render_table(cov_data: dict[str, Any], threshold: float, diff: bool = False) -> None:
    """Render coverage data as a Rich table."""
    modules = cov_data.get("modules", {})
    totals = cov_data.get("totals", {})

    if not modules:
        console.print("[yellow]No coverage data available.[/yellow]")
        console.print("[dim]Try running with a broader scope or checking test discovery.[/dim]")
        return

    table = Table(title=f"Coverage Report (threshold: {threshold}%)")
    table.add_column("Module", style="cyan")
    table.add_column("Statements", justify="right")
    table.add_column("Covered", justify="right")
    table.add_column("Percent", justify="right")
    table.add_column("Status", justify="center")

    for mod_key, mdata in sorted(modules.items()):
        if diff and mdata["pass"]:
            continue
        pct = mdata["percent"]
        status = "✅" if mdata["pass"] else "❌"
        pct_style = "green" if mdata["pass"] else "red"
        table.add_row(
            mod_key,
            str(mdata["statements"]),
            str(mdata["covered"]),
            f"[{pct_style}]{pct}%[/]",
            status,
        )

    if totals:
        t = totals
        sep = Table.grid()
        sep.add_row()
        console.print(sep)
        total_table = Table(show_header=False, box=None)
        total_table.add_column(style="bold")
        total_table.add_column(justify="right")
        total_table.add_row("TOTAL", "")
        total_table.add_row("  Statements", str(t["statements"]))
        total_table.add_row("  Covered", str(t["covered"]))
        tpct = t["percent"]
        tstyle = "green" if t["pass"] else "red"
        total_table.add_row("  Percent", f"[{tstyle}]{tpct}%[/]")
        total_table.add_row("  Threshold", f"{threshold}%")
        total_table.add_row("  Status", "✅ PASS" if t["pass"] else "❌ FAIL")
        console.print(total_table)

    console.print("\n[dim]Coverage JSON output was saved temporarily for parsing.[/dim]")

    if cov_data.get("html_dir"):
        html_path = cov_data["html_dir"]
        console.print(f"\n[green]HTML report:[/green] {html_path}/index.html")


@coverage_app.command("report")
def coverage_report(
    module: Optional[str] = typer.Option(
        None,
        "--module",
        "-m",
        help="Specific module to measure (e.g. src/api/routes/tools)",
    ),
    threshold: float = typer.Option(
        DEFAULT_THRESHOLD,
        "--threshold",
        "-t",
        help="Minimum coverage percentage",
    ),
    html: bool = typer.Option(
        False,
        "--html",
        help="Generate HTML coverage report",
    ),
    diff: bool = typer.Option(
        False,
        "--diff",
        "-d",
        help="Show only modules below threshold",
    ),
) -> None:
    """Ejecutar pytest con coverage y mostrar resultados por módulo.

    Analiza la cobertura de tests del proyecto y la presenta en una
    tabla Rich con status por módulo. Útil para pre-commit checks y CI.
    """
    cov_data = _run_coverage(module=module, threshold=threshold, html=html)

    console.print()
    _render_table(cov_data, threshold, diff=diff)

    tests_failed = cov_data.get("returncode", 0) != 0 and "FAILED" in cov_data.get("stdout", "")
    below_threshold = any(not m["pass"] for m in cov_data.get("modules", {}).values())

    if tests_failed or below_threshold:
        console.print("[red]Coverage checks failed.[/red]")
        raise typer.Exit(code=1)

    console.print("[bold green]All coverage checks passed.[/bold green]")


if __name__ == "__main__":
    coverage_app()
