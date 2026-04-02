"""tests/integration/test_architect_flow_additional.py — Phase 4 ArchitectFlow additional coverage.

Covers:
  - Full ArchitectFlow execution lifecycle
  - WorkflowDefinition validation integration
  - Agent persistence and upsert behavior
  - Dynamic flow registration
  - Error handling for invalid workflows
"""

from __future__ import annotations

import pytest
from unittest.mock import MagicMock, AsyncMock, patch, call
from uuid import uuid4
import json

from src.flows.architect_flow import ArchitectFlow, ArchitectState
from src.flows.workflow_definition import WorkflowDefinition, AgentDefinition, StepDefinition, ApprovalRule
from src.flows.state import FlowStatus


# ── Test fixtures ────────────────────────────────────────────────

@pytest.fixture
def valid_workflow_definition():
    """Valid WorkflowDefinition for testing."""
    return WorkflowDefinition(
        name="Invoice Approval Workflow",
        description="Automated invoice approval process with multiple steps",
        flow_type="invoice_approval",
        steps=[
            StepDefinition(
                id="step_1",
                name="Extract Invoice Data",
                description="Extract key data from the invoice document",
                agent_role="extractor",
                depends_on=None,
                requires_approval=False,
            ),
            StepDefinition(
                id="step_2",
                name="Validate Invoice",
                description="Validate invoice against business rules",
                agent_role="validator",
                depends_on=["step_1"],
                requires_approval=False,
            ),
        ],
        agents=[
            AgentDefinition(
                role="extractor",
                goal="Extract invoice data accurately",
                backstory="You are an expert at data extraction from documents",
                allowed_tools=["ocr_tool"],
                rules=["Always validate extracted data"],
                model="claude-sonnet-4-20250514",
                max_iter=5,
            ),
            AgentDefinition(
                role="validator",
                goal="Validate invoices against rules",
                backstory="You are a compliance specialist",
                allowed_tools=["db_read"],
                rules=["Check all compliance requirements"],
                model="claude-sonnet-4-20250514",
                max_iter=5,
            ),
        ],
        approval_rules=[
            ApprovalRule(
                condition="monto > 10000",
                description="Invoices over 10k require manager approval",
            )
        ],
    )


# ── ArchitectFlow execution tests ───────────────────────────────

class TestArchitectFlowExecution:
    """ArchitectFlow._run_crew() full execution tests."""

    @pytest.mark.asyncio
    async def test_full_execution_lifecycle(
        self, mock_tenant_client, mock_service_client, mock_event_store,
        sample_org_id, valid_workflow_definition
    ):
        """ArchitectFlow executes full lifecycle successfully."""
        flow = ArchitectFlow(org_id=sample_org_id)
        flow.state = ArchitectState(
            task_id=str(uuid4()),
            org_id=sample_org_id,
            flow_type="architect_flow",
            input_data={
                "description": "Create an invoice approval workflow",
                "conversation_id": "conv-123",
            },
        )

        # Mock agent execution
        mock_result = MagicMock()
        mock_result.raw = json.dumps(valid_workflow_definition.model_dump())

        # Mock service client for uniqueness check
        mock_service_client.table.return_value.select.return_value.eq.return_value.maybe_single.return_value.execute.return_value = MagicMock(data=None)

        with patch.object(flow, "_execute_architect_agent", new_callable=AsyncMock) as mock_exec:
            mock_exec.return_value = mock_result

            result = await flow._run_crew()

        # Verify result structure
        assert "flow_type" in result
        assert "template_id" in result
        assert "agents_created" in result
        assert "steps_count" in result
        assert result["steps_count"] == 2

        # Verify state was updated
        assert flow.state.workflow_template_id is not None
        assert len(flow.state.agents_created) == 2

    @pytest.mark.asyncio
    async def test_executes_architect_agent(
        self, mock_tenant_client, mock_service_client, sample_org_id
    ):
        """ArchitectFlow._execute_architect_agent calls the LLM."""
        flow = ArchitectFlow(org_id=sample_org_id)
        flow.state = ArchitectState(
            task_id=str(uuid4()),
            org_id=sample_org_id,
            flow_type="architect_flow",
            input_data={"description": "Test workflow"},
        )

        mock_result = MagicMock()
        mock_result.raw = '{"name": "Test", "description": "Test desc", "flow_type": "test", "steps": [{"id": "s1", "name": "S", "description": "Desc", "agent_role": "a1"}], "agents": [{"role": "a1", "goal": "Goal text here", "backstory": "Backstory text"}]}'

        with patch("src.flows.architect_flow.Agent") as mock_agent_cls:
            with patch("src.flows.architect_flow.Task") as mock_task_cls:
                with patch("src.flows.architect_flow.Crew") as mock_crew_cls:
                    mock_crew = MagicMock()
                    mock_crew_cls.return_value = mock_crew
                    mock_crew.kickoff_async.return_value = mock_result

                    result = await flow._execute_architect_agent("Test description")

                    # Crew should have been executed
                    mock_crew.kickoff_async.assert_called_once()


# ── WorkflowDefinition parsing tests ────────────────────────────

class TestWorkflowDefinitionParsing:
    """ArchitectFlow._parse_workflow_definition() tests."""

    def test_parses_clean_json(self, sample_org_id):
        """_parse_workflow_definition parses clean JSON."""
        flow = ArchitectFlow(org_id=sample_org_id)

        raw = MagicMock()
        raw.raw = json.dumps({
            "name": "Test Workflow",
            "description": "Test description here",
            "flow_type": "test_workflow",
            "steps": [{"id": "s1", "name": "Step", "description": "Description", "agent_role": "a1"}],
            "agents": [{"role": "a1", "goal": "Goal text here", "backstory": "Backstory text"}],
        })

        result = flow._parse_workflow_definition(raw)

        assert result.name == "Test Workflow"
        assert result.flow_type == "test_workflow"
        assert len(result.steps) == 1
        assert len(result.agents) == 1

    def test_parses_json_with_markdown_code_blocks(self, sample_org_id):
        """_parse_workflow_definition extracts JSON from markdown blocks."""
        flow = ArchitectFlow(org_id=sample_org_id)

        raw = MagicMock()
        raw.raw = '''Here's the workflow:

```json
{
  "name": "Test Workflow",
  "description": "Test description here",
  "flow_type": "test_workflow",
  "steps": [{"id": "s1", "name": "Step", "description": "Description", "agent_role": "a1"}],
  "agents": [{"role": "a1", "goal": "Goal text here", "backstory": "Backstory text"}]
}
```

Hope this helps!'''

        result = flow._parse_workflow_definition(raw)

        assert result.name == "Test Workflow"

    def test_parses_json_with_extraneous_text(self, sample_org_id):
        """_parse_workflow_definition handles extraneous text."""
        flow = ArchitectFlow(org_id=sample_org_id)

        raw = MagicMock()
        raw.raw = '''
        Sure! I can help with that. Here's the JSON:
        {"name": "Test Workflow", "description": "Test description here", "flow_type": "test_workflow", "steps": [{"id": "s1", "name": "Step", "description": "Description", "agent_role": "a1"}], "agents": [{"role": "a1", "goal": "Goal text here", "backstory": "Backstory text"}]}
        Let me know if you need anything else!
        '''

        result = flow._parse_workflow_definition(raw)

        assert result.name == "Test Workflow"

    def test_raises_on_invalid_json(self, sample_org_id):
        """_parse_workflow_definition raises on invalid JSON."""
        flow = ArchitectFlow(org_id=sample_org_id)

        raw = MagicMock()
        raw.raw = '{"invalid": json, "missing": quotes}'

        with pytest.raises(ValueError, match="JSON inválido"):
            flow._parse_workflow_definition(raw)

    def test_raises_on_missing_json_structure(self, sample_org_id):
        """_parse_workflow_definition raises when no JSON found."""
        flow = ArchitectFlow(org_id=sample_org_id)

        raw = MagicMock()
        raw.raw = "This is just plain text with no JSON"

        with pytest.raises(ValueError, match="no retornó un objeto JSON"):
            flow._parse_workflow_definition(raw)

    def test_validates_agent_role_references(self, sample_org_id):
        """_parse_workflow_definition validates agent role references."""
        flow = ArchitectFlow(org_id=sample_org_id)

        raw = MagicMock()
        # Step references non-existent agent role
        raw.raw = json.dumps({
            "name": "Test",
            "description": "Test description here",
            "flow_type": "test",
            "steps": [{"id": "s1", "name": "Step", "description": "Description", "agent_role": "nonexistent"}],
            "agents": [{"role": "a1", "goal": "Goal text here", "backstory": "Backstory text"}],
        })

        with pytest.raises(ValueError, match="nonexistent"):
            flow._parse_workflow_definition(raw)


# ── Flow type uniqueness tests ──────────────────────────────────

class TestFlowTypeUniqueness:
    """_ensure_unique_flow_type() behavior."""

    @patch("src.flows.architect_flow.get_service_client")
    def test_returns_same_if_unique(self, mock_svc, sample_org_id):
        """_ensure_unique_flow_type returns same name if unique."""
        mock_svc.return_value.table.return_value.select.return_value.eq.return_value.maybe_single.return_value.execute.return_value = MagicMock(data=None)

        flow = ArchitectFlow(org_id=sample_org_id)
        result = flow._ensure_unique_flow_type("unique_flow")

        assert result == "unique_flow"

    @patch("src.flows.architect_flow.get_service_client")
    def test_adds_suffix_if_exists(self, mock_svc, sample_org_id):
        """_ensure_unique_flow_type adds org suffix if exists."""
        mock_svc.return_value.table.return_value.select.return_value.eq.return_value.maybe_single.return_value.execute.return_value = MagicMock(data={"id": "existing"})

        flow = ArchitectFlow(org_id="org-abc123")
        result = flow._ensure_unique_flow_type("existing_flow")

        assert result.startswith("existing_flow_")
        assert "orgabc12" in result


# ── Template persistence tests ──────────────────────────────────

class TestTemplatePersistence:
    """_persist_template() behavior."""

    @pytest.mark.asyncio
    async def test_inserts_workflow_template(self, mock_tenant_client, sample_org_id, valid_workflow_definition):
        """_persist_template inserts workflow_templates row."""
        flow = ArchitectFlow(org_id=sample_org_id)
        flow.state = ArchitectState(
            task_id=str(uuid4()),
            org_id=sample_org_id,
            flow_type="architect_flow",
            input_data={"conversation_id": "conv-123"},
        )

        template_id = await flow._persist_template(valid_workflow_definition)

        # Insert should be called
        assert mock_tenant_client.table("workflow_templates").insert.called

        # Check inserted data
        insert_call = mock_tenant_client.table("workflow_templates").insert
        inserted_data = insert_call.call_args[0][0]
        assert inserted_data["org_id"] == sample_org_id
        assert inserted_data["name"] == "Invoice Approval Workflow"
        assert inserted_data["flow_type"] == "invoice_approval"
        assert inserted_data["conversation_id"] == "conv-123"
        assert inserted_data["is_active"] is True

    @pytest.mark.asyncio
    async def test_returns_generated_uuid(self, mock_tenant_client, sample_org_id, valid_workflow_definition):
        """_persist_template returns generated template_id."""
        flow = ArchitectFlow(org_id=sample_org_id)
        flow.state = ArchitectState(
            task_id=str(uuid4()),
            org_id=sample_org_id,
            flow_type="architect_flow",
            input_data={},
        )

        template_id = await flow._persist_template(valid_workflow_definition)

        # Should return a valid UUID string
        assert isinstance(template_id, str)
        assert len(template_id) > 0


# ── Agent persistence tests ─────────────────────────────────────

class TestAgentPersistence:
    """_persist_agents() behavior."""

    @pytest.mark.asyncio
    async def test_inserts_new_agents(self, mock_tenant_client, sample_org_id, valid_workflow_definition):
        """_persist_agents inserts new agents into agent_catalog."""
        flow = ArchitectFlow(org_id=sample_org_id)
        flow.state = ArchitectState(
            task_id=str(uuid4()),
            org_id=sample_org_id,
            flow_type="architect_flow",
            input_data={},
        )

        # Mock: no existing agents
        mock_tenant_client.table.return_value.select.return_value.eq.return_value.eq.return_value.maybe_single.return_value.execute.return_value = MagicMock(data=None)

        created = await flow._persist_agents(valid_workflow_definition)

        # Both agents should be created
        assert len(created) == 2
        assert "extractor" in created
        assert "validator" in created

        # Upsert should be called twice
        assert mock_tenant_client.table("agent_catalog").upsert.call_count == 2

    @pytest.mark.asyncio
    async def test_skips_existing_agents(self, mock_tenant_client, sample_org_id, valid_workflow_definition):
        """_persist_agents skips agents that already exist."""
        flow = ArchitectFlow(org_id=sample_org_id)
        flow.state = ArchitectState(
            task_id=str(uuid4()),
            org_id=sample_org_id,
            flow_type="architect_flow",
            input_data={},
        )

        # Mock: first agent exists, second doesn't
        call_count = [0]

        def select_side_effect(*args, **kwargs):
            call_count[0] += 1
            if call_count[0] == 1:
                # First agent exists
                return MagicMock(data={"id": "existing"})
            else:
                # Second doesn't
                return MagicMock(data=None)

        mock_tenant_client.table.return_value.select.return_value.eq.return_value.eq.return_value.maybe_single.return_value.execute.side_effect = select_side_effect

        created = await flow._persist_agents(valid_workflow_definition)

        # Only second agent should be created
        assert len(created) == 1
        assert "validator" in created

    @pytest.mark.asyncio
    async def test_upserts_with_correct_data(self, mock_tenant_client, sample_org_id):
        """_persist_agents upserts with correct agent data."""
        flow = ArchitectFlow(org_id=sample_org_id)
        flow.state = ArchitectState(
            task_id=str(uuid4()),
            org_id=sample_org_id,
            flow_type="architect_flow",
            input_data={},
        )

        # Mock: no existing agents
        mock_tenant_client.table.return_value.select.return_value.eq.return_value.eq.return_value.maybe_single.return_value.execute.return_value = MagicMock(data=None)

        workflow = WorkflowDefinition(
            name="Test",
            description="Test desc",
            flow_type="test",
            steps=[{"id": "s1", "name": "S", "description": "D", "agent_role": "test_agent"}],
            agents=[
                AgentDefinition(
                    role="test_agent",
                    goal="Test goal text",
                    backstory="Test backstory text",
                    allowed_tools=["tool1", "tool2"],
                    rules=["rule1"],
                    model="claude-sonnet-4-20250514",
                    max_iter=3,
                )
            ],
            approval_rules=[],
        )

        await flow._persist_agents(workflow)

        # Check upsert data
        upsert_call = mock_tenant_client.table("agent_catalog").upsert
        upserted_data = upsert_call.call_args[0][0]
        assert upserted_data["org_id"] == sample_org_id
        assert upserted_data["role"] == "test_agent"
        assert upserted_data["soul_json"]["goal"] == "Test goal text"
        assert upserted_data["allowed_tools"] == ["tool1", "tool2"]
        assert upserted_data["max_iter"] == 3


# ── Dynamic flow registration tests ─────────────────────────────

class TestDynamicFlowRegistration:
    """_register_dynamic_flow() behavior."""

    def test_registers_flow_in_registry(self, sample_org_id, valid_workflow_definition):
        """_register_dynamic_flow registers flow in FLOW_REGISTRY."""
        flow = ArchitectFlow(org_id=sample_org_id)
        flow.state = ArchitectState(
            task_id=str(uuid4()),
            org_id=sample_org_id,
            flow_type="architect_flow",
            input_data={},
        )

        from src.flows.registry import flow_registry
        flow_registry.clear()

        flow._register_dynamic_flow("test_registered_flow", valid_workflow_definition)

        assert flow_registry.has("test_registered_flow")

    def test_registers_with_correct_definition(self, sample_org_id, valid_workflow_definition):
        """_register_dynamic_flow registers with correct definition."""
        flow = ArchitectFlow(org_id=sample_org_id)
        flow.state = ArchitectState(
            task_id=str(uuid4()),
            org_id=sample_org_id,
            flow_type="architect_flow",
            input_data={},
        )

        from src.flows.registry import flow_registry
        from src.flows.dynamic_flow import DynamicWorkflow

        flow_registry.clear()
        flow._register_dynamic_flow("test_def_flow", valid_workflow_definition)

        FlowClass = flow_registry.get("test_def_flow")
        assert FlowClass._template_definition["name"] == "Invoice Approval Workflow"


# ── Validation integration tests ────────────────────────────────

class TestValidationIntegration:
    """Workflow validation integration tests."""

    @pytest.mark.asyncio
    async def test_rejects_invalid_workflow(self, mock_tenant_client, mock_service_client, sample_org_id):
        """ArchitectFlow rejects invalid workflows."""
        flow = ArchitectFlow(org_id=sample_org_id)
        flow.state = ArchitectState(
            task_id=str(uuid4()),
            org_id=sample_org_id,
            flow_type="architect_flow",
            input_data={"description": "Test"},
        )

        # Mock agent returns invalid workflow (missing required fields)
        mock_result = MagicMock()
        mock_result.raw = json.dumps({
            "name": "T",  # Too short (min 3)
            "description": "Short",  # Too short (min 10)
        })

        with patch.object(flow, "_execute_architect_agent", new_callable=AsyncMock) as mock_exec:
            mock_exec.return_value = mock_result

            with pytest.raises(ValueError, match="Workflow inválido"):
                await flow._run_crew()
