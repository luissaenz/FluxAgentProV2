"""tests/integration/test_bundle_upsert.py — Test B6: Upsert functionality.

Verifies that re-importing a bundle with existing agents/skills
performs an UPDATE instead of a duplicate key error.
"""

from __future__ import annotations

import io
import json
import zipfile
from unittest.mock import MagicMock, patch

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


class TestBundleUpsert:
    """Test suite for B6: Upsert (Agent/Skill already exists)."""

    def test_upsert_replaces_existing_agent(self):
        """Verifies that re-importing the same agent updates it.

        Note: We mock the RPC call to simulate successful upsert behavior.
        The real logic is tested in PostgreSQL (0027_bundle_rpc.sql).
        """
        org_id = "test-org-upsert"
        # 1. Initial bundle state
        agent_data_v1 = {"role": "upsert_agent", "goal": "Initial Goal"}
        agent_json_v1 = json.dumps(agent_data_v1)
        manifest_v1 = {
            "version": "2.0",
            "bundle_info": {"name": "upsert-test-v1"},
            "hashes": {
                "agents/upsert_agent.json": calculate_sha256(agent_json_v1.encode())
            },
        }
        zip_v1 = create_test_zip(
            {
                "manifest.json": json.dumps(manifest_v1),
                "agents/upsert_agent.json": agent_json_v1,
            }
        )

        # 2. Updated bundle state (same role, different goal)
        agent_data_v2 = {"role": "upsert_agent", "goal": "Updated Goal"}
        agent_json_v2 = json.dumps(agent_data_v2)
        manifest_v2 = {
            "version": "2.0",
            "bundle_info": {"name": "upsert-test-v2"},
            "hashes": {
                "agents/upsert_agent.json": calculate_sha256(agent_json_v2.encode())
            },
        }
        zip_v2 = create_test_zip(
            {
                "manifest.json": json.dumps(manifest_v2),
                "agents/upsert_agent.json": agent_json_v2,
            }
        )

        # Mock successful RPC response for both imports
        mock_db = MagicMock()
        rpc_chain = MagicMock()

        # Result for V1
        res_v1 = BundleRPCResult(
            status="success",
            bundle_id="bundle-v1",
            agents_count=1,
            flows_count=0,
            skills_count=0,
        ).model_dump()

        # Result for V2
        res_v2 = BundleRPCResult(
            status="success",
            bundle_id="bundle-v2",
            agents_count=1,
            flows_count=0,
            skills_count=0,
        ).model_dump()

        rpc_chain.execute.side_effect = [MagicMock(data=res_v1), MagicMock(data=res_v2)]
        mock_db.rpc.return_value = rpc_chain

        cm = MagicMock()
        cm.__enter__.return_value = mock_db
        cm.__exit__.return_value = False

        with patch("src.services.import_service.get_tenant_client", return_value=cm):
            service = ImportService(org_id=org_id)

            # First import
            result1 = service.process_bundle(zip_v1)
            assert result1.status == "success"
            assert result1.bundle_id == "bundle-v1"

            # Second import (same agent role)
            result2 = service.process_bundle(zip_v2)
            assert result2.status == "success"
            assert result2.bundle_id == "bundle-v2"

        # Verification of calls
        assert mock_db.rpc.call_count == 2
        # Verify the second call payload contains the updated goal
        call_args = mock_db.rpc.call_args_list[1]
        assert call_args[0][0] == "import_bundle_atomic"
        full_payload = call_args[0][1]
        assert full_payload["p_payload"]["agents"][0]["goal"] == "Updated Goal"

    def test_upsert_replaces_existing_skill(self):
        """Verifies that re-importing a skill with same name updates its code."""
        org_id = "test-org-upsert-skill"

        # Initial Skill
        skill_v1 = "def my_skill(): return 1"
        manifest_v1 = {
            "version": "2.0",
            "hashes": {"skills/test.py": calculate_sha256(skill_v1.encode())},
        }
        zip_v1 = create_test_zip(
            {
                "manifest.json": json.dumps(manifest_v1),
                "skills/test.py": skill_v1,
            }
        )

        # Updated Skill
        skill_v2 = "def my_skill(): return 2"
        manifest_v2 = {
            "version": "2.0",
            "hashes": {"skills/test.py": calculate_sha256(skill_v2.encode())},
        }
        zip_v2 = create_test_zip(
            {
                "manifest.json": json.dumps(manifest_v2),
                "skills/test.py": skill_v2,
            }
        )

        mock_db = MagicMock()
        rpc_chain = MagicMock()

        res_v1 = BundleRPCResult(
            status="success", bundle_id="b1", skills_count=1
        ).model_dump()
        res_v2 = BundleRPCResult(
            status="success", bundle_id="b2", skills_count=1
        ).model_dump()

        rpc_chain.execute.side_effect = [MagicMock(data=res_v1), MagicMock(data=res_v2)]
        mock_db.rpc.return_value = rpc_chain
        cm = MagicMock()
        cm.__enter__.return_value = mock_db
        cm.__exit__.return_value = False

        with patch("src.services.import_service.get_tenant_client", return_value=cm):
            service = ImportService(org_id=org_id)
            service.process_bundle(zip_v1)
            service.process_bundle(zip_v2)

        # Verify second call payload
        call_args = mock_db.rpc.call_args_list[1]
        full_payload = call_args[0][1]
        assert full_payload["p_payload"]["skills"]["test.py"] == skill_v2
