"""src/cli/commands/sync_step_names.py — 'fap sync-step-names' command.

Verifica/corrige nombres de pasos en TESTING.md y CHANGELOG.md
contra fuente de verdad configurable (phase-state.md o plan.md).
"""

from __future__ import annotations

import re
from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

console = Console()

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
TESTING_MD = PROJECT_ROOT / "TESTING.md"
CHANGELOG_MD = PROJECT_ROOT / "CHANGELOG.md"
PLAN_MD = PROJECT_ROOT / "DEVS" / "plan.md"

TESTING_H_RE = re.compile(r"^### Paso (\d+): (.+)$")
CHANGELOG_H_RE = re.compile(r"^#### Paso (\d+) — (.+)$")
PLAN_H_RE = re.compile(r"### Paso (\d+): (.+)")

# Canonical names: phase-state.md + analysis §4 corrections
PHASE_STATE_CANONICAL: dict[int, str] = {
    0: "Auditoria de Linea Base",
    1: "Cobertura Unitaria de Gaps Criticos",
    2: "Tests de Integracion de Flujos Criticos",
    3: "E2E — Flujos Completos con Mocks",
    4: "Tests de Estrés y Robustez",
    5: "Tests de Seguridad — Hardening",
    6: "Performance y Observabilidad",
    7: "Documentacion y Cierre",
}


def _extract_plan_names() -> dict[int, str]:
    """Parse plan.md Tarea 3.1 table for proposed step names."""
    if not PLAN_MD.exists():
        console.print("[red]Error:[/red] plan.md no encontrado.")
        raise typer.Exit(code=1)

    text = PLAN_MD.read_text(encoding="utf-8")
    names: dict[int, str] = {}

    for line in text.splitlines():
        s = line.strip()
        if not s.startswith("|") or s.count("|") < 4:
            continue
        parts = [p.strip() for p in s.split("|") if p.strip()]
        if len(parts) < 3:
            continue
        try:
            int(parts[0])
        except ValueError:
            continue
        new_heading = parts[2].strip("`").strip()
        m = PLAN_H_RE.match(new_heading)
        if m:
            names[int(m.group(1))] = m.group(2).strip()

    if not names:
        console.print("[red]Error:[/red] No se encontró la tabla Tarea 3.1 en plan.md.")
        raise typer.Exit(code=1)

    return names


def _get_canonical(source: str) -> dict[int, str]:
    if source == "phase-state":
        return dict(PHASE_STATE_CANONICAL)
    elif source == "plan":
        return _extract_plan_names()
    console.print(f"[red]Error:[/red] Source '{source}' desconocida. Usar 'phase-state' o 'plan'.")
    raise typer.Exit(code=1)


def _scan_heads(path: Path, pattern: re.Pattern) -> dict[int, tuple[str, int]]:
    results: dict[int, tuple[str, int]] = {}
    for i, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        m = pattern.match(line)
        if m:
            results[int(m.group(1))] = (m.group(2).strip(), i)
    return results


def sync_step_names(
    check: bool = typer.Option(False, "--check", help="Lista discrepancias. Exit 0 si ok, 1 si drift"),
    fix: bool = typer.Option(False, "--fix", help="Aplica correcciones a TESTING.md + CHANGELOG.md"),
    source: str = typer.Option("phase-state", "--source", help="Fuente de verdad: 'phase-state' (default) o 'plan'"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Muestra cambios propuestos sin modificar archivos"),
):
    """Verificar/corregir nombres de pasos en TESTING.md y CHANGELOG.md."""
    canonical = _get_canonical(source)
    testing_heads = _scan_heads(TESTING_MD, TESTING_H_RE)
    changelog_heads = _scan_heads(CHANGELOG_MD, CHANGELOG_H_RE)

    disc: list[tuple[str, int, int, str, str]] = []
    for doc, heads in [("TESTING.md", testing_heads), ("CHANGELOG.md", changelog_heads)]:
        for step, expected in sorted(canonical.items()):
            if step not in heads:
                continue
            current, lineno = heads[step]
            if current != expected:
                disc.append((doc, lineno, step, current, expected))

    if disc:
        console.print(f"\n[red]{len(disc)} discrepancia(s) encontrada(s):[/red]\n")
        tbl = Table(title=f"Discrepancias (source: {source})")
        tbl.add_column("Archivo", style="cyan")
        tbl.add_column("Línea", style="yellow")
        tbl.add_column("Paso", style="magenta")
        tbl.add_column("Actual", style="red")
        tbl.add_column("Esperado", style="green")
        for d in disc:
            tbl.add_row(str(d[0]), str(d[1]), str(d[2]), d[3], d[4])
        console.print(tbl)
    else:
        console.print("\n[green]0 discrepancias encontradas.[/green]")

    if fix and disc:
        if dry_run:
            console.print(f"\n[yellow]Dry-run: {len(disc)} cambio(s) listo(s) para aplicar.[/yellow]")
        else:
            fixes = 0
            for doc_name, pat, doc_path in [
                ("TESTING.md", TESTING_H_RE, TESTING_MD),
                ("CHANGELOG.md", CHANGELOG_H_RE, CHANGELOG_MD),
            ]:
                text = doc_path.read_text(encoding="utf-8")
                count = 0
                for dd in disc:
                    if dd[0] != doc_name:
                        continue
                    _, _, step, cur, exp = dd
                    if pat == TESTING_H_RE:
                        old, new = f"### Paso {step}: {cur}", f"### Paso {step}: {exp}"
                    else:
                        old, new = f"#### Paso {step} — {cur}", f"#### Paso {step} — {exp}"
                    if old in text:
                        text = text.replace(old, new, 1)
                        count += 1
                if count:
                    doc_path.write_text(text, encoding="utf-8")
                    fixes += count
            console.print(f"\n[green]{fixes} discrepancia(s) corregida(s).[/green]")
    elif fix and not disc:
        console.print("\n[green]No hay discrepancias para corregir.[/green]")

    if check:
        raise typer.Exit(code=1 if disc else 0)


if __name__ == "__main__":
    typer.run(sync_step_names)
