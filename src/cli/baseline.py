"""src/cli/baseline.py — Implementation of 'fap baseline-check' command.

DX Tooling: Ejecuta verificaciones P0.1-P0.5 en secuencia:
  P0.1: pytest --collect-only (importabilidad)
  P0.2: pytest tests/ excluyendo latency test
  P0.3: ruff check src/ tests/
  P0.4: tool_registry.list_tools()
  P0.5: pytest --fixtures
Reporte consolidado con pass/fail por sub-paso. Gate check automatico.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

console = Console()

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


def _run_cmd(cmd: list[str], timeout: int = 120) -> tuple[bool, str]:
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=str(PROJECT_ROOT),
        )
        output = result.stdout + result.stderr
        return result.returncode == 0, output
    except subprocess.TimeoutExpired:
        return False, f"Command timed out after {timeout}s"
    except Exception as e:
        return False, str(e)


def _check_p0_1_importability() -> tuple[bool, str]:
    """P0.1: Verificar importabilidad via pytest --collect-only."""
    console.print("[cyan]P0.1: Verificando importabilidad (pytest --collect-only)...[/cyan]")
    passed, output = _run_cmd(["uv", "run", "pytest", "--collect-only", "-q", "--no-header"])
    if passed:
        console.print("[green]  [OK] Todos los modulos importan correctamente[/green]")
    else:
        console.print("[red]  [FAIL] Errores de import detectados[/red]")
    return passed, output


def _check_p0_2_existing_suite() -> tuple[bool, str]:
    """P0.2: Ejecutar suite existente excluyendo test de latencia."""
    console.print("[cyan]P0.2: Ejecutando suite existente (excluyendo latency)...[/cyan]")
    passed, output = _run_cmd(
        ["uv", "run", "pytest", "tests/", "-k", "not latency", "-q", "--no-header", "--tb=short"],
        timeout=300,
    )
    if passed:
        console.print("[green]  [OK] Suite existente pasa 100%[/green]")
    else:
        console.print("[red]  [FAIL] Fallos en suite existente[/red]")
    return passed, output


def _check_p0_3_lint() -> tuple[bool, str]:
    """P0.3: Verificar lint con ruff."""
    console.print("[cyan]P0.3: Verificando lint (ruff check src/ tests/)...[/cyan]")
    passed, output = _run_cmd(["uv", "run", "ruff", "check", "src/", "tests/"])
    if passed:
        console.print("[green]  [OK] 0 errores de lint[/green]")
    else:
        console.print("[red]  [FAIL] Errores de lint detectados[/red]")
    return passed, output


def _check_p0_4_tool_registry() -> tuple[bool, str]:
    """P0.4: Verificar tool_registry.list_tools()."""
    console.print("[cyan]P0.4: Verificando tool_registry.list_tools()...[/cyan]")
    try:
        from src.tools.registry import tool_registry

        tools = tool_registry.list_tools()
        if tools:
            console.print(f"[green]  [OK] Tools registradas: {len(tools)}[/green]")
            for t in tools:
                console.print(f"       - {t}")
            return True, f"Tools: {', '.join(tools)}"
        else:
            console.print("[yellow]  [WARN] tool_registry.list_tools() retorno vacio[/yellow]")
            return True, "Empty tool list"
    except Exception as e:
        console.print(f"[red]  [FAIL] Error accediendo tool_registry: {e}[/red]")
        return False, str(e)


def _check_p0_5_fixtures() -> tuple[bool, str]:
    """P0.5: Verificar fixtures disponibles."""
    console.print("[cyan]P0.5: Verificando fixtures via pytest --fixtures...[/cyan]")
    passed, output = _run_cmd(
        ["uv", "run", "pytest", "--fixtures", "-q", "--no-header"],
        timeout=60,
    )
    key_fixtures = [
        "sample_org_id",
        "mock_service_client",
        "mock_tenant_client",
        "global_llm_mock",
        "mock_mcp_pool",
    ]
    found = [f for f in key_fixtures if f in output]
    missing = [f for f in key_fixtures if f not in output]
    if not missing:
        console.print(f"[green]  [OK] {len(found)}/{len(key_fixtures)} fixtures clave encontradas[/green]")
    else:
        console.print(f"[yellow]  [WARN] Fixtures faltantes: {', '.join(missing)}[/yellow]")
    return passed, output


def baseline_check(
    audit_tools: bool = typer.Option(
        False, "--audit-tools", help="Incluye auditoria detallada de tools"
    ),
) -> None:
    """Ejecuta verificaciones P0.1-P0.5 para establecer linea base.

    Reporta pass/fail por sub-paso y determina si el GATE esta verde.
    """
    console.print(
        "\n"
        + "=" * 50
        + "\n  FAP Baseline Check — Paso 0: Auditoria de Linea Base\n"
        + "=" * 50
        + "\n",
        style="bold cyan",
    )

    results: dict[str, tuple[bool, str]] = {}

    # P0.1: Importabilidad
    p0_1_pass, p0_1_out = _check_p0_1_importability()
    results["P0.1 (importabilidad)"] = (p0_1_pass, p0_1_out[:500])

    # P0.2: Suite existente
    p0_2_pass, p0_2_out = _check_p0_2_existing_suite()
    results["P0.2 (suite existente)"] = (p0_2_pass, p0_2_out[:500])

    # P0.3: Lint
    p0_3_pass, p0_3_out = _check_p0_3_lint()
    results["P0.3 (lint)"] = (p0_3_pass, p0_3_out[:500])

    # P0.4: Tool registry
    p0_4_pass, p0_4_out = _check_p0_4_tool_registry()
    results["P0.4 (tool registry)"] = (p0_4_pass, p0_4_out[:500])

    # P0.5: Fixtures
    p0_5_pass, p0_5_out = _check_p0_5_fixtures()
    results["P0.5 (fixtures)"] = (p0_5_pass, p0_5_out[:500])

    if audit_tools:
        console.print("\n[bold cyan]Auditoria detallada de tools:[/bold cyan]")
        try:
            from src.tools.registry import tool_registry

            tools = tool_registry.list_tools()
            for t in tools:
                meta = tool_registry.get_metadata(t)
                if meta:
                    console.print(f"  - [bold]{t}[/bold]: {meta.description}")
        except Exception as e:
            console.print(f"[red]  Error en auditoria: {e}[/red]")

    # Reporte consolidado
    console.print("\n[bold]Resumen Baseline Check:[/bold]\n")

    table = Table(title="Resultados Paso 0")
    table.add_column("Sub-paso", style="cyan")
    table.add_column("Estado", style="green")

    all_pass = True
    for name, (passed, _) in results.items():
        status = "[PASS]" if passed else "[FAIL]"
        table.add_row(name, status)
        if not passed:
            all_pass = False

    console.print(table)

    console.print("\n" + "=" * 50)

    if all_pass:
        console.print("\n[bold green]  GATE: [PASS] Linea base establecida. Continuar a Paso 1.[/bold green]")
    else:
        console.print("\n[bold red]  GATE: [FAIL] NO PASADO. Revisar errores antes de continuar.[/bold red]")

    console.print("\n" + "=" * 50 + "\n")

    if not all_pass:
        console.print("[yellow]Detalle de fallos:[/yellow]")
        for name, (passed, output) in results.items():
            if not passed:
                console.print(f"\n[bold]{name}[/bold]:")
                console.print(output[:1000])

        raise typer.Exit(code=1)
