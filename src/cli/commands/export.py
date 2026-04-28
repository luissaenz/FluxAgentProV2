"""src/cli/commands/export.py — Implementation of 'fap export-agents' command."""

import os
from pathlib import Path

import typer
from rich import print

from src.cli.utils import calculate_dir_hashes, create_manifest_base, save_json
from src.db.session import get_service_client


def export_agents(
    org_id: str = typer.Option(..., help="UUID of the organization to export from"),
    output: Path = typer.Option(
        Path("migration_bundle"),
        "--output",
        "-o",
        help="Directory to save the exported bundle",
    ),
):
    """Export agents from the database to a bundle structure for migration."""
    print(f"EXPORTING agents for Org: [bold]{org_id}[/bold]")

    try:
        # 1. Connect to Supabase
        svc = get_service_client()

        # 2. Fetch Agents
        # NOTA: Usamos service client para bypass RLS y ver todos los agentes de la org.
        result = svc.table("agent_catalog").select("*").eq("org_id", org_id).execute()

        if not result.data:
            print(
                f"[yellow]![/yellow] No agents found for organization [bold]{org_id}[/bold]."
            )
            raise typer.Exit(code=0)

        # 3. Create structure
        agents_dir = output / "agents"
        os.makedirs(agents_dir, exist_ok=True)
        os.makedirs(output / "flows", exist_ok=True)
        os.makedirs(output / "skills", exist_ok=True)
        os.makedirs(output / "context", exist_ok=True)

        # 4. Map and save agents
        for agent in result.data:
            role = agent.get("role", "unknown")
            # SUPUESTO: La estructura del JSON exportado debe coincidir con la esperada por el Bundle v2.
            # Mapeamos soul_json al formato plano del bundle.
            soul = agent.get("soul_json", {})
            agent_def = {
                "role": role,
                "goal": soul.get("goal", ""),
                "backstory": soul.get("backstory", ""),
                "allowed_tools": agent.get("allowed_tools", []),
                "rules": soul.get("rules", []),
                "model": soul.get("model", "anthropic/claude-sonnet-4-7"),
                "max_iter": agent.get("max_iter", 5),
            }

            save_json(agents_dir / f"{role}.json", agent_def)
            print(f"  - Exported: [cyan]{role}[/cyan]")

        # 5. Create manifest with initial hashes
        manifest = create_manifest_base(f"migration_{org_id[:8]}")
        save_json(output / "manifest.json", manifest)

        # Recalculate hashes to make it "package-ready"
        manifest["hashes"] = calculate_dir_hashes(output)
        save_json(output / "manifest.json", manifest)

        print(
            f"\n[bold green]OK:[/bold green] Exported {len(result.data)} agents to [bold]{output}[/bold]."
        )
        print("\nNext steps:")
        print(f"  1. Review the exported agents in {agents_dir}/")
        print(
            f"  2. Run [cyan]fap package {output}[/cyan] to create the migration ZIP."
        )

    except Exception as e:
        print(f"[red]Error:[/red] Export failed: {e}")
        raise typer.Exit(code=1)
