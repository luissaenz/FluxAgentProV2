"""src/cli/commands/test_step.py — Implementation of 'fap test-step' command.

DX Tooling: Ejecuta tests de un paso específico del plan de certificación.
Dogfooding obligatorio — el implementador DEBE usar esta herramienta.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path
from typing import Optional

import typer
from rich import print
from rich.console import Console

console = Console()

# ── Paso → archivos de test ──────────────────────────────────────

STEP_TEST_FILES: dict[int, list[str]] = {
    1: [
        "tests/unit/test_mcp_pool_circuit.py",
        "tests/unit/test_service_connector.py",
        "tests/unit/test_approval_operators.py",
        "tests/unit/test_sanitizer.py",
    ],
    2: [
        "tests/integration/test_mcp_resilience.py",
        "tests/integration/test_handover_real.py",
        "tests/unit/test_approval_operators.py",
    ],
}

# ── Paso → archivos para cobertura ──────────────────────────────

STEP_COVERAGE_FILES: dict[int, list[str]] = {
    1: [
        "src/tools/mcp_pool.py",
        "src/tools/service_connector.py",
        "src/flows/dynamic_flow.py",
        "src/mcp/sanitizer.py",
    ],
    2: [
        "src/tools/mcp_pool.py",
        "src/flows/dynamic_flow.py",
    ],
}

# ── Thresholds de cobertura por paso ────────────────────────────

STEP_COVERAGE_THRESHOLDS: dict[int, dict[str, int]] = {
    1: {
        "src/tools/mcp_pool.py": 80,
        "src/tools/service_connector.py": 70,
        "src/mcp/sanitizer.py": 100,
    },
}


def _resolve_project_root() -> Path:
    """Resolve project root from this file's location."""
    return Path(__file__).resolve().parents[3]


def test_step(
    step: int = typer.Argument(
        ...,
        help="Número de paso a ejecutar (ej: 1)",
    ),
    cov: bool = typer.Option(
        False,
        "--cov",
        help="Ejecutar con cobertura por archivo",
    ),
    verbose: bool = typer.Option(
        True,
        "--verbose/--no-verbose",
        "-v/-q",
        help="Output detallado de pytest",
    ),
    fail_fast: bool = typer.Option(
        False,
        "--fail-fast",
        "-x",
        help="Detener en el primer fallo",
    ),
    keep_going: bool = typer.Option(
        False,
        "--keep-going",
        help="Intentar continuar tras errores",
    ),
):
    """Ejecutar tests de un paso del plan de certificación.

    Ejemplos:
        fap test-step 1              # Corre los 27 tests del Paso 1
        fap test-step 1 --cov        # Añade cobertura por archivo
        fap test-step 1 --fail-fast  # Detener en primer fallo
    """
    project_root = _resolve_project_root()

    if step not in STEP_TEST_FILES:
        print(f"[red]Error:[/red] Paso '{step}' no definido.")
        print(f"Pasos disponibles: {list(STEP_TEST_FILES.keys())}")
        raise typer.Exit(code=1)

    test_files = STEP_TEST_FILES[step]
    coverage_files = STEP_COVERAGE_FILES.get(step, [])
    thresholds = STEP_COVERAGE_THRESHOLDS.get(step, {})

    # Verificar archivos existen
    missing = [f for f in test_files if not (project_root / f).exists()]
    if missing:
        print("[red]Error:[/red] Faltan archivos de test:")
        for f in missing:
            print(f"  - {f}")
        raise typer.Exit(code=1)

    # ── Construir comando pytest ─────────────────────────────────
    cmd: list[str] = [sys.executable, "-m", "pytest"]

    if verbose:
        cmd.append("-v")
    cmd.append("--tb=short")

    if fail_fast:
        cmd.append("-x")
    elif keep_going:
        cmd.append("--continue-on-collection-errors")

    # Cobertura
    coverage_data_file = None
    if cov:
        coverage_data_file = str(
            project_root / ".coverage" / f".coverage.step_{step}"
        )
        cmd.append(f"--cov-config={project_root / 'pyproject.toml'}")

    # Añadir archivos de test
    for tf in test_files:
        cmd.append(str(project_root / tf))

    if cov:
        for cf in coverage_files:
            cmd.append(f"--cov={cf}")

    # ── Mostrar resumen ─────────────────────────────────────────

    print(f"\n[bold cyan]fap test-step {step}[/bold cyan]")
    print(f"[dim]Paso {step}: {len(test_files)} archivos de test[/dim]")
    if cov:
        print(f"[dim]Cobertura: {len(coverage_files)} archivos fuente[/dim]")
    print()

    # ── Ejecutar ─────────────────────────────────────────────────

    env = {}
    if cov and coverage_data_file:
        env["COVERAGE_FILE"] = coverage_data_file

    result = subprocess.run(
        cmd,
        cwd=str(project_root),
        env={**os.environ, **env},
    )

    # ── Mostrar resultado ───────────────────────────────────────

    if result.returncode == 0:
        print(f"\n[bold green]Paso {step} PASSED — todos los tests OK[/bold green]")
    else:
        print(f"\n[bold red]Paso {step} FAILED — código salida {result.returncode}[/bold red]")

    # ── Validar thresholds de cobertura ─────────────────────────

    if cov and thresholds:
        _check_coverage_thresholds(project_root, step, thresholds)

    raise typer.Exit(code=result.returncode)


def _check_coverage_thresholds(
    project_root: Path,
    step: int,
    thresholds: dict[str, int],
) -> None:
    """Validate coverage thresholds for the step."""
    coverage_ok = True
    for file_path, min_pct in thresholds.items():
        actual_pct = _get_coverage_for_file(project_root, file_path, step)
        if actual_pct is not None and actual_pct < min_pct:
            print(
                f"[red]COBERTURA BAJO UMBRAL:[/red] "
                f"{file_path} → {actual_pct}% (mínimo {min_pct}%)"
            )
            coverage_ok = False

    if not coverage_ok:
        raise typer.Exit(code=2)


def _get_coverage_for_file(
    project_root: Path, file_path: str, step: int
) -> Optional[float]:
    """Read coverage percentage for a file from .coverage data."""
    import importlib.util

    try:
        spec = importlib.util.find_spec("coverage")
        if not spec:
            return None

        cov_module = importlib.util.import_module("coverage")

        coverage_data_file = project_root / ".coverage" / f".coverage.step_{step}"
        if not coverage_data_file.exists():
            return None

        cov = cov_module.Coverage(data_file=str(coverage_data_file))
        cov.load()

        analysis = cov.analysis2(str(project_root / file_path))
        if analysis is None:
            return None

        _, executable, _, missing, _ = analysis
        if not executable:
            return 100.0

        covered = len(executable) - len(missing)
        return (covered / len(executable)) * 100
    except Exception:
        return None


if __name__ == "__main__":
    test_step()
