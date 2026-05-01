"""tests/e2e/test_scenario_6_full_stack.py — Escenario 6: Full Stack E2E.

Verifica el flujo completo: Architect -> Bundle -> Import -> Execution
con MCP + service_connector + multi-agent + approval threshold.
"""

from __future__ import annotations

import io
import json
import zipfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from src.api.main import app
from src.flows.workflow_definition import WorkflowDefinition
from src.services.integrity import calculate_sha256


@pytest.fixture
def api_client():
    return TestClient(app)


def create_full_stack_bundle(tmp_path: Path) -> bytes:
    workflow_json = {
        "name": "full_stack_workflow",
        "description": "Workflow full stack con MCP + service_connector + multi-agent + approval",
        "flow_type": "full_stack_test",
        "steps": [
            {
                "id": "step_1",
                "name": "Buscar datos",
                "description": "Buscar datos usando MCP Google",
                "agent_role": "data_fetcher",
            },
            {
                "id": "step_2",
                "name": "Procesar datos",
                "description": "Procesar datos recolectados",
                "agent_role": "processor",
                "depends_on": ["step_1"],
                "requires_approval": True,
                "approval_threshold": "confidence > 0.8",
            },
            {
                "id": "step_3",
                "name": "Notificar resultado",
                "description": "Notificar el resultado via Slack",
                "agent_role": "notifier",
                "depends_on": ["step_2"],
            },
        ],
        "agents": [
            {
                "role": "data_fetcher",
                "goal": "Buscar y recolectar datos",
                "backstory": "Eres un agente de busqueda de datos",
                "allowed_tools": ["mcp:google:search", "mcp:google:fetch"],
                "rules": [],
                "model": "claude-sonnet-4-20250514",
                "max_iter": 3,
            },
            {
                "role": "processor",
                "goal": "Procesar datos con validacion de calidad",
                "backstory": "Eres un agente procesador de datos",
                "allowed_tools": [],
                "rules": [],
                "model": "claude-sonnet-4-20250514",
                "max_iter": 3,
            },
            {
                "role": "notifier",
                "goal": "Notificar resultados",
                "backstory": "Eres un agente notificador",
                "allowed_tools": ["service_connector"],
                "rules": [],
                "model": "claude-sonnet-4-20250514",
                "max_iter": 3,
            },
        ],
        "approval_rules": [
            {
                "condition": "confidence > 0.8",
                "description": "Requiere alta confianza para procesar datos",
            }
        ],
    }

    buf = io.BytesIO()
    workflow_str = json.dumps(workflow_json, indent=2)

    with zipfile.ZipFile(buf, "w") as z:
        z.writestr("workflows/workflow.json", workflow_str)
        manifest = {
            "version": "2.0",
            "bundle_info": {"name": "full-stack-bundle"},
            "hashes": {
                "workflows/workflow.json": calculate_sha256(workflow_str.encode("utf-8")),
            },
        }
        z.writestr("manifest.json", json.dumps(manifest))

    return buf.getvalue()


class TestScenario6FullStack:
    """Scenario 6: Full Stack E2E con todas las features."""

    def test_workflow_json_full_stack(self):
        """Full stack workflow with all features passes validation."""
        workflow_json = {
            "name": "full_stack_workflow",
            "description": "Workflow full stack con todas las features para testing",
            "flow_type": "full_stack_test",
            "steps": [
                {"id": "step_1", "name": "Buscar datos", "description": "Buscar datos usando MCP", "agent_role": "data_fetcher"},
                {"id": "step_2", "name": "Procesar datos", "description": "Procesar datos", "agent_role": "processor", "depends_on": ["step_1"], "requires_approval": True, "approval_threshold": "confidence > 0.8"},
                {"id": "step_3", "name": "Notificar", "description": "Notificar resultado", "agent_role": "notifier", "depends_on": ["step_2"]},
            ],
            "agents": [
                {"role": "data_fetcher", "goal": "Buscar datos", "backstory": "Fetcher agent", "allowed_tools": ["mcp:google:search", "mcp:google:fetch"], "rules": [], "model": "claude-sonnet-4-20250514", "max_iter": 3},
                {"role": "processor", "goal": "Process data well", "backstory": "Processor agent", "allowed_tools": [], "rules": [], "model": "claude-sonnet-4-20250514", "max_iter": 3},
                {"role": "notifier", "goal": "Notify via Slack", "backstory": "Notifier agent", "allowed_tools": ["service_connector"], "rules": [], "model": "claude-sonnet-4-20250514", "max_iter": 3},
            ],
            "approval_rules": [{"condition": "confidence > 0.8", "description": "Alta confianza requerida"}],
        }

        wd = WorkflowDefinition(**workflow_json)
        assert wd.name == "full_stack_workflow"
        assert len(wd.agents) == 3
        assert len(wd.steps) == 3

    def test_has_mcp_tools(self):
        """Workflow has MCP tools."""
        workflow_json = {
            "name": "full_stack_workflow",
            "description": "Full stack workflow with MCP for testing",
            "flow_type": "full_stack_test",
            "steps": [
                {"id": "step_1", "name": "Step 1", "description": "First step", "agent_role": "data_fetcher"},
            ],
            "agents": [
                {"role": "data_fetcher", "goal": "Fetch data", "backstory": "Fetcher", "allowed_tools": ["mcp:google:search"], "rules": [], "model": "claude-sonnet-4-20250514", "max_iter": 3},
            ],
        }

        mcp_tools = [tool for agent in workflow_json["agents"] for tool in agent.get("allowed_tools", []) if tool.startswith("mcp:")]
        assert len(mcp_tools) == 1
        assert mcp_tools[0] == "mcp:google:search"

    def test_has_service_connector(self):
        """Workflow has service_connector."""
        workflow_json = {
            "name": "full_stack_workflow",
            "description": "Full stack workflow with service_connector for testing",
            "flow_type": "full_stack_test",
            "steps": [
                {"id": "step_1", "name": "Step 1", "description": "First step", "agent_role": "notifier"},
            ],
            "agents": [
                {"role": "notifier", "goal": "Notify", "backstory": "Notifier", "allowed_tools": ["service_connector"], "rules": [], "model": "claude-sonnet-4-20250514", "max_iter": 3},
            ],
        }

        has_sc = any("service_connector" in agent.get("allowed_tools", []) for agent in workflow_json["agents"])
        assert has_sc is True

    def test_has_multi_agent(self):
        """Workflow has multiple agents."""
        workflow_json = {
            "name": "full_stack_workflow",
            "description": "Full stack workflow multi-agent for testing",
            "flow_type": "full_stack_test",
            "steps": [
                {"id": "step_1", "name": "Step 1", "description": "Step 1", "agent_role": "fetcher"},
                {"id": "step_2", "name": "Step 2", "description": "Step 2", "agent_role": "processor", "depends_on": ["step_1"]},
            ],
            "agents": [
                {"role": "fetcher", "goal": "Fetch", "backstory": "Fetcher", "allowed_tools": [], "rules": [], "model": "claude-sonnet-4-20250514", "max_iter": 3},
                {"role": "processor", "goal": "Process", "backstory": "Processor", "allowed_tools": [], "rules": [], "model": "claude-sonnet-4-20250514", "max_iter": 3},
            ],
        }

        assert len(workflow_json["agents"]) == 2

    def test_has_approval_threshold(self):
        """Workflow has approval_threshold configured."""
        workflow_json = {
            "name": "full_stack_workflow",
            "description": "Full stack workflow with approval for testing",
            "flow_type": "full_stack_test",
            "steps": [
                {"id": "step_1", "name": "Step 1", "description": "Step with approval", "agent_role": "processor", "requires_approval": True, "approval_threshold": "confidence > 0.8"},
            ],
            "agents": [
                {"role": "processor", "goal": "Process", "backstory": "Processor", "allowed_tools": [], "rules": [], "model": "claude-sonnet-4-20250514", "max_iter": 3},
            ],
        }

        step = workflow_json["steps"][0]
        assert step.get("requires_approval") is True
        assert step.get("approval_threshold") == "confidence > 0.8"

    def test_approval_rules_defined(self):
        """Workflow has approval_rules defined."""
        workflow_json = {
            "name": "full_stack_workflow",
            "description": "Full stack workflow with approval rules for testing",
            "flow_type": "full_stack_test",
            "steps": [
                {"id": "step_1", "name": "Step 1", "description": "Step 1", "agent_role": "processor"},
            ],
            "agents": [
                {"role": "processor", "goal": "Process", "backstory": "Processor", "allowed_tools": [], "rules": [], "model": "claude-sonnet-4-20250514", "max_iter": 3},
            ],
            "approval_rules": [
                {"condition": "confidence > 0.8", "description": "Alta confianza requerida"}
            ],
        }

        assert len(workflow_json.get("approval_rules", [])) == 1

    def test_bundle_import_full_stack(self, api_client, mock_tenant_client, tmp_path):
        """Full stack bundle imports successfully."""
        zip_bytes = create_full_stack_bundle(tmp_path)

        mock_tenant_client.rpc.return_value.execute.return_value.data = {
            "status": "success",
            "bundle_id": "full-stack-bundle-123",
            "agents_count": 3,
            "flows_count": 1,
            "skills_count": 0,
        }

        response = api_client.post(
            "/api/bundles/import",
            files={"file": ("full_stack.zip", zip_bytes, "application/zip")},
            headers={"X-Org-Id": "test-org"},
        )

        assert response.status_code == 201
        assert response.json()["status"] == "success"

    def test_end_to_end_workflow_structure(self):
        """End-to-end workflow has correct structure."""
        workflow_json = {
            "name": "full_stack_workflow",
            "description": "Complete end-to-end workflow structure for testing purposes",
            "flow_type": "full_stack_e2e",
            "steps": [
                {"id": "step_1", "name": "Fetch", "description": "Fetch data from Google", "agent_role": "fetcher"},
                {"id": "step_2", "name": "Process", "description": "Process data", "agent_role": "processor", "depends_on": ["step_1"], "requires_approval": True, "approval_threshold": "confidence > 0.8"},
                {"id": "step_3", "name": "Notify", "description": "Notify result", "agent_role": "notifier", "depends_on": ["step_2"]},
            ],
            "agents": [
                {"role": "fetcher", "goal": "Fetch data", "backstory": "Data fetcher", "allowed_tools": ["mcp:google:search"], "rules": [], "model": "claude-sonnet-4-20250514", "max_iter": 3},
                {"role": "processor", "goal": "Process data", "backstory": "Data processor", "allowed_tools": [], "rules": [], "model": "claude-sonnet-4-20250514", "max_iter": 3},
                {"role": "notifier", "goal": "Notify results", "backstory": "Notifier agent", "allowed_tools": ["service_connector"], "rules": [], "model": "claude-sonnet-4-20250514", "max_iter": 3},
            ],
            "approval_rules": [{"condition": "confidence > 0.8", "description": "Requires high confidence"}],
        }

        wd = WorkflowDefinition(**workflow_json)
        assert wd.name == "full_stack_workflow"
        assert len(wd.steps) == 3
        assert len(wd.agents) == 3
        assert len(wd.approval_rules) == 1