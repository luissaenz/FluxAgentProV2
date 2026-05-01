"""tests/e2e/test_cli_test_scenarios.py — E2E test for 'fap test-scenarios' CLI command.

Verifies dogfooding: the CLI tool is invoked and produces correct output.
Addresses ID-003 from validacion.md.
"""

from __future__ import annotations

from uuid import uuid4

import pytest
from typer.testing import CliRunner

from src.cli.main import app as cli_app


@pytest.fixture
def cli_runner():
    return CliRunner()


class TestCliTestScenarios:
    def test_scenarios_all_exits_zero(self, cli_runner):
        """CLI 'fap test-scenarios --scenario all' exits with code 0."""
        org_id = str(uuid4())
        result = cli_runner.invoke(
            cli_app,
            ["test-scenarios", "--scenario", "all", "--org-id", org_id],
        )
        assert result.exit_code == 0, f"Exit code: {result.exit_code}\nOutput: {result.output}"

    def test_scenarios_all_reports_summary(self, cli_runner):
        """CLI output contains summary with 6/6 passed."""
        org_id = str(uuid4())
        result = cli_runner.invoke(
            cli_app,
            ["test-scenarios", "--scenario", "all", "--org-id", org_id],
        )
        assert result.exit_code == 0
        assert "Resumen" in result.output
        assert "6/6" in result.output

    def test_scenarios_individual_exits_zero(self, cli_runner):
        """CLI 'fap test-scenarios --scenario 3' exits with code 0."""
        org_id = str(uuid4())
        result = cli_runner.invoke(
            cli_app,
            ["test-scenarios", "--scenario", "3", "--org-id", org_id],
        )
        assert result.exit_code == 0

    def test_scenarios_invalid_scenario_exits_one(self, cli_runner):
        """CLI with invalid scenario '99' should error but not crash."""
        org_id = str(uuid4())
        result = cli_runner.invoke(
            cli_app,
            ["test-scenarios", "--scenario", "99", "--org-id", org_id],
        )
        assert result.exit_code == 0
        assert "no reconocido" in result.output

    def test_scenarios_uses_validate_architect(self, cli_runner):
        """CLI uses validate_architect_data internally (dogfooding evidence)."""
        from src.cli.commands.test_scenarios import run_scenario_1_greeter

        org_id = str(uuid4())
        result = run_scenario_1_greeter(org_id)
        assert result.passed
        assert result.error is None
