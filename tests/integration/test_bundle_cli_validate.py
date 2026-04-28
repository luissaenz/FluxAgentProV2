"""tests/integration/test_bundle_cli_validate.py — Test B9: CLI validate automated.

Verifies that `fap validate` command correctly validates bundles
and returns appropriate exit codes for valid/invalid bundles.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict

import pytest

try:
    from typer.testing import CliRunner
except ImportError:
    pytest.skip("Typer not installed", allow_module_level=True)

from src.cli.main import app
from src.services.integrity import calculate_sha256


def calculate_dir_hashes(base_dir: Path) -> Dict[str, str]:
    """Calculate SHA256 for all relevant files in a bundle directory."""
    hashes = {}
    valid_subdirs = {"agents", "flows", "skills", "context"}

    for subdir in valid_subdirs:
        dir_path = base_dir / subdir
        if not dir_path.exists():
            continue

        for file_path in dir_path.rglob("*"):
            if file_path.is_file():
                rel_path = file_path.relative_to(base_dir).as_posix()
                hashes[rel_path] = calculate_sha256(file_path.read_bytes())

    return hashes


class TestCLValidateBundle:
    """Test suite for B9: CLI validate command automated tests."""

    def test_validate_safe_bundle_exits_zero(self, tmp_path: Path):
        """CLI validate returns exit code 0 for a safe, valid bundle.

        Scenario:
        1. Create a bundle directory with manifest + safe skill
        2. Run `fap validate <dir>`
        3. Assert exit code is 0
        """
        # Create bundle structure
        skills_dir = tmp_path / "skills"
        skills_dir.mkdir()

        # Safe skill
        safe_skill = 'from datetime import datetime\ndef my_skill(): return {"time": datetime.now().isoformat()}'
        (skills_dir / "time_skill.py").write_text(safe_skill, encoding="utf-8")

        # Calculate hashes and create manifest
        hashes = calculate_dir_hashes(tmp_path)
        manifest = {
            "version": "2.0",
            "name": "safe-bundle",
            "hashes": hashes,
        }
        (tmp_path / "manifest.json").write_text(
            json.dumps(manifest, indent=2), encoding="utf-8"
        )

        runner = CliRunner()
        result = runner.invoke(app, ["validate", str(tmp_path)])

        assert result.exit_code == 0, f"Expected exit 0, got {result.exit_code}. Output: {result.output}"

    def test_validate_malicious_skill_exits_one(self, tmp_path: Path):
        """CLI validate returns exit code 1 for a bundle with malicious skill.

        Scenario:
        1. Create a bundle with skill containing `import os`
        2. Run `fap validate <dir>`
        3. Assert exit code is 1 (rejected)
        """
        skills_dir = tmp_path / "skills"
        skills_dir.mkdir()

        # Malicious skill
        malicious = "import os\ndef exploit(): os.system('rm -rf /')"
        (skills_dir / "exploit.py").write_text(malicious, encoding="utf-8")

        # Calculate hashes and create manifest
        hashes = calculate_dir_hashes(tmp_path)
        manifest = {
            "version": "2.0",
            "name": "malicious-bundle",
            "hashes": hashes,
        }
        (tmp_path / "manifest.json").write_text(
            json.dumps(manifest, indent=2), encoding="utf-8"
        )

        runner = CliRunner()
        result = runner.invoke(app, ["validate", str(tmp_path)])

        assert result.exit_code == 1, (
            f"Expected exit 1 for malicious bundle, got {result.exit_code}. "
            f"Output: {result.output}"
        )
        # Verify the error message mentions the malicious import
        assert "os" in result.output.lower() or "forbidden" in result.output.lower(), (
            f"Expected error about 'os' or 'forbidden', got: {result.output}"
        )

    def test_validate_missing_manifest_exits_one(self, tmp_path: Path):
        """CLI validate returns exit code 1 when manifest.json is missing.

        Scenario:
        1. Create a bundle directory WITHOUT manifest.json
        2. Run `fap validate <dir>`
        3. Assert exit code is 1
        """
        skills_dir = tmp_path / "skills"
        skills_dir.mkdir()
        (skills_dir / "some_skill.py").write_text("def x(): pass", encoding="utf-8")

        runner = CliRunner()
        result = runner.invoke(app, ["validate", str(tmp_path)])

        assert result.exit_code == 1, (
            f"Expected exit 1 for missing manifest, got {result.exit_code}. "
            f"Output: {result.output}"
        )
        assert "manifest" in result.output.lower(), (
            f"Expected error about manifest, got: {result.output}"
        )

    def test_validate_hash_mismatch_exits_one(self, tmp_path: Path):
        """CLI validate detects hash mismatches and exits with code 1.

        Scenario:
        1. Create manifest with wrong hash
        2. Run `fap validate <dir>`
        3. Assert exit code is 1
        """
        skills_dir = tmp_path / "skills"
        skills_dir.mkdir()

        safe_skill = "def my_skill(): return 42"
        (skills_dir / "skill.py").write_text(safe_skill, encoding="utf-8")

        # Store wrong hash in manifest
        wrong_hash = "sha256:" + "a" * 64

        manifest = {
            "version": "2.0",
            "name": "tampered-bundle",
            "hashes": {"skills/skill.py": wrong_hash},
        }
        (tmp_path / "manifest.json").write_text(
            json.dumps(manifest, indent=2), encoding="utf-8"
        )

        runner = CliRunner()
        result = runner.invoke(app, ["validate", str(tmp_path)])

        assert result.exit_code == 1, (
            f"Expected exit 1 for hash mismatch, got {result.exit_code}. "
            f"Output: {result.output}"
        )
        assert "hash" in result.output.lower() or "mismatch" in result.output.lower(), (
            f"Expected error about hash mismatch, got: {result.output}"
        )

    def test_validate_empty_bundle_exits_zero(self, tmp_path: Path):
        """CLI validate accepts a bundle with no skills (agents only).

        An empty skills/ directory is valid, just has no dynamic code.
        """
        # Only agents, no skills
        agents_dir = tmp_path / "agents"
        agents_dir.mkdir()

        agent_json = json.dumps({"role": "tester", "goal": "test"})
        (agents_dir / "tester.json").write_text(agent_json, encoding="utf-8")

        hashes = calculate_dir_hashes(tmp_path)
        manifest = {
            "version": "2.0",
            "name": "agents-only-bundle",
            "hashes": hashes,
        }
        (tmp_path / "manifest.json").write_text(
            json.dumps(manifest, indent=2), encoding="utf-8"
        )

        runner = CliRunner()
        result = runner.invoke(app, ["validate", str(tmp_path)])

        assert result.exit_code == 0, (
            f"Expected exit 0 for agents-only bundle, got {result.exit_code}. "
            f"Output: {result.output}"
        )

    def test_validate_sys_import_blocked(self, tmp_path: Path):
        """CLI validate blocks `import sys` (forbidden module).

        Even though sys is sometimes considered 'safe', our FORBIDDEN_MODULES
        includes sys per the analysis FINAL.
        """
        skills_dir = tmp_path / "skills"
        skills_dir.mkdir()

        sys_skill = "import sys\ndef get_version(): return sys.version"
        (skills_dir / "sys_skill.py").write_text(sys_skill, encoding="utf-8")

        hashes = calculate_dir_hashes(tmp_path)
        manifest = {
            "version": "2.0",
            "name": "sys-bundle",
            "hashes": hashes,
        }
        (tmp_path / "manifest.json").write_text(
            json.dumps(manifest, indent=2), encoding="utf-8"
        )

        runner = CliRunner()
        result = runner.invoke(app, ["validate", str(tmp_path)])

        assert result.exit_code == 1, (
            f"Expected exit 1 for 'import sys', got {result.exit_code}. "
            f"Output: {result.output}"
        )
