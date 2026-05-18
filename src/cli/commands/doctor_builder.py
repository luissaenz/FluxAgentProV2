"""src/cli/commands/doctor_builder.py — `fap doctor builder` CLI command.

DX Tooling (Tarea 0, Paso 11): Diagnostica los 6 fixes críticos del Builder
en un solo comando. Verifica idempotencia del seed, sincronización de breadcrumbs,
integridad de mocks, TypeScript, y regresiones de conftest.

Uso:
    fap doctor builder
"""

from __future__ import annotations

import logging
from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

logger = logging.getLogger(__name__)
console = Console()

doctor_builder_app = typer.Typer(
    help="Diagnostics for Builder stability fixes.",
    no_args_is_help=True,
)

# Project root: 4 levels up from this file
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent


def _check_seed_idempotency() -> tuple[bool, str]:
    """Check ID-C02: templates_seed.py uses ON CONFLICT or upsert pattern (atomic)."""
    seed_file = PROJECT_ROOT / "src" / "cli" / "commands" / "templates_seed.py"
    if not seed_file.exists():
        return False, f"File not found: {seed_file}"

    content = seed_file.read_text(encoding="utf-8")
    has_upsert = ".upsert(" in content
    has_on_conflict = "on_conflict" in content.lower()

    # SELECT+INSERT is NOT acceptable — it's susceptible to race conditions
    has_select_insert = '.select("id")' in content and ".insert(" in content

    if has_select_insert:
        return False, "Uses SELECT+INSERT pattern — susceptible to race conditions"
    if has_upsert or has_on_conflict:
        return True, "Uses atomic upsert/ON CONFLICT pattern (safe idempotency)"
    return False, "No idempotency pattern detected — risk of duplicate inserts"


def _check_breadcrumb_sync() -> tuple[bool, str]:
    """Check ID-C03: BuilderBreadcrumb is connected to dynamic tab state."""
    page_file = PROJECT_ROOT / "dashboard" / "app" / "(app)" / "builder" / "page.tsx"
    breadcrumb_file = (
        PROJECT_ROOT / "dashboard" / "components" / "builder" / "BuilderBreadcrumb.tsx"
    )

    if not page_file.exists():
        return False, f"File not found: {page_file}"
    if not breadcrumb_file.exists():
        return False, f"File not found: {breadcrumb_file}"

    page_content = page_file.read_text(encoding="utf-8")
    # Check for hardcoded activeTab
    has_hardcoded = 'activeTab="agent-form"' in page_content
    has_context = "useBuilderTab" in page_content or "BuilderTabProvider" in page_content

    if has_hardcoded and not has_context:
        return False, "activeTab is hardcoded in page.tsx — breadcrumbs are static"
    if has_context:
        return True, "BuilderTabProvider/useBuilderTab detected — breadcrumbs are synced"
    return True, "activeTab is not hardcoded"


def _check_mock_patching() -> tuple[bool, str]:
    """Check ID-C04/ID-051: test_builder_scenarios.py patches at correct namespaces."""
    test_file = PROJECT_ROOT / "tests" / "e2e" / "test_builder_scenarios.py"
    if not test_file.exists():
        return False, f"File not found: {test_file}"

    content = test_file.read_text(encoding="utf-8")

    # Bad pattern: patching at the source module instead of consumption point
    bad_patches = content.count('patch("src.db.session.get_tenant_client"')
    good_patches = content.count('patch("src.api.routes.')

    if bad_patches > 0:
        return False, (
            f"Found {bad_patches} patches at src.db.session (ineffective). "
            f"Should patch at src.api.routes.* namespace."
        )
    if good_patches > 0:
        return True, f"Found {good_patches} patches at correct router namespaces"
    return True, "No direct db.session patches found"


def _check_typescript_integrity() -> tuple[bool, str]:
    """Check ID-023: AgentForm.tsx Zod schema has .min(10) on goal/backstory."""
    agent_form = (
        PROJECT_ROOT / "dashboard" / "components" / "builder" / "AgentForm.tsx"
    )
    if not agent_form.exists():
        return False, f"File not found: {agent_form}"

    content = agent_form.read_text(encoding="utf-8")
    has_goal_min = ".min(10" in content and "goal" in content
    has_backstory_min = ".min(10" in content and "backstory" in content

    # Check for llmProvider using z.string() instead of z.enum()
    uses_string_provider = "llmProvider: z.string()" in content
    uses_enum_provider = "llmProvider: z.enum(" in content

    issues = []
    if not has_goal_min:
        issues.append("goal missing .min(10)")
    if not has_backstory_min:
        issues.append("backstory missing .min(10)")
    if uses_enum_provider and not uses_string_provider:
        issues.append("llmProvider uses z.enum() — may cause type mismatch")

    if issues:
        return False, "; ".join(issues)
    return True, "Zod schema has proper validations"


def _check_conftest_regression() -> tuple[bool, str]:
    """Check ID-052: global_llm_mock is scoped to e2e tests, not global."""
    global_conftest = PROJECT_ROOT / "tests" / "conftest.py"
    e2e_conftest = PROJECT_ROOT / "tests" / "e2e" / "conftest.py"

    if not global_conftest.exists():
        return False, f"File not found: {global_conftest}"

    global_content = global_conftest.read_text(encoding="utf-8")
    has_llm_in_global = "def global_llm_mock" in global_content

    if has_llm_in_global:
        return (
            False,
            "global_llm_mock is still in global conftest — should be in tests/e2e/conftest.py",
        )

    if e2e_conftest.exists():
        e2e_content = e2e_conftest.read_text(encoding="utf-8")
        if "def global_llm_mock" in e2e_content:
            return True, "global_llm_mock scoped to tests/e2e/conftest.py — safe"

    return True, "global_llm_mock is not present in global conftest"


def _check_conftest_tenant_patches() -> tuple[bool, str]:
    """Check that conftest patches tenant_client at router namespaces."""
    conftest = PROJECT_ROOT / "tests" / "conftest.py"
    if not conftest.exists():
        return False, f"File not found: {conftest}"

    content = conftest.read_text(encoding="utf-8")
    # Check for router-level patches
    has_agents_patch = "src.api.routes.agents.get_tenant_client" in content

    if has_agents_patch:
        return True, "conftest patches tenant_client at router namespaces"
    return False, "conftest missing patches at src.api.routes.agents.get_tenant_client"


@doctor_builder_app.command("builder")
def doctor_builder() -> None:
    """Run all 6 diagnostic checks for Builder stability."""
    console.print("\n[bold cyan]FAP Doctor Builder — Diagnostics[/bold cyan]\n")

    checks = [
        ("ID-C02: Seed Idempotency", _check_seed_idempotency),
        ("ID-C03: Breadcrumb Sync", _check_breadcrumb_sync),
        ("ID-C04: Mock Patching (tests)", _check_mock_patching),
        ("ID-023: TypeScript/Zod Integrity", _check_typescript_integrity),
        ("ID-051: Conftest Tenant Patches", _check_conftest_tenant_patches),
        ("ID-052: Conftest Regression Guard", _check_conftest_regression),
    ]

    table = Table(title="Builder Stability Checks")
    table.add_column("Check", style="cyan", min_width=35)
    table.add_column("Status", justify="center", min_width=6)
    table.add_column("Detail", style="dim")

    all_passed = True
    for name, check_fn in checks:
        passed, detail = check_fn()
        status = "[green]OK[/green]" if passed else "[red]FAIL[/red]"
        if not passed:
            all_passed = False
        table.add_row(name, status, detail)

    console.print(table)

    if all_passed:
        console.print("\n[bold green]All checks passed.[/bold green]\n")
    else:
        console.print(
            "\n[bold red]Some checks failed. Fix issues before proceeding.[/bold red]\n"
        )
        raise typer.Exit(code=1)
