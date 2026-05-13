"""src/cli/commands/bundle_export.py — `fap bundle export` CLI command.

Exports agents (and optionally skills) from database into a FAP-Bundle v2 ZIP.
Uses ExportService to share logic with the HTTP endpoint (dogfooding).
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console

from src.cli.config import CLIConfig
from src.db.session import get_service_client
from src.services.bundle_schemas import (
    AgentExportItem,
    ExportBundleRequest,
    SkillExportItem,
)
from src.services.export_service import ExportService

logger = logging.getLogger(__name__)
console = Console()

bundle_app = typer.Typer(
    help="Bundle management: export, validate, etc.",
    no_args_is_help=True,
)


@bundle_app.command("export")
def export_bundle(
    org_id: Optional[str] = typer.Option(
        None, "--org-id", "-o", help="Organization UUID"
    ),
    output: Path = typer.Option(
        Path("export_bundle.zip"), "--output", help="Output ZIP file path"
    ),
    include_skills: bool = typer.Option(
        False, "--include-skills", help="Include skills from skill_catalog in the bundle"
    ),
    roles: Optional[str] = typer.Option(
        None, "--roles", help="Comma-separated list of agent roles to export (all if not set)"
    ),
    version: str = typer.Option(
        "1.0.0", "--version", help="Bundle version string"
    ),
) -> None:
    """Export agents from the database to a FAP-Bundle v2 ZIP file."""
    config = CLIConfig.load()
    if org_id is None:
        org_id = config.org_id

    if not org_id:
        console.print("[red]Error:[/red] --org-id required. Set FAP_ORG_ID in .env or pass --org-id.")
        raise typer.Exit(code=1)

    try:
        svc = get_service_client()

        # Fetch agents from DB
        query = svc.table("agent_catalog").select("*").eq("org_id", org_id).eq("is_active", True)
        result = query.execute()

        if not result.data:
            console.print(f"[yellow]! No agents found for org [bold]{org_id}[/bold].[/yellow]")
            raise typer.Exit(code=0)

        agents_data = result.data

        # Filter by roles if specified
        if roles:
            role_set = {r.strip() for r in roles.split(",") if r.strip()}
            agents_data = [a for a in agents_data if a.get("role") in role_set]
            if not agents_data:
                console.print(f"[yellow]! No agents match specified roles: {roles}[/yellow]")
                raise typer.Exit(code=0)

        # Build ExportBundleRequest payload
        agent_items = []
        for a in agents_data:
            agent_items.append(
                AgentExportItem(
                    role=a.get("role", "unknown"),
                    soul_json=a.get("soul_json", {}),
                    allowed_tools=a.get("allowed_tools", []),
                    max_iter=a.get("max_iter", 5),
                )
            )

        skill_items = []
        if include_skills:
            skill_result = (
                svc.table("skill_catalog")
                .select("name,code_source")
                .eq("org_id", org_id)
                .eq("is_active", True)
                .execute()
            )
            for s in (skill_result.data or []):
                skill_items.append(
                    SkillExportItem(name=s["name"], code=s["code_source"])
                )

        payload = ExportBundleRequest(
            bundle_name=f"cli_export_{org_id[:8]}",
            agents=agent_items,
            skills=skill_items if skill_items else None,
        )

        # SUPUESTO: version from CLI not passed through ExportBundleRequest (no version field in spec).
        # Using default "1.0.0" via ExportService. Future: add version field to ExportBundleRequest if needed.

        # Use ExportService (dogfooding — same logic as HTTP endpoint)
        service = ExportService(org_id=org_id)
        zip_bytes, _filename = service.export(payload)

        # Write to disk
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_bytes(zip_bytes)

        skill_count = len(skill_items)
        console.print(
            f"\n[bold green]OK[/bold green] Exported {len(agent_items)} agent(s)"
            + (f" + {skill_count} skill(s)" if skill_count else "")
            + f" to [bold]{output}[/bold] ({len(zip_bytes)} bytes)"
        )

    except Exception as e:
        logger.exception("Bundle export failed for org %s", org_id)
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(code=1)
