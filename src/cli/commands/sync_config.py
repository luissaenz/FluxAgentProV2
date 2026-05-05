"""src/cli/commands/sync_config.py — 'fap sync-config' command.

Verifica/corrige desincronización entre proyecto-config.json,
phase-state.md y plan.md. Detecta drift en phase_name,
current_step y pipeline flags.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

console = Console()

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
CONFIG_PATH = PROJECT_ROOT / "proyecto-config.json"
PLAN_MD_PATH = PROJECT_ROOT / "DEVS" / "plan.md"
PLAN_JSON_PATH = PROJECT_ROOT / "DEVS" / "plan.json"
PHASE_STATE_PATH = PROJECT_ROOT / "DEVS" / "phase-state.md"

DISCREPANCIA_RE = re.compile(
    r"^- \*\*📝 CORRECCIÓN \([^)]+\):\*\*.*", re.MULTILINE
)


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _drift_report() -> list[dict]:
    """Detecta drift entre config y estado real del proyecto."""
    config = _load_json(CONFIG_PATH)
    plan_json_data = _load_json(PLAN_JSON_PATH)
    phase_state_text = PHASE_STATE_PATH.read_text(encoding="utf-8")
    plan_md_text = PLAN_MD_PATH.read_text(encoding="utf-8")
    plan_md_steps = len(re.findall(r"^## Paso \d+:", plan_md_text, re.MULTILINE))

    drift: list[dict] = []

    # 1. Verify phase_name
    expected_name = "patch_agents"
    actual_name = config.get("phase", {}).get("phase_name", "")
    if actual_name != expected_name:
        drift.append({
            "field": "phase.phase_name",
            "actual": actual_name,
            "expected": expected_name,
            "file": "proyecto-config.json",
            "fixable": True,
        })

    # 2. Verify current_step
    expected_step = "06-ExcelWriterTool"
    actual_step = config.get("phase", {}).get("current_step", "")
    if actual_step != expected_step:
        drift.append({
            "field": "phase.current_step",
            "actual": actual_step,
            "expected": expected_step,
            "file": "proyecto-config.json",
            "fixable": True,
        })

    # 3. Verify plan_json_steps_total
    expected_total = plan_md_steps
    actual_total = config.get("pipeline", {}).get("plan_json_steps_total", 0)
    if actual_total != expected_total:
        drift.append({
            "field": "pipeline.plan_json_steps_total",
            "actual": str(actual_total),
            "expected": str(expected_total),
            "file": "proyecto-config.json",
            "fixable": True,
        })

    # 4. Verify plan_json_steps_pending
    done_count = config.get("pipeline", {}).get("plan_json_steps_done", 0)
    expected_pending = expected_total - done_count
    actual_pending = config.get("pipeline", {}).get("plan_json_steps_pending", 0)
    if actual_pending != expected_pending:
        drift.append({
            "field": "pipeline.plan_json_steps_pending",
            "actual": str(actual_pending),
            "expected": str(expected_pending),
            "file": "proyecto-config.json",
            "fixable": True,
        })

    # 5. Verify plan.json has all steps from plan.md
    plan_json_steps = len(plan_json_data.get("steps", []))
    if plan_json_steps < plan_md_steps:
        missing = plan_md_steps - plan_json_steps
        drift.append({
            "field": "plan.json steps count",
            "actual": str(plan_json_steps),
            "expected": str(plan_md_steps),
            "file": "DEVS/plan.json",
            "fixable": False,
            "note": f"Faltan {missing} step(s). Agregar manualmente.",
        })

    # 6. Check phase-state.md for stale phase_name: "testing" references
    # that claim it's the current state (not historical)
    stale_refs = []
    for i, line in enumerate(phase_state_text.splitlines(), 1):
        if 'phase_name: "testing"' in line and (
            "aun" in line.lower()
            or "persiste" in line.lower()
            or "sigue" in line.lower()
            or "desactualizado" in line.lower()
            or "no existe" in line.lower()
        ):
            if "resuelto" in line.lower() or "corregido" in line.lower():
                continue
            stale_refs.append((i, line.strip()))
    if stale_refs:
        drift.append({
            "field": "phase-state.md stale refs",
            "actual": f"{len(stale_refs)} stale reference(s) to phase_name: testing",
            "expected": "0 stale references",
            "file": "DEVS/phase-state.md",
            "fixable": False,
            "note": f"Line(s): {', '.join(str(r[0]) for r in stale_refs)}",
        })

    return drift


def _apply_fixes(dry_run: bool = False) -> int:
    """Aplica fixes a proyecto-config.json. Retorna count de fixes."""
    config = _load_json(CONFIG_PATH)
    fixes = 0

    # Fix current_step
    if config.get("phase", {}).get("current_step") != "06-ExcelWriterTool":
        if dry_run:
            console.print(
                "  [yellow]~[/yellow] phase.current_step: "
                f"'{config['phase']['current_step']}' -> '06-ExcelWriterTool'"
            )
        else:
            config["phase"]["current_step"] = "06-ExcelWriterTool"
            console.print(
                "  [green]+[/green] phase.current_step -> '06-ExcelWriterTool'"
            )
        fixes += 1

    # Fix plan_json_steps_total
    plan_md_text = PLAN_MD_PATH.read_text(encoding="utf-8")
    plan_md_steps = len(re.findall(r"^## Paso \d+:", plan_md_text, re.MULTILINE))
    if config.get("pipeline", {}).get("plan_json_steps_total") != plan_md_steps:
        if dry_run:
            console.print(
                "  [yellow]~[/yellow] pipeline.plan_json_steps_total: "
                f"{config['pipeline']['plan_json_steps_total']} -> {plan_md_steps}"
            )
        else:
            config["pipeline"]["plan_json_steps_total"] = plan_md_steps
            console.print(
                f"  [green]+[/green] pipeline.plan_json_steps_total -> {plan_md_steps}"
            )
        fixes += 1

    # Fix plan_json_steps_pending = total - done
    done_count = config.get("pipeline", {}).get("plan_json_steps_done", 0)
    expected_pending = plan_md_steps - done_count
    actual_pending = config.get("pipeline", {}).get("plan_json_steps_pending", 0)
    if actual_pending != expected_pending:
        if dry_run:
            console.print(
                "  [yellow]~[/yellow] pipeline.plan_json_steps_pending: "
                f"{actual_pending} -> {expected_pending}"
            )
        else:
            config["pipeline"]["plan_json_steps_pending"] = expected_pending
            console.print(
                f"  [green]+[/green] pipeline.plan_json_steps_pending -> {expected_pending}"
            )
        fixes += 1

    if fixes and not dry_run:
        CONFIG_PATH.write_text(
            json.dumps(config, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )

    return fixes


def sync_config(
    check: bool = typer.Option(False, "--check", help="Detecta drift. Exit 0 si sync, 1 si no"),
    fix: bool = typer.Option(False, "--fix", help="Aplica correcciones a proyecto-config.json"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Muestra cambios sin aplicar"),
):
    """Verificar/corregir sincronización de proyecto-config.json con estado real del proyecto."""
    drift = _drift_report()

    if not drift:
        console.print("\n[green]+ 0 discrepancias. proyecto-config.json sincronizado.[/green]")
        if check:
            raise typer.Exit(code=0)
        return

    console.print(f"\n[red]{len(drift)} discrepancia(s) detectada(s):[/red]\n")
    tbl = Table(title="Discrepancias config vs estado real")
    tbl.add_column("Campo", style="cyan")
    tbl.add_column("Actual", style="red")
    tbl.add_column("Esperado", style="green")
    tbl.add_column("Archivo", style="yellow")
    for d in drift:
        note = d.get("note", "")
        expected_display = d["expected"]
        if note:
            expected_display += f" ({note})"
        tbl.add_row(d["field"], d["actual"], expected_display, d["file"])
    console.print(tbl)

    if fix:
        console.print("\n[yellow]Aplicando fixes a proyecto-config.json...[/yellow]")
        applied = _apply_fixes(dry_run=dry_run)
        if dry_run:
            console.print(f"\n[green]{applied} cambio(s) listo(s) para aplicar (dry-run).[/green]")
        else:
            console.print(f"\n[green]{applied} fix(es) aplicado(s).[/green]")
    else:
        fixable = sum(1 for d in drift if d.get("fixable"))
        manual = len(drift) - fixable
        console.print(
            f"\n[yellow]{fixable} fixeable(s) via --fix. "
            f"{manual} requiere(n) edición manual.[/yellow]"
        )

    if check:
        raise typer.Exit(code=1 if drift else 0)


if __name__ == "__main__":
    typer.run(sync_config)
