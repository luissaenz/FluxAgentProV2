"""src/cli/commands/test_builder.py — `fap test builder` CLI command.

DX Tooling: ejecuta la suite de tests de integración del Builder Visual
y genera un reporte de integridad opcional en HTML.

Uso:
    fap test builder --org-id test-org --report
    fap test builder --org-id test-org --cov
"""

from __future__ import annotations

import json
import logging
import subprocess
import sys
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table

logger = logging.getLogger(__name__)
console = Console()

test_builder_app = typer.Typer(
    help="Builder integration tests: run E2E scenarios and integrity report.",
    no_args_is_help=True,
)


@test_builder_app.command("run")
def run_builder_tests(
    org_id: str = typer.Option(
        "test-org",
        "--org-id",
        "-o",
        help="Organization UUID for test context",
    ),
    report: bool = typer.Option(
        False,
        "--report",
        help="Generate HTML integrity report",
    ),
    scenario: Optional[str] = typer.Option(
        "all",
        "--scenario",
        "-s",
        help="Scenario to run: agent, playground, crew, roundtrip, or 'all'",
    ),
    cov: bool = typer.Option(
        False,
        "--cov",
        help="Include coverage report after tests",
    ),
) -> None:
    """Ejecutar tests de integración del Builder Visual.

    Ejecuta la suite de escenarios E2E definida en
    tests/e2e/test_builder_scenarios.py y valida la integridad de los
    endpoints del builder (agents, templates, workflows, bundles).
    """
    test_file = (
        Path(__file__).resolve().parent.parent.parent.parent
        / "tests"
        / "e2e"
        / "test_builder_scenarios.py"
    )

    if not test_file.exists():
        console.print(f"[red]Error:[/red] Test file not found: {test_file}")
        raise typer.Exit(code=1)

    console.print(f"[cyan]Running builder tests for org:[/cyan] {org_id}")
    console.print(f"[cyan]Test file:[/cyan] {test_file}")
    console.print(f"[cyan]Scenario:[/cyan] {scenario}")

    cmd = [
        sys.executable,
        "-m",
        "pytest",
        str(test_file),
        "-v",
        "--timeout=120",
        "-o",
        "log_cli=true",
    ]

    if cov:
        cmd.extend(["--cov=src", "--cov-report=json"])

    if scenario != "all":
        cmd.extend(["-k", scenario])

    console.print(f"\n[dim]Command: {' '.join(cmd)}[/dim]\n")

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=300,
        )

        console.print(result.stdout)

        if result.returncode != 0:
            console.print(f"[red]Tests failed with exit code {result.returncode}[/red]")
            if result.stderr:
                console.print(f"[red]Stderr:[/red]\n{result.stderr}")

            if report:
                _generate_html_report(
                    org_id, result.stdout + result.stderr, test_file, passed=False
                )

            raise typer.Exit(code=result.returncode)

        console.print("\n[bold green]All builder tests passed.[/bold green]")

        if cov:
            _show_coverage_summary()

        if report:
            _generate_html_report(org_id, result.stdout, test_file, passed=True)

    except subprocess.TimeoutExpired:
        console.print("[red]Error:[/red] Test execution timed out (5 min)")
        raise typer.Exit(code=1)
    except Exception as exc:
        console.print(f"[red]Error:[/red] {exc}")
        raise typer.Exit(code=1)


def _show_coverage_summary() -> None:
    """Parse coverage.json and display a summary table."""
    cov_path = Path(__file__).resolve().parent.parent.parent.parent / "coverage.json"
    if not cov_path.exists():
        console.print("[yellow]Coverage data not found (coverage.json missing).[/yellow]")
        return

    try:
        raw = json.loads(cov_path.read_text(encoding="utf-8"))
        files = raw.get("files", {})

        module_totals: dict[str, dict[str, float | int]] = {}
        for filepath, fdata in files.items():
            if not filepath.startswith("src/"):
                continue
            parts = filepath.split("/")
            mod_key = "/".join(parts[:3]) if len(parts) > 3 else "/".join(parts[:2])
            if mod_key not in module_totals:
                module_totals[mod_key] = {"statements": 0, "covered": 0}
            summary = fdata.get("summary", {})
            module_totals[mod_key]["statements"] += summary.get("num_statements", 0)
            module_totals[mod_key]["covered"] += summary.get("covered_lines", 0)

        table = Table(title="Coverage Summary (builder)")
        table.add_column("Module", style="cyan")
        table.add_column("Statements", justify="right")
        table.add_column("Covered", justify="right")
        table.add_column("Percent", justify="right")

        for mod_key, mtotals in sorted(module_totals.items()):
            stmts = mtotals["statements"]
            covered = mtotals["covered"]
            pct = (covered / stmts * 100) if stmts > 0 else 0.0
            style = "green" if pct >= 75 else "red"
            table.add_row(mod_key, str(stmts), str(covered), f"[{style}]{pct:.1f}%[/]")

        console.print()
        console.print(table)

        cov_path.unlink(missing_ok=True)

    except (json.JSONDecodeError, KeyError) as exc:
        console.print(f"[yellow]Could not parse coverage.json: {exc}[/yellow]")


def _generate_html_report(
    org_id: str, output: str, test_file: Path, passed: bool
) -> None:
    """Generate an optional HTML integrity report."""
    report_dir = Path(__file__).resolve().parent.parent.parent.parent / "reports"
    report_dir.mkdir(exist_ok=True)

    timestamp = __import__("datetime").datetime.now().strftime("%Y%m%d_%H%M%S")
    report_path = report_dir / f"builder_report_{timestamp}.html"

    status_text = "PASSED" if passed else "FAILED"

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Builder Integrity Report — {timestamp}</title>
    <style>
        body {{ font-family: 'Segoe UI', system-ui, sans-serif; max-width: 900px; margin: 2rem auto; padding: 0 1rem; }}
        h1 {{ color: #1a1a2e; }}
        .summary {{ padding: 1rem; border-radius: 8px; margin: 1rem 0; }}
        .pass {{ background: #d4edda; color: #155724; }}
        .fail {{ background: #f8d7da; color: #721c24; }}
        pre {{ background: #f5f5f5; padding: 1rem; border-radius: 4px; overflow-x: auto; }}
        table {{ width: 100%; border-collapse: collapse; margin-top: 1rem; }}
        th, td {{ border: 1px solid #ddd; padding: 0.5rem; text-align: left; }}
        th {{ background: #1a1a2e; color: white; }}
    </style>
</head>
<body>
    <h1>Builder Integrity Report</h1>
    <p><strong>Org ID:</strong> {org_id}</p>
    <p><strong>Timestamp:</strong> {timestamp}</p>
    <p><strong>Test file:</strong> {test_file}</p>
    <div class="summary {"pass" if passed else "fail"}">
        <strong>Status: {status_text}</strong>
    </div>
    <h2>Output</h2>
    <pre>{__import__("html").escape(output)}</pre>
</body>
</html>"""

    report_path.write_text(html)
    console.print(f"[green]HTML report saved:[/green] {report_path}")


if __name__ == "__main__":
    test_builder_app()
