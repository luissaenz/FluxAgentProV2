"""src/cli/main.py — Entry point for FAP-CLI."""

import io
import sys

import typer

# Analysis Final §2.2: Ensure UTF-8 on Windows for Rich compatibility
# Mitigation §7: Only apply if TTY to avoid interference with tests/redirection
if sys.platform == "win32" and sys.stdout.isatty():
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8")

from src.cli.commands.baseline_check import baseline_check
from src.cli.commands.bundle_export import bundle_app
from src.cli.commands.check_deadlock import check_deadlock
from src.cli.commands.check_env import check_env
from src.cli.commands.dev import dev_command
from src.cli.commands.export import export_agents
from src.cli.commands.init import init_bundle
from src.cli.commands.lint_fix import lint_fix
from src.cli.commands.login import login
from src.cli.commands.package import package_bundle
from src.cli.commands.perf_check import perf_check
from src.cli.commands.phase_close import phase_close
from src.cli.commands.publish import publish_bundle
from src.cli.commands.run import app as run_app
from src.cli.commands.scaffold import scaffold_command
from src.cli.commands.security_audit import security_audit
from src.cli.commands.stress_bench import stress_bench
from src.cli.commands.sync_config import sync_config
from src.cli.commands.sync_step_names import sync_step_names
from src.cli.commands.templates_seed import templates_app
from src.cli.commands.test_scenarios import test_scenarios
from src.cli.commands.test_step import test_step
from src.cli.commands.tool_call_test import test_tool_call
from src.cli.commands.tools_list import tools_list_app
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
app.add_typer(templates_app, name="templates")
app.add_typer(tools_list_app, name="tools")
app.command("validate-tools")(validate_tools_command)
app.command("validate-architect-output")(validate_architect_output)
app.command("test-scenarios")(test_scenarios)
app.command("phase-close")(phase_close)
app.command("check-deadlock")(check_deadlock)
app.command("check-env")(check_env)
app.command("baseline-check")(baseline_check)
app.command("test-step")(test_step)
app.command("security-audit")(security_audit)
app.command("stress-bench")(stress_bench)
app.command("perf-check")(perf_check)
app.command("sync-step-names")(sync_step_names)
app.command("sync-config")(sync_config)
app.command("lint-fix")(lint_fix)
app.command("test-tool-call")(test_tool_call)
app.add_typer(bundle_app, name="bundle")

if __name__ == "__main__":
    app()
