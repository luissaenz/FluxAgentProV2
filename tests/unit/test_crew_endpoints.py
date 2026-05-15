"""tests/unit/test_crew_endpoints.py — Unit tests for GET /agents and POST /workflows endpoints."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from src.api.main import app

AGENT_LIST_DATA = [
    {
        "id": "a1111111-1111-1111-1111-111111111111",
        "role": "researcher",
        "soul_json": {"goal": "Research topics", "backstory": "Expert researcher"},
        "allowed_tools": ["web_search"],
        "max_iter": 3,
        "is_active": True,
        "org_id": "org-001",
    },
    {
        "id": "a2222222-2222-2222-2222-222222222222",
        "role": "writer",
        "soul_json": {"goal": "Write content", "backstory": "Creative writer"},
        "allowed_tools": [],
        "max_iter": 4,
        "is_active": False,
        "org_id": "org-001",
    },
]


@pytest.fixture
def client():
    return TestClient(app)


class TestListAgents:
    def test_list_agents_active_only(self, client):
        """TP-1: GET /agents lista agentes de org con active_only=true."""
        mock_response = MagicMock()
        mock_response.data = AGENT_LIST_DATA[:1]

        with patch("src.api.routes.agents.get_tenant_client") as mock_tenant:
            mock_db = MagicMock()
            mock_query = MagicMock()
            mock_query.eq.return_value = mock_query
            mock_query.execute.return_value = mock_response
            mock_db.table.return_value.select.return_value.eq.return_value = mock_query
            mock_tenant.return_value.__enter__.return_value = mock_db

            response = client.get("/agents?active_only=true", headers={"X-Org-ID": "org-001"})

        assert response.status_code == 200
        data = response.json()
        assert "agents" in data
        assert len(data["agents"]) == 1
        agent = data["agents"][0]
        assert agent["role"] == "researcher"
        assert agent["goal"] == "Research topics"
        assert agent["backstory"] == "Expert researcher"
        assert agent["allowed_tools"] == ["web_search"]
        assert agent["max_iter"] == 3

    def test_list_agents_empty_org(self, client):
        """TP-2: GET /agents con org sin agentes."""
        mock_response = MagicMock()
        mock_response.data = []

        with patch("src.api.routes.agents.get_tenant_client") as mock_tenant:
            mock_db = MagicMock()
            mock_query = MagicMock()
            mock_query.eq.return_value = mock_query
            mock_query.execute.return_value = mock_response
            mock_db.table.return_value.select.return_value.eq.return_value = mock_query
            mock_tenant.return_value.__enter__.return_value = mock_db

            response = client.get("/agents?active_only=true", headers={"X-Org-ID": "org-empty"})

        assert response.status_code == 200
        data = response.json()
        assert "agents" in data
        assert len(data["agents"]) == 0

    def test_list_agents_missing_org_id(self, client):
        """GET /agents sin X-Org-ID header → 400 o 422 (FastAPI validation)."""
        response = client.get("/agents")
        assert response.status_code in (400, 422)


class TestCreateWorkflow:
    def test_create_workflow_success(self, client):
        """TP-3: POST /workflows crea workflow_template."""
        mock_existing = MagicMock()
        mock_existing.data = None  # no existing workflow

        with patch("src.api.routes.workflows.get_tenant_client") as mock_tenant:
            def mock_select_side_effect(*_args, **_kwargs):
                return mock_existing

            mock_db = MagicMock()
            mock_select = MagicMock()
            mock_select.eq.return_value = mock_select
            mock_select.maybe_single.return_value = mock_select
            mock_select.execute.return_value = mock_existing
            mock_db.table.return_value.select.return_value = mock_select
            mock_db.table.return_value.insert.return_value.execute.return_value = None
            mock_tenant.return_value.__enter__.return_value = mock_db

            payload = {
                "name": "Test Crew",
                "flow_type": "test_crew_001",
                "definition": {"steps": [], "agents": []},
                "status": "draft",
            }
            response = client.post("/workflows", json=payload, headers={"X-Org-ID": "org-001"})

        assert response.status_code == 201
        data = response.json()
        assert "id" in data
        assert data["flow_type"] == "test_crew_001"
        assert data["status"] == "draft"

    def test_create_workflow_duplicate(self, client):
        """TP-4: POST /workflows con flow_type duplicado → 409."""
        mock_existing = MagicMock()
        mock_existing.data = {"id": "existing"}

        with patch("src.api.routes.workflows.get_tenant_client") as mock_tenant:
            mock_db = MagicMock()
            mock_select = MagicMock()
            mock_select.eq.return_value = mock_select
            mock_select.maybe_single.return_value = mock_select
            mock_select.execute.return_value = mock_existing
            mock_db.table.return_value.select.return_value = mock_select
            mock_tenant.return_value.__enter__.return_value = mock_db

            payload = {
                "name": "Duplicate Crew",
                "flow_type": "test_crew_001",
                "definition": {"steps": []},
                "status": "draft",
            }
            response = client.post("/workflows", json=payload, headers={"X-Org-ID": "org-001"})

        assert response.status_code == 409


class TestCrewValidate:
    def test_validate_agent_no_tasks(self, monkeypatch, tmp_path):
        """TP-7: fap crew validate detecta agente sin tarea."""
        from src.cli.commands.crew import _validate_crew_graph

        graph = {
            "nodes": [
                {
                    "id": "a1",
                    "type": "agentNode",
                    "data": {"role": "researcher", "goal": "Research", "tools": []},
                    "position": {"x": 100, "y": 100},
                },
            ],
            "edges": [],
        }

        errors, warnings = _validate_crew_graph(graph)
        assert len(errors) == 0
        assert any("no assigned tasks" in w.lower() for w in warnings)

    def test_validate_duplicate_role(self, monkeypatch, tmp_path):
        """TP-8: fap crew validate detecta rol duplicado."""
        from src.cli.commands.crew import _validate_crew_graph

        graph = {
            "nodes": [
                {
                    "id": "a1",
                    "type": "agentNode",
                    "data": {"role": "researcher", "goal": "Research", "tools": []},
                    "position": {"x": 100, "y": 100},
                },
                {
                    "id": "a2",
                    "type": "agentNode",
                    "data": {"role": "researcher", "goal": "Research more", "tools": []},
                    "position": {"x": 100, "y": 220},
                },
            ],
            "edges": [],
        }

        errors, warnings = _validate_crew_graph(graph)
        assert any("duplicate role" in e.lower() for e in errors)

    def test_validate_valid_graph(self, monkeypatch, tmp_path):
        from src.cli.commands.crew import _validate_crew_graph

        graph = {
            "nodes": [
                {
                    "id": "a1",
                    "type": "agentNode",
                    "data": {"role": "researcher", "goal": "Research", "tools": []},
                    "position": {"x": 100, "y": 100},
                },
                {
                    "id": "t1",
                    "type": "taskNode",
                    "data": {"description": "Do research", "expectedOutput": "Report"},
                    "position": {"x": 400, "y": 100},
                },
            ],
            "edges": [
                {"id": "e1", "source": "a1", "target": "t1", "sourceHandle": "bottom", "targetHandle": "left"},
            ],
        }

        errors, warnings = _validate_crew_graph(graph)
        assert len(errors) == 0
