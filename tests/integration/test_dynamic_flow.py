"""tests/integration/test_dynamic_flow.py — Phase 3 dynamic workflow tests.

Covers:
  - DynamicWorkflow registration
  - Step execution from template
  - Approval rule evaluation
  - State persistence after each step
  - Event emission per step
"""

from __future__ import annotations

import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from uuid import uuid4

from src.flows.dynamic_flow import DynamicWorkflow
from src.flows.state import FlowStatus


# ── Test templates ──────────────────────────────────────────────

SIMPLE_WORKFLOW_TEMPLATE = {
    "name": "Simple Test Workflow",
    "description": "A simple workflow for testing",
    "flow_type": "simple_test",
    "steps": [
        {
            "id": "step_1",
            "name": "First Step",
            "description": "Execute first analysis",
            "agent_role": "analyst",
            "depends_on": None,
            "requires_approval": False,
        },
        {
            "id": "step_2",
            "name": "Second Step",
            "description": "Process the results",
            "agent_role": "processor",
            "depends_on": ["step_1"],
            "requires_approval": False,
        },
    ],
    "agents": [
        {
            "role": "analyst",
            "goal": "Analyze data thoroughly",
            "backstory": "You are an expert data analyst.",
            "allowed_tools": [],
            "rules": [],
            "model": "claude-sonnet-4-20250514",
            "max_iter": 5,
        },
        {
            "role": "processor",
            "goal": "Process analysis results",
            "backstory": "You are a data processing specialist.",
            "allowed_tools": [],
            "rules": [],
            "model": "claude-sonnet-4-20250514",
            "max_iter": 5,
        },
    ],
    "approval_rules": [],
}

WORKFLOW_WITH_APPROVAL_TEMPLATE = {
    "name": "Workflow with Approval",
    "description": "Workflow that requires approval",
    "flow_type": "approval_test",
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


# ── DynamicWorkflow registration tests ──────────────────────────


class TestDynamicWorkflowRegistration:
    """DynamicWorkflow.register() behavior."""

    def test_register_creates_subclass(self):
        """register() creates a proper subclass."""
        DynamicWorkflow.register(
            flow_type="test_flow",
            definition=SIMPLE_WORKFLOW_TEMPLATE,
        )

        from src.flows.registry import flow_registry

        # Flow should be registered
        assert flow_registry.has("test_flow")

        # Get the registered flow class
        FlowClass = flow_registry.get("test_flow")
        assert FlowClass.__name__ == "DynamicFlow_test_flow"
        assert FlowClass._template_definition == SIMPLE_WORKFLOW_TEMPLATE
        assert FlowClass._flow_type == "test_flow"

    def test_register_stores_definition(self):
        """register() stores the template definition."""
        DynamicWorkflow.register(
            flow_type="another_flow",
            definition={"custom": "data", "steps": [{"id": "s1"}]},
        )

        from src.flows.registry import flow_registry

        FlowClass = flow_registry.get("another_flow")

        assert FlowClass._template_definition["custom"] == "data"
        assert len(FlowClass._template_definition["steps"]) == 1


# ── DynamicWorkflow execution tests ─────────────────────────────


class TestDynamicWorkflowExecution:
    """DynamicWorkflow._run_crew() execution tests."""

    @pytest.mark.asyncio
    async def test_executes_all_steps_sequentially(
        self, mock_tenant_client, mock_service_client, mock_event_store, sample_org_id
    ):
        """DynamicWorkflow executes all steps in sequence."""
        # Create flow instance
        flow = DynamicWorkflow(org_id=sample_org_id)
        flow._template_definition = SIMPLE_WORKFLOW_TEMPLATE
        flow._flow_type = "simple_test"
        flow.state = MagicMock()
        flow.state.input_data = {"test": "data"}

        # Mock BaseCrew
        mock_crew_analyst = MagicMock()
        mock_crew_analyst.run_async = AsyncMock(
            return_value=MagicMock(raw="Analysis result")
        )

        mock_crew_processor = MagicMock()
        mock_crew_processor.run_async = AsyncMock(
            return_value=MagicMock(raw="Processing result")
        )

        with patch("src.flows.dynamic_flow.BaseCrew") as MockBaseCrew:

            def crew_side_effect(org_id, role):
                if role == "analyst":
                    return mock_crew_analyst
                elif role == "processor":
                    return mock_crew_processor
                return MagicMock()

            MockBaseCrew.side_effect = crew_side_effect

            result = await flow._run_crew()

        # Both steps should have executed
        assert mock_crew_analyst.run_async.called
        assert mock_crew_processor.run_async.called

        # Results should contain both step outputs
        assert "step_1" in result
        assert "step_2" in result

    @pytest.mark.asyncio
    async def test_persists_state_after_each_step(
        self, mock_tenant_client, mock_service_client, mock_event_store, sample_org_id
    ):
        """DynamicWorkflow persists state after each step."""
        flow = DynamicWorkflow(org_id=sample_org_id)
        flow._template_definition = SIMPLE_WORKFLOW_TEMPLATE
        flow._flow_type = "simple_test"
        flow.state = MagicMock()
        flow.state.input_data = {"test": "data"}
        flow.persist_state = AsyncMock()

        mock_crew = MagicMock()
        mock_crew.run_async = AsyncMock(return_value=MagicMock(raw="Result"))

        with patch("src.flows.dynamic_flow.BaseCrew", return_value=mock_crew):
            await flow._run_crew()

        # persist_state should be called after each step (2 steps)
        assert flow.persist_state.call_count >= 2

    @pytest.mark.asyncio
    async def test_emits_event_after_each_step(
        self, mock_tenant_client, mock_service_client, mock_event_store, sample_org_id
    ):
        """DynamicWorkflow emits event after each step."""
        flow = DynamicWorkflow(org_id=sample_org_id)
        flow._template_definition = SIMPLE_WORKFLOW_TEMPLATE
        flow._flow_type = "simple_test"
        flow.state = MagicMock()
        flow.state.input_data = {"test": "data"}
        flow.emit_event = AsyncMock()

        mock_crew = MagicMock()
        mock_crew.run_async = AsyncMock(return_value=MagicMock(raw="Result"))

        with patch("src.flows.dynamic_flow.BaseCrew", return_value=mock_crew):
            await flow._run_crew()

        # emit_event should be called for each step
        assert flow.emit_event.call_count >= 2

        # Check event types
        event_calls = [call[0][0] for call in flow.emit_event.call_args_list]
        assert "step.step_1.completed" in event_calls
        assert "step.step_2.completed" in event_calls

    @pytest.mark.asyncio
    async def test_skips_step_without_agent_role(
        self, mock_tenant_client, mock_service_client, mock_event_store, sample_org_id
    ):
        """DynamicWorkflow skips steps without agent_role."""
        template_with_missing_role = {
            **SIMPLE_WORKFLOW_TEMPLATE,
            "steps": [
                {
                    "id": "step_1",
                    "name": "Step 1",
                    "description": "Desc",
                    "agent_role": "analyst",
                },
                {
                    "id": "step_2",
                    "name": "Step 2",
                    "description": "Desc",
                    "agent_role": None,
                },
            ],
            "agents": SIMPLE_WORKFLOW_TEMPLATE["agents"][:1],
        }

        flow = DynamicWorkflow(org_id=sample_org_id)
        flow._template_definition = template_with_missing_role
        flow._flow_type = "test_skip"
        flow.state = MagicMock()
        flow.state.input_data = {"test": "data"}
        flow.emit_event = AsyncMock()

        mock_crew = MagicMock()
        mock_crew.run_async = AsyncMock(return_value=MagicMock(raw="Result"))

        with patch("src.flows.dynamic_flow.BaseCrew", return_value=mock_crew):
            result = await flow._run_crew()

        # Only step_1 should have executed
        assert "step_1" in result
        assert "step_2" not in result


# ── Approval rule evaluation tests ──────────────────────────────


class TestApprovalRuleEvaluation:
    """_check_approval_rule() behavior."""

    def test_check_approval_rule_greater_than_true(self, sample_org_id):
        """_check_approval_rule returns True when condition met."""
        flow = DynamicWorkflow(org_id=sample_org_id)
        flow._template_definition = WORKFLOW_WITH_APPROVAL_TEMPLATE

        rule = {"condition": "monto > 50000", "description": "High value"}
        results = {"step_1": {"result": "100000"}}

        assert flow._check_approval_rule(rule, results) is True

    def test_check_approval_rule_greater_than_false(self, sample_org_id):
        """_check_approval_rule returns False when condition not met."""
        flow = DynamicWorkflow(org_id=sample_org_id)
        flow._template_definition = WORKFLOW_WITH_APPROVAL_TEMPLATE

        rule = {"condition": "monto > 50000", "description": "High value"}
        results = {"step_1": {"result": "30000"}}

        assert flow._check_approval_rule(rule, results) is False

    def test_check_approval_rule_with_invalid_condition(self, sample_org_id):
        """_check_approval_rule handles invalid conditions gracefully."""
        flow = DynamicWorkflow(org_id=sample_org_id)
        flow._template_definition = WORKFLOW_WITH_APPROVAL_TEMPLATE

        rule = {"condition": "invalid syntax >>>", "description": "Bad rule"}
        results = {"step_1": {"result": "100"}}

        # Should not raise, just return False
        assert flow._check_approval_rule(rule, results) is False

    def test_check_approval_rule_with_non_numeric_result(self, sample_org_id):
        """_check_approval_rule handles non-numeric results."""
        flow = DynamicWorkflow(org_id=sample_org_id)
        flow._template_definition = WORKFLOW_WITH_APPROVAL_TEMPLATE

        rule = {"condition": "monto > 50000", "description": "High value"}
        results = {"step_1": {"result": "not a number"}}

        # Should not raise, just return False
        assert flow._check_approval_rule(rule, results) is False


# ── Dynamic workflow with approval tests ────────────────────────


class TestDynamicWorkflowWithApproval:
    """DynamicWorkflow approval integration."""

    @pytest.mark.asyncio
    async def test_triggers_approval_when_rule_matches(
        self, mock_tenant_client, mock_service_client, mock_event_store, sample_org_id
    ):
        """DynamicWorkflow calls request_approval when rule matches."""
        flow = DynamicWorkflow(org_id=sample_org_id)
        flow._template_definition = WORKFLOW_WITH_APPROVAL_TEMPLATE
        flow._flow_type = "approval_test"
        flow.state = MagicMock()
        flow.state.input_data = {"test": "data"}

        # Mock crew to return high amount
        mock_crew = MagicMock()
        mock_crew.run_async = AsyncMock(return_value=MagicMock(raw="100000"))

        # Mock RPC for request_approval
        mock_service_client.rpc.return_value.execute.return_value = MagicMock(data=1)

        with patch("src.flows.dynamic_flow.BaseCrew", return_value=mock_crew):
            with patch.object(
                flow, "request_approval", new_callable=AsyncMock
            ) as mock_request:
                result = await flow._run_crew()

                # request_approval should have been called
                mock_request.assert_called_once()


# ── load_dynamic_flows_from_db tests ────────────────────────────


class TestLoadDynamicFlowsFromDB:
    """load_dynamic_flows_from_db() behavior."""

    @patch("src.db.session.get_service_client")
    def test_loads_active_flows(self, mock_get_svc):
        """load_dynamic_flows_from_db loads active workflows."""
        mock_svc = MagicMock()
        mock_get_svc.return_value = mock_svc

        mock_svc.table.return_value.select.return_value.eq.return_value.execute.return_value = MagicMock(
            data=[
                {"flow_type": "flow_a", "definition": {"name": "A"}},
                {"flow_type": "flow_b", "definition": {"name": "B"}},
            ]
        )

        from src.flows.dynamic_flow import load_dynamic_flows_from_db
        from src.flows.registry import flow_registry

        # Clear registry first
        flow_registry.clear()

        count = load_dynamic_flows_from_db()

        assert count == 2
        assert flow_registry.has("flow_a")
        assert flow_registry.has("flow_b")

    @patch("src.db.session.get_service_client")
    def test_skips_invalid_flows(self, mock_get_svc):
        """load_dynamic_flows_from_db skips invalid workflows."""
        mock_svc = MagicMock()
        mock_get_svc.return_value = mock_svc

        # One valid, one invalid (missing required fields)
        mock_svc.table.return_value.select.return_value.eq.return_value.execute.return_value = MagicMock(
            data=[
                {
                    "flow_type": "valid_flow",
                    "definition": {
                        "name": "Valid",
                        "steps": [{"id": "s1", "agent_role": "a1"}],
                        "agents": [{"role": "a1"}],
                    },
                },
                {"flow_type": "invalid_flow", "definition": {"invalid": "data"}},
            ]
        )

        from src.flows.dynamic_flow import load_dynamic_flows_from_db
        from src.flows.registry import flow_registry

        flow_registry.clear()
        count = load_dynamic_flows_from_db()

        # Only valid flow should be loaded
        assert count >= 1
        assert flow_registry.has("valid_flow")
