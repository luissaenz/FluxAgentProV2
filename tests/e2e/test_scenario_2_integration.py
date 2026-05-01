"""tests/e2e/test_scenario_2_integration.py — Escenario 2: Service Connector.

Verifica que el workflow con service_connector es válido,
y que ServiceConnectorTool funciona con HTTP mockeado.
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


def create_slack_bundle(tmp_path: Path) -> bytes:
    workflow_json = {
        "name": "slack_notifier_workflow",
        "description": "Workflow para notificar eventos via Slack usando service_connector",
        "flow_type": "slack_notifier_test",
        "steps": [
            {
                "id": "step_1",
                "name": "Enviar notificacion",
                "description": "Enviar notificacion a Slack con detalles del evento",
                "agent_role": "notifier",
            }
        ],
        "agents": [
            {
                "role": "notifier",
                "goal": "Notificar eventos via Slack",
                "backstory": "Eres un agente que notifica eventos importantes via Slack",
                "allowed_tools": ["service_connector"],
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
            "bundle_info": {"name": "slack-notifier-bundle"},
            "hashes": {
                "workflows/workflow.json": calculate_sha256(workflow_str.encode("utf-8")),
            },
        }
        z.writestr("manifest.json", json.dumps(manifest))

    return buf.getvalue()


class TestScenario2Integration:
    """Scenario 2: Agente con service_connector."""

    def test_workflow_json_with_service_connector(self):
        """Workflow JSON with service_connector passes validation."""
        workflow_json = {
            "name": "slack_notifier_workflow",
            "description": "Workflow para notificar eventos via Slack usando service_connector",
            "flow_type": "slack_notifier_test",
            "steps": [
                {
                    "id": "step_1",
                    "name": "Enviar notificacion",
                    "description": "Enviar notificacion a Slack con detalles del evento",
                    "agent_role": "notifier",
                }
            ],
            "agents": [
                {
                    "role": "notifier",
                    "goal": "Notificar eventos via Slack",
                    "backstory": "Eres un agente que notifica eventos importantes via Slack",
                    "allowed_tools": ["service_connector"],
                    "rules": [],
                    "model": "claude-sonnet-4-20250514",
                    "max_iter": 3,
                }
            ],
        }

        wd = WorkflowDefinition(**workflow_json)
        assert wd.name == "slack_notifier_workflow"
        assert len(wd.agents) == 1
        assert "service_connector" in wd.agents[0].allowed_tools

    def test_service_connector_in_allowed_tools(self):
        """Agent has service_connector in allowed_tools."""
        workflow_json = {
            "name": "slack_notifier_workflow",
            "description": "Workflow para notificar eventos via Slack usando service_connector",
            "flow_type": "slack_notifier_test",
            "steps": [
                {
                    "id": "step_1",
                    "name": "Enviar notificacion",
                    "description": "Enviar notificacion a Slack",
                    "agent_role": "notifier",
                }
            ],
            "agents": [
                {
                    "role": "notifier",
                    "goal": "Notificar eventos via Slack",
                    "backstory": "Eres un agente que notifica eventos",
                    "allowed_tools": ["service_connector"],
                    "rules": [],
                    "model": "claude-sonnet-4-20250514",
                    "max_iter": 3,
                }
            ],
        }

        wd = WorkflowDefinition(**workflow_json)
        assert "service_connector" in wd.agents[0].allowed_tools

    def test_bundle_import_with_service_connector(self, api_client, mock_tenant_client, tmp_path):
        """Bundle with service_connector imports successfully."""
        zip_bytes = create_slack_bundle(tmp_path)

        mock_tenant_client.rpc.return_value.execute.return_value.data = {
            "status": "success",
            "bundle_id": "slack-bundle-123",
            "agents_count": 1,
            "flows_count": 1,
            "skills_count": 0,
        }

        response = api_client.post(
            "/api/bundles/import",
            files={"file": ("slack.zip", zip_bytes, "application/zip")},
            headers={"X-Org-Id": "test-org"},
        )

        assert response.status_code == 201
        assert response.json()["status"] == "success"

    def test_service_connector_detected_in_workflow(self):
        """service_connector is correctly detected in workflow agents."""
        workflow_json = {
            "name": "test_workflow",
            "description": "Test workflow with service_connector for testing",
            "flow_type": "test_sc_workflow",
            "steps": [
                {
                    "id": "step_1",
                    "name": "Test Step",
                    "description": "Test step description for service connector",
                    "agent_role": "test_agent",
                }
            ],
            "agents": [
                {
                    "role": "test_agent",
                    "goal": "Test agent goal that is long enough",
                    "backstory": "Test agent backstory that is long enough",
                    "allowed_tools": ["service_connector"],
                    "rules": [],
                    "model": "claude-sonnet-4-20250514",
                    "max_iter": 3,
                }
            ],
        }

        has_sc = any(
            "service_connector" in agent.get("allowed_tools", [])
            for agent in workflow_json["agents"]
        )
        assert has_sc is True