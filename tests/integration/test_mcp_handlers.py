"""Tests for MCP Handlers — Integration with Flows and DB Mocking."""

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from src.mcp.exceptions import AuthError
from src.mcp.handlers import (
    handle_approve_task,
    handle_execute_flow,
    handle_get_task,
)


@pytest.mark.asyncio
async def test_handle_execute_flow_success(mock_service_client, sample_org_id):
    """Test successful flow execution via handler."""
    claims = {"sub": "user_123", "role": "authenticated"}
    input_data = {"test": "data"}

    # Mock verify_org_membership to return a user_id
    with patch("src.mcp.handlers.verify_org_membership") as mock_auth:
        mock_auth.return_value = {"user_id": "user_123"}

        # Mock the flow execution in registry
        mock_flow = MagicMock()
        mock_flow.execute = AsyncMock(
            return_value=MagicMock(task_id="task_abc", status="running")
        )

        with patch("src.mcp.handlers.flow_registry") as mock_reg:
            mock_reg.has.return_value = True
            mock_reg.get.return_value = MagicMock(return_value=mock_flow)

            res = await handle_execute_flow(
                org_id=sample_org_id,
                flow_type="test_flow",
                input_data=input_data,
                claims=claims,
            )

            assert res["task_id"] == "task_abc"
            assert res["status"] == "running"
            assert "correlation_id" in res


@pytest.mark.asyncio
async def test_handle_get_task_success(mock_service_client, sample_org_id):
    """Test retrieving task state from snapshot."""
    task_id = str(uuid4())
    claims = {"sub": "user_123"}

    # Prepare mock data for snapshot
    mock_snapshot = {
        "task_id": task_id,
        "org_id": sample_org_id,
        "state_json": {
            "task_id": task_id,
            "org_id": sample_org_id,
            "flow_type": "generic_flow",
            "status": "completed",
            "result": {"foo": "bar"},
            "error": None,
            "logic_state": {},
        },
    }

    # Patch get_service_client explicitly for this module
    with patch("src.mcp.handlers.get_service_client", return_value=mock_service_client):
        # The mock client from conftest.py returns the same chain for all methods
        mock_service_client.table("snapshots").execute.return_value.data = mock_snapshot

        with patch("src.mcp.handlers.verify_org_membership"):
            res = await handle_get_task(sample_org_id, task_id, claims)

            assert res["task_id"] == task_id
            assert res["status"] == "completed"


@pytest.mark.asyncio
async def test_handle_approve_task_success(mock_service_client, sample_org_id):
    """Test HITL approval process."""
    task_id = str(uuid4())
    claims = {"sub": "user_123"}

    mock_pending = {
        "id": 1,
        "task_id": task_id,
        "flow_type": "generic_flow",
        "status": "pending",
    }

    with patch("src.mcp.handlers.get_service_client", return_value=mock_service_client):
        mock_service_client.table(
            "pending_approvals"
        ).execute.return_value.data = mock_pending

        with patch("src.mcp.handlers.verify_org_membership") as mock_auth:
            mock_auth.return_value = {"user_id": "user_123"}

            # Mock flow registry and flow instance
            mock_flow = MagicMock()
            mock_flow.state.status = "completed"
            mock_flow.resume = AsyncMock()

            with patch("src.mcp.handlers.flow_registry") as mock_reg:
                mock_reg.get.return_value = MagicMock(return_value=mock_flow)

                res = await handle_approve_task(sample_org_id, task_id, claims)

                assert res["task_id"] == task_id
                assert res["status"] == "completed"
                assert res["decision"] == "approved"

                # Verify DB update call
                mock_service_client.table("pending_approvals").update.assert_called()


@pytest.mark.asyncio
async def test_handle_auth_failure(sample_org_id):
    """Test that AuthError is propagated when verify_org_membership fails."""
    with patch(
        "src.mcp.handlers.verify_org_membership", side_effect=AuthError("Forbidden")
    ):
        with pytest.raises(AuthError):
            await handle_get_task(sample_org_id, "task_123", {})
