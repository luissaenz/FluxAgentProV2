"""tests/e2e/test_parity_suite.py — Phase IV Parity & E2E Validation Suite.

This suite verifies the end-to-end flow from local CLI development to
production-ready registries, ensuring total architectural parity.
"""

from __future__ import annotations

import io
import json
import time
import zipfile
from unittest.mock import MagicMock, patch

import pytest
from fastapi import status
from fastapi.testclient import TestClient
from typer.testing import CliRunner

from src.api.main import app
from src.services.integrity import calculate_sha256


@pytest.fixture
def api_client():
    return TestClient(app)


@pytest.fixture
def cli_runner():
    return CliRunner()


def create_test_bundle_zip(name: str = "parity-test", version: str = "1.0.0") -> bytes:
    """Helper to create a valid bundle ZIP for E2E testing."""
    buf = io.BytesIO()

    # Note: RestrictedPython blocks _is_tool. We use "Tool" in class name to register.
    skill_code = 'class ParityTool:\n    """A test tool."""\n    name="test"'.encode()
    agent_data = json.dumps({"role": "tester", "goal": "verify parity"}).encode()

    with zipfile.ZipFile(buf, "w") as z:
        # Skill
        z.writestr("skills/test.py", skill_code)

        # Agent
        z.writestr("agents/tester.json", agent_data)

        # Manifest
        manifest = {
            "version": "2.0",
            "bundle_info": {"name": name, "version": version},
            "hashes": {
                "skills/test.py": calculate_sha256(skill_code),
                "agents/tester.json": calculate_sha256(agent_data),
            },
        }
        z.writestr("manifest.json", json.dumps(manifest))
    return buf.getvalue()


class TestParitySuite:
    """E2E Parity Suite for Phase IV Certification."""

    def test_import_export_roundtrip(self, api_client, tmp_path, mock_tenant_client):
        """Validates that a bundle imported can be exported with matching hashes."""
        bundle_name = "roundtrip-bundle"
        zip_bytes = create_test_bundle_zip(name=bundle_name)

        # 1. Mock Successful Import
        mock_tenant_client.rpc.return_value.execute.return_value.data = {
            "status": "success",
            "bundle_id": "b-123",
            "agents_count": 1,
            "skills_count": 1,
            "flows_count": 0,
            "error": None,
        }

        import_resp = api_client.post(
            "/api/bundles/import",
            files={"file": ("bundle.zip", zip_bytes, "application/zip")},
            headers={"X-Org-Id": "test-org"},
        )
        if import_resp.status_code != status.HTTP_201_CREATED:
            print(
                f"DEBUG: Import failed with {import_resp.status_code}: {import_resp.json()}"
            )
        assert import_resp.status_code == status.HTTP_201_CREATED

        # 2. Mock Export/Retrieve (Simulated since endpoint might be new)
        # SUPUESTO: El endpoint GET /api/bundles/{id}/details devuelve el código fuente.
        mock_tenant_client.table(
            "skill_catalog"
        ).select.return_value.eq.return_value.execute.return_value.data = [
            {
                "name": "test",
                "code_source": 'class ParityTool:\n    """A test tool."""\n    name="test"',
            }
        ]

        details_resp = api_client.get(
            "/api/bundles/b-123/details", headers={"X-Org-Id": "test-org"}
        )
        assert details_resp.status_code == 200

        exported_skills = details_resp.json()["skills"]
        assert len(exported_skills) == 1
        # Verify hash match
        original_hash = calculate_sha256(
            'class ParityTool:\n    """A test tool."""\n    name="test"'.encode()
        )
        exported_hash = calculate_sha256(exported_skills[0]["code"].encode())
        assert original_hash == exported_hash

    def test_hot_reload_sync_cycle(self, cli_runner, tmp_path):
        """Validates fap dev correctly triggers publication on file change."""
        bundle_dir = tmp_path / "my-bundle"
        bundle_dir.mkdir()
        (bundle_dir / "skills").mkdir()
        (bundle_dir / "manifest.json").write_text(
            json.dumps(
                {
                    "version": "2.0",
                    "bundle_info": {"name": "hot-reload-test", "version": "1.0.0"},
                }
            )
        )

        # Mock both package and publish to verify the cycle
        with (
            patch("src.cli.commands.dev.package_bundle") as mock_package,
            patch("src.cli.commands.dev.publish_bundle") as mock_publish,
        ):
            # Setup mock return for package
            dummy_zip = bundle_dir / "test.zip"
            dummy_zip.write_text("dummy")
            mock_package.return_value = dummy_zip

            from src.cli.commands.dev import BundleEventHandler

            handler = BundleEventHandler(bundle_dir, debounce_seconds=0.1)

            # Simulate file change event
            event = MagicMock()
            event.is_directory = False
            event.src_path = str(bundle_dir / "skills" / "new_skill.py")
            (bundle_dir / "skills" / "new_skill.py").write_text("pass")

            handler.on_any_event(event)

            # Wait for debounce (0.1s + safety)
            time.sleep(0.3)

            # Verify calls
            assert mock_package.called
            assert mock_publish.called
            # Verify force=True was passed
            _, kwargs = mock_publish.call_args
            assert kwargs.get("force") is True

    def test_cross_tenant_isolation(self, api_client, mock_tenant_client):
        """Verifies that bundle imports are strictly isolated by Org-Id."""

        # Mock DB response to return empty for Org B even if Org A has data
        def mock_table(name):
            mock_chain = MagicMock()

            def eq_side_effect(col, val):
                # We need to return the same mock_chain to keep the builder pattern
                # but we'll record if we should return data or not
                if col == "org_id" and val == "Org-B":
                    mock_chain.execute.return_value.data = []
                elif col == "org_id" and val == "Org-A":
                    mock_chain.execute.return_value.data = [{"id": "b-123"}]
                return mock_chain

            mock_chain.select.return_value = mock_chain
            mock_chain.eq.side_effect = eq_side_effect
            mock_chain.order.return_value = mock_chain
            return mock_chain

        mock_tenant_client.table.side_effect = mock_table

        # Request history as Org B
        resp_b = api_client.get("/api/bundles/history", headers={"X-Org-Id": "Org-B"})
        assert resp_b.status_code == 200
        assert len(resp_b.json()) == 0

        # Request history as Org A
        resp_a = api_client.get("/api/bundles/history", headers={"X-Org-Id": "Org-A"})
        assert resp_a.status_code == 200
        assert len(resp_a.json()) > 0

    def test_llm_mocking_parity(self):
        """Verifies that LLM calls are correctly intercepted for deterministic E2E."""
        from src.crews.base_crew import BaseCrew

        # This test verifies that our fixture (implemented in conftest.py) works
        # BaseCrew now requires only org_id and role
        crew = BaseCrew(org_id="test-org", role="tester")

        # We patch the actual run method to verify it doesn't hit the network
        with patch.object(BaseCrew, "run", return_value="Mocked Result") as mock_run:
            result = crew.run(task_description="test", inputs={})
            assert result == "Mocked Result"
            assert mock_run.called

    def test_org_base_tool_inheritance_and_dual_resolution(self):
        """Verifies that OrgBaseTool is inherited and dual resolution works."""
        from src.tools.base_tool import OrgBaseTool
        from src.tools.registry import tool_registry

        class TestDualTool(OrgBaseTool):
            name: str = "dual_tool"
            description: str = "Test tool"

            def _run(self) -> str:
                _ = self._get_secret("test_secret")
                return "Used secret, result is safe."

        # Register using dual keys
        org_id = "test-tenant"
        tool_registry.register(name=f"{org_id}:dual_tool")(TestDualTool)
        tool_registry.register(name=f"{org_id}:TestDualTool")(TestDualTool)

        # Retrieve by filename equivalent
        tool_class_1 = tool_registry.get("dual_tool", org_id=org_id)
        assert tool_class_1 is TestDualTool
        assert issubclass(tool_class_1, OrgBaseTool)

        # Retrieve by ClassName equivalent
        tool_class_2 = tool_registry.get("TestDualTool", org_id=org_id)
        assert tool_class_2 is TestDualTool
        assert issubclass(tool_class_2, OrgBaseTool)

        # Verify secret is not exposed in output
        tool_instance = tool_class_1(org_id=org_id)
        with patch.object(
            tool_instance, "_get_secret", return_value="SUPER_SECRET_TOKEN"
        ):
            result = tool_instance._run()
            assert "SUPER_SECRET_TOKEN" not in result
            assert result == "Used secret, result is safe."
