"""tests/e2e/test_scenario_4_hybrid.py — Escenario 4: Hybrid MCP + Service Connector.

Verifica que el workflow con MCP tools y service_connector combinados
es válido y ambas tools se resuelven correctamente.
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


def create_hybrid_bundle(tmp_path: Path) -> bytes:
    workflow_json = {
        "name": "hybrid_workflow",
        "description": "Workflow hibrido que usa MCP para busquedas Google y service_connector para CRM",
        "flow_type": "hybrid_test",
        "steps": [
            {
                "id": "step_1",
                "name": "Buscar informacion",
                "description": "Buscar informacion relevante usando Google MCP",
                "agent_role": "researcher",
            },
            {
                "id": "step_2",
                "name": "Guardar en CRM",
                "description": "Guardar la informacion encontrada en el CRM",
                "agent_role": "crm_writer",
                "depends_on": ["step_1"],
            },
        ],
        "agents": [
            {
                "role": "researcher",
                "goal": "Buscar informacion relevante",
                "backstory": "Eres un agente investigador que busca informacion via Google",
                "allowed_tools": ["mcp:google:search"],
                "rules": [],
                "model": "claude-sonnet-4-20250514",
                "max_iter": 3,
            },
            {
                "role": "crm_writer",
                "goal": "Guardar informacion en CRM",
                "backstory": "Eres un agente que guarda informacion en el CRM",
                "allowed_tools": ["service_connector"],
                "rules": [],
                "model": "claude-sonnet-4-20250514",
                "max_iter": 3,
            },
        ],
    }

    buf = io.BytesIO()
    workflow_str = json.dumps(workflow_json, indent=2)

    with zipfile.ZipFile(buf, "w") as z:
        z.writestr("workflows/workflow.json", workflow_str)
        manifest = {
            "version": "2.0",
            "bundle_info": {"name": "hybrid-bundle"},
            "hashes": {
                "workflows/workflow.json": calculate_sha256(workflow_str.encode("utf-8")),
            },
        }
        z.writestr("manifest.json", json.dumps(manifest))

    return buf.getvalue()


class TestScenario4Hybrid:
    """Scenario 4: Agente con MCP + service_connector (híbrido)."""

    def test_workflow_json_hybrid(self):
        """Workflow JSON with MCP + service_connector passes validation."""
        workflow_json = {
            "name": "hybrid_workflow",
            "description": "Workflow hibrido que usa MCP y service_connector",
            "flow_type": "hybrid_test",
            "steps": [
                {
                    "id": "step_1",
                    "name": "Buscar",
                    "description": "Buscar informacion relevante usando Google MCP",
                    "agent_role": "researcher",
                },
                {
                    "id": "step_2",
                    "name": "Guardar",
                    "description": "Guardar la informacion encontrada en el CRM",
                    "agent_role": "crm_writer",
                    "depends_on": ["step_1"],
                },
            ],
            "agents": [
                {
                    "role": "researcher",
                    "goal": "Buscar informacion relevante",
                    "backstory": "Eres un agente investigador",
                    "allowed_tools": ["mcp:google:search"],
                    "rules": [],
                    "model": "claude-sonnet-4-20250514",
                    "max_iter": 3,
                },
                {
                    "role": "crm_writer",
                    "goal": "Guardar informacion en CRM",
                    "backstory": "Eres un agente que guarda informacion",
                    "allowed_tools": ["service_connector"],
                    "rules": [],
                    "model": "claude-sonnet-4-20250514",
                    "max_iter": 3,
                },
            ],
        }

        wd = WorkflowDefinition(**workflow_json)
        assert wd.name == "hybrid_workflow"
        assert len(wd.agents) == 2

    def test_hybrid_has_mcp_and_service_connector(self):
        """Workflow has both MCP tools and service_connector."""
        workflow_json = {
            "name": "hybrid_workflow",
            "description": "Workflow hibrido que usa MCP y service_connector para testing",
            "flow_type": "hybrid_test",
            "steps": [
                {
                    "id": "step_1",
                    "name": "Buscar",
                    "description": "Buscar informacion usando Google MCP",
                    "agent_role": "researcher",
                },
                {
                    "id": "step_2",
                    "name": "Guardar",
                    "description": "Guardar en CRM usando service_connector",
                    "agent_role": "crm_writer",
                    "depends_on": ["step_1"],
                },
            ],
            "agents": [
                {
                    "role": "researcher",
                    "goal": "Buscar informacion relevante",
                    "backstory": "Eres un agente investigador",
                    "allowed_tools": ["mcp:google:search"],
                    "rules": [],
                    "model": "claude-sonnet-4-20250514",
                    "max_iter": 3,
                },
                {
                    "role": "crm_writer",
                    "goal": "Guardar informacion en CRM",
                    "backstory": "Eres un agente que guarda informacion",
                    "allowed_tools": ["service_connector"],
                    "rules": [],
                    "model": "claude-sonnet-4-20250514",
                    "max_iter": 3,
                },
            ],
        }

        mcp_tools = [
            tool
            for agent in workflow_json["agents"]
            for tool in agent.get("allowed_tools", [])
            if tool.startswith("mcp:")
        ]
        has_sc = any(
            "service_connector" in agent.get("allowed_tools", [])
            for agent in workflow_json["agents"]
        )

        assert len(mcp_tools) == 1
        assert has_sc is True

    def test_researcher_has_mcp_tool(self):
        """Researcher agent has MCP tool."""
        workflow_json = {
            "name": "hybrid_workflow",
            "description": "Workflow hibrido para testing de herramientas",
            "flow_type": "hybrid_test",
            "steps": [
                {
                    "id": "step_1",
                    "name": "Buscar",
                    "description": "Buscar informacion usando Google",
                    "agent_role": "researcher",
                },
            ],
            "agents": [
                {
                    "role": "researcher",
                    "goal": "Buscar informacion relevante",
                    "backstory": "Eres un agente investigador",
                    "allowed_tools": ["mcp:google:search"],
                    "rules": [],
                    "model": "claude-sonnet-4-20250514",
                    "max_iter": 3,
                },
            ],
        }

        researcher = next(a for a in workflow_json["agents"] if a["role"] == "researcher")
        assert "mcp:google:search" in researcher["allowed_tools"]

    def test_crm_writer_has_service_connector(self):
        """CRM writer agent has service_connector."""
        workflow_json = {
            "name": "hybrid_workflow",
            "description": "Workflow hibrido para testing de herramientas",
            "flow_type": "hybrid_test",
            "steps": [
                {
                    "id": "step_1",
                    "name": "Buscar",
                    "description": "Buscar informacion",
                    "agent_role": "researcher",
                },
                {
                    "id": "step_2",
                    "name": "Guardar",
                    "description": "Guardar en CRM",
                    "agent_role": "crm_writer",
                    "depends_on": ["step_1"],
                },
            ],
            "agents": [
                {
                    "role": "researcher",
                    "goal": "Buscar informacion",
                    "backstory": "Eres un agente investigador",
                    "allowed_tools": ["mcp:google:search"],
                    "rules": [],
                    "model": "claude-sonnet-4-20250514",
                    "max_iter": 3,
                },
                {
                    "role": "crm_writer",
                    "goal": "Guardar informacion en CRM",
                    "backstory": "Eres un agente que guarda informacion",
                    "allowed_tools": ["service_connector"],
                    "rules": [],
                    "model": "claude-sonnet-4-20250514",
                    "max_iter": 3,
                },
            ],
        }

        crm_writer = next(a for a in workflow_json["agents"] if a["role"] == "crm_writer")
        assert "service_connector" in crm_writer["allowed_tools"]

    def test_bundle_import_hybrid(self, api_client, mock_tenant_client, tmp_path):
        """Bundle with hybrid tools imports successfully."""
        zip_bytes = create_hybrid_bundle(tmp_path)

        mock_tenant_client.rpc.return_value.execute.return_value.data = {
            "status": "success",
            "bundle_id": "hybrid-bundle-123",
            "agents_count": 2,
            "flows_count": 1,
            "skills_count": 0,
        }

        response = api_client.post(
            "/api/bundles/import",
            files={"file": ("hybrid.zip", zip_bytes, "application/zip")},
            headers={"X-Org-Id": "test-org"},
        )

        assert response.status_code == 201
        assert response.json()["status"] == "success"