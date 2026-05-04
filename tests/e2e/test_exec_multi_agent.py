"""tests/e2e/test_exec_multi_agent.py — Escenario 4: multi-agente execution.

Tests MultiCrewFlow with real BaseCrew execution (mocked DB + CrewAI).
Exercises: analyst -> router -> reviewer pipeline.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest

from src.flows.multi_crew_flow import MultiCrewFlow
from src.flows.state import FlowStatus

AGENT_CONFIGS = {
    "analyst": {
        "role": "analyst",
        "soul_json": {
            "role": "analyst",
            "goal": "Analyze data thoroughly",
            "backstory": "Expert data analyst.",
        },
        "allowed_tools": [],
        "model": "claude-sonnet-4-20250514",
        "max_iter": 3,
        "is_active": True,
    },
    "processor": {
        "role": "processor",
        "soul_json": {
            "role": "processor",
            "goal": "Process analysis results",
            "backstory": "Expert data processor.",
        },
        "allowed_tools": [],
        "model": "claude-sonnet-4-20250514",
        "max_iter": 3,
        "is_active": True,
    },
    "reviewer": {
        "role": "reviewer",
        "soul_json": {
            "role": "reviewer",
            "goal": "Review and summarise results",
            "backstory": "Expert reviewer.",
        },
        "allowed_tools": [],
        "model": "claude-sonnet-4-20250514",
        "max_iter": 3,
        "is_active": True,
    },
}


def _setup_agent_catalog(mock_service_client, org_id):
    """Configure agent_catalog mock to return role-specific data."""
    role_configs = {
        role: {**cfg, "org_id": org_id} for role, cfg in AGENT_CONFIGS.items()
    }

    catalog = mock_service_client.table("agent_catalog")
    catalog._current_role = "analyst"

    def eq_side(column, value):
        if column == "role":
            catalog._current_role = value
        return catalog

    def execute_side():
        role = catalog._current_role
        cfg = role_configs.get(role)
        mock_resp = MagicMock()
        mock_resp.data = cfg
        return mock_resp

    catalog.eq.side_effect = eq_side
    catalog.execute.side_effect = execute_side


class TestExecMultiAgent:
    """Escenario 4: MultiCrewFlow execution with real BaseCrew."""

    @pytest.mark.asyncio
    async def test_multi_crew_completes(
        self, mock_service_client, mock_tenant_client, mock_event_store
    ):
        """MultiCrewFlow executes analyst -> reviewer, completes."""
        org_id = str(uuid4())
        _setup_agent_catalog(mock_service_client, org_id)

        with patch("src.crews.factory.get_settings") as mock_get:
            mock_settings = MagicMock()
            mock_settings.get_llm.return_value = "groq/llama-3.3-70b-versatile"
            mock_get.return_value = mock_settings

            flow = MultiCrewFlow(org_id=org_id, user_id=str(uuid4()))
            state = await flow.execute({"query": "Analyze sales data"})

        assert state.status == FlowStatus.COMPLETED.value, f"Got {state.status}"
        assert state.crew_a_output is not None
        assert state.crew_c_output is not None
        assert state.crew_b_output is None

    @pytest.mark.asyncio
    async def test_multi_crew_output_structure(
        self, mock_service_client, mock_tenant_client, mock_event_store
    ):
        """MultiCrewFlow output contains all crew results."""
        org_id = str(uuid4())
        _setup_agent_catalog(mock_service_client, org_id)

        with patch("src.crews.factory.get_settings") as mock_get:
            mock_settings = MagicMock()
            mock_settings.get_llm.return_value = "groq/llama-3.3-70b-versatile"
            mock_get.return_value = mock_settings

            flow = MultiCrewFlow(org_id=org_id, user_id=str(uuid4()))
            state = await flow.execute({"query": "Analyze sales data"})

        assert "crew_a" in state.output_data
        assert "crew_c" in state.output_data
        assert state.output_data["crew_a"] is not None

    @pytest.mark.asyncio
    async def test_rejects_empty_input(
        self, mock_service_client, mock_tenant_client
    ):
        """Empty input raises ValueError."""
        flow = MultiCrewFlow(org_id=str(uuid4()), user_id=str(uuid4()))
        with pytest.raises(ValueError, match="Input validation failed"):
            await flow.execute({})

    @pytest.mark.asyncio
    async def test_crew_a_not_found_fails(
        self, mock_service_client, mock_tenant_client, mock_event_store
    ):
        """Missing analyst agent fails the flow."""
        org_id = str(uuid4())

        catalog = mock_service_client.table("agent_catalog")
        mock_resp = MagicMock()
        mock_resp.data = None
        catalog.execute.return_value = mock_resp

        flow = MultiCrewFlow(org_id=org_id, user_id=str(uuid4()))
        with pytest.raises(Exception, match="No active agent"):
            await flow.execute({"query": "test"})
        assert flow.state.status == FlowStatus.FAILED.value
