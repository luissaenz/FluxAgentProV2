"""TestBaseFlow — Unit tests for the BaseFlow lifecycle.

Covers:
  - validate_input returns True / False correctly
  - execute() runs full lifecycle → COMPLETED
  - execute() marks state as FAILED on _run_crew error
  - BaseFlowState transitions
"""

from __future__ import annotations

import pytest
from typing import Dict, Any
from uuid import uuid4

from src.flows.base_flow import BaseFlow
from src.flows.state import BaseFlowState, FlowStatus


# ── concrete test stub ──────────────────────────────────────────

class _SuccessFlow(BaseFlow):
    """Stub that always succeeds."""

    def validate_input(self, input_data: Dict[str, Any]) -> bool:
        return "text" in input_data

    async def _run_crew(self) -> Dict[str, Any]:
        return {"result": "success"}


class _FailingFlow(BaseFlow):
    """Stub whose crew always explodes."""

    def validate_input(self, input_data: Dict[str, Any]) -> bool:
        return True

    async def _run_crew(self) -> Dict[str, Any]:
        raise RuntimeError("Crew crashed on purpose")


# ── state transitions ──────────────────────────────────────────

class TestBaseFlowState:
    def test_start(self, sample_org_id):
        state = BaseFlowState(
            task_id=str(uuid4()),
            org_id=sample_org_id,
            flow_type="test",
        )
        state.start()
        assert state.status == FlowStatus.RUNNING.value
        assert state.started_at is not None

    def test_complete(self, sample_org_id):
        state = BaseFlowState(
            task_id=str(uuid4()),
            org_id=sample_org_id,
            flow_type="test",
        )
        state.start()
        state.complete({"answer": 42})
        assert state.status == FlowStatus.COMPLETED.value
        assert state.output_data == {"answer": 42}
        assert state.completed_at is not None

    def test_fail(self, sample_org_id):
        state = BaseFlowState(
            task_id=str(uuid4()),
            org_id=sample_org_id,
            flow_type="test",
        )
        state.start()
        state.fail("something broke")
        assert state.status == FlowStatus.FAILED.value
        assert state.error == "something broke"

    def test_uuid_validation_rejects_garbage(self):
        with pytest.raises(ValueError, match="Invalid UUID"):
            BaseFlowState(
                task_id="not-a-uuid",
                org_id=str(uuid4()),
                flow_type="test",
            )

    def test_to_snapshot_roundtrip(self, sample_org_id):
        state = BaseFlowState(
            task_id=str(uuid4()),
            org_id=sample_org_id,
            flow_type="test",
            input_data={"text": "hi"},
        )
        snapshot = state.to_snapshot()
        restored = BaseFlowState.from_snapshot(snapshot)
        assert restored.task_id == state.task_id
        assert restored.flow_type == "test"


# ── validate_input ──────────────────────────────────────────────

class TestValidateInput:
    def test_valid(self, sample_org_id):
        flow = _SuccessFlow(org_id=sample_org_id)
        assert flow.validate_input({"text": "hello"}) is True

    def test_invalid(self, sample_org_id):
        flow = _SuccessFlow(org_id=sample_org_id)
        assert flow.validate_input({}) is False


# ── execute lifecycle ───────────────────────────────────────────

class TestExecuteLifecycle:
    @pytest.mark.asyncio
    async def test_success(self, mock_tenant_client, mock_event_store, sample_org_id):
        flow = _SuccessFlow(org_id=sample_org_id)
        state = await flow.execute({"text": "hello"})

        assert state.status == FlowStatus.COMPLETED.value
        assert state.output_data == {"result": "success"}
        assert state.error is None

    @pytest.mark.asyncio
    async def test_failure_marks_state(self, mock_tenant_client, mock_event_store, sample_org_id):
        flow = _FailingFlow(org_id=sample_org_id)

        with pytest.raises(RuntimeError, match="Crew crashed"):
            await flow.execute({"text": "hello"})

        assert flow.state is not None
        assert flow.state.status == FlowStatus.FAILED.value
        assert "Crew crashed" in flow.state.error

    @pytest.mark.asyncio
    async def test_invalid_input_raises(self, sample_org_id):
        flow = _SuccessFlow(org_id=sample_org_id)

        with pytest.raises(ValueError, match="Input validation failed"):
            await flow.execute({})
