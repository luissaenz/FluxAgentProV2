"""E2E tests: Production flows with full mocks — Paso 3.

E3.1 Degraded MCP: resolve_tools partial failure
E3.2 Approval Gate HITL: execute -> pause -> resume -> complete
E3.3 Multi-step Handover: 3-step context preservation

All tests use mocked DB, LLM, and MCP. No external dependencies.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from src.crews.factory import AgentFactory
from src.flows.dynamic_flow import DynamicWorkflow
from src.flows.state import FlowStatus

# ── Templates ────────────────────────────────────────────────────

APPROVAL_TEMPLATE = {
    "name": "Approval Test Workflow",
    "description": "Workflow that triggers approval gate",
    "flow_type": "e2e_approval_test",
    "steps": [
        {
            "id": "step_1",
            "name": "Calculate Amount",
            "description": "Calculate the transaction amount",
            "agent_role": "calculator",
            "depends_on": None,
            "requires_approval": False,
        },
    ],
    "agents": [
        {
            "role": "calculator",
            "goal": "Calculate amounts accurately",
            "backstory": "You are a financial calculator.",
            "allowed_tools": [],
            "rules": [],
            "model": "claude-sonnet-4-20250514",
            "max_iter": 5,
        },
    ],
    "approval_rules": [
        {
            "condition": "monto > 50000",
            "description": "Amounts over 50k require approval",
        }
    ],
}

HANDOVER_3STEP_TEMPLATE = {
    "name": "3-Step Handover Workflow",
    "description": "3-step workflow for context preservation test",
    "flow_type": "e2e_handover_test",
    "steps": [
        {
            "id": "step_1",
            "name": "First Analysis",
            "description": "Execute first analysis",
            "agent_role": "analyst",
            "depends_on": None,
            "requires_approval": False,
        },
        {
            "id": "step_2",
            "name": "Process Results",
            "description": "Process analysis results",
            "agent_role": "processor",
            "depends_on": ["step_1"],
            "requires_approval": False,
        },
        {
            "id": "step_3",
            "name": "Review Output",
            "description": "Review the processed output",
            "agent_role": "reviewer",
            "depends_on": ["step_2"],
            "requires_approval": False,
        },
    ],
    "agents": [
        {
            "role": "analyst",
            "goal": "Analyze data thoroughly and prepare output for next step",
            "backstory": "You are an expert data analyst.",
            "allowed_tools": [],
            "rules": [],
            "model": "claude-sonnet-4-20250514",
            "max_iter": 5,
        },
        {
            "role": "processor",
            "goal": "Process analysis results from previous step",
            "backstory": "You are a data processing specialist.",
            "allowed_tools": [],
            "rules": [],
            "model": "claude-sonnet-4-20250514",
            "max_iter": 5,
        },
        {
            "role": "reviewer",
            "goal": "Review processed output and provide final assessment",
            "backstory": "You are a senior quality reviewer.",
            "allowed_tools": [],
            "rules": [],
            "model": "claude-sonnet-4-20250514",
            "max_iter": 5,
        },
    ],
    "approval_rules": [],
}


# ── Fixtures ──────────────────────────────────────────────────────


@pytest.fixture(autouse=True)
def reset_mcp_pool():
    """Avoid MCPPool singleton contamination between tests."""
    from src.tools.mcp_pool import MCPPool

    MCPPool.reset()
    yield
    MCPPool.reset()


# ── E3.1: Degraded MCP ────────────────────────────────────────────


class TestE3_1DegradedMCP:
    """E3.1: Workflow with degraded MCP survives without crash."""

    @pytest.mark.asyncio
    async def test_resolve_tools_partial_failure(
        self,
        mock_service_client,
        mock_tenant_client,
        mock_event_store,
        sample_org_id,
    ):
        """resolve_tools with 2 MCP tools -> 1 works, 1 fails -> returns 1 tool, error logged."""
        mock_tool = MagicMock()
        mock_tool.name = "tool_a"

        with patch.object(AgentFactory, "_resolve_mcp_tool") as mock_resolve:
            mock_resolve.side_effect = [mock_tool, Exception("MCP connection failed")]

            with patch("src.crews.factory.logger") as mock_logger:
                tools = AgentFactory.resolve_tools(
                    ["mcp:server:tool_a", "mcp:server:tool_b"],
                    sample_org_id,
                    async_mode=True,
                )

        assert len(tools) == 1
        assert tools[0].name == "tool_a"
        assert mock_logger.error.called
        log_msg = mock_logger.error.call_args[0][0]
        assert "Failed to resolve MCP tool" in log_msg


# ── E3.2: Approval Gate HITL ─────────────────────────────────────


class TestE3_2ApprovalGateHITL:
    """E3.2: Full HITL cycle: execute -> pause -> resume -> complete."""

    @pytest.mark.asyncio
    async def test_approval_flow_pending_to_awaiting(
        self,
        mock_service_client,
        mock_tenant_client,
        mock_event_store,
        sample_org_id,
    ):
        """execute() with approval rule -> state.status == AWAITING_APPROVAL."""
        mock_crew = MagicMock()
        mock_crew.run_async = AsyncMock(return_value=MagicMock(raw="100000"))
        mock_crew.get_last_tokens_used = MagicMock(return_value=0)

        mock_service_client.rpc.return_value.execute.return_value = MagicMock(data=1)

        with patch("src.flows.dynamic_flow.BaseCrew", return_value=mock_crew):
            flow = DynamicWorkflow(org_id=sample_org_id)
            flow._template_definition = APPROVAL_TEMPLATE
            flow._flow_type = "e2e_approval_test"
            state = await flow.execute(input_data={"monto": 100000})

        assert state.status == FlowStatus.AWAITING_APPROVAL

    @pytest.mark.asyncio
    async def test_approval_flow_resume_completes(
        self,
        mock_service_client,
        mock_tenant_client,
        sample_org_id,
    ):
        """resume(task_id, "approved") -> COMPLETED with {"approval": "accepted"}."""
        task_id = str(uuid4())

        mock_service_client.table(
            "snapshots",
        ).select.return_value.eq.return_value.eq.return_value.maybe_single.return_value.execute.return_value = MagicMock(
            data={
                "task_id": task_id,
                "org_id": sample_org_id,
                "flow_type": "e2e_approval_test",
                "status": "awaiting_approval",
                "state_json": {
                    "task_id": task_id,
                    "org_id": sample_org_id,
                    "flow_type": "e2e_approval_test",
                    "status": "awaiting_approval",
                    "correlation_id": "test-corr-id",
                    "input_data": {},
                },
            },
        )

        flow = DynamicWorkflow(org_id=sample_org_id)
        flow.event_store = MagicMock()

        await flow.resume(
            task_id=task_id,
            decision="approved",
            decided_by="supervisor1",
        )

        assert flow.state.status == FlowStatus.COMPLETED
        assert flow.state.output_data == {"approval": "accepted"}
        assert flow.state.approval_payload is None


# ── E3.3: Multi-step Handover ────────────────────────────────────


class TestE3_3MultiStepHandover:
    """E3.3: 3-step handover with accumulated context."""

    @pytest.mark.asyncio
    async def test_three_step_context_preservation(
        self,
        mock_service_client,
        mock_tenant_client,
        mock_event_store,
        sample_org_id,
    ):
        """3 steps executed sequentially, step_3 receives context from steps 1+2."""
        mock_crew_step1 = MagicMock()
        mock_crew_step1.run_async = AsyncMock(
            return_value=MagicMock(raw="Output A"),
        )
        mock_crew_step1.get_last_tokens_used = MagicMock(return_value=100)

        mock_crew_step2 = MagicMock()
        mock_crew_step2.run_async = AsyncMock(
            return_value=MagicMock(raw="Output B"),
        )
        mock_crew_step2.get_last_tokens_used = MagicMock(return_value=200)

        mock_crew_step3 = MagicMock()
        mock_crew_step3.run_async = AsyncMock(
            return_value=MagicMock(raw="Output C"),
        )
        mock_crew_step3.get_last_tokens_used = MagicMock(return_value=300)

        flow = DynamicWorkflow(org_id=sample_org_id)
        flow._template_definition = HANDOVER_3STEP_TEMPLATE
        flow._flow_type = "e2e_handover_test"
        flow.state = MagicMock()
        flow.state.input_data = {"original_key": "original_value"}
        flow.persist_state = AsyncMock()
        flow.emit_event = AsyncMock()
        flow.get_last_tokens_used = MagicMock(return_value=0)

        with patch("src.flows.dynamic_flow.BaseCrew") as MockBaseCrew:

            def crew_side_effect(org_id, role):
                if role == "analyst":
                    return mock_crew_step1
                if role == "processor":
                    return mock_crew_step2
                if role == "reviewer":
                    return mock_crew_step3
                return MagicMock()

            MockBaseCrew.side_effect = crew_side_effect

            result = await flow._run_crew()

        assert mock_crew_step1.run_async.called
        assert mock_crew_step2.run_async.called
        assert mock_crew_step3.run_async.called

        step2_inputs = mock_crew_step2.run_async.call_args.kwargs["inputs"]
        assert "previous_results" in step2_inputs
        assert "step_1" in step2_inputs["previous_results"]
        assert step2_inputs["previous_results"]["step_1"]["result"] == "Output A"

        step3_inputs = mock_crew_step3.run_async.call_args.kwargs["inputs"]
        assert "previous_results" in step3_inputs
        assert "step_1" in step3_inputs["previous_results"]
        assert "step_2" in step3_inputs["previous_results"]
        assert step3_inputs["previous_results"]["step_1"]["result"] == "Output A"
        assert step3_inputs["previous_results"]["step_2"]["result"] == "Output B"

        assert "step_1" in result
        assert "step_2" in result
        assert "step_3" in result
        assert result["step_1"]["result"] == "Output A"
        assert result["step_2"]["result"] == "Output B"
        assert result["step_3"]["result"] == "Output C"
