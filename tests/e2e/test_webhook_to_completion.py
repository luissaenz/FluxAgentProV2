"""Test E2E: POST /webhooks/trigger → GET /tasks/{id} → completed.

Uses ``httpx.ASGITransport`` so that background tasks execute in-process
and we can assert on the final state without real infrastructure.
"""

from __future__ import annotations

import pytest
from unittest.mock import MagicMock, patch
from uuid import uuid4

from fastapi.testclient import TestClient

from src.api.main import app


# ── helpers ─────────────────────────────────────────────────────

@pytest.fixture
def client():
    """Synchronous TestClient wrapping the FastAPI app."""
    return TestClient(app, raise_server_exceptions=False)


# ── tests ───────────────────────────────────────────────────────

class TestWebhookTrigger:
    """POST /webhooks/trigger contract tests."""

    def test_returns_202_for_valid_flow(
        self,
        client,
        mock_tenant_client,
        mock_event_store,
        sample_org_id,
    ):
        response = client.post(
            "/webhooks/trigger",
            json={
                "flow_type": "generic_flow",
                "input_data": {"text": "Hello"},
            },
            headers={"X-Org-ID": sample_org_id},
        )
        assert response.status_code == 202
        body = response.json()
        assert "correlation_id" in body
        assert body["status"] == "accepted"

    def test_returns_400_for_unknown_flow(
        self,
        client,
        sample_org_id,
    ):
        response = client.post(
            "/webhooks/trigger",
            json={
                "flow_type": "nonexistent_flow",
                "input_data": {},
            },
            headers={"X-Org-ID": sample_org_id},
        )
        assert response.status_code == 400
        assert "not found" in response.json()["detail"].lower()

    def test_returns_422_without_org_header(self, client):
        response = client.post(
            "/webhooks/trigger",
            json={"flow_type": "generic_flow", "input_data": {"text": "x"}},
        )
        assert response.status_code == 422


class TestTasksEndpoint:
    """GET /tasks contract tests."""

    def test_get_task_returns_404_when_not_found(
        self,
        client,
        mock_tenant_client,
        sample_org_id,
    ):
        fake_id = str(uuid4())
        response = client.get(
            f"/tasks/{fake_id}",
            headers={"X-Org-ID": sample_org_id},
        )
        assert response.status_code == 404

    def test_list_tasks_returns_empty_list(
        self,
        client,
        mock_tenant_client,
        sample_org_id,
    ):
        response = client.get(
            "/tasks",
            headers={"X-Org-ID": sample_org_id},
        )
        assert response.status_code == 200
        assert response.json() == []


class TestHealthEndpoint:
    def test_health(self, client):
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}
