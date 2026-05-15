"""Tests: HITL — Flow pauses at request_approval() and resumes."""

from __future__ import annotations

import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from uuid import uuid4

from src.flows.state import BaseFlowState, FlowStatus
from src.flows.base_flow import BaseFlow


class DummyFlowForHITL(BaseFlow):
    """Flow de prueba que pausa en request_approval()."""

    def validate_input(self, input_data):
        return True

    async def _run_crew(self):
        if self.state.input_data.get("require_approval"):
            await self.request_approval(
                description="Aprobar operación",
                payload={"monto": self.state.input_data.get("monto", 0)}
            )
        return {"result": "done"}


class TestRequestApproval:
    """request_approval() pausa el Flow correctamente."""

    @pytest.mark.asyncio
    async def test_creates_pending_approval_row(self, mock_service_client, mock_tenant_client, sample_org_id):
        """request_approval() crea fila en pending_approvals con status=pending."""
        task_id = str(uuid4())
        flow = DummyFlowForHITL(org_id=sample_org_id)
        flow.state = BaseFlowState(
            task_id=task_id,
            org_id=sample_org_id,
            flow_type="DummyFlowForHITL",
            input_data={"require_approval": True, "monto": 100_000},
        )

        # Mock RPC next_event_sequence
        mock_service_client.rpc.return_value.execute.return_value = MagicMock(data=1)

        await flow.request_approval(
            description="Aprobar operación",
            payload={"monto": 100_000}
        )

        # pending_approvals.insert fue llamado
        assert mock_tenant_client.table("pending_approvals").insert.called

    @pytest.mark.asyncio
    async def test_updates_state_to_awaiting(self, mock_service_client, mock_tenant_client, sample_org_id):
        """Tras request_approval(), state.status = AWAITING_APPROVAL."""
        task_id = str(uuid4())
        flow = DummyFlowForHITL(org_id=sample_org_id)
        flow.state = BaseFlowState(
            task_id=task_id,
            org_id=sample_org_id,
            flow_type="DummyFlowForHITL",
        )

        mock_service_client.rpc.return_value.execute.return_value = MagicMock(data=1)

        assert flow.state.status == FlowStatus.PENDING

        await flow.request_approval(description="Test", payload={})

        assert flow.state.status == FlowStatus.AWAITING_APPROVAL

    @pytest.mark.asyncio
    async def test_stores_approval_payload(self, mock_service_client, mock_tenant_client, sample_org_id):
        """approval_payload se almacena en el estado."""
        task_id = str(uuid4())
        flow = DummyFlowForHITL(org_id=sample_org_id)
        flow.state = BaseFlowState(
            task_id=task_id,
            org_id=sample_org_id,
            flow_type="DummyFlowForHITL",
        )

        mock_service_client.rpc.return_value.execute.return_value = MagicMock(data=1)

        await flow.request_approval(
            description="Aprobar operación",
            payload={"monto": 100_000, "description": "Compra mayor"}
        )

        assert flow.state.approval_payload == {"monto": 100_000, "description": "Compra mayor"}


class TestResume:
    """resume() restaura estado y continúa según decisión."""

    @pytest.mark.asyncio
    async def test_resume_approved_calls_on_approved(self, mock_service_client, sample_org_id):
        """resume(decision='approved') llama a _on_approved()."""
        task_id = str(uuid4())
        mock_service_client.table("snapshots").select.return_value.eq.return_value.eq.return_value.maybe_single.return_value.execute.return_value = MagicMock(data={
            "task_id": task_id,
            "org_id": sample_org_id,
            "flow_type": "DummyFlowForHITL",
            "status": "awaiting_approval",
            "state_json": {
                "task_id": task_id,
                "org_id": sample_org_id,
                "flow_type": "DummyFlowForHITL",
                "status": "awaiting_approval",
            },
        })
        mock_service_client.rpc.return_value.execute.return_value = MagicMock(data=2)

        flow = DummyFlowForHITL(org_id=sample_org_id)
        flow.event_store = MagicMock()

        with patch.object(flow, '_on_approved', new_callable=AsyncMock) as mock_approved:
            await flow.resume(task_id="task_test", decision="approved", decided_by="supervisor1")
            mock_approved.assert_called_once()

    @pytest.mark.asyncio
    async def test_resume_rejected_calls_on_rejected(self, mock_service_client, sample_org_id):
        """resume(decision='rejected') llama a _on_rejected()."""
        task_id = str(uuid4())
        mock_service_client.table("snapshots").select.return_value.eq.return_value.eq.return_value.maybe_single.return_value.execute.return_value = MagicMock(data={
            "task_id": task_id,
            "org_id": sample_org_id,
            "flow_type": "DummyFlowForHITL",
            "status": "awaiting_approval",
            "state_json": {
                "task_id": task_id,
                "org_id": sample_org_id,
                "flow_type": "DummyFlowForHITL",
                "status": "awaiting_approval",
            },
        })
        mock_service_client.rpc.return_value.execute.return_value = MagicMock(data=2)

        flow = DummyFlowForHITL(org_id=sample_org_id)
        flow.event_store = MagicMock()

        with patch.object(flow, '_on_rejected', new_callable=AsyncMock) as mock_rejected:
            await flow.resume(task_id="task_test", decision="rejected", decided_by="supervisor1")
            mock_rejected.assert_called_once_with("supervisor1")

    @pytest.mark.asyncio
    async def test_resume_stores_decision_in_state(self, mock_service_client, sample_org_id):
        """approval_decision y approval_decided_by se guardan en el estado."""
        task_id = str(uuid4())
        mock_service_client.table("snapshots").select.return_value.eq.return_value.eq.return_value.maybe_single.return_value.execute.return_value = MagicMock(data={
            "task_id": task_id,
            "org_id": sample_org_id,
            "flow_type": "DummyFlowForHITL",
            "status": "awaiting_approval",
            "state_json": {
                "task_id": task_id,
                "org_id": sample_org_id,
                "flow_type": "DummyFlowForHITL",
                "status": "awaiting_approval",
            },
        })
        mock_service_client.rpc.return_value.execute.return_value = MagicMock(data=2)

        flow = DummyFlowForHITL(org_id=sample_org_id)
        flow.event_store = MagicMock()

        with patch.object(flow, '_on_approved', new_callable=AsyncMock):
            await flow.resume(task_id="task_test", decision="approved", decided_by="supervisor1")

        assert flow.state.approval_decision == "approved"
        assert flow.state.approval_decided_by == "supervisor1"

    @pytest.mark.asyncio
    async def test_resume_raises_when_no_snapshot(self, mock_service_client, sample_org_id):
        """Si no hay snapshot → raise ValueError."""
        mock_service_client.table("snapshots").select.return_value.eq.return_value.eq.return_value.maybe_single.return_value.execute.return_value = MagicMock(data=None)

        flow = DummyFlowForHITL(org_id=sample_org_id)

        with pytest.raises(ValueError) as exc_info:
            await flow.resume(task_id="task_test", decision="approved", decided_by="supervisor1")

        assert "No snapshot found" in str(exc_info.value)


class TestOnApproved:
    """_on_approved() hook por defecto."""

    @pytest.mark.asyncio
    async def test_sets_state_to_running(self, sample_org_id):
        """Por defecto, _on_approved() marca como RUNNING."""
        task_id = str(uuid4())
        flow = DummyFlowForHITL(org_id=sample_org_id)
        flow.state = BaseFlowState(
            task_id=task_id,
            org_id=sample_org_id,
            flow_type="DummyFlowForHITL",
            status=FlowStatus.AWAITING_APPROVAL,
            approval_payload={"monto": 100},
        )
        flow.event_store = MagicMock()

        with patch.object(flow, 'persist_state', new_callable=AsyncMock):
            with patch.object(flow, 'emit_event', new_callable=AsyncMock):
                await flow._on_approved()

        assert flow.state.status == FlowStatus.RUNNING
        assert flow.state.approval_payload is None  # Limpiado tras uso


class TestOnRejected:
    """_on_rejected() hook por defecto."""

    @pytest.mark.asyncio
    async def test_fails_the_flow(self, sample_org_id):
        """Por defecto, _on_rejected() marca como FAILED."""
        task_id = str(uuid4())
        flow = DummyFlowForHITL(org_id=sample_org_id)
        flow.state = BaseFlowState(
            task_id=task_id,
            org_id=sample_org_id,
            flow_type="DummyFlowForHITL",
            status=FlowStatus.AWAITING_APPROVAL,
        )
        flow.event_store = MagicMock()

        with patch.object(flow, 'persist_state', new_callable=AsyncMock):
            with patch.object(flow, 'emit_event', new_callable=AsyncMock):
                await flow._on_rejected("supervisor1")

        assert flow.state.status == FlowStatus.FAILED
        assert "Rejected by supervisor" in flow.state.error
