"""tests/e2e/test_exec_agent_mcp.py — Escenario 2: agente + MCP execution.

Tests flow execution with MCP tools CONFIGURED on agent.
MCP resolution skipped (no MCPPool) — validates config + flow path.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from src.flows.base_flow import BaseFlow
from src.flows.registry import register_flow
from src.flows.state import FlowStatus

SAMPLE_AGENT_CONFIG = {
    "role": "mcp_agent",
    "soul_json": {
        "role": "mcp_agent",
        "goal": "Use MCP tools",
        "backstory": "Agent with MCP access.",
    },
    "allowed_tools": ["mcp:filesystem:list_files", "mcp:filesystem:read_file"],
    "model": "claude-sonnet-4-20250514",
    "max_iter": 3,
    "is_active": True,
}


@register_flow("test_exec_mcp", category="test")
class MCPAgentFlow(BaseFlow):
    def validate_input(self, input_data):
        return bool(input_data)

    async def _run_crew(self):
        from src.crews.base_crew import BaseCrew

        crew = BaseCrew(self.org_id, role="mcp_agent")
        result = await crew.run_async(
            task_description="Use MCP tools",
            inputs=self.state.input_data,
        )
        return {"result": str(result)}


class TestExecAgentMCP:
    """Escenario 2: agente simple + MCP tools."""

    @pytest.mark.asyncio
    async def test_mcp_flow_completes(
        self, mock_service_client, mock_tenant_client, mock_event_store
    ):
        """Flow with MCP tools configured completes."""
        org_id = str(uuid4())
        agent_config = {**SAMPLE_AGENT_CONFIG, "org_id": org_id}
        mock_resp = MagicMock()
        mock_resp.data = agent_config
        mock_service_client.table("agent_catalog").execute.return_value = mock_resp

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

            flow = MCPAgentFlow(org_id=org_id, user_id=str(uuid4()))
            state = await flow.execute({"path": "/tmp"})

        assert state.status == FlowStatus.COMPLETED.value, f"Got {state.status}"
        assert state.task_id is not None
        assert state.output_data is not None

    @pytest.mark.asyncio
    async def test_rejects_empty_input(
        self, mock_service_client, mock_tenant_client
    ):
        flow = MCPAgentFlow(org_id=str(uuid4()), user_id=str(uuid4()))
        with pytest.raises(ValueError, match="Input validation failed"):
            await flow.execute({})
