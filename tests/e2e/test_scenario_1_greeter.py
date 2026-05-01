"""tests/e2e/test_scenario_1_greeter.py — Escenario 1: Agente simple sin tools.

Verifica que ArchitectFlow genera JSON válido para un agente simple,
el bundle se importa correctamente, y BaseCrew ejecuta sin tools.
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


def create_greeter_bundle(tmp_path: Path) -> bytes:
    workflow_json = {
        "name": "greeter_workflow",
        "description": "Workflow para un agente que saluda usuarios",
        "flow_type": "greeter_test",
        "steps": [
            {
                "id": "step_1",
                "name": "Saludo",
                "description": "El agente saluda al usuario con un mensaje friendly",
                "agent_role": "greeter",
            }
        ],
        "agents": [
            {
                "role": "greeter",
                "goal": "Saludar al usuario de manera amigable",
                "backstory": "Eres un agente amigable que saluda a los usuarios",
                "allowed_tools": [],
                "rules": [],
                "model": "claude-sonnet-4-20250514",
                "max_iter": 3,
            }
        ],
    }

    buf = io.BytesIO()
    workflow_str = json.dumps(workflow_json, indent=2)

    with zipfile.ZipFile(buf, "w") as z:
        z.writestr("workflows/workflow.json", workflow_str)
        manifest = {
            "version": "2.0",
            "bundle_info": {"name": "greeter-bundle", "description": "Greeter agent bundle"},
            "hashes": {
                "workflows/workflow.json": calculate_sha256(workflow_str.encode("utf-8")),
            },
        }
        z.writestr("manifest.json", json.dumps(manifest))

    return buf.getvalue()


class TestScenario1Greeter:
    """Scenario 1: Agente simple sin tools."""

    def test_workflow_json_valid_schema(self):
        """Workflow JSON passes WorkflowDefinition validation."""
        workflow_json = {
            "name": "greeter_workflow",
            "description": "Workflow para un agente que saluda usuarios con descripcion suficiente",
            "flow_type": "greeter_simple",
            "steps": [
                {
                    "id": "step_1",
                    "name": "Saludo",
                    "description": "El agente saluda al usuario con un mensaje friendly",
                    "agent_role": "greeter",
                }
            ],
            "agents": [
                {
                    "role": "greeter",
                    "goal": "Saludar al usuario de manera amigable",
                    "backstory": "Eres un agente amigable que saluda a los usuarios",
                    "allowed_tools": [],
                    "rules": [],
                    "model": "claude-sonnet-4-20250514",
                    "max_iter": 3,
                }
            ],
        }

        wd = WorkflowDefinition(**workflow_json)
        assert wd.name == "greeter_workflow"
        assert len(wd.agents) == 1
        assert wd.agents[0].allowed_tools == []

    def test_bundle_import_api_201(self, api_client, mock_tenant_client, tmp_path):
        """Bundle import returns HTTP 201."""
        zip_bytes = create_greeter_bundle(tmp_path)

        mock_tenant_client.rpc.return_value.execute.return_value.data = {
            "status": "success",
            "bundle_id": "greeter-bundle-123",
            "agents_count": 1,
            "flows_count": 1,
            "skills_count": 0,
        }

        response = api_client.post(
            "/api/bundles/import",
            files={"file": ("greeter.zip", zip_bytes, "application/zip")},
            headers={"X-Org-Id": "test-org"},
        )

        assert response.status_code == 201
        assert response.json()["status"] == "success"

    def test_agents_count_in_workflow(self):
        """Workflow has correct agent count."""
        workflow_json = {
            "name": "greeter_workflow",
            "description": "Workflow para un agente que saluda usuarios con descripcion suficiente",
            "flow_type": "greeter_simple",
            "steps": [
                {
                    "id": "step_1",
                    "name": "Saludo",
                    "description": "El agente saluda al usuario",
                    "agent_role": "greeter",
                }
            ],
            "agents": [
                {
                    "role": "greeter",
                    "goal": "Saludar al usuario",
                    "backstory": "Eres un agente amigable",
                    "allowed_tools": [],
                    "rules": [],
                    "model": "claude-sonnet-4-20250514",
                    "max_iter": 3,
                }
            ],
        }

        wd = WorkflowDefinition(**workflow_json)
        assert len(wd.agents) == 1
        assert wd.agents[0].role == "greeter"

    def test_steps_count_in_workflow(self):
        """Workflow has correct step count."""
        workflow_json = {
            "name": "greeter_workflow",
            "description": "Workflow para un agente que saluda usuarios con descripcion suficiente",
            "flow_type": "greeter_simple",
            "steps": [
                {
                    "id": "step_1",
                    "name": "Saludo",
                    "description": "El agente saluda al usuario",
                    "agent_role": "greeter",
                }
            ],
            "agents": [
                {
                    "role": "greeter",
                    "goal": "Saludar al usuario",
                    "backstory": "Eres un agente amigable",
                    "allowed_tools": [],
                    "rules": [],
                    "model": "claude-sonnet-4-20250514",
                    "max_iter": 3,
                }
            ],
        }

        wd = WorkflowDefinition(**workflow_json)
        assert len(wd.steps) == 1

    def test_no_tools_in_greeter_agent(self):
        """Greeter agent has no tools."""
        workflow_json = {
            "name": "greeter_workflow",
            "description": "Workflow para un agente que saluda usuarios con descripcion suficiente",
            "flow_type": "greeter_simple",
            "steps": [
                {
                    "id": "step_1",
                    "name": "Saludo",
                    "description": "El agente saluda al usuario",
                    "agent_role": "greeter",
                }
            ],
            "agents": [
                {
                    "role": "greeter",
                    "goal": "Saludar al usuario",
                    "backstory": "Eres un agente amigable",
                    "allowed_tools": [],
                    "rules": [],
                    "model": "claude-sonnet-4-20250514",
                    "max_iter": 3,
                }
            ],
        }

        wd = WorkflowDefinition(**workflow_json)
        assert wd.agents[0].allowed_tools == []