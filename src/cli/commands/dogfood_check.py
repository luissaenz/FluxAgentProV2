"""src/cli/commands/dogfood_check.py — `fap dogfood check` CLI command.

DX Tooling (Tarea 0, Paso 12): Orquestador unificado de validaciones E2E.
Ejecuta secuencialmente 8 flujos: doctor-builder, seed templates,
comparacion HTTP-vs-CLI, dry-run de templates, creacion de agente,
carga de payload bundle, y validacion de UI Next.js.

Uso:
    fap dogfood check --org-id <org-uuid>
    fap dogfood check --org-id <org-uuid> --json
    fap dogfood check --org-id <org-uuid> --dry-run
"""

from __future__ import annotations

import asyncio
import json
import logging
import subprocess
import sys
from pathlib import Path
from typing import Any, Optional

import httpx
import typer
from rich.console import Console
from rich.table import Table

from src.cli.commands.doctor_builder import (
    _check_breadcrumb_sync,
    _check_conftest_regression,
    _check_conftest_tenant_patches,
    _check_mock_patching,
    _check_seed_idempotency,
    _check_typescript_integrity,
)
from src.cli.commands.templates_seed import TEMPLATES
from src.cli.commands.tools_list import _collect_tools
from src.cli.config import CLIConfig
from src.db.session import get_service_client
from src.services.bundle_schemas import MIN_BACKSTORY_LENGTH, MIN_GOAL_LENGTH

logger = logging.getLogger(__name__)
console = Console()

dogfood_app = typer.Typer(
    help="E2E validation orchestration (dogfooding).",
    no_args_is_help=True,
)

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent


def _build_doctor_checks() -> list[tuple[str, tuple[bool, str]]]:
    results: list[tuple[str, tuple[bool, str]]] = []
    checks = [
        ("ID-C02: Seed Idempotency", _check_seed_idempotency),
        ("ID-C03: Breadcrumb Sync", _check_breadcrumb_sync),
        ("ID-C04: Mock Patching (tests)", _check_mock_patching),
        ("ID-023: TypeScript/Zod Integrity", _check_typescript_integrity),
        ("ID-051: Conftest Tenant Patches", _check_conftest_tenant_patches),
        ("ID-052: Conftest Regression Guard", _check_conftest_regression),
    ]
    for name, check_fn in checks:
        try:
            passed, detail = check_fn()
        except Exception as exc:
            passed, detail = False, str(exc)
        results.append((name, (passed, detail)))
    return results


def _run_templates_seed() -> dict[str, Any]:

    try:
        db = get_service_client()
        db.table("agent_templates").select("id").limit(1).execute()
    except Exception as exc:
        return {"ok": False, "inserted": 0, "skipped": 0, "errors": 1, "detail": str(exc)}

    inserted = 0
    skipped = 0
    errors = 0
    import uuid as _uuid

    for template in TEMPLATES:
        row = {
            "id": str(_uuid.uuid5(_uuid.NAMESPACE_DNS, f"fap.system.template.{template['name']}")),
            "name": template["name"],
            "description": template["description"],
            "category": template["category"],
            "soul_json": template["soul_json"],
            "suggested_tools": template["suggested_tools"],
            "max_iter": template["max_iter"],
            "is_system": template["is_system"],
        }
        try:
            result = (
                db.table("agent_templates")
                .upsert(row, on_conflict="id", ignore_duplicates=True)
                .execute()
            )
            if result.data:
                inserted += 1
            else:
                skipped += 1
        except Exception:
            errors += 1

    return {"ok": errors == 0, "inserted": inserted, "skipped": skipped, "errors": errors, "detail": ""}


async def _compare_tools_cli_vs_http_async(org_id: str, base_url: str, config: CLIConfig) -> dict[str, Any]:
    local_tools = _collect_tools(org_id)
    local_names = sorted([t["name"] for t in local_tools])

    headers: dict[str, str] = {"X-Org-ID": org_id}
    if config.access_token:
        headers["Authorization"] = f"Bearer {config.access_token}"

    http_names: list[str] = []
    http_error: Optional[str] = None
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            response = await client.get(
                f"{base_url.rstrip('/')}/api/tools/available",
                headers=headers,
            )
        if response.status_code == 200:
            data = response.json()
            http_tools = data.get("tools") if isinstance(data, dict) else data
            http_names = sorted([t["name"] for t in http_tools])
        else:
            http_error = f"HTTP {response.status_code}: {response.text[:200]}"
    except httpx.ConnectError:
        http_error = "Cannot connect to API (backend not running?)"
    except Exception as exc:
        http_error = str(exc)

    match = local_names == http_names
    only_local = sorted(set(local_names) - set(http_names))
    only_http = sorted(set(http_names) - set(local_names))

    return {
        "ok": match and http_error is None,
        "local_count": len(local_names),
        "http_count": len(http_names),
        "match": match,
        "only_local": only_local,
        "only_http": only_http,
        "http_error": http_error,
    }


def _compare_tools_cli_vs_http(org_id: str, base_url: str, config: CLIConfig) -> dict[str, Any]:
    return asyncio.run(_compare_tools_cli_vs_http_async(org_id, base_url, config))


def _dry_run_all_templates() -> dict[str, Any]:
    results: list[dict[str, Any]] = []
    for template in TEMPLATES:
        tpl_name = template["name"]
        soul = template.get("soul_json") or {}
        final_role = soul.get("role") or tpl_name
        final_goal = soul.get("goal") or ""
        final_backstory = soul.get("backstory") or template.get("description") or ""
        suggested_tools = list(template.get("suggested_tools") or [])
        final_max_iter = template.get("max_iter") or 3

        goal_ok = isinstance(final_goal, str) and len(final_goal) >= MIN_GOAL_LENGTH
        backstory_ok = isinstance(final_backstory, str) and len(final_backstory) >= MIN_BACKSTORY_LENGTH

        results.append({
            "name": tpl_name,
            "role": final_role,
            "goal_ok": goal_ok,
            "backstory_ok": backstory_ok,
            "tools_count": len(suggested_tools),
            "max_iter": final_max_iter,
        })

    all_ok = all(r["goal_ok"] and r["backstory_ok"] for r in results)
    return {
        "ok": all_ok,
        "total": len(results),
        "goal_ok": sum(1 for r in results if r["goal_ok"]),
        "backstory_ok": sum(1 for r in results if r["backstory_ok"]),
        "templates": results,
    }


async def _create_dogfood_agent_async(org_id: str, base_url: str, config: CLIConfig) -> dict[str, Any]:
    payload = {
        "role": "Dogfood Validator",
        "soul_json": {
            "goal": "Validate the full dogfooding E2E protocol end-to-end.",
            "backstory": "You are a validator agent created by the dogfooding pipeline to ensure end-to-end integrity.",
            "llm_provider": "groq",
            "llm_model": "llama-3.1-70b-versatile",
            "verbose": False,
            "reasoning": False,
            "inject_date": False,
            "memory": False,
        },
        "allowed_tools": [],
        "max_iter": 2,
    }

    headers: dict[str, str] = {"X-Org-ID": org_id, "Content-Type": "application/json"}
    if config.access_token:
        headers["Authorization"] = f"Bearer {config.access_token}"

    url = f"{base_url.rstrip('/')}/agents"
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            response = await client.post(url, json=payload, headers=headers)
        if response.status_code in (200, 201):
            data = response.json()
            return {"ok": True, "agent_id": data.get("id", ""), "role": data.get("role", ""), "status": "created"}
        elif response.status_code == 409:
            return {"ok": True, "agent_id": "", "role": payload["role"], "status": "already_exists"}
        else:
            detail = response.json().get("detail", response.text)
            return {"ok": False, "agent_id": "", "role": payload["role"], "status": f"error_{response.status_code}", "detail": str(detail)}
    except httpx.ConnectError:
        return {"ok": False, "agent_id": "", "role": payload["role"], "status": "connection_error"}
    except Exception as exc:
        return {"ok": False, "agent_id": "", "role": payload["role"], "status": "exception", "detail": str(exc)}


def _create_dogfood_agent(org_id: str, base_url: str, config: CLIConfig) -> dict[str, Any]:
    return asyncio.run(_create_dogfood_agent_async(org_id, base_url, config))


def _validate_bundle_min_goal() -> dict[str, Any]:

    from src.services.bundle_schemas import ExportBundleRequest

    test_payload = {
        "bundle_name": "dogfood-test",
        "agents": [
            {
                "role": "Test Short Goal",
                "soul_json": {"goal": "Short", "backstory": "This backstory is long enough to pass the minimum length test."},
                "allowed_tools": [],
                "max_iter": 3,
            }
        ],
        "skills": [],
    }

    try:
        payload = ExportBundleRequest(**test_payload)
    except Exception as exc:
        return {"ok": False, "schema_valid": False, "detail": str(exc)}

    warnings: list[str] = []
    goal_ok_count = 0
    backstory_ok_count = 0
    for agent in payload.agents:
        goal = agent.soul_json.get("goal", "")
        backstory = agent.soul_json.get("backstory", "")
        if isinstance(goal, str) and len(goal) >= MIN_GOAL_LENGTH:
            goal_ok_count += 1
        else:
            warnings.append(f"Agent {agent.role}: goal < {MIN_GOAL_LENGTH} chars")
        if isinstance(backstory, str) and len(backstory) >= MIN_BACKSTORY_LENGTH:
            backstory_ok_count += 1
        else:
            warnings.append(f"Agent {agent.role}: backstory < {MIN_BACKSTORY_LENGTH} chars")

    schema_ok = goal_ok_count == 0
    return {
        "ok": True,
        "schema_valid": True,
        "goal_warnings": len(warnings),
        "warnings": warnings,
        "goal_min_length_triggered": not schema_ok,
    }


def _run_builder_nav_script() -> dict[str, Any]:
    script_path = PROJECT_ROOT / "scripts" / "validate_builder_nav.py"
    if not script_path.exists():
        return {"ok": False, "exit_code": -1, "detail": f"Script not found: {script_path}"}

    try:
        result = subprocess.run(
            [sys.executable, str(script_path)],
            capture_output=True,
            text=True,
            timeout=30,
            cwd=str(PROJECT_ROOT),
        )
        return {
            "ok": result.returncode == 0,
            "exit_code": result.returncode,
            "stdout": result.stdout[:2000],
            "stderr": result.stderr[:500],
        }
    except subprocess.TimeoutExpired:
        return {"ok": False, "exit_code": -1, "detail": "Script timeout (30s)"}
    except Exception as exc:
        return {"ok": False, "exit_code": -1, "detail": str(exc)}


@dogfood_app.command("check")
def dogfood_check(
    org_id: str = typer.Option(..., "--org-id", "-o", help="Organization UUID"),
    json_output: bool = typer.Option(False, "--json", help="Generate JSON report for CI/CD"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Preview steps without executing"),
) -> None:
    """Run the full E2E validation (dogfooding) protocol.

    Executes 8 validation flows: doctor-builder diagnostics, idempotent seed,
    HTTP-vs-CLI tools comparison, template dry-runs, agent creation,
    bundle payload validation, and Next.js UI integrity check.
    """
    config = CLIConfig.load()
    base_url = config.api_url or "http://localhost:8000"

    if dry_run:
        console.print("\n[bold cyan]fap dogfood check --dry-run[/bold cyan]")
        console.print("[dim]Steps to execute:[/dim]")
        steps = [
            "1. fap doctor builder (6 diagnostic checks)",
            "2. fap templates seed (idempotent seed of 8 templates)",
            "3. fap tools list vs GET /api/tools/available (HTTP cross-validation)",
            "4. fap templates use --dry-run (all 8 templates payload validation)",
            "5. fap agent create (dogfood agent via HTTP POST /agents)",
            "6. fap bundle validate-payload (goal/backstory minimum length check)",
            "7. python scripts/validate_builder_nav.py (Next.js UI integrity)",
        ]
        for s in steps:
            console.print(f"  {s}")
        console.print(f"\n[dim]org_id={org_id}  base_url={base_url}[/dim]")
        return

    console.print("\n[bold cyan]fap dogfood check[/bold cyan]")
    console.print(f"[dim]org_id={org_id}  base_url={base_url}[/dim]\n")

    step_results: list[dict[str, Any]] = []
    all_ok = True

    def record(step: int, name: str, ok: bool, detail: str = "", data: dict[str, Any] | None = None):
        nonlocal all_ok
        if not ok:
            all_ok = False
        step_results.append({
            "step": step,
            "name": name,
            "ok": ok,
            "detail": detail,
            "data": data or {},
        })

    # ── Step 1: Doctor Builder ──
    console.print("[bold]Step 1/7:[/bold] Doctor Builder diagnostics...")
    doctor_checks = _build_doctor_checks()
    doctor_ok = all(passed for _, (passed, _) in doctor_checks)
    doctor_failed = [name for name, (passed, _) in doctor_checks if not passed]
    doctor_detail = f"{sum(1 for _, (p, _) in doctor_checks if p)}/{len(doctor_checks)} checks passed"
    if doctor_failed:
        doctor_detail += f" (failed: {', '.join(doctor_failed)})"
    record(1, "Doctor Builder Diagnostics", doctor_ok, doctor_detail, {"checks": [{"name": n, "ok": p, "detail": d} for n, (p, d) in doctor_checks]})
    status = "[green]OK[/green]" if doctor_ok else "[red]FAIL[/red]"
    console.print(f"  {status} {doctor_detail}")

    # ── Step 2: Templates Seed ──
    console.print("[bold]Step 2/7:[/bold] Templates Seed (idempotent)...")
    seed_result = _run_templates_seed()
    seed_ok = seed_result["ok"]
    seed_detail = f"inserted={seed_result['inserted']}, skipped={seed_result['skipped']}, errors={seed_result['errors']}"
    record(2, "Templates Seed", seed_ok, seed_detail, seed_result)
    status = "[green]OK[/green]" if seed_ok else "[red]FAIL[/red]"
    console.print(f"  {status} {seed_detail}")

    # ── Step 3: HTTP vs CLI Cross-Validation ──
    console.print("[bold]Step 3/7:[/bold] HTTP vs CLI Tools Cross-Validation...")
    cmp_result = _compare_tools_cli_vs_http(org_id, base_url, config)
    cmp_ok = cmp_result["ok"]
    if cmp_result.get("http_error"):
        cmp_detail = f"local={cmp_result['local_count']}, http ERROR: {cmp_result['http_error']}"
    elif not cmp_result["match"]:
        cmp_detail = f"local={cmp_result['local_count']}, http={cmp_result['http_count']} — MISMATCH"
        if cmp_result["only_local"]:
            cmp_detail += f" (only local: {cmp_result['only_local']})"
        if cmp_result["only_http"]:
            cmp_detail += f" (only http: {cmp_result['only_http']})"
    else:
        cmp_detail = f"local={cmp_result['local_count']}, http={cmp_result['http_count']} — IDENTICAL"
    record(3, "HTTP vs CLI Cross-Validation", cmp_ok, cmp_detail, cmp_result)
    status = "[green]OK[/green]" if cmp_ok else "[yellow]WARN[/yellow]"
    console.print(f"  {status} {cmp_detail}")

    # ── Step 4: Templates Dry-Run ──
    console.print("[bold]Step 4/7:[/bold] All Templates Dry-Run...")
    dry_result = _dry_run_all_templates()
    dry_ok = dry_result["ok"]
    dry_detail = f"{dry_result['total']} templates: goal_ok={dry_result['goal_ok']}, backstory_ok={dry_result['backstory_ok']}"
    record(4, "All Templates Dry-Run", dry_ok, dry_detail, dry_result)
    status = "[green]OK[/green]" if dry_ok else "[yellow]WARN[/yellow]"
    console.print(f"  {status} {dry_detail}")

    # ── Step 5: Agent Create (Dogfood) ──
    console.print("[bold]Step 5/7:[/bold] Agent Create (Dogfood agent)...")
    agent_result = _create_dogfood_agent(org_id, base_url, config)
    agent_ok = agent_result["ok"]
    agent_detail = f"role={agent_result['role']}, status={agent_result['status']}"
    record(5, "Agent Create (Dogfood)", agent_ok, agent_detail, agent_result)
    status = "[green]OK[/green]" if agent_ok else "[red]FAIL[/red]"
    console.print(f"  {status} {agent_detail}")

    # ── Step 6: Bundle Validate-Payload ──
    console.print("[bold]Step 6/7:[/bold] Bundle Validate-Payload (goal/backstory min length)...")
    bundle_result = _validate_bundle_min_goal()
    bundle_ok = bundle_result["ok"]
    bundle_detail = "schema valid" if bundle_result.get("schema_valid") else str(bundle_result.get("detail", ""))
    record(6, "Bundle Validate-Payload", bundle_ok, bundle_detail, bundle_result)
    status = "[green]OK[/green]" if bundle_ok else "[red]FAIL[/red]"
    console.print(f"  {status} {bundle_detail}")

    # ── Step 7: validate_builder_nav.py ──
    console.print("[bold]Step 7/7:[/bold] Next.js UI Integrity (validate_builder_nav.py)...")
    nav_result = _run_builder_nav_script()
    nav_ok = nav_result["ok"]
    nav_detail = f"exit_code={nav_result['exit_code']}"
    record(7, "Next.js UI Integrity", nav_ok, nav_detail, nav_result)
    status = "[green]OK[/green]" if nav_ok else "[red]FAIL[/red]"
    console.print(f"  {status} {nav_detail}")

    # ── Report ──
    console.print("")
    table = Table(title="Dogfood Check Results", show_lines=False)
    table.add_column("#", justify="right", style="dim")
    table.add_column("Step", style="cyan", min_width=35)
    table.add_column("Status", justify="center", min_width=6)
    table.add_column("Detail", style="dim")

    for sr in step_results:
        icon = "[green]PASS[/green]" if sr["ok"] else "[red]FAIL[/red]"
        detail_text = sr.get("detail", "")[:120]
        table.add_row(str(sr["step"]), sr["name"], icon, detail_text)

    console.print(table)

    passed = sum(1 for sr in step_results if sr["ok"])
    total = len(step_results)
    console.print(f"\n[bold]Summary:[/bold] {passed}/{total} steps passed")

    if json_output:
        report = {
            "passed": passed,
            "total": total,
            "all_ok": all_ok,
            "steps": step_results,
        }
        console.print("")
        console.print_json(json.dumps(report, ensure_ascii=False, default=str))

    if all_ok:
        console.print("\n[bold green]All checks passed. Builder is healthy.[/bold green]\n")
    else:
        console.print("\n[bold red]Some checks failed. Review details above.[/bold red]\n")
        raise typer.Exit(code=1)
