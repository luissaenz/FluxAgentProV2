"""tests/unit/test_templates.py — Unit tests for agent template endpoints."""

from __future__ import annotations

from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from src.api.main import app
from tests.conftest import mock_db, mock_db_filter, mock_db_single

TEMPLATE_DATA = [
    {
        "id": "11111111-1111-1111-1111-111111111111",
        "name": "Research Agent",
        "description": "Conducts thorough research on topics",
        "category": "Research",
        "suggested_tools": ["fetch_url", "search"],
        "max_iter": 5,
        "is_system": True,
        "created_at": "2026-05-13T00:00:00Z",
    },
    {
        "id": "22222222-2222-2222-2222-222222222222",
        "name": "Code Reviewer",
        "description": "Reviews code for quality and security",
        "category": "Development",
        "suggested_tools": ["code_analyzer"],
        "max_iter": 3,
        "is_system": True,
        "created_at": "2026-05-13T00:00:00Z",
    },
]

TEMPLATE_DETAIL = {
    "id": "11111111-1111-1111-1111-111111111111",
    "name": "Research Agent",
    "description": "Conducts thorough research on topics",
    "category": "Research",
    "soul_json": {
        "role": "Research Specialist",
        "goal": "Research topics thoroughly and synthesize findings",
        "backstory": "Expert researcher with years of experience",
    },
    "suggested_tools": ["fetch_url", "search"],
    "max_iter": 5,
    "is_system": True,
    "created_at": "2026-05-13T00:00:00Z",
    "updated_at": "2026-05-13T00:00:00Z",
}


@pytest.fixture
def client():
    return TestClient(app)


class TestListTemplates:
    def test_list_empty(self, client):
        mock = mock_db([])
        with patch("src.api.routes.templates.get_service_client", return_value=mock):
            resp = client.get("/api/templates")
        assert resp.status_code == 200
        body = resp.json()
        assert body["templates"] == []
        assert body["count"] == 0

    def test_list_all(self, client):
        mock = mock_db(TEMPLATE_DATA)
        with patch("src.api.routes.templates.get_service_client", return_value=mock):
            resp = client.get("/api/templates")
        assert resp.status_code == 200
        body = resp.json()
        assert len(body["templates"]) == 2
        assert body["count"] == 2
        assert body["templates"][0]["name"] == "Research Agent"
        assert body["templates"][1]["name"] == "Code Reviewer"

    def test_list_filter_by_category(self, client):
        filtered = [t for t in TEMPLATE_DATA if t["category"] == "Research"]
        mock = mock_db_filter(filtered)
        with patch("src.api.routes.templates.get_service_client", return_value=mock):
            resp = client.get("/api/templates?category=Research")
        assert resp.status_code == 200
        body = resp.json()
        assert len(body["templates"]) == 1
        assert body["count"] == 1
        assert body["templates"][0]["name"] == "Research Agent"
        assert body["templates"][0]["category"] == "Research"

    def test_list_no_auth_required(self, client):
        mock = mock_db([])
        with patch("src.api.routes.templates.get_service_client", return_value=mock):
            resp = client.get("/api/templates", headers={})
        assert resp.status_code == 200


class TestGetTemplate:
    def test_get_by_id_found(self, client):
        mock = mock_db_single(TEMPLATE_DETAIL)
        with patch("src.api.routes.templates.get_service_client", return_value=mock):
            resp = client.get(f"/api/templates/{TEMPLATE_DETAIL['id']}")
        assert resp.status_code == 200
        body = resp.json()
        assert body["name"] == "Research Agent"
        assert body["category"] == "Research"
        assert "soul_json" in body
        assert body["soul_json"]["role"] == "Research Specialist"
        assert body["soul_json"]["goal"] is not None
        assert body["soul_json"]["backstory"] is not None

    def test_get_by_id_not_found(self, client):
        mock = mock_db_single(None)
        with patch("src.api.routes.templates.get_service_client", return_value=mock):
            resp = client.get("/api/templates/00000000-0000-0000-0000-000000000000")
        assert resp.status_code == 404
        body = resp.json()
        assert body["detail"] == "Template not found"

    def test_get_by_id_includes_soul_json(self, client):
        mock = mock_db_single(TEMPLATE_DETAIL)
        with patch("src.api.routes.templates.get_service_client", return_value=mock):
            resp = client.get(f"/api/templates/{TEMPLATE_DETAIL['id']}")
        assert resp.status_code == 200
        body = resp.json()
        sj = body["soul_json"]
        assert "role" in sj
        assert "goal" in sj
        assert "backstory" in sj
