"""src/cli/commands/templates_seed.py — `fap templates seed` CLI command.

Inserts 8 pre-defined agent templates into Supabase agent_templates table.

Dogfooding workflow (run after migration 030):
  1. fap templates seed                    # insert 8 system templates
  2. fap templates seed --dry-run           # preview without inserting
  3. fap templates seed --reset             # re-insert (deletes existing first)
  4. GET /api/templates                     # verify list returns 8 templates
  5. GET /api/templates/{id}                # verify detail with soul_json
  6. GET /api/templates?category=Research   # verify category filter
"""
from __future__ import annotations

import logging
import uuid

import typer
from rich.console import Console
from rich.table import Table

from src.db.session import get_service_client

logger = logging.getLogger(__name__)

console = Console()
templates_app = typer.Typer(
    help="Manage agent templates.",
    no_args_is_help=True,
)

TEMPLATES = [
    {
        "name": "Research Agent",
        "description": "Conducts in-depth research across multiple sources and synthesizes findings.",
        "category": "Research",
        "soul_json": {
            "role": "Research Specialist",
            "goal": "Research topics thoroughly and produce accurate, well-structured reports.",
            "backstory": "You are a research agent specialized in gathering, analyzing, and synthesizing information from diverse sources to produce high-quality reports.",
        },
        "suggested_tools": ["sql_analytical", "event_store"],
        "max_iter": 5,
        "is_system": True,
    },
    {
        "name": "Code Reviewer",
        "description": "Reviews source code for bugs, security issues, and quality standards.",
        "category": "Development",
        "soul_json": {
            "role": "Code Reviewer",
            "goal": "Review code for errors, vulnerabilities, and inefficiencies.",
            "backstory": "You are a senior code reviewer with experience across multiple languages and frameworks. You detect bugs, security vulnerabilities, and poor practices.",
        },
        "suggested_tools": [],
        "max_iter": 3,
        "is_system": True,
    },
    {
        "name": "Data Analyst",
        "description": "Analyzes structured data, generates insights, and creates visualizations from Excel and databases.",
        "category": "Development",
        "soul_json": {
            "role": "Data Analyst",
            "goal": "Analyze data and extract actionable business insights.",
            "backstory": "You are a data analyst expert in SQL, Excel, and visualization. You transform raw data into strategic recommendations.",
        },
        "suggested_tools": ["sql_analytical", "excel_reader", "excel_writer"],
        "max_iter": 5,
        "is_system": True,
    },
    {
        "name": "Customer Support",
        "description": "Handles customer inquiries, resolves issues, and escalates when necessary.",
        "category": "Support",
        "soul_json": {
            "role": "Customer Support Agent",
            "goal": "Resolve customer inquiries quickly and effectively, escalating when needed.",
            "backstory": "You are an empathetic and efficient customer support agent. You prioritize customer satisfaction while following established procedures.",
        },
        "suggested_tools": [],
        "max_iter": 3,
        "is_system": True,
    },
    {
        "name": "Document Writer",
        "description": "Creates technical documents, reports, proposals, and guides with professional formatting.",
        "category": "General",
        "soul_json": {
            "role": "Document Writer",
            "goal": "Create professional, clear, and well-structured documents.",
            "backstory": "You are an expert technical writer who produces high-quality documentation. You adapt tone and format to the target audience.",
        },
        "suggested_tools": ["excel_writer"],
        "max_iter": 4,
        "is_system": True,
    },
    {
        "name": "Translator",
        "description": "Translates text between multiple languages while preserving context, tone, and technical accuracy.",
        "category": "General",
        "soul_json": {
            "role": "Translator Agent",
            "goal": "Translate content between languages preserving meaning, tone, and cultural context.",
            "backstory": "You are a professional multilingual translator with cultural sensitivity. You adapt the message to the audience's context while preserving meaning.",
        },
        "suggested_tools": [],
        "max_iter": 2,
        "is_system": True,
    },
    {
        "name": "Summarizer",
        "description": "Condenses long documents, conversations, and reports into concise, actionable summaries.",
        "category": "General",
        "soul_json": {
            "role": "Summarizer Agent",
            "goal": "Condense extensive information into clear summaries highlighting key points.",
            "backstory": "You are an information synthesis specialist. You identify essential content and present it concisely without losing accuracy.",
        },
        "suggested_tools": [],
        "max_iter": 3,
        "is_system": True,
    },
    {
        "name": "General Assistant",
        "description": "Versatile assistant for general tasks, brainstorming, and daily operational support.",
        "category": "General",
        "soul_json": {
            "role": "General Assistant",
            "goal": "Help with varied daily tasks efficiently and proactively.",
            "backstory": "You are a generalist assistant adaptable to any task. From basic research to information organization, you are ready to help.",
        },
        "suggested_tools": ["excel_reader", "excel_writer"],
        "max_iter": 5,
        "is_system": True,
    },
]


@templates_app.command("seed")
def seed_templates(
    dry_run: bool = typer.Option(
        False, help="Preview without inserting"
    ),
    reset: bool = typer.Option(
        False, help="Delete all existing system templates and re-insert"
    ),
) -> None:
    """Seed the agent_templates table with 8 pre-defined system templates."""
    db = get_service_client()

    if reset:
        console.print("[yellow]Resetting system templates...[/yellow]")
        try:
            db.table("agent_templates").delete().eq("is_system", True).execute()
            console.print("[green]System templates deleted.[/green]")
        except Exception as exc:
            logger.exception("Failed to reset system templates")
            console.print(f"[red]Error resetting templates: {exc}[/red]")

    if dry_run:
        console.print("[bold cyan]--dry-run mode: previewing 8 templates[/bold cyan]\n")
        table = Table(title="Templates Preview")
        table.add_column("Name", style="cyan")
        table.add_column("Category", style="magenta")
        table.add_column("Tools", style="green")
        for t in TEMPLATES:
            table.add_row(
                t["name"],
                t["category"],
                ", ".join(t["suggested_tools"]) if t["suggested_tools"] else "(none)",
            )
        console.print(table)
        console.print(f"\n[bold]Total:[/bold] {len(TEMPLATES)} template(s) — not inserted")
        return

    inserted = 0
    skipped = 0
    errors = 0

    for template in TEMPLATES:
        try:
            existing = (
                db.table("agent_templates")
                .select("id")
                .eq("name", template["name"])
                .eq("is_system", True)
                .execute()
            )
            if existing.data:
                console.print(f"  [dim]-[/dim] {template['name']} (already exists, skipped)")
                skipped += 1
                continue

            db.table("agent_templates").insert(
                {
                    "id": str(uuid.uuid5(uuid.NAMESPACE_DNS, f"fap.system.template.{template['name']}")),
                    "name": template["name"],
                    "description": template["description"],
                    "category": template["category"],
                    "soul_json": template["soul_json"],
                    "suggested_tools": template["suggested_tools"],
                    "max_iter": template["max_iter"],
                    "is_system": template["is_system"],
                },
            ).execute()
            inserted += 1
            console.print(f"  [green]OK[/green] {template['name']}")
        except Exception as exc:
            logger.exception("Failed to insert template '%s'", template["name"])
            console.print(f"  [red]FAIL[/red] {template['name']}: {exc}")
            errors += 1

    console.print(f"\n[bold]Inserted:[/bold] {inserted} template(s)")
    if skipped:
        console.print(f"[dim]Skipped:[/dim] {skipped} (already exist)")
    if errors:
        console.print(f"[bold red]Errors:[/bold red] {errors}")
    if reset:
        console.print("[yellow]Run migration 030 first if table does not exist.[/yellow]")
