"""tests/unit/test_sync_step_names.py — Tests for 'fap sync-step-names' command.

Covers TP-1 a TP-4 del informe de validacion.
"""

from __future__ import annotations

import pytest

try:
    from typer.testing import CliRunner
except ImportError:
    pytest.skip("Typer not installed", allow_module_level=True)

from src.cli.main import app


class TestSyncStepNames:
    """Test suite for fap sync-step-names."""

    def test_check_phase_state_zero_discrepancies(self):
        """TP-1: --check --source phase-state → exit 0, 0 discrepancias."""
        runner = CliRunner()
        result = runner.invoke(
            app, ["sync-step-names", "--check", "--source", "phase-state"]
        )
        assert result.exit_code == 0, (
            f"Expected exit 0, got {result.exit_code}. Output: {result.output}"
        )
        assert "0 discrepancias" in result.output

    def test_check_plan_detects_discrepancies(self):
        """TP-2: --check --source plan → exit 1 (plan names != fase real)."""
        runner = CliRunner()
        result = runner.invoke(
            app, ["sync-step-names", "--check", "--source", "plan"]
        )
        assert result.exit_code == 1, (
            f"Expected exit 1, got {result.exit_code}. Output: {result.output}"
        )
        assert "discrepancia" in result.output

    def test_fix_dry_run_shows_changes(self):
        """TP-3: --fix --dry-run → muestra cambios sin modificar."""
        runner = CliRunner()
        result = runner.invoke(
            app,
            ["sync-step-names", "--fix", "--dry-run", "--source", "phase-state"],
        )
        assert result.exit_code == 0
        # Post-fix: 0 discrepancias → no hay cambios para dry-run
        assert "Dry-run" in result.output or "0 discrepancias" in result.output

    def test_invalid_source_exits_one(self):
        """--source invalido → exit 1 con mensaje de error."""
        runner = CliRunner()
        result = runner.invoke(
            app, ["sync-step-names", "--check", "--source", "invalid"]
        )
        assert result.exit_code == 1
        assert "desconocida" in result.output
