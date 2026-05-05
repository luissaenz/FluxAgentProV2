"""tests/e2e/test_exec_agent_mcp.py — Escenario 2: agente + MCP execution.

Tests flow execution with MCP tools CONFIGURED on agent.
MCP resolution uses async resolve_tools_async() with MCPPool mock.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import crewai
import pytest

from src.flows.base_flow import BaseFlow
from src.flows.registry import register_flow
from src.flows.state import FlowStatus

# Save real classes before global_llm_mock patches them
_REAL_CREW = crewai.Crew
_REAL_TASK = crewai.Task
_REAL_AGENT = crewai.Agent

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


@pytest.fixture
def mock_mcp_pool_tools():
    """Mock MCPPool.get_tools() to return controlled tools without real infrastructure."""
    from crewai.tools import BaseTool

    class _MockTool(BaseTool):
        name: str
        description: str

        def _run(self, *args, **kwargs):
            return f"result from {self.name}"

    mock_tools = []
    for tool_name in ["list_files", "read_file"]:
        mock_tools.append(
            _MockTool(name=tool_name, description=f"Mock {tool_name} tool")
        )

    mock_pool = MagicMock()
    mock_pool.get_tools = AsyncMock(return_value=mock_tools)

    with patch("src.tools.mcp_pool.MCPPool") as MockMCPPool:
        MockMCPPool.get.return_value = mock_pool
        yield mock_pool


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
        self, mock_service_client, mock_tenant_client, mock_event_store, mock_mcp_pool_tools
    ):
        """Flow with MCP tools configured completes using real async resolution."""
        org_id = str(uuid4())
        agent_config = {**SAMPLE_AGENT_CONFIG, "org_id": org_id}
        mock_resp = MagicMock()
        mock_resp.data = agent_config
        mock_service_client.table("agent_catalog").execute.return_value = mock_resp

        # Counter-patch global_llm_mock + use real LLM with natively-supported model
        real_llm = crewai.LLM(model="openai/gpt-3.5-turbo", api_key="sk-test")
        mock_settings = MagicMock()
        mock_settings.get_llm.return_value = real_llm

        with (
            patch("crewai.Crew", _REAL_CREW),
            patch("crewai.Task", _REAL_TASK),
            patch("crewai.Agent", _REAL_AGENT),
            patch("src.crews.factory.get_settings", return_value=mock_settings),
            patch.object(real_llm, "call", return_value="Mocked LLM response"),
        ):
            flow = MCPAgentFlow(org_id=org_id, user_id=str(uuid4()))
            state = await flow.execute({"path": "/tmp"})

        assert state.status == FlowStatus.COMPLETED.value, f"Got {state.status}"
        assert state.task_id is not None
        assert state.output_data is not None

        # Verify MCPPool was called (async resolution happened)
        mock_mcp_pool_tools.get_tools.assert_awaited()

    @pytest.mark.asyncio
    async def test_rejects_empty_input(
        self, mock_service_client, mock_tenant_client
    ):
        flow = MCPAgentFlow(org_id=str(uuid4()), user_id=str(uuid4()))
        with pytest.raises(ValueError, match="Input validation failed"):
            await flow.execute({})
