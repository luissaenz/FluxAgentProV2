"""src/cli/main.py — Entry point for FAP-CLI."""

import typer

from src.cli.commands.export import export_agents
from src.cli.commands.init import init_bundle
from src.cli.commands.package import package_bundle
from src.cli.commands.validate import validate_bundle

app = typer.Typer(
    help="FluxAgentPro-v2 CLI — Manage agents, flows, and skills via Bundles.",
    no_args_is_help=True,
    rich_markup_mode="rich",
)

# Register commands
app.command("init")(init_bundle)
app.command("validate")(validate_bundle)
app.command("package")(package_bundle)
app.command("export-agents")(export_agents)

if __name__ == "__main__":
    app()
