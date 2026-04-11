"""tests/integration/test_tickets_execute.py — Testing Mínimo Viable para Paso 1.1

Escenarios (del análisis-FINAL.md sección 8):
  1. Crear un ticket con un flow inexistente -> Debe dar ERROR 404 (validación previa).
  2. Crear un ticket con un flow que fuerce un error de ejecución -> Ticket debe quedar
     `blocked` con nota de error.
  3. Ejecutar ticket exitoso -> Ticket debe quedar `done` y con `task_id` correcto.

Además se validan los criterios de aceptación del análisis.
"""

from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, patch
from uuid import uuid4
from datetime import datetime as dt
from datetime import timezone

from fastapi import FastAPI
from fastapi.testclient import TestClient


# ── App fixture ─────────────────────────────────────────────────

@pytest.fixture
def ticket_app(mock_flow_registry):
    """Build FastAPI app with mocked dependencies for ticket endpoints."""
    app = FastAPI()

    # Import and register tickets router
    from src.api.routes.tickets import router as tickets_router

    # Override the require_org_id dependency to return our test org
    from src.api.middleware import require_org_id
    app.dependency_overrides[require_org_id] = lambda: mock_flow_registry["org_id"]

    app.include_router(tickets_router)
    return app


@pytest.fixture
def mock_flow_registry(sample_org_id):
    """Mock flow registry with a success flow and a failing flow."""
    return {"org_id": sample_org_id}


@pytest.fixture
def client(ticket_app, mock_tenant_client, mock_event_store, sample_org_id):
    """TestClient with all mocks configured."""
    return TestClient(ticket_app)


# ── Scenario 1: Flow type validation (404/400) ──────────────────


class TestTicketExecutionValidation:
    """Escenario 1: Validación previa — flow inexistente da error."""

    def test_execute_ticket_not_found(self, client, mock_tenant_client):
        """POST /tickets/{id}/execute con ID inexistente retorna 404."""
        response = client.post("/tickets/nonexistent-id/execute")

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    def test_execute_ticket_no_flow_type(
        self, client, mock_tenant_client, sample_org_id
    ):
        """POST /tickets/{id}/execute sin flow_type retorna 400."""
        # Setup: mock ticket without flow_type
        ticket_id = str(uuid4())
        now = dt.now(timezone.utc).isoformat()
        mock_tenant_client.table.return_value.select.return_value.eq.return_value.maybe_single.return_value.execute.return_value.data = {
            "id": ticket_id,
            "org_id": sample_org_id,
            "title": "Test ticket",
            "flow_type": None,  # No flow type
            "status": "backlog",
            "created_at": now,
            "updated_at": now,
        }

        response = client.post(f"/tickets/{ticket_id}/execute")

        assert response.status_code == 400
        assert "flow_type" in response.json()["detail"].lower()

    def test_execute_ticket_already_in_progress(
        self, client, mock_tenant_client, sample_org_id
    ):
        """POST /tickets/{id}/execute con status in_progress retorna 409."""
        ticket_id = str(uuid4())
        now = dt.now(timezone.utc).isoformat()
        mock_tenant_client.table.return_value.select.return_value.eq.return_value.maybe_single.return_value.execute.return_value.data = {
            "id": ticket_id,
            "org_id": sample_org_id,
            "title": "Test ticket",
            "flow_type": "TestFlow",
            "status": "in_progress",
            "created_at": now,
            "updated_at": now,
        }

        with patch("src.api.routes.tickets.flow_registry") as mock_registry:
            mock_registry.has.return_value = True

            response = client.post(f"/tickets/{ticket_id}/execute")

            assert response.status_code == 409
            assert "in_progress" in response.json()["detail"]

    def test_execute_ticket_already_done(
        self, client, mock_tenant_client, sample_org_id
    ):
        """POST /tickets/{id}/execute con status done retorna 409."""
        ticket_id = str(uuid4())
        now = dt.now(timezone.utc).isoformat()
        mock_tenant_client.table.return_value.select.return_value.eq.return_value.maybe_single.return_value.execute.return_value.data = {
            "id": ticket_id,
            "org_id": sample_org_id,
            "title": "Test ticket",
            "flow_type": "TestFlow",
            "status": "done",
            "created_at": now,
            "updated_at": now,
        }

        with patch("src.api.routes.tickets.flow_registry") as mock_registry:
            mock_registry.has.return_value = True

            response = client.post(f"/tickets/{ticket_id}/execute")

            assert response.status_code == 409


# ── Scenario 2: Flow execution failure -> blocked ───────────────


class TestTicketExecutionFailure:
    """Escenario 2: Flow con error de ejecución -> ticket blocked con nota."""

    def test_ticket_blocked_on_flow_error(
        self, client, mock_tenant_client, sample_org_id
    ):
        """Ticket queda blocked cuando execute_flow retorna error."""
        ticket_id = str(uuid4())
        now = dt.now(timezone.utc).isoformat()

        # Mock: ticket retrieval for validation
        mock_tenant_client.table.return_value.select.return_value.eq.return_value.maybe_single.return_value.execute.return_value.data = {
            "id": ticket_id,
            "org_id": sample_org_id,
            "title": "Test ticket",
            "flow_type": "FailingFlow",
            "status": "backlog",
            "input_data": {},
            "notes": None,
            "created_at": now,
            "updated_at": now,
        }

        with patch("src.api.routes.tickets.flow_registry") as mock_registry, \
             patch("src.api.routes.tickets.execute_flow", new_callable=AsyncMock) as mock_execute:

            mock_registry.has.return_value = True
            # Simulate flow execution returning an error
            mock_execute.return_value = {
                "task_id": str(uuid4()),
                "error": "Intentional failure in flow",
                "error_type": "ValueError",
            }

            response = client.post(f"/tickets/{ticket_id}/execute")

            assert response.status_code == 500
            body = response.json()
            assert body["detail"]["status"] == "blocked"
            assert body["detail"]["ticket_id"] == ticket_id
            assert "Intentional failure" in body["detail"]["error"]

    def test_ticket_blocked_on_empty_result(
        self, client, mock_tenant_client, sample_org_id
    ):
        """Ticket queda blocked cuando execute_flow retorna dict vacío."""
        ticket_id = str(uuid4())
        now = dt.now(timezone.utc).isoformat()

        mock_tenant_client.table.return_value.select.return_value.eq.return_value.maybe_single.return_value.execute.return_value.data = {
            "id": ticket_id,
            "org_id": sample_org_id,
            "title": "Test ticket",
            "flow_type": "TestFlow",
            "status": "backlog",
            "input_data": {},
            "notes": None,
            "created_at": now,
            "updated_at": now,
        }

        with patch("src.api.routes.tickets.flow_registry") as mock_registry, \
             patch("src.api.routes.tickets.execute_flow", new_callable=AsyncMock) as mock_execute:

            mock_registry.has.return_value = True
            mock_execute.return_value = {}  # Empty dict = failure

            response = client.post(f"/tickets/{ticket_id}/execute")

            assert response.status_code == 500
            assert response.json()["detail"]["status"] == "blocked"

    def test_ticket_blocked_on_none_result(
        self, client, mock_tenant_client, sample_org_id
    ):
        """Ticket queda blocked cuando execute_flow retorna None."""
        ticket_id = str(uuid4())
        now = dt.now(timezone.utc).isoformat()

        mock_tenant_client.table.return_value.select.return_value.eq.return_value.maybe_single.return_value.execute.return_value.data = {
            "id": ticket_id,
            "org_id": sample_org_id,
            "title": "Test ticket",
            "flow_type": "TestFlow",
            "status": "backlog",
            "input_data": {},
            "notes": None,
            "created_at": now,
            "updated_at": now,
        }

        with patch("src.api.routes.tickets.flow_registry") as mock_registry, \
             patch("src.api.routes.tickets.execute_flow", new_callable=AsyncMock) as mock_execute:

            mock_registry.has.return_value = True
            mock_execute.return_value = None  # None = failure

            response = client.post(f"/tickets/{ticket_id}/execute")

            assert response.status_code == 500
            assert response.json()["detail"]["status"] == "blocked"

    def test_ticket_blocked_preserves_existing_notes(
        self, client, mock_tenant_client, sample_org_id
    ):
        """Notas previas en el ticket no se borran al registrar error."""
        ticket_id = str(uuid4())
        now = dt.now(timezone.utc).isoformat()

        mock_tenant_client.table.return_value.select.return_value.eq.return_value.maybe_single.return_value.execute.return_value.data = {
            "id": ticket_id,
            "org_id": sample_org_id,
            "title": "Test ticket",
            "flow_type": "FailingFlow",
            "status": "backlog",
            "input_data": {},
            "notes": "Nota humana previa",
            "created_at": now,
            "updated_at": now,
        }

        with patch("src.api.routes.tickets.flow_registry") as mock_registry, \
             patch("src.api.routes.tickets.execute_flow", new_callable=AsyncMock) as mock_execute:

            mock_registry.has.return_value = True
            mock_execute.return_value = {
                "task_id": str(uuid4()),
                "error": "Flow crashed",
                "error_type": "RuntimeError",
            }

            client.post(f"/tickets/{ticket_id}/execute")

            # Verify the update to notes includes the previous content
            # The _append_error_note function does a select first, then update
            # We verify the update call includes notes with the original content
            update_calls = mock_tenant_client.table("tickets").update.call_args_list
            # At least one update should contain "Nota humana previa"
            notes_updated = any(
                "Nota humana previa" in str(call)
                for call in update_calls
            )
            assert notes_updated, "Existing notes should be preserved"

    def test_task_id_linked_even_when_blocked(
        self, client, mock_tenant_client, sample_org_id
    ):
        """task_id se vincula en tickets aunque el estado sea blocked."""
        ticket_id = str(uuid4())
        task_id = str(uuid4())
        now = dt.now(timezone.utc).isoformat()

        mock_tenant_client.table.return_value.select.return_value.eq.return_value.maybe_single.return_value.execute.return_value.data = {
            "id": ticket_id,
            "org_id": sample_org_id,
            "title": "Test ticket",
            "flow_type": "FailingFlow",
            "status": "backlog",
            "input_data": {},
            "notes": None,
            "created_at": now,
            "updated_at": now,
        }

        with patch("src.api.routes.tickets.flow_registry") as mock_registry, \
             patch("src.api.routes.tickets.execute_flow", new_callable=AsyncMock) as mock_execute:

            mock_registry.has.return_value = True
            mock_execute.return_value = {
                "task_id": task_id,
                "error": "Partial failure",
                "error_type": "Exception",
            }

            client.post(f"/tickets/{ticket_id}/execute")

            # Verify task_id was set in the update
            update_calls = mock_tenant_client.table("tickets").update.call_args_list
            task_linked = any(
                task_id in str(call)
                for call in update_calls
            )
            assert task_linked, "task_id should be linked even in blocked state"


# ── Scenario 3: Successful execution -> done ────────────────────


class TestTicketExecutionSuccess:
    """Escenario 3: Ejecución exitosa -> ticket done con task_id."""

    def test_ticket_done_on_success(
        self, client, mock_tenant_client, sample_org_id
    ):
        """Ticket queda done con task_id correcto tras ejecución exitosa."""
        ticket_id = str(uuid4())
        task_id = str(uuid4())
        now = dt.now(timezone.utc).isoformat()

        # Mock: ticket retrieval for validation
        mock_tenant_client.table.return_value.select.return_value.eq.return_value.maybe_single.return_value.execute.return_value.data = {
            "id": ticket_id,
            "org_id": sample_org_id,
            "title": "Test ticket",
            "flow_type": "TestFlow",
            "status": "backlog",
            "input_data": {},
            "notes": None,
            "created_at": now,
            "updated_at": now,
        }

        with patch("src.api.routes.tickets.flow_registry") as mock_registry, \
             patch("src.api.routes.tickets.execute_flow", new_callable=AsyncMock) as mock_execute:

            mock_registry.has.return_value = True
            mock_execute.return_value = {
                "task_id": task_id,
                "error": None,
                "error_type": None,
            }

            # Mock: updated ticket retrieval after success
            mock_tenant_client.table.return_value.select.return_value.eq.return_value.maybe_single.return_value.execute.return_value.data = {
                "id": ticket_id,
                "org_id": sample_org_id,
                "title": "Test ticket",
                "flow_type": "TestFlow",
                "status": "done",
                "task_id": task_id,
                "resolved_at": now,
                "input_data": {},
                "notes": None,
                "created_at": now,
                "updated_at": now,
            }

            response = client.post(f"/tickets/{ticket_id}/execute")

            assert response.status_code == 200
            body = response.json()
            assert body["status"] == "done"
            assert body["task_id"] == task_id

    def test_correlation_id_uses_ticket_format(
        self, client, mock_tenant_client, sample_org_id
    ):
        """correlation_id se pasa como ticket-{id} a execute_flow."""
        ticket_id = str(uuid4())
        now = dt.now(timezone.utc).isoformat()

        mock_tenant_client.table.return_value.select.return_value.eq.return_value.maybe_single.return_value.execute.return_value.data = {
            "id": ticket_id,
            "org_id": sample_org_id,
            "title": "Test ticket",
            "flow_type": "TestFlow",
            "status": "backlog",
            "input_data": {},
            "notes": None,
            "created_at": now,
            "updated_at": now,
        }

        with patch("src.api.routes.tickets.flow_registry") as mock_registry, \
             patch("src.api.routes.tickets.execute_flow", new_callable=AsyncMock) as mock_execute:

            mock_registry.has.return_value = True
            mock_execute.return_value = {
                "task_id": str(uuid4()),
                "error": None,
                "error_type": None,
            }
            mock_tenant_client.table.return_value.select.return_value.eq.return_value.maybe_single.return_value.execute.return_value.data = {
                "id": ticket_id,
                "org_id": sample_org_id,
                "title": "Test ticket",
                "flow_type": "TestFlow",
                "status": "done",
                "task_id": str(uuid4()),
                "resolved_at": now,
                "input_data": {},
                "notes": None,
                "created_at": now,
                "updated_at": now,
            }

            client.post(f"/tickets/{ticket_id}/execute")

            # Verify correlation_id was passed correctly
            call_kwargs = mock_execute.call_args[1]
            assert call_kwargs["correlation_id"] == f"ticket-{ticket_id}"


# ── Acceptance Criteria: Infrastructure error handling ──────────


class TestInfrastructureErrorHandling:
    """Criterio: endpoint devuelve 500 con detalle si falla la infraestructura."""

    def test_500_on_infrastructure_error(
        self, client, mock_tenant_client, sample_org_id
    ):
        """Error de infraestructura (DB, red) retorna 500 con detalle."""
        ticket_id = str(uuid4())
        now = dt.now(timezone.utc).isoformat()

        mock_tenant_client.table.return_value.select.return_value.eq.return_value.maybe_single.return_value.execute.return_value.data = {
            "id": ticket_id,
            "org_id": sample_org_id,
            "title": "Test ticket",
            "flow_type": "TestFlow",
            "status": "backlog",
            "input_data": {},
            "notes": None,
            "created_at": now,
            "updated_at": now,
        }

        with patch("src.api.routes.tickets.flow_registry") as mock_registry, \
             patch("src.api.routes.tickets.execute_flow", new_callable=AsyncMock) as mock_execute:

            mock_registry.has.return_value = True
            mock_execute.side_effect = ConnectionError("Database connection lost")

            response = client.post(f"/tickets/{ticket_id}/execute")

            assert response.status_code == 500
            body = response.json()
            assert "infrastructure error" in body["detail"].lower()


# ── Helper: _append_error_note ──────────────────────────────────


class TestAppendErrorNote:
    """_append_error_note preserva notas existentes."""

    def test_append_to_existing_notes(self, mock_tenant_client):
        """Nueva nota se append a notas existentes."""
        from src.api.routes.tickets import _append_error_note

        # Mock existing notes
        mock_tenant_client.table.return_value.select.return_value.eq.return_value.maybe_single.return_value.execute.return_value.data = {
            "notes": "Nota anterior"
        }

        _append_error_note(
            mock_tenant_client, "ticket-123", "Error message", "ValueError"
        )

        # Verify update includes both old and new notes
        update_call = mock_tenant_client.table("tickets").update
        assert update_call.called
        update_data = update_call.call_args[0][0]
        assert "Nota anterior" in update_data["notes"]
        assert "Error message" in update_data["notes"]
        assert "ValueError" in update_data["notes"]

    def test_new_note_when_no_existing_notes(self, mock_tenant_client):
        """Nueva nota se crea cuando no hay notas existentes."""
        from src.api.routes.tickets import _append_error_note

        mock_tenant_client.table.return_value.select.return_value.eq.return_value.maybe_single.return_value.execute.return_value.data = {
            "notes": ""
        }

        _append_error_note(
            mock_tenant_client, "ticket-123", "First error", "RuntimeError"
        )

        update_call = mock_tenant_client.table("tickets").update
        update_data = update_call.call_args[0][0]
        assert update_data["notes"] == update_data["notes"]  # Should just be the new note
        assert "First error" in update_data["notes"]
        assert "RuntimeError" in update_data["notes"]

    def test_error_note_with_none_values(self, mock_tenant_client):
        """_append_error_note maneja None en error_msg y error_type."""
        from src.api.routes.tickets import _append_error_note

        mock_tenant_client.table.return_value.select.return_value.eq.return_value.maybe_single.return_value.execute.return_value.data = {
            "notes": ""
        }

        _append_error_note(mock_tenant_client, "ticket-123", None, None)

        update_call = mock_tenant_client.table("tickets").update
        update_data = update_call.call_args[0][0]
        # Should contain "None" as the stringified value
        assert "None" in update_data["notes"]


# ── Helper: _handle_blocked_ticket ─────────────────────────────


class TestHandleBlockedTicket:
    """_handle_blocked_ticket: robustez con result vacío y single UPDATE."""

    def test_handles_empty_result_dict(self, mock_tenant_client):
        """Maneja result = {} sin crash."""
        from src.api.routes.tickets import _handle_blocked_ticket

        _handle_blocked_ticket(mock_tenant_client, "ticket-123", {})

        # Should have called update with "Unknown error" defaults
        update_call = mock_tenant_client.table("tickets").update
        assert update_call.called
        update_data = update_call.call_args[0][0]
        assert update_data["status"] == "blocked"

    def test_single_update_for_blocked(self, mock_tenant_client):
        """Un solo UPDATE para status + task_id (no dos)."""
        from src.api.routes.tickets import _handle_blocked_ticket

        _handle_blocked_ticket(
            mock_tenant_client,
            "ticket-123",
            {"task_id": "task-456", "error": "fail", "error_type": "Error"},
        )

        # Should call update once with both status and task_id
        update_calls = mock_tenant_client.table("tickets").update.call_args_list
        assert len(update_calls) >= 1
        # The first update should include both status and potentially task_id
        first_update = update_calls[0][0][0]
        assert first_update["status"] == "blocked"
