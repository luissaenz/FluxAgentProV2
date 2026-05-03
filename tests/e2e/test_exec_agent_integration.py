"""tests/e2e/test_exec_agent_integration.py — Escenario 3: agente + integracion.

Tests flow execution with service_connector tool configured.
Exercises AgentFactory.resolve_tools() through real ToolRegistry.
"""

from __future__ import annotations

from unittest.mock import MagicMock
from uuid import uuid4

import pytest

from src.flows.base_flow import BaseFlow
from src.flows.registry import register_flow
from src.flows.state import FlowStatus

SAMPLE_AGENT_CONFIG = {
    "role": "integration_agent",
    "soul_json": {
        "role": "integration_agent",
        "goal": "Call external services",
        "backstory": "Agent with integration access.",
    },
    "allowed_tools": ["service_connector"],
    "model": "claude-sonnet-4-20250514",
    "max_iter": 3,
    "is_active": True,
}


@register_flow("test_exec_integration", category="test")
class IntegrationAgentFlow(BaseFlow):
    def validate_input(self, input_data):
        return bool(input_data)

    async def _run_crew(self):
        from src.crews.base_crew import BaseCrew

        crew = BaseCrew(self.org_id, role="integration_agent")
        result = await crew.run_async(
            task_description="Call external API",
            inputs=self.state.input_data,
        )
        return {"result": str(result)}


class TestExecAgentIntegration:
    """Escenario 3: agente simple + service_connector."""

    @pytest.mark.asyncio
    async def test_integration_flow_completes(
        self, mock_service_client, mock_tenant_client, mock_event_store
    ):
        """Flow with service_connector tool executes and completes."""
        org_id = str(uuid4())
        agent_config = {**SAMPLE_AGENT_CONFIG, "org_id": org_id}
        mock_resp = MagicMock()
        mock_resp.data = agent_config
        mock_service_client.table("agent_catalog").execute.return_value = mock_resp

        flow = IntegrationAgentFlow(org_id=org_id, user_id=str(uuid4()))
        state = await flow.execute({"endpoint": "/api/data"})

        assert state.status == FlowStatus.COMPLETED.value, f"Got {state.status}"
        assert state.task_id is not None
        assert state.output_data is not None

    @pytest.mark.asyncio
    async def test_rejects_empty_input(
        self, mock_service_client, mock_tenant_client
    ):
        flow = IntegrationAgentFlow(org_id=str(uuid4()), user_id=str(uuid4()))
        with pytest.raises(ValueError, match="Input validation failed"):
            await flow.execute({})
