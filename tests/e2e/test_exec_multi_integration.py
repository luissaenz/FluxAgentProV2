"""tests/e2e/test_exec_multi_integration.py — Escenario 6: multi-agente + integracion.

Tests MultiCrewFlow with service_connector on all agents.
"""

from __future__ import annotations

from unittest.mock import MagicMock
from uuid import uuid4

import pytest

from src.flows.multi_crew_flow import MultiCrewFlow
from src.flows.state import FlowStatus

AGENT_CONFIGS = {
    "analyst": {
        "role": "analyst",
        "soul_json": {"role": "analyst", "goal": "Analyze", "backstory": "Analyst."},
        "allowed_tools": ["service_connector"],
        "model": "claude-sonnet-4-20250514",
        "max_iter": 3,
        "is_active": True,
    },
    "processor": {
        "role": "processor",
        "soul_json": {"role": "processor", "goal": "Process", "backstory": "Processor."},
        "allowed_tools": ["service_connector"],
        "model": "claude-sonnet-4-20250514",
        "max_iter": 3,
        "is_active": True,
    },
    "reviewer": {
        "role": "reviewer",
        "soul_json": {"role": "reviewer", "goal": "Review", "backstory": "Reviewer."},
        "allowed_tools": ["service_connector"],
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


class TestExecMultiIntegration:
    """Escenario 6: multi-agente + service_connector."""

    @pytest.mark.asyncio
    async def test_multi_integration_completes(
        self, mock_service_client, mock_tenant_client, mock_event_store
    ):
        org_id = str(uuid4())
        _setup_catalog(mock_service_client, org_id)

        flow = MultiCrewFlow(org_id=org_id, user_id=str(uuid4()))
        state = await flow.execute({"query": "test"})

        assert state.status == FlowStatus.COMPLETED.value, f"Got {state.status}"
        assert state.crew_a_output is not None
