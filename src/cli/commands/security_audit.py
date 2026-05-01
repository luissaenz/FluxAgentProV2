"""src/cli/commands/security_audit.py — 'fap security-audit' command.

Runs all SE5.x security tests with category filtering and JSON output.
DX Tooling for Paso 5 Security Hardening — dogfooding obligatorio.
"""

from __future__ import annotations

import json as json_mod
import re
import subprocess
import sys
from pathlib import Path
from typing import Optional

import typer
from rich import print
from rich.console import Console

console = Console()

PROJECT_ROOT = Path(__file__).resolve().parents[3]

CATEGORY_MARKERS: dict[str, list[str]] = {
    "imports": [
        "test_se5_1_import_subprocess",
        "test_se5_2_import_shutil",
        "test_se5_3_import_ctypes",
        "test_se5_4_import_socket",
        "test_se5_5_import_gc",
        "test_se5_6_import_inspect",
        "test_se5_7_import_requests",
    ],
    "calls": [
        "test_se5_8_forbidden_import_call",
        "test_se5_9_forbidden_compile",
        "test_se5_10_forbidden_exec",
    ],
    "async": [
        "test_se5_11_async_non_system_blocked",
        "test_se5_12_async_system_allowed",
    ],
    "regresion": [
        "test_se5_13_execute_blocks_forbidden_import",
        "test_se5_14_execute_blocks_builtins_bypass",
        "test_se5_15_verify_compilation_blocks_injected_import",
        "test_se5_16_execute_blocks_indirect_import_bypass",
    ],
    "escape": [
        "test_se5_17_importlib_bypass",
        "test_se5_18_hex_exec_bypass",
    ],
}

ALL_TESTS = [
    test for tests in CATEGORY_MARKERS.values() for test in tests
]

SECURITY_TEST_FILES = [
    "tests/unit/test_security_guard.py",
    "tests/unit/test_security_guard_escape.py",
]


def _resolve_project_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _parse_pytest_output(stdout: str) -> dict:
    passed = 0
    failed = 0
    errors = 0
    failures: list[str] = []

    for line in stdout.splitlines():
        if re.match(r"^.*PASSED\s*\[", line) or line.strip().endswith("PASSED"):
            passed += 1
        elif re.match(r"^.*FAILED\s*\[", line) or line.strip().endswith("FAILED"):
            failed += 1
        elif re.match(r"^.*ERROR\s*\[", line) or line.strip().endswith("ERROR"):
            errors += 1

    for line in stdout.splitlines():
        if "FAILED" in line:
            match = re.search(r"(test_se5_\w+)", line)
            if match:
                failures.append(match.group(1))

    return {
        "passed": passed,
        "failed": failed,
        "errors": errors,
        "total": passed + failed + errors,
        "failures": failures,
    }


def _run_tests(kw_filter: str = "", json_output: bool = False) -> dict:
    project_root = _resolve_project_root()

    test_files = SECURITY_TEST_FILES.copy()

    missing = [f for f in test_files if not (project_root / f).exists()]
    if missing:
        msg = f"Faltan archivos de test: {missing}"
        if json_output:
            return {"error": msg}
        print(f"[red]Error:[/red] {msg}")
        raise typer.Exit(code=1)

    cmd: list[str] = [sys.executable, "-m", "pytest", "-v", "--tb=short"]

    if kw_filter:
        cmd.extend(["-k", kw_filter])

    for tf in test_files:
        cmd.append(str(project_root / tf))

    result = subprocess.run(
        cmd,
        cwd=str(project_root),
        capture_output=True,
        text=True,
    )

    parsed = _parse_pytest_output(result.stdout + result.stderr)

    if json_output:
        parsed["exit_code"] = result.returncode
        parsed["categories"] = {k: len(v) for k, v in CATEGORY_MARKERS.items()}
        print(json_mod.dumps(parsed, indent=2))
        raise typer.Exit(code=result.returncode)

    if result.returncode == 0:
        print(f"\n[bold green]SECURITY-AUDIT PASSED ({parsed['passed']}/{parsed['total']} tests)[/bold green]")
    else:
        print(f"\n[bold red]SECURITY-AUDIT FAILED ({parsed['failed']} failures, {parsed['errors']} errors)[/bold red]")
        if parsed["failures"]:
            print("[red]Failing tests:[/red]")
            for f in parsed["failures"]:
                print(f"  [red]✗[/red] {f}")

    raise typer.Exit(code=result.returncode)


def security_audit(
    category: Optional[str] = typer.Option(
        None,
        "--category",
        "-c",
        help="Filter by category: imports, calls, async, escape, regresion",
    ),
    json_output: bool = typer.Option(
        False,
        "--json",
        "-j",
        help="Output JSON for CI integration",
    ),
):
    """Run all SE5.x security tests or filter by category.

    Ejemplos:
        fap security-audit                    # todos los tests SE5.x
        fap security-audit --category imports  # solo imports prohibidos
        fap security-audit --category calls    # solo calls prohibidos
        fap security-audit --json              # output JSON para CI
    """
    if category:
        if category not in CATEGORY_MARKERS:
            print(f"[red]Error:[/red] Categoria '{category}' no valida.")
            print(f"Categorias disponibles: {list(CATEGORY_MARKERS.keys())}")
            raise typer.Exit(code=1)

        markers = CATEGORY_MARKERS[category]
        kw_filter = " or ".join(markers)
        if not json_output:
            print(f"\n[bold cyan]fap security-audit --category {category}[/bold cyan]")
            print(f"[dim]Tests: {', '.join(markers)}[/dim]\n")
    else:
        kw_filter = " or ".join(ALL_TESTS)
        if not json_output:
            print("\n[bold cyan]fap security-audit[/bold cyan]")
            print(f"[dim]Todos los tests SE5.x ({len(ALL_TESTS)} tests)[/dim]\n")

    _run_tests(kw_filter=kw_filter, json_output=json_output)
