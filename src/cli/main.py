"""src/cli/main.py — Entry point for FAP-CLI."""

import io
import sys

import typer

# Analysis Final §2.2: Ensure UTF-8 on Windows for Rich compatibility
# Mitigation §7: Only apply if TTY to avoid interference with tests/redirection
if sys.platform == "win32" and sys.stdout.isatty():
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8")

from src.cli.baseline import baseline_check
from src.cli.commands.dev import dev_command
from src.cli.commands.export import export_agents
from src.cli.commands.init import init_bundle
from src.cli.commands.login import login
from src.cli.commands.package import package_bundle
from src.cli.commands.phase_close import phase_close
from src.cli.commands.publish import publish_bundle
from src.cli.commands.run import app as run_app
from src.cli.commands.scaffold import scaffold_command
from src.cli.commands.test_scenarios import test_scenarios
from src.cli.commands.validate import validate_bundle
from src.cli.commands.validate_architect import validate_architect_output
from src.cli.commands.validate_tools import validate_tools_command

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
app.command("validate-tools")(validate_tools_command)
app.command("validate-architect-output")(validate_architect_output)
app.command("test-scenarios")(test_scenarios)
app.command("phase-close")(phase_close)
app.command("baseline-check")(baseline_check)

if __name__ == "__main__":
    app()
