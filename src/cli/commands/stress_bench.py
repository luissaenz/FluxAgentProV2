"""src/cli/commands/stress_bench.py — 'fap stress-bench' command.

DX Tooling: Genera fixtures masivos, ejecuta suite stress con métricas.
Paso 4: Estrés y Condiciones de Borde.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table

console = Console()

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
STRESS_DIR = PROJECT_ROOT / "tests" / "stress"


def _parse_size(size_str: str) -> int:
    """Parse human-readable size (10MB, 5MB, 1GB) to bytes."""
    size_str = size_str.strip().upper()
    if size_str.endswith("GB"):
        return int(float(size_str[:-2]) * 1024**3)
    if size_str.endswith("MB"):
        return int(float(size_str[:-2]) * 1024**2)
    if size_str.endswith("KB"):
        return int(float(size_str[:-2]) * 1024)
    return int(size_str)


def _ensure_stress_dir() -> None:
    """Create tests/stress/ + __init__.py if missing."""
    STRESS_DIR.mkdir(parents=True, exist_ok=True)
    init_file = STRESS_DIR / "__init__.py"
    if not init_file.exists():
        init_file.write_text('"""Stress and edge-case tests — Paso 4."""\n')
        console.print(f"[green]Created {init_file}[/green]")


def _build_test_env(
    tools: int,
    workflows: int,
    sanitizer_size: str,
    json_depth: int,
) -> dict:
    """Build environment variables for test parameterisation."""
    env = os.environ.copy()
    env["STRESS_TOOLS_COUNT"] = str(tools)
    env["STRESS_WORKFLOWS_COUNT"] = str(workflows)
    env["STRESS_SANITIZER_SIZE"] = str(_parse_size(sanitizer_size))
    env["STRESS_JSON_DEPTH"] = str(json_depth)
    return env


def _run_suite(test_filter: Optional[str], env: dict) -> tuple[bool, str, float]:
    """Run pytest tests/stress/ and return (passed, output, elapsed_seconds)."""
    cmd = [
        sys.executable,
        "-m",
        "pytest",
        str(STRESS_DIR),
        "-v",
        "--tb=short",
        "--no-header",
    ]
    if test_filter:
        cmd.extend(["-k", test_filter])

    console.print(f"\n[cyan]Running: {' '.join(cmd[:4])} ...[/cyan]")
    start = time.time()
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=300, env=env)
    elapsed = time.time() - start
    output = result.stdout + result.stderr
    passed = result.returncode == 0
    return passed, output, elapsed


_PYTEST_LINE_RE = re.compile(
    r"::([\w_]+)\s+(PASSED|FAILED|ERROR)\b",
)


def _parse_pytest_output(output: str) -> dict[str, dict]:
    """Parse pytest -v output to extract per-test results.

    Returns mapping of test_name -> {"passed": bool, "time": str or None}.
    """
    tests: dict[str, dict] = {}
    for line in output.splitlines():
        m = _PYTEST_LINE_RE.search(line)
        if m:
            test_name = m.group(1)
            tests[test_name] = {"passed": m.group(2) == "PASSED", "time": None}
    return tests


def _build_report(
    passed: bool,
    output: str,
    elapsed: float,
    tests: dict,
    env: dict,
    iterations: int,
) -> dict:
    """Build the full report dict."""
    passed_count = sum(1 for t in tests.values() if t["passed"])
    total = len(tests)
    return {
        "timestamp": datetime.utcnow().isoformat(),
        "parameters": {
            "tools": env.get("STRESS_TOOLS_COUNT", "500"),
            "workflows": env.get("STRESS_WORKFLOWS_COUNT", "50"),
            "sanitizer_size": env.get("STRESS_SANITIZER_SIZE", "10485760"),
            "json_depth": env.get("STRESS_JSON_DEPTH", "20"),
            "iterations": iterations,
        },
        "suite": {
            "passed": passed,
            "total_tests": total,
            "passed_tests": passed_count,
            "failed_tests": total - passed_count,
            "elapsed_seconds": round(elapsed, 2),
        },
        "tests": tests,
        "raw_output": output[-2000:],
    }


def stress_bench(
    tools: int = typer.Option(
        500, "--tools", "-t", help="Number of mock tools to register",
    ),
    workflows: int = typer.Option(
        50, "--workflows", "-w", help="Number of concurrent workflows",
    ),
    sanitizer_size: str = typer.Option(
        "10MB", "--sanitizer-size", "-s", help="String size for sanitizer stress test",
    ),
    json_depth: int = typer.Option(
        20, "--json-depth", "-d", help="Nesting depth for JSON stress test",
    ),
    test: Optional[str] = typer.Option(
        None, "--test", "-k", help="Run specific test (e.g. S4.1)",
    ),
    iterations: int = typer.Option(
        1, "--iterations", "-i", help="Number of iterations to run",
    ),
    benchmark: bool = typer.Option(
        False, "--benchmark", help="Save benchmark baseline",
    ),
) -> None:
    """Ejecutar suite de estrés y condiciones de borde (Paso 4).

    Genera fixtures masivos automáticamente, ejecuta tests S4.1-S4.7,
    y reporta métricas de tiempo y memoria.
    """
    console.print(
        "\n"
        + "=" * 60
        + "\n  FAP Stress Bench — Paso 4: Estrés y Condiciones de Borde\n"
        + "=" * 60
        + "\n",
        style="bold cyan",
    )

    _ensure_stress_dir()

    console.print("\n[cyan]Parameters:[/cyan]")
    console.print(f"  Tools: {tools}")
    console.print(f"  Workflows: {workflows}")
    console.print(f"  Sanitizer size: {sanitizer_size}")
    console.print(f"  JSON depth: {json_depth}")
    console.print(f"  Iterations: {iterations}")

    env = _build_test_env(tools, workflows, sanitizer_size, json_depth)

    iteration_results: list[dict] = []
    all_pass = True

    for i in range(iterations):
        if iterations > 1:
            console.print(f"\n[bold]Iteration {i + 1}/{iterations}[/bold]")
        passed, output, elapsed = _run_suite(test, env)
        tests = _parse_pytest_output(output)
        report = _build_report(passed, output, elapsed, tests, env, iterations)

        iteration_results.append(report)
        if not passed:
            all_pass = False

        # Display suite summary
        suite = report["suite"]
        status_style = "green" if suite["passed"] else "red"
        console.print(
            f"\n[{status_style}]Suite: "
            f"{'PASSED' if suite['passed'] else 'FAILED'} "
            f"({suite['passed_tests']}/{suite['total_tests']} tests, "
            f"{suite['elapsed_seconds']}s)[/{status_style}]"
        )

    # Final table
    console.print("\n" + "=" * 60)
    table = Table(title="Stress Bench Results")
    table.add_column("Test", style="cyan")
    table.add_column("Status", style="green")
    table.add_column("Iterations", style="yellow")

    all_test_names: set = set()
    for rep in iteration_results:
        all_test_names.update(rep["tests"].keys())

    for test_name in sorted(all_test_names):
        results_for_test = []
        for rep in iteration_results:
            t = rep["tests"].get(test_name)
            results_for_test.append(t["passed"] if t else False)
        status = (
            "[green]PASS[/green]"
            if all(results_for_test)
            else "[red]FAIL[/red]"
        )
        table.add_row(
            test_name,
            status,
            str(len(results_for_test)),
        )

    console.print(table)

    # Summary
    passed_total = sum(
        1 for rep in iteration_results for t in rep["tests"].values() if t["passed"]
    )
    total_tests = sum(len(rep["tests"]) for rep in iteration_results)
    console.print(
        f"\n[bold]Resumen: {passed_total}/{total_tests} tests aprobados "
        f"en {iterations} iteracion(es)[/bold]"
    )

    if benchmark:
        baseline_path = PROJECT_ROOT / "stress_bench_baseline.json"
        baseline_path.write_text(
            json.dumps(
                {
                    "timestamp": datetime.utcnow().isoformat(),
                    "parameters": {
                        "tools": tools,
                        "workflows": workflows,
                        "sanitizer_size": sanitizer_size,
                        "json_depth": json_depth,
                    },
                    "results": iteration_results,
                },
                indent=2,
            )
        )
        console.print(f"[green]Baseline saved to: {baseline_path}[/green]")

    if not all_pass:
        console.print(
            "\n[yellow]Last failure output:[/yellow]"
        )
        console.print(iteration_results[-1]["raw_output"][:3000])
        raise typer.Exit(code=1)

    raise typer.Exit(code=0)


if __name__ == "__main__":
    stress_bench()
