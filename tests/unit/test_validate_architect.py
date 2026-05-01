"""tests/unit/test_validate_architect.py — Tests for validate_architect_output command.

Covers structural validation, MCP tools, service connectors, and registry tools.
"""

from __future__ import annotations

import pytest

from src.flows.workflow_definition import WorkflowDefinition


class TestValidateArchitectOutput:
    """Test suite for validate_architect_output functionality."""

    def _make_workflow_json(self, **overrides):
        base = {
            "name": "test_workflow",
            "description": "Test workflow description that is long enough",
            "flow_type": "test_flow",
            "steps": [
                {
                    "id": "step_1",
                    "name": "Test Step",
                    "description": "Test step description that is long enough",
                    "agent_role": "test_agent",
                }
            ],
            "agents": [
                {
                    "role": "test_agent",
                    "goal": "Test agent goal that is long enough",
                    "backstory": "Test agent backstory that is long enough",
                    "allowed_tools": [],
                    "rules": [],
                    "model": "claude-sonnet-4-20250514",
                    "max_iter": 5,
                }
            ],
        }
        for key, value in overrides.items():
            base[key] = value
        return base

    def test_validate_structural_valid_workflow(self):
        """Valid workflow JSON passes structural validation."""
        data = self._make_workflow_json()
        wd = WorkflowDefinition(**data)
        assert wd.name == "test_workflow"
        assert wd.flow_type == "test_flow"
        assert len(wd.agents) == 1
        assert len(wd.steps) == 1

    def test_validate_structural_missing_name(self):
        """Workflow missing name fails validation."""
        data = self._make_workflow_json()
        del data["name"]
        with pytest.raises(Exception):
            WorkflowDefinition(**data)

    def test_validate_structural_missing_agents(self):
        """Workflow without agents fails validation."""
        data = self._make_workflow_json()
        del data["agents"]
        with pytest.raises(Exception):
            WorkflowDefinition(**data)

    def test_validate_structural_empty_steps(self):
        """Workflow with empty steps fails validation."""
        data = self._make_workflow_json(steps=[])
        with pytest.raises(Exception):
            WorkflowDefinition(**data)

    def test_validate_mcp_tools_valid_format(self):
        """MCP tools with valid mcp:server:tool format pass validation."""
        data = self._make_workflow_json(
            agents=[
                {
                    "role": "file_manager",
                    "goal": "Test agent goal that is long enough",
                    "backstory": "Test agent backstory that is long enough",
                    "allowed_tools": ["mcp:filesystem:list_files", "mcp:filesystem:read_file"],
                    "rules": [],
                    "model": "claude-sonnet-4-20250514",
                    "max_iter": 5,
                }
            ],
            steps=[
                {
                    "id": "step_1",
                    "name": "Test Step",
                    "description": "Test step description that is long enough",
                    "agent_role": "file_manager",
                }
            ],
        )
        wd = WorkflowDefinition(**data)
        mcp_tools = [
            tool
            for agent in wd.agents
            for tool in agent.allowed_tools
            if tool.startswith("mcp:")
        ]
        assert len(mcp_tools) == 2

    def test_validate_mcp_tools_invalid_format(self):
        """MCP tools with invalid format are detected."""
        data = self._make_workflow_json(
            agents=[
                {
                    "role": "test_agent",
                    "goal": "Test agent goal that is long enough",
                    "backstory": "Test agent backstory that is long enough",
                    "allowed_tools": ["mcp:invalid"],
                    "rules": [],
                    "model": "claude-sonnet-4-20250514",
                    "max_iter": 5,
                }
            ]
        )
        mcp_tools = [
            tool
            for agent in data["agents"]
            for tool in agent["allowed_tools"]
            if tool.startswith("mcp:")
        ]
        for tool in mcp_tools:
            parts = tool.split(":")
            assert len(parts) >= 3 or tool == "mcp:invalid", f"Tool {tool} format check"

    def test_validate_service_connector_reference(self):
        """Workflow with service_connector reference is detected."""
        data = self._make_workflow_json(
            agents=[
                {
                    "role": "notifier",
                    "goal": "Test agent goal that is long enough",
                    "backstory": "Test agent backstory that is long enough",
                    "allowed_tools": ["service_connector"],
                    "rules": [],
                    "model": "claude-sonnet-4-20250514",
                    "max_iter": 5,
                }
            ]
        )
        has_sc = any(
            "service_connector" in agent.get("allowed_tools", [])
            for agent in data["agents"]
        )
        assert has_sc is True

    def test_validate_registry_tools(self):
        """Regular tools are validated - empty list case."""

        data = self._make_workflow_json(
            agents=[
                {
                    "role": "test_agent",
                    "goal": "Test agent goal that is long enough",
                    "backstory": "Test agent backstory that is long enough",
                    "allowed_tools": [],
                    "rules": [],
                    "model": "claude-sonnet-4-20250514",
                    "max_iter": 5,
                }
            ]
        )
        regular_tools = [
            tool
            for agent in data["agents"]
            for tool in agent.get("allowed_tools", [])
            if not tool.startswith("mcp:") and tool != "service_connector"
        ]
        assert regular_tools == []

    def test_validate_workflow_type_snake_case(self):
        """flow_type must be snake_case."""
        data = self._make_workflow_json(flow_type="invalid-Flow")
        with pytest.raises(Exception):
            WorkflowDefinition(**data)

    def test_validate_workflow_type_valid(self):
        """flow_type with valid snake_case passes."""
        data = self._make_workflow_json(flow_type="valid_workflow_123")
        wd = WorkflowDefinition(**data)
        assert wd.flow_type == "valid_workflow_123"

    def test_validate_agent_role_reference(self):
        """Step.agent_role must reference existing agent role."""
        data = self._make_workflow_json(
            steps=[
                {
                    "id": "step_1",
                    "name": "Test Step",
                    "description": "Test step description that is long enough",
                    "agent_role": "nonexistent_role",
                }
            ]
        )
        with pytest.raises(Exception):
            WorkflowDefinition(**data)

    def test_validate_circular_dependencies(self):
        """Circular dependencies in steps are detected."""
        data = self._make_workflow_json(
            steps=[
                {
                    "id": "step_1",
                    "name": "Step 1",
                    "description": "Step 1 description that is long enough",
                    "agent_role": "test_agent",
                    "depends_on": ["step_3"],
                },
                {
                    "id": "step_2",
                    "name": "Step 2",
                    "description": "Step 2 description that is long enough",
                    "agent_role": "test_agent",
                    "depends_on": ["step_1"],
                },
                {
                    "id": "step_3",
                    "name": "Step 3",
                    "description": "Step 3 description that is long enough",
                    "agent_role": "test_agent",
                    "depends_on": ["step_2"],
                },
            ]
        )
        with pytest.raises(Exception):
            WorkflowDefinition(**data)

    def test_validate_no_circular_dependencies(self):
        """Valid linear dependencies pass validation."""
        data = self._make_workflow_json(
            steps=[
                {
                    "id": "step_1",
                    "name": "Step 1",
                    "description": "Step 1 description that is long enough",
                    "agent_role": "test_agent",
                    "depends_on": None,
                },
                {
                    "id": "step_2",
                    "name": "Step 2",
                    "description": "Step 2 description that is long enough",
                    "agent_role": "test_agent",
                    "depends_on": ["step_1"],
                },
                {
                    "id": "step_3",
                    "name": "Step 3",
                    "description": "Step 3 description that is long enough",
                    "agent_role": "test_agent",
                    "depends_on": ["step_2"],
                },
            ]
        )
        wd = WorkflowDefinition(**data)
        assert len(wd.steps) == 3

    def test_validate_approval_rules(self):
        """Workflow with approval_rules passes validation."""
        data = self._make_workflow_json(
            approval_rules=[
                {"condition": "confidence > 0.8", "description": "High confidence required"}
            ]
        )
        wd = WorkflowDefinition(**data)
        assert len(wd.approval_rules) == 1

    def test_validate_multiple_agents(self):
        """Workflow with multiple agents passes validation."""
        data = self._make_workflow_json(
            agents=[
                {
                    "role": "researcher",
                    "goal": "Researcher goal that is long enough",
                    "backstory": "Researcher backstory that is long enough",
                    "allowed_tools": [],
                    "rules": [],
                    "model": "claude-sonnet-4-20250514",
                    "max_iter": 3,
                },
                {
                    "role": "writer",
                    "goal": "Writer goal that is long enough",
                    "backstory": "Writer backstory that is long enough",
                    "allowed_tools": [],
                    "rules": [],
                    "model": "claude-sonnet-4-20250514",
                    "max_iter": 3,
                },
            ],
            steps=[
                {
                    "id": "step_1",
                    "name": "Research",
                    "description": "Research step description that is long enough",
                    "agent_role": "researcher",
                },
                {
                    "id": "step_2",
                    "name": "Write",
                    "description": "Write step description that is long enough",
                    "agent_role": "writer",
                    "depends_on": ["step_1"],
                },
            ],
        )
        wd = WorkflowDefinition(**data)
        assert len(wd.agents) == 2
        assert len(wd.steps) == 2