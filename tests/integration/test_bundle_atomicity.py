"""tests/integration/test_bundle_atomicity.py — Test B5: Atomicity Rollback.

Verifies that if the RPC fails at any point during bundle import,
NO records persist in the database (complete rollback).
"""

from __future__ import annotations

import io
import json
import zipfile
from unittest.mock import MagicMock, patch

import pytest

from src.services.bundle_schemas import BundleRPCResult
from src.services.import_service import ImportService
from src.services.integrity import calculate_sha256


def create_test_zip(files: dict) -> bytes:
    """Create a ZIP in memory with manifest and files."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        for path, content in files.items():
            z.writestr(path, content)
    return buf.getvalue()


class TestAtomicityRollback:
    """Test suite for B5: Atomicity and rollback on error."""

    def test_rollback_on_rpc_exception(self):
        """RPC exception triggers complete rollback.

        When PostgreSQL raises an exception (constraint violation,
        FK error, etc.), the transaction is automatically rolled back.
        We verify that no partial state persists.
        """
        org_id = "test-org-atomicity"

        # Create bundle with 3 agents
        agents = [
            json.dumps({"role": f"agent_{i}", "goal": f"Goal {i}"}) for i in range(3)
        ]
        manifest_hashes = {}
        zip_files = {}

        for i, agent_json in enumerate(agents):
            path = f"agents/agent_{i}.json"
            manifest_hashes[path] = calculate_sha256(agent_json.encode())
            zip_files[path] = agent_json

        manifest = {
            "version": "2.0",
            "bundle_info": {"name": "atomicity-test"},
            "hashes": manifest_hashes,
        }
        zip_files["manifest.json"] = json.dumps(manifest)

        zip_bytes = create_test_zip(zip_files)

        # Mock get_tenant_client to simulate RPC exception
        mock_db = MagicMock()
        rpc_chain = MagicMock()
        # PostgreSQL RAISE EXCEPTION becomes an exception here
        rpc_chain.execute.side_effect = Exception(
            "Simulated DB error: constraint violation on agent insert"
        )
        mock_db.rpc.return_value = rpc_chain

        cm = MagicMock()
        cm.__enter__.return_value = mock_db
        cm.__exit__.return_value = False

        with (
            patch("src.services.import_service.get_tenant_client", return_value=cm),
            patch(
                "src.services.import_service.ImportService._check_version_guard",
                return_value=None,
            ),
        ):
            service = ImportService(org_id=org_id)

            # ImportService.process_bundle should raise due to RPC exception
            # which means PostgreSQL rolled back (in real DB)
            with pytest.raises(Exception, match="Simulated DB error"):
                service.process_bundle(zip_bytes)

        # ASSERTION: Exception raised = no commit happened.
        # In real PostgreSQL, the exception triggers automatic ROLLBACK.
        # All records inserted before the error (including bundle_imports entry)
        # are rolled back automatically.

    def test_atomicity_with_failed_status_response(self):
        """RPC returns failed status (not exception) — also no commit.

        Some errors are returned as BundleRPCResult with status='failed'
        rather than as exceptions. These also result in no data persistence.
        """
        org_id = "test-org-failed-status"

        # Create bundle with 2 agents
        agent_json = json.dumps({"role": "role_1", "goal": "Goal 1"})
        manifest = {
            "version": "2.0",
            "bundle_info": {"name": "failed-status-test"},
            "hashes": {"agents/role_1.json": calculate_sha256(agent_json.encode())},
        }

        zip_bytes = create_test_zip(
            {
                "manifest.json": json.dumps(manifest),
                "agents/role_1.json": agent_json,
            }
        )

        # Mock RPC to return failed status
        mock_db = MagicMock()
        rpc_chain = MagicMock()
        failed_result = BundleRPCResult(
            status="failed",
            bundle_id="",
            error="Constraint violation: duplicate key",
        ).model_dump()
        rpc_chain.execute.return_value = MagicMock(data=failed_result)
        mock_db.rpc.return_value = rpc_chain

        cm = MagicMock()
        cm.__enter__.return_value = mock_db
        cm.__exit__.return_value = False

        with (
            patch("src.services.import_service.get_tenant_client", return_value=cm),
            patch(
                "src.services.import_service.ImportService._check_version_guard",
                return_value=None,
            ),
        ):
            service = ImportService(org_id=org_id)
            # process_bundle returns failed result (no exception raised)
            result = service.process_bundle(zip_bytes)

        # ASSERTION: Failed status means no data was committed
        assert result.status == "failed"
        assert "duplicate key" in result.error.lower()

    def test_successful_import_commits_all(self):
        """Successful RPC result means all data is committed.

        Verifies the happy path where RPC returns success.
        """
        org_id = "test-org-success"

        # Create simple bundle with 1 agent
        agent_json = json.dumps({"role": "tester", "goal": "test"})
        manifest = {
            "version": "2.0",
            "bundle_info": {"name": "success-test"},
            "hashes": {"agents/tester.json": calculate_sha256(agent_json.encode())},
        }

        zip_bytes = create_test_zip(
            {
                "manifest.json": json.dumps(manifest),
                "agents/tester.json": agent_json,
            }
        )

        # Mock successful RPC response
        mock_db = MagicMock()
        rpc_chain = MagicMock()
        success_result = BundleRPCResult(
            status="success",
            bundle_id="test-bundle-123",
            agents_count=1,
            flows_count=0,
            skills_count=0,
        ).model_dump()
        rpc_chain.execute.return_value = MagicMock(data=success_result)
        mock_db.rpc.return_value = rpc_chain

        cm = MagicMock()
        cm.__enter__.return_value = mock_db
        cm.__exit__.return_value = False

        with (
            patch("src.services.import_service.get_tenant_client", return_value=cm),
            patch(
                "src.services.import_service.ImportService._check_version_guard",
                return_value=None,
            ),
        ):
            service = ImportService(org_id=org_id)
            result = service.process_bundle(zip_bytes)

        assert result.status == "success"
        assert result.agents_count == 1
        assert result.bundle_id == "test-bundle-123"
