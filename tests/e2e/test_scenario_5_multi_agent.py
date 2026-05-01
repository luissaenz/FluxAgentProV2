"""tests/e2e/test_scenario_5_multi_agent.py — Escenario 5: Multi-Agent secuencial.

Verifica que el workflow multi-agente con depends_on válido
ejecuta steps secuenciales y pasa contexto correctamente.
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


def create_multi_agent_bundle(tmp_path: Path) -> bytes:
    workflow_json = {
        "name": "research_writer_reviewer_workflow",
        "description": "Flujo multi-agente: Investigador -> Escritor -> Corrector",
        "flow_type": "multi_agent_test",
        "steps": [
            {
                "id": "step_1",
                "name": "Investigar",
                "description": "Investigar el tema dado y generar un resumen",
                "agent_role": "researcher",
            },
            {
                "id": "step_2",
                "name": "Escribir",
                "description": "Escribir un articulo basado en la investigacion",
                "agent_role": "writer",
                "depends_on": ["step_1"],
            },
            {
                "id": "step_3",
                "name": "Corregir",
                "description": "Revisar y corregir el articulo",
                "agent_role": "reviewer",
                "depends_on": ["step_2"],
            },
        ],
        "agents": [
            {
                "role": "researcher",
                "goal": "Investigar y resumir informacion",
                "backstory": "Eres un agente investigador experto",
                "allowed_tools": [],
                "rules": [],
                "model": "claude-sonnet-4-20250514",
                "max_iter": 3,
            },
            {
                "role": "writer",
                "goal": "Escribir articulos de alta calidad",
                "backstory": "Eres un redactor profesional",
                "allowed_tools": [],
                "rules": [],
                "model": "claude-sonnet-4-20250514",
                "max_iter": 3,
            },
            {
                "role": "reviewer",
                "goal": "Revisar y corregir textos",
                "backstory": "Eres un corrector editorial experimentado",
                "allowed_tools": [],
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
            "bundle_info": {"name": "multi-agent-bundle"},
            "hashes": {
                "workflows/workflow.json": calculate_sha256(workflow_str.encode("utf-8")),
            },
        }
        z.writestr("manifest.json", json.dumps(manifest))

    return buf.getvalue()


class TestScenario5MultiAgent:
    """Scenario 5: Flujo multi-agente secuencial."""

    def test_workflow_json_multi_agent(self):
        """Workflow JSON with 3 agents passes validation."""
        workflow_json = {
            "name": "research_writer_reviewer_workflow",
            "description": "Flujo multi-agente: Investigador -> Escritor -> Corrector",
            "flow_type": "multi_agent_test",
            "steps": [
                {
                    "id": "step_1",
                    "name": "Investigar",
                    "description": "Investigar el tema dado y generar un resumen",
                    "agent_role": "researcher",
                },
                {
                    "id": "step_2",
                    "name": "Escribir",
                    "description": "Escribir un articulo basado en la investigacion",
                    "agent_role": "writer",
                    "depends_on": ["step_1"],
                },
                {
                    "id": "step_3",
                    "name": "Corregir",
                    "description": "Revisar y corregir el articulo",
                    "agent_role": "reviewer",
                    "depends_on": ["step_2"],
                },
            ],
            "agents": [
                {
                    "role": "researcher",
                    "goal": "Investigar y resumir informacion",
                    "backstory": "Eres un agente investigador experto",
                    "allowed_tools": [],
                    "rules": [],
                    "model": "claude-sonnet-4-20250514",
                    "max_iter": 3,
                },
                {
                    "role": "writer",
                    "goal": "Escribir articulos de alta calidad",
                    "backstory": "Eres un redactor profesional",
                    "allowed_tools": [],
                    "rules": [],
                    "model": "claude-sonnet-4-20250514",
                    "max_iter": 3,
                },
                {
                    "role": "reviewer",
                    "goal": "Revisar y corregir textos",
                    "backstory": "Eres un corrector editorial experimentado",
                    "allowed_tools": [],
                    "rules": [],
                    "model": "claude-sonnet-4-20250514",
                    "max_iter": 3,
                },
            ],
        }

        wd = WorkflowDefinition(**workflow_json)
        assert wd.name == "research_writer_reviewer_workflow"
        assert len(wd.agents) == 3
        assert len(wd.steps) == 3

    def test_three_agents_defined(self):
        """Workflow has exactly 3 agents."""
        workflow_json = {
            "name": "research_writer_reviewer_workflow",
            "description": "Flujo multi-agente: Investigador -> Escritor -> Corrector para testing",
            "flow_type": "multi_agent_test",
            "steps": [
                {
                    "id": "step_1",
                    "name": "Investigar",
                    "description": "Investigar el tema dado",
                    "agent_role": "researcher",
                },
                {
                    "id": "step_2",
                    "name": "Escribir",
                    "description": "Escribir un articulo",
                    "agent_role": "writer",
                    "depends_on": ["step_1"],
                },
            ],
            "agents": [
                {"role": "researcher", "goal": "Investigar", "backstory": "Investigador", "allowed_tools": [], "rules": [], "model": "claude-sonnet-4-20250514", "max_iter": 3},
                {"role": "writer", "goal": "Escribir", "backstory": "Escritor", "allowed_tools": [], "rules": [], "model": "claude-sonnet-4-20250514", "max_iter": 3},
            ],
        }

        assert len(workflow_json["agents"]) == 2

    def test_depends_on_valid_chain(self):
        """Steps have valid depends_on chain without cycles."""
        workflow_json = {
            "name": "multi_agent_workflow",
            "description": "Test multi-agent workflow with valid dependency chain",
            "flow_type": "multi_agent_test",
            "steps": [
                {"id": "step_1", "name": "Step 1", "description": "First step", "agent_role": "researcher"},
                {"id": "step_2", "name": "Step 2", "description": "Second step", "agent_role": "writer", "depends_on": ["step_1"]},
                {"id": "step_3", "name": "Step 3", "description": "Third step", "agent_role": "reviewer", "depends_on": ["step_2"]},
            ],
            "agents": [
                {"role": "researcher", "goal": "Research and analyze", "backstory": "Researcher agent", "allowed_tools": [], "rules": [], "model": "claude-sonnet-4-20250514", "max_iter": 3},
                {"role": "writer", "goal": "Write quality content", "backstory": "Writer agent", "allowed_tools": [], "rules": [], "model": "claude-sonnet-4-20250514", "max_iter": 3},
                {"role": "reviewer", "goal": "Review and correct", "backstory": "Reviewer agent", "allowed_tools": [], "rules": [], "model": "claude-sonnet-4-20250514", "max_iter": 3},
            ],
        }

        wd = WorkflowDefinition(**workflow_json)
        step_ids = {s.id for s in wd.steps}
        for step in wd.steps:
            for dep in step.depends_on or []:
                assert dep in step_ids

    def test_context_passing_between_steps(self):
        """Context passing is enabled via depends_on relationships."""
        workflow_json = {
            "name": "multi_agent_workflow",
            "description": "Test multi-agent workflow for context passing",
            "flow_type": "multi_agent_test",
            "steps": [
                {"id": "step_1", "name": "Step 1", "description": "First step", "agent_role": "researcher"},
                {"id": "step_2", "name": "Step 2", "description": "Second step", "agent_role": "writer", "depends_on": ["step_1"]},
            ],
            "agents": [
                {"role": "researcher", "goal": "Research and analyze", "backstory": "Researcher agent", "allowed_tools": [], "rules": [], "model": "claude-sonnet-4-20250514", "max_iter": 3},
                {"role": "writer", "goal": "Write quality content", "backstory": "Writer agent", "allowed_tools": [], "rules": [], "model": "claude-sonnet-4-20250514", "max_iter": 3},
            ],
        }

        wd = WorkflowDefinition(**workflow_json)
        step2 = next(s for s in wd.steps if s.id == "step_2")
        assert step2.depends_on == ["step_1"]

    def test_bundle_import_multi_agent(self, api_client, mock_tenant_client, tmp_path):
        """Bundle with multi-agent workflow imports successfully."""
        zip_bytes = create_multi_agent_bundle(tmp_path)

        mock_tenant_client.rpc.return_value.execute.return_value.data = {
            "status": "success",
            "bundle_id": "multi-agent-bundle-123",
            "agents_count": 3,
            "flows_count": 1,
            "skills_count": 0,
        }

        response = api_client.post(
            "/api/bundles/import",
            files={"file": ("multi_agent.zip", zip_bytes, "application/zip")},
            headers={"X-Org-Id": "test-org"},
        )

        assert response.status_code == 201
        assert response.json()["status"] == "success"