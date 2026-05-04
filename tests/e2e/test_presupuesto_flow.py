"""tests/e2e/test_presupuesto_flow.py — Paso 5: PresupuestoFlow registrado.

Plan:
- Flow registrado en flow_registry
- POST /webhooks/trigger con flow_type="presupuesto"
- GET /api/tasks/{task_id} → status COMPLETED + output
- Multi-turn: ejecutar flow, verificar output en DB
"""

from __future__ import annotations

import json
import re
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import crewai
import pytest
from fastapi.testclient import TestClient

# Import to trigger @register_flow
import src.flows.presupuesto_flow  # noqa: F401
from src.api.main import app
from src.api.middleware import require_org_id, verify_org_membership
from src.config import get_settings
from src.flows.base_flow import BaseFlow
from src.flows.presupuesto_flow import PresupuestoFlow
from src.flows.registry import flow_registry
from src.flows.state import FlowStatus

_REAL_CREW = crewai.Crew
_REAL_TASK = crewai.Task
_REAL_AGENT = crewai.Agent


def _has_groq_key() -> bool:
    try:
        s = get_settings()
        return bool(s.groq_api_key)
    except Exception:
        return False


_RUN_REAL_LLM = _has_groq_key()


def _extract_json(text: str) -> str:
    match = re.search(r"```(?:json)?\s*\n?(.*?)\n?```", text, re.DOTALL)
    return match.group(1).strip() if match else text.strip()


AGENT_CONFIG = {
    "role": "presupuestador",
    "soul_json": {
        "role": "Cotizador de Eventos",
        "goal": "Generar presupuestos usando excel_reader con datos reales",
        "backstory": "Sos un experto en cotización que SIEMPRE usa herramientas.",
    },
    "allowed_tools": ["excel_reader"],
    "model": "groq/llama-3.3-70b-versatile",
    "max_iter": 5,
    "is_active": True,
}


VALID_INPUT = {
    "tipo_evento": "boda",
    "pax": 150,
    "duracion_horas": 6,
    "provincia": "Tucumán",
    "fecha": "2026-03-15",
    "menu": "premium",
}


# ── API test client fixture ───────────────────────────────────────


@pytest.fixture
def api_client():
    """TestClient with verify_org_membership overridden."""
    async def mock_auth():
        return {"user_id": "test-user", "org_id": "sample-org", "role": "admin"}
    app.dependency_overrides[verify_org_membership] = mock_auth
    with TestClient(app, raise_server_exceptions=False) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def api_client_no_auth():
    """TestClient without auth override (require_org_id still works)."""
    with TestClient(app, raise_server_exceptions=False) as c:
        yield c


# ── Tests ─────────────────────────────────────────────────────────


class TestPresupuestoFlowRegistry:
    """Flow registrado en flow_registry."""

    def test_flow_registered(self):
        assert flow_registry.has("presupuesto"), "Flow 'presupuesto' not registered!"
        FlowClass = flow_registry.get("presupuesto")
        assert FlowClass.__name__ == "PresupuestoFlow"

    def test_validate_input_requires_all_fields(self):
        flow = PresupuestoFlow(org_id=str(uuid4()), user_id=str(uuid4()))
        assert flow.validate_input(VALID_INPUT)
        assert not flow.validate_input({"tipo_evento": "boda"})
        assert not flow.validate_input({"tipo_evento": "boda", "pax": 100, "fecha": "2026-01-01"})
        assert not flow.validate_input({})

    def test_validate_input_rejects_missing_provincia(self):
        flow = PresupuestoFlow(org_id=str(uuid4()), user_id=str(uuid4()))
        assert not flow.validate_input({"tipo_evento": "boda", "pax": 100, "fecha": "2026-01-01"})

    def test_validate_input_accepts_with_provincia(self):
        flow = PresupuestoFlow(org_id=str(uuid4()), user_id=str(uuid4()))
        assert flow.validate_input({**VALID_INPUT, "pax": 100})


class TestPresupuestoWebhookTrigger:
    """POST /webhooks/trigger con flow_type='presupuesto'."""

    def test_webhook_returns_202_with_task_id(
        self, api_client_no_auth, mock_tenant_client, mock_event_store
    ):
        org_id = str(uuid4())
        resp = api_client_no_auth.post(
            "/webhooks/trigger",
            json={"flow_type": "presupuesto", "input_data": VALID_INPUT},
            headers={"X-Org-ID": org_id},
        )
        assert resp.status_code == 202, f"Got {resp.status_code}: {resp.text}"
        body = resp.json()
        assert "task_id" in body
        assert body["status"] == "accepted"
        assert "correlation_id" in body

    def test_webhook_rejects_missing_input_fields(
        self, api_client_no_auth, mock_tenant_client
    ):
        resp = api_client_no_auth.post(
            "/webhooks/trigger",
            json={
                "flow_type": "presupuesto",
                "input_data": {"tipo_evento": "boda"},
            },
            headers={"X-Org-ID": str(uuid4())},
        )
        assert resp.status_code == 400
        assert "validation" in resp.json()["detail"].lower()

    def test_webhook_rejects_unknown_flow_type(
        self, api_client_no_auth
    ):
        resp = api_client_no_auth.post(
            "/webhooks/trigger",
            json={"flow_type": "nonexistent", "input_data": {}},
            headers={"X-Org-ID": str(uuid4())},
        )
        assert resp.status_code == 400
        assert "not found" in resp.json()["detail"].lower()


class TestPresupuestoTasksEndpoint:
    """GET /api/tasks/{task_id} → status COMPLETED + output."""

    def test_get_task_returns_completed_with_output(
        self, api_client, mock_service_client, mock_tenant_client
    ):
        task_id = str(uuid4())
        result_data = {"result": '{"costo_total": 1000}', "flow_type": "presupuesto"}
        task_row = {
            "id": task_id,
            "org_id": "sample-org",
            "flow_type": "presupuesto",
            "status": "completed",
            "result": result_data,
            "error": None,
            "tokens_used": 500,
            "approval_required": False,
            "approval_status": "none",
            "approval_payload": None,
            "created_at": "2026-03-15T10:00:00",
            "updated_at": "2026-03-15T10:05:00",
            "max_retries": 3,
            "payload": VALID_INPUT,
            "correlation_id": str(uuid4()),
        }

        tasks_chain = MagicMock()
        tasks_chain.execute.return_value = MagicMock(data=[task_row])
        tasks_chain.select.return_value = tasks_chain
        tasks_chain.eq.return_value = tasks_chain
        tasks_chain.maybe_single.return_value = tasks_chain

        orig_side = mock_service_client.table.side_effect
        mock_service_client.table.side_effect = lambda name: tasks_chain if name == "tasks" else (
            orig_side(name) if orig_side else MagicMock()
        )

        resp = api_client.get(f"/tasks/{task_id}", headers={"X-Org-ID": "sample-org"})
        assert resp.status_code == 200, f"Got {resp.status_code}: {resp.text}"
        body = resp.json()
        assert body["status"] == "completed"
        assert body["result"]["result"] == result_data["result"]
        assert body["flow_type"] == "presupuesto"
        assert body["tokens_used"] == 500
        assert body["task_id"] == task_id

    def test_get_task_returns_404_for_unknown(
        self, api_client, mock_tenant_client
    ):
        resp = api_client.get(f"/tasks/{uuid4()}", headers={"X-Org-ID": "sample-org"})
        assert resp.status_code == 404


class TestPresupuestoPersistence:
    """Multi-turn: ejecutar flow, verificar output en DB."""

    @pytest.mark.asyncio
    async def test_execute_persists_state_to_db(
        self, mock_service_client, mock_tenant_client, mock_event_store
    ):
        org_id = str(uuid4())
        agent_config = {**AGENT_CONFIG, "org_id": org_id,
                        "soul_json": {**AGENT_CONFIG["soul_json"]}}

        mock_resp = MagicMock()
        mock_resp.data = agent_config
        mock_service_client.table("agent_catalog").execute.return_value = mock_resp

        flow = PresupuestoFlow(org_id=org_id, user_id=str(uuid4()))
        # Mock BaseCrew to skip real LLM
        fake_result = MagicMock()
        fake_result.raw = '{"costo_total": 500000}'
        fake_result.__str__.return_value = fake_result.raw

        with patch("src.flows.presupuesto_flow.BaseCrew") as MockCrew:
            mock_crew = MagicMock()
            mock_crew.run_async = AsyncMock(return_value=fake_result)
            MockCrew.return_value = mock_crew

            state = await flow.execute(VALID_INPUT)

        assert state.status == FlowStatus.COMPLETED.value
        assert state.task_id is not None

        # Verificar output en DB (mock calls)
        mock_service_client.table("tasks").insert.assert_called()
        mock_service_client.table("tasks").update.assert_called()
        mock_service_client.table("snapshots").upsert.assert_called()

        output = state.output_data
        assert "result" in output
        assert "costo_total" in output["result"]

    @pytest.mark.skipif(not _RUN_REAL_LLM, reason="Requiere GROQ_API_KEY")
    @pytest.mark.real_llm
    @pytest.mark.asyncio
    async def test_execute_with_real_llm(
        self, mock_service_client, mock_tenant_client, mock_event_store
    ):
        org_id = str(uuid4())
        agent_config = {**AGENT_CONFIG, "org_id": org_id,
                        "soul_json": {**AGENT_CONFIG["soul_json"]}}

        mock_resp = MagicMock()
        mock_resp.data = agent_config
        mock_service_client.table("agent_catalog").execute.return_value = mock_resp

        with (
            patch("crewai.Crew", _REAL_CREW),
            patch("crewai.Task", _REAL_TASK),
            patch("crewai.Agent", _REAL_AGENT),
            patch("src.crews.factory.get_settings", return_value=get_settings()),
        ):
            flow = PresupuestoFlow(org_id=org_id, user_id=str(uuid4()))
            state = await flow.execute(VALID_INPUT)

        assert state.status == FlowStatus.COMPLETED.value, f"Got {state.status}"
        assert state.output_data is not None
        assert "result" in state.output_data
        assert "Mocked Crew" not in state.output_data["result"]

        # DB persistence
        mock_service_client.table("tasks").insert.assert_called()
        mock_service_client.table("tasks").update.assert_called()
        mock_service_client.table("snapshots").upsert.assert_called()

        raw = state.output_data["result"]
        try:
            data = json.loads(_extract_json(raw))
        except json.JSONDecodeError:
            data = {"raw": raw[:200]}

        assert "costo" in raw.lower() or "precio" in raw.lower() or "total" in str(data)
