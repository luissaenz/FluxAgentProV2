"""tests/e2e/test_scenario_3_mcp.py — Escenario 3: MCP Tools.

Verifica que el workflow con MCP tools (mcp:server:tool format)
es válido y que MCPPool puede ser mockeado correctamente.
"""

from __future__ import annotations

import io
import json
import zipfile
from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from src.api.main import app
from src.flows.workflow_definition import WorkflowDefinition
from src.services.integrity import calculate_sha256


@pytest.fixture
def api_client():
    return TestClient(app)


def create_file_manager_bundle(tmp_path: Path) -> bytes:
    workflow_json = {
        "name": "file_manager_workflow",
        "description": "Workflow para gestionar archivos usando MCP filesystem server",
        "flow_type": "file_manager_test",
        "steps": [
            {
                "id": "step_1",
                "name": "Listar archivos",
                "description": "Listar archivos en el directorio especificado",
                "agent_role": "file_manager",
            },
            {
                "id": "step_2",
                "name": "Leer archivo",
                "description": "Leer el contenido de un archivo especifico",
                "agent_role": "file_manager",
                "depends_on": ["step_1"],
            },
        ],
        "agents": [
            {
                "role": "file_manager",
                "goal": "Gestionar archivos del sistema",
                "backstory": "Eres un agente que gestiona archivos usando el servidor MCP filesystem",
                "allowed_tools": ["mcp:filesystem:list_files", "mcp:filesystem:read_file"],
                "rules": [],
                "model": "claude-sonnet-4-20250514",
                "max_iter": 5,
            }
        ],
    }

    buf = io.BytesIO()
    workflow_str = json.dumps(workflow_json, indent=2)

    with zipfile.ZipFile(buf, "w") as z:
        z.writestr("workflows/workflow.json", workflow_str)
        manifest = {
            "version": "2.0",
            "bundle_info": {"name": "file-manager-bundle"},
            "hashes": {
                "workflows/workflow.json": calculate_sha256(workflow_str.encode("utf-8")),
            },
        }
        z.writestr("manifest.json", json.dumps(manifest))

    return buf.getvalue()


class TestScenario3MCP:
    """Scenario 3: Agente con MCP tools."""

    def test_workflow_json_with_mcp_tools(self):
        """Workflow JSON with MCP tools passes validation."""
        workflow_json = {
            "name": "file_manager_workflow",
            "description": "Workflow para gestionar archivos usando MCP filesystem server",
            "flow_type": "file_manager_test",
            "steps": [
                {
                    "id": "step_1",
                    "name": "Listar archivos",
                    "description": "Listar archivos en el directorio especificado",
                    "agent_role": "file_manager",
                }
            ],
            "agents": [
                {
                    "role": "file_manager",
                    "goal": "Gestionar archivos del sistema",
                    "backstory": "Eres un agente que gestiona archivos usando el servidor MCP filesystem",
                    "allowed_tools": ["mcp:filesystem:list_files", "mcp:filesystem:read_file"],
                    "rules": [],
                    "model": "claude-sonnet-4-20250514",
                    "max_iter": 5,
                }
            ],
        }

        wd = WorkflowDefinition(**workflow_json)
        assert wd.name == "file_manager_workflow"
        assert len(wd.agents) == 1

    def test_mcp_tools_format_valid(self):
        """MCP tools have valid mcp:server:tool format."""
        workflow_json = {
            "name": "file_manager_workflow",
            "description": "Workflow para gestionar archivos usando MCP filesystem server",
            "flow_type": "file_manager_test",
            "steps": [
                {
                    "id": "step_1",
                    "name": "Listar archivos",
                    "description": "Listar archivos en el directorio",
                    "agent_role": "file_manager",
                }
            ],
            "agents": [
                {
                    "role": "file_manager",
                    "goal": "Gestionar archivos del sistema",
                    "backstory": "Eres un agente que gestiona archivos",
                    "allowed_tools": ["mcp:filesystem:list_files", "mcp:filesystem:read_file"],
                    "rules": [],
                    "model": "claude-sonnet-4-20250514",
                    "max_iter": 5,
                }
            ],
        }

        mcp_tools = [
            tool
            for agent in workflow_json["agents"]
            for tool in agent.get("allowed_tools", [])
            if tool.startswith("mcp:")
        ]

        assert len(mcp_tools) == 2
        for tool in mcp_tools:
            parts = tool.split(":")
            assert len(parts) == 3
            assert parts[0] == "mcp"
            assert parts[1] and parts[2]

    def test_mcp_tools_detected_in_workflow(self):
        """MCP tools are correctly detected in workflow agents."""
        workflow_json = {
            "name": "test_workflow",
            "description": "Test workflow with MCP tools for testing purposes",
            "flow_type": "test_mcp_workflow",
            "steps": [
                {
                    "id": "step_1",
                    "name": "Test Step",
                    "description": "Test step description for MCP tools",
                    "agent_role": "test_agent",
                }
            ],
            "agents": [
                {
                    "role": "test_agent",
                    "goal": "Test agent goal that is long enough",
                    "backstory": "Test agent backstory that is long enough",
                    "allowed_tools": ["mcp:filesystem:list_files", "mcp:google:search"],
                    "rules": [],
                    "model": "claude-sonnet-4-20250514",
                    "max_iter": 5,
                }
            ],
        }

        mcp_tools = [
            tool
            for agent in workflow_json["agents"]
            for tool in agent.get("allowed_tools", [])
            if tool.startswith("mcp:")
        ]

        assert len(mcp_tools) == 2
        assert "mcp:filesystem:list_files" in mcp_tools
        assert "mcp:google:search" in mcp_tools

    def test_mcp_pool_mocked_correctly(self, mock_mcp_pool):
        """MCPPool.get_tools() returns mocked tools."""
        import asyncio

        async def run_test():
            tools = await mock_mcp_pool.get_tools("org-123", "filesystem")
            return tools

        tools = asyncio.run(run_test())
        assert len(tools) == 3
        assert tools[0].name == "list_files"
        assert tools[1].name == "read_file"
        assert tools[2].name == "write_file"

    def test_async_mode_required_for_mcp(self):
        """MCP tools require async_mode in AgentFactory.resolve_tools."""
        from src.crews.factory import AgentFactory

        with patch.object(AgentFactory, "_resolve_mcp_tool", return_value=None):
            tools = AgentFactory.resolve_tools(
                ["mcp:filesystem:list_files"], "org-123", async_mode=False
            )
            assert tools == []

    def test_bundle_import_with_mcp_tools(self, api_client, mock_tenant_client, tmp_path):
        """Bundle with MCP tools imports successfully."""
        zip_bytes = create_file_manager_bundle(tmp_path)

        mock_tenant_client.rpc.return_value.execute.return_value.data = {
            "status": "success",
            "bundle_id": "file-manager-bundle-123",
            "agents_count": 1,
            "flows_count": 1,
            "skills_count": 0,
        }

        response = api_client.post(
            "/api/bundles/import",
            files={"file": ("file_manager.zip", zip_bytes, "application/zip")},
            headers={"X-Org-Id": "test-org"},
        )

        assert response.status_code == 201
        assert response.json()["status"] == "success"