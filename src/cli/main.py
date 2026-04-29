"""src/cli/main.py — Entry point for FAP-CLI."""

import typer

from src.cli.commands.dev import dev_command
from src.cli.commands.export import export_agents
from src.cli.commands.init import init_bundle
from src.cli.commands.login import login
from src.cli.commands.package import package_bundle
from src.cli.commands.publish import publish_bundle
from src.cli.commands.run import app as run_app
from src.cli.commands.scaffold import scaffold_command
from src.cli.commands.validate import validate_bundle

app = typer.Typer(
    help="FluxAgentPro-v2 CLI — Manage agents, flows, and skills via Bundles.",
    no_args_is_help=True,
    rich_markup_mode="rich",
)

# Register commands
app.command("init")(init_bundle)
app.command("login")(login)
app.command("validate")(validate_bundle)
app.command("package")(package_bundle)
app.command("publish")(publish_bundle)
app.add_typer(run_app, name="run")
app.command("scaffold")(scaffold_command)
app.command("dev")(dev_command)
app.command("export-agents")(export_agents)

if __name__ == "__main__":
    app()
