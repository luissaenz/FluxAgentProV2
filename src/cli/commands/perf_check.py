from __future__ import annotations

import json
import re
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

console = Console()

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
PERF_TEST_FILE = PROJECT_ROOT / "tests" / "stress" / "test_performance.py"
REPORTS_DIR = PROJECT_ROOT / "reports"

BENCH_THRESHOLDS: dict[str, float] = {
    "resolve_tools_50": 0.10,
    "workflow_definition_10x5": 0.050,
    "sanitize_1mb": 0.50,
    "circuit_closed": 0.001,
    "circuit_open": 0.001,
}

BENCH_TIME_RE = re.compile(r"BENCH_TIME:\s+(\S+)\s+([\d.]+)s")
PYTEST_TEST_RE = re.compile(r"::Test\w+::(\w+)\s+(PASSED|FAILED|ERROR)?")
PYTEST_SUMMARY_RE = re.compile(r"==\s+(\d+)\s+passed.*?in\s+([\d.]+)s")


def _ensure_reports_dir() -> None:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)


def _warmup() -> None:
    cmd = [
        sys.executable, "-m", "pytest", str(PERF_TEST_FILE),
        "--tb=short", "-q", "--no-header",
    ]
    for i in range(3):
        console.print(f"  Warmup {i+1}/3...", end=" ")
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        console.print("OK" if r.returncode == 0 else "WARN")


def _run_and_parse(verbose: bool) -> tuple[dict[str, dict], int, float]:
    cmd = [
        sys.executable, "-m", "pytest", str(PERF_TEST_FILE),
        "-v", "--tb=short", "--no-header", "-s",
    ]
    if verbose:
        console.print(f"\n[cyan]Running: {' '.join(cmd[:4])} ...[/cyan]")

    start = time.time()
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    elapsed = time.time() - start
    output = r.stdout + r.stderr

    if verbose:
        console.print(output)

    tests: dict[str, dict] = {}

    for line in output.splitlines():
        tm = PYTEST_TEST_RE.search(line)
        if tm:
            tname = tm.group(1)
            status = tm.group(2)
            tests[tname] = {"passed": status == "PASSED" if status else False, "elapsed": None}

            btm = BENCH_TIME_RE.search(line)
            if btm:
                tests[tname]["elapsed"] = float(btm.group(2))
            continue

        # Handle "PASSED"/"FAILED" on next line when test used -s output
        if line.strip() in ("PASSED", "FAILED", "ERROR"):
            for _, tdata in reversed(list(tests.items())):
                if tdata["elapsed"] is not None and tdata["passed"] is False:
                    tdata["passed"] = line.strip() == "PASSED"
                    break

    sm = PYTEST_SUMMARY_RE.search(output)
    summary_passed = int(sm.group(1)) if sm else 0

    return tests, summary_passed, elapsed


def _find_threshold(test_name: str) -> float | None:
    for key, thr in BENCH_THRESHOLDS.items():
        if key in test_name:
            return thr
    return None


def _build_report(tests: dict, summary_passed: int, total_elapsed: float) -> dict:
    now = datetime.now(timezone.utc)
    results = []
    all_pass = True
    for tn, td in tests.items():
        passed = td["passed"]
        if not passed:
            all_pass = False
        results.append({
            "test": tn,
            "passed": passed,
            "elapsed_seconds": td["elapsed"],
            "threshold_seconds": _find_threshold(tn),
        })
    return {
        "timestamp": now.isoformat(),
        "suite": {
            "passed": all_pass and summary_passed == len(tests),
            "total_tests": len(tests),
            "passed_tests": summary_passed,
            "failed_tests": len(tests) - summary_passed,
            "total_elapsed_seconds": round(total_elapsed, 3),
        },
        "benchmarks": results,
    }


def _load_baseline() -> dict | None:
    p = REPORTS_DIR / "perf_baseline.json"
    if p.exists():
        try:
            return json.loads(p.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return None
    return None


def _compare(report: dict, baseline: dict, verbose: bool) -> list[dict]:
    regressions: list[dict] = []
    base_map = {b["test"]: b for b in baseline.get("benchmarks", [])}
    for bench in report["benchmarks"]:
        base = base_map.get(bench["test"])
        if not base or bench["elapsed_seconds"] is None or base["elapsed_seconds"] is None:
            continue
        diff = bench["elapsed_seconds"] - base["elapsed_seconds"]
        pct = (diff / base["elapsed_seconds"]) * 100 if base["elapsed_seconds"] > 0 else 0
        if pct > 20:
            regressions.append({
                "test": bench["test"],
                "baseline_seconds": base["elapsed_seconds"],
                "current_seconds": bench["elapsed_seconds"],
                "increase_pct": round(pct, 1),
            })
        if verbose:
            s = "[red]REGRESSION[/red]" if pct > 20 else "[green]OK[/green]"
            console.print(
                f"  {bench['test']}: {base['elapsed_seconds']*1000:.1f}ms -> "
                f"{bench['elapsed_seconds']*1000:.1f}ms ({pct:+.1f}%) {s}"
            )
    return regressions


def perf_check(
    baseline: bool = typer.Option(False, "--baseline", help="Save as baseline"),
    compare: bool = typer.Option(False, "--compare", help="Compare vs baseline"),
    json_output: bool = typer.Option(False, "--json", help="JSON output"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Verbose output"),
    skip_warmup: bool = typer.Option(False, "--no-warmup", help="Skip warmup"),
) -> None:
    """Ejecutar benchmarks P6.1-P6.4. Verifica thresholds, genera reporte."""
    console.print(
        "\n" + "=" * 60
        + "\n  FAP Perf Check — Paso 6: Performance Benchmarks\n"
        + "=" * 60 + "\n",
        style="bold cyan",
    )
    _ensure_reports_dir()

    if not PERF_TEST_FILE.exists():
        console.print(f"[red]Error:[/red] File not found: {PERF_TEST_FILE}")
        raise typer.Exit(code=1)

    if not skip_warmup:
        console.print("\n[cyan]Warmup (3 iterations)...[/cyan]")
        _warmup()

    console.print("\n[cyan]Running benchmarks...[/cyan]")
    tests, summary_passed, total_elapsed = _run_and_parse(verbose)

    if not tests:
        console.print("[red]Error:[/red] No tests parsed.")
        raise typer.Exit(code=1)

    report = _build_report(tests, summary_passed, total_elapsed)

    report_path = REPORTS_DIR / "perf_report.json"
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    console.print(f"[dim]Report saved: {report_path}[/dim]")

    if baseline:
        bp = REPORTS_DIR / "perf_baseline.json"
        bp.write_text(json.dumps(report, indent=2), encoding="utf-8")
        console.print(f"[green]Baseline saved: {bp}[/green]")

    regressions = []
    if compare:
        base = _load_baseline()
        if base:
            console.print("\n[cyan]Comparing with baseline...[/cyan]")
            regressions = _compare(report, base, verbose)
        else:
            console.print("[yellow]No baseline. Run --baseline first.[/yellow]")

    console.print("\n" + "=" * 60)
    table = Table(title="Performance Benchmarks Results")
    table.add_column("Benchmark", style="cyan")
    table.add_column("Status", style="green")
    table.add_column("Time", style="yellow")
    table.add_column("Threshold", style="magenta")

    for bench in report["benchmarks"]:
        status = "[green]PASS[/green]" if bench["passed"] else "[red]FAIL[/red]"
        elapsed = f"{bench['elapsed_seconds']*1000:.2f}ms" if bench["elapsed_seconds"] is not None else "N/A"
        threshold = bench.get("threshold_seconds")
        tstr = f"{threshold*1000:.0f}ms" if threshold else "N/A"
        table.add_row(bench["test"], status, elapsed, tstr)

    console.print(table)

    suite = report["suite"]
    style = "green" if suite["passed"] else "red"
    console.print(
        f"\n[{style}]Resumen: {suite['passed_tests']}/{suite['total_tests']} "
        f"({suite['total_elapsed_seconds']}s)[/{style}]"
    )

    if regressions:
        console.print("\n[red]Regresiones:[/red]")
        for r in regressions:
            console.print(
                f"  [red]{r['test']}:[/red] "
                f"{r['baseline_seconds']*1000:.1f}ms -> {r['current_seconds']*1000:.1f}ms "
                f"({r['increase_pct']:+.1f}%)"
            )

    if json_output:
        console.print(json.dumps(report, indent=2))

    if not suite["passed"] or regressions:
        raise typer.Exit(code=1)
    raise typer.Exit(code=0)


if __name__ == "__main__":
    perf_check()
