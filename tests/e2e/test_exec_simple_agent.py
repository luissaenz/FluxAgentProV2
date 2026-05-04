"""tests/e2e/test_exec_simple_agent.py — Escenario 1: agente simple execution.

Tests full BaseFlow lifecycle end-to-end with mocked DB and CrewAI:
  execute() -> validate -> create_task -> start -> _run_crew -> complete

Unlike test_scenario_1_greeter.py (schema-only), this tests the real
execution pipeline through BaseFlow.execute().
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest

from src.flows.base_flow import BaseFlow
from src.flows.registry import register_flow
from src.flows.state import FlowStatus

SAMPLE_AGENT_CONFIG = {
    "role": "greeter",
    "soul_json": {
        "role": "greeter",
        "goal": "Greet the user warmly",
        "backstory": "You are a friendly greeter agent.",
    },
    "allowed_tools": [],
    "model": "claude-sonnet-4-20250514",
    "max_iter": 3,
    "is_active": True,
}


@register_flow("test_exec_simple", category="test")
class SimpleAgentFlow(BaseFlow):
    """Minimal flow that executes a single agent via BaseCrew."""

    def validate_input(self, input_data):
        return bool(input_data)

    async def _run_crew(self):
        from src.crews.base_crew import BaseCrew

        crew = BaseCrew(self.org_id, role="greeter")
        result = await crew.run_async(
            task_description="Greet the user",
            inputs=self.state.input_data,
        )
        return {"result": str(result)}


class TestExecSimpleAgent:
    """Escenario 1: agente simple — execution lifecycle."""

    @pytest.mark.asyncio
    async def test_full_lifecycle_completes(
        self, mock_service_client, mock_tenant_client, mock_event_store
    ):
        """Full lifecycle: execute -> complete with valid output."""
        org_id = str(uuid4())

        agent_config = {**SAMPLE_AGENT_CONFIG, "org_id": org_id}
        mock_resp = MagicMock()
        mock_resp.data = agent_config
        mock_service_client.table("agent_catalog").execute.return_value = mock_resp

        with patch("src.crews.factory.get_settings") as mock_get:
            mock_settings = MagicMock()
            mock_settings.get_llm.return_value = "groq/llama-3.3-70b-versatile"
            mock_get.return_value = mock_settings

            flow = SimpleAgentFlow(org_id=org_id, user_id=str(uuid4()))
            state = await flow.execute({"user": "Alice", "message": "Hello!"})

        assert state.status == FlowStatus.COMPLETED.value, f"Got {state.status}"
        assert state.task_id is not None
        assert state.output_data is not None
        assert "result" in state.output_data
        assert state.flow_type == "test_exec_simple"
        assert state.org_id == org_id

    @pytest.mark.asyncio
    async def test_state_transitions(
        self, mock_service_client, mock_tenant_client, mock_event_store
    ):
        """State: PENDING (via None) -> RUNNING -> COMPLETED."""
        org_id = str(uuid4())
        agent_config = {**SAMPLE_AGENT_CONFIG, "org_id": org_id}
        mock_resp = MagicMock()
        mock_resp.data = agent_config
        mock_service_client.table("agent_catalog").execute.return_value = mock_resp

        with patch("src.crews.factory.get_settings") as mock_get:
            mock_settings = MagicMock()
            mock_settings.get_llm.return_value = "groq/llama-3.3-70b-versatile"
            mock_get.return_value = mock_settings

            flow = SimpleAgentFlow(org_id=org_id, user_id=str(uuid4()))
            assert flow.state is None

            state = await flow.execute({"user": "Bob"})
        assert FlowStatus(state.status) == FlowStatus.COMPLETED
        assert state.task_id is not None

    @pytest.mark.asyncio
    async def test_rejects_empty_input(
        self, mock_service_client, mock_tenant_client
    ):
        """Empty input raises ValueError."""
        flow = SimpleAgentFlow(org_id=str(uuid4()), user_id=str(uuid4()))
        with pytest.raises(ValueError, match="Input validation failed"):
            await flow.execute({})

    @pytest.mark.asyncio
    async def test_agent_not_found_fails_flow(
        self, mock_service_client, mock_tenant_client, mock_event_store
    ):
        """Missing agent in catalog fails the flow gracefully."""
        org_id = str(uuid4())
        mock_resp = MagicMock()
        mock_resp.data = None
        mock_service_client.table("agent_catalog").execute.return_value = mock_resp

        flow = SimpleAgentFlow(org_id=org_id, user_id=str(uuid4()))
        with pytest.raises(Exception, match="No active agent"):
            await flow.execute({"user": "Charlie"})

        assert flow.state is not None
        assert flow.state.status == FlowStatus.FAILED.value
        assert "No active agent" in flow.state.error
