"""tests/e2e/test_exec_multi_mcp.py — Escenario 5: multi-agente + MCP.

Tests MultiCrewFlow with MCP tools configured on all agents.
MCP resolution skipped — validates config + multi-crew path.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from src.flows.multi_crew_flow import MultiCrewFlow
from src.flows.state import FlowStatus

AGENT_CONFIGS = {
    "analyst": {
        "role": "analyst",
        "soul_json": {"role": "analyst", "goal": "Analyze", "backstory": "Analyst."},
        "allowed_tools": ["mcp:filesystem:list_files"],
        "model": "claude-sonnet-4-20250514",
        "max_iter": 3,
        "is_active": True,
    },
    "processor": {
        "role": "processor",
        "soul_json": {"role": "processor", "goal": "Process", "backstory": "Processor."},
        "allowed_tools": ["mcp:filesystem:read_file"],
        "model": "claude-sonnet-4-20250514",
        "max_iter": 3,
        "is_active": True,
    },
    "reviewer": {
        "role": "reviewer",
        "soul_json": {"role": "reviewer", "goal": "Review", "backstory": "Reviewer."},
        "allowed_tools": ["mcp:filesystem:write_file"],
        "model": "claude-sonnet-4-20250514",
        "max_iter": 3,
        "is_active": True,
    },
}


def _setup_catalog(mock_service_client, org_id):
    role_configs = {r: {**c, "org_id": org_id} for r, c in AGENT_CONFIGS.items()}
    catalog = mock_service_client.table("agent_catalog")
    catalog._current_role = "analyst"

    def eq_side(column, value):
        if column == "role":
            catalog._current_role = value
        return catalog

    def execute_side():
        cfg = role_configs.get(catalog._current_role)
        resp = MagicMock()
        resp.data = cfg
        return resp

    catalog.eq.side_effect = eq_side
    catalog.execute.side_effect = execute_side


class TestExecMultiMCP:
    """Escenario 5: multi-agente + MCP tools."""

    @pytest.mark.asyncio
    async def test_multi_mcp_completes(
        self, mock_service_client, mock_tenant_client, mock_event_store
    ):
        org_id = str(uuid4())
        _setup_catalog(mock_service_client, org_id)

        with (
            patch(
                "src.crews.factory.AgentFactory._resolve_mcp_tool_async",
                new_callable=AsyncMock,
                return_value=None,
            ),
            patch("src.crews.factory.get_settings") as mock_get,
        ):
            mock_settings = MagicMock()
            mock_settings.get_llm.return_value = "groq/llama-3.3-70b-versatile"
            mock_get.return_value = mock_settings

            flow = MultiCrewFlow(org_id=org_id, user_id=str(uuid4()))
            state = await flow.execute({"query": "test"})

        assert state.status == FlowStatus.COMPLETED.value, f"Got {state.status}"
        assert state.crew_a_output is not None
