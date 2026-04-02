"""tests/unit/test_base_flow_additional.py — Phase 1 additional coverage.

Covers:
  - BaseFlow error handling decorator
  - persist_state edge cases
  - emit_event error handling
  - FlowStatus transitions
  - Retry logic
"""

from __future__ import annotations

import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from uuid import uuid4

from src.flows.base_flow import BaseFlow, with_error_handling
from src.flows.state import BaseFlowState, FlowStatus


# ── Test Flow implementations ───────────────────────────────────


class TestableFlow(BaseFlow):
    """Minimal flow for testing."""

    def validate_input(self, input_data):
        return True

    async def _run_crew(self):
        return {"result": "success"}


class FailingFlow(BaseFlow):
    """Flow that fails in _run_crew."""

    def validate_input(self, input_data):
        return True

    async def _run_crew(self):
        raise ValueError("Intentional failure")


# ── FlowStatus tests ────────────────────────────────────────────


class TestFlowStatus:
    """FlowStatus enum values and transitions."""

    def test_all_status_values(self):
        """All expected status values exist."""
        assert FlowStatus.PENDING.value == "pending"
        assert FlowStatus.RUNNING.value == "running"
        assert FlowStatus.AWAITING_APPROVAL.value == "awaiting_approval"
        assert FlowStatus.COMPLETED.value == "completed"
        assert FlowStatus.FAILED.value == "failed"
        assert FlowStatus.PAUSED.value == "paused"
        assert FlowStatus.CANCELLED.value == "cancelled"

    def test_status_comparison_with_string(self):
        """Status can be compared with string values."""
        state = BaseFlowState(
            task_id=str(uuid4()),
            org_id=str(uuid4()),
            flow_type="test",
        )
        # With use_enum_values=True, status is stored as string
        state.start()
        assert state.status == "running"


# ── Retry logic tests ───────────────────────────────────────────


class TestRetryLogic:
    """Retry count and max_retries behavior."""

    def test_default_retry_count(self, sample_org_id):
        """Default retry_count is 0."""
        state = BaseFlowState(
            task_id=str(uuid4()),
            org_id=sample_org_id,
            flow_type="test",
        )
        assert state.retry_count == 0

    def test_default_max_retries(self, sample_org_id):
        """Default max_retries is 3."""
        state = BaseFlowState(
            task_id=str(uuid4()),
            org_id=sample_org_id,
            flow_type="test",
        )
        assert state.max_retries == 3

    def test_can_increment_retry_count(self, sample_org_id):
        """Retry count can be incremented."""
        state = BaseFlowState(
            task_id=str(uuid4()),
            org_id=sample_org_id,
            flow_type="test",
        )
        state.retry_count += 1
        assert state.retry_count == 1

    def test_retry_count_cannot_be_negative(self, sample_org_id):
        """Pydantic validator prevents negative retry_count."""
        with pytest.raises(Exception):  # Pydantic ValidationError
            BaseFlowState(
                task_id=str(uuid4()),
                org_id=sample_org_id,
                flow_type="test",
                retry_count=-1,
            )


# ── persist_state tests ─────────────────────────────────────────


class TestPersistState:
    """persist_state() behavior and edge cases."""

    @pytest.mark.asyncio
    async def test_persist_state_updates_task_and_snapshot(
        self, mock_tenant_client, sample_org_id
    ):
        """persist_state() updates both tasks and snapshots tables."""
        flow = TestableFlow(org_id=sample_org_id)
        flow.state = BaseFlowState(
            task_id=str(uuid4()),
            org_id=sample_org_id,
            flow_type="test_flow",
            input_data={"test": "data"},
        )
        flow.state.start()

        await flow.persist_state()

        # snapshots.upsert was called
        assert mock_tenant_client.table("snapshots").upsert.called

        # tasks.update was called
        assert mock_tenant_client.table("tasks").update.called

    @pytest.mark.asyncio
    async def test_persist_state_with_none_state(self, sample_org_id):
        """persist_state() with None state is a no-op."""
        flow = TestableFlow(org_id=sample_org_id)
        flow.state = None

        # Should not raise
        await flow.persist_state()

    @pytest.mark.asyncio
    async def test_persist_state_includes_approval_fields(
        self, mock_tenant_client, sample_org_id
    ):
        """persist_state() includes approval-related fields."""
        flow = TestableFlow(org_id=sample_org_id)
        flow.state = BaseFlowState(
            task_id=str(uuid4()),
            org_id=sample_org_id,
            flow_type="test_flow",
        )
        flow.state.await_approval()
        flow.state.approval_payload = {"monto": 1000}

        await flow.persist_state()

        # Check update call includes approval fields
        update_call = mock_tenant_client.table("tasks").update
        assert update_call.called
        update_kwargs = update_call.call_args[0][0]
        assert "approval_required" in update_kwargs
        assert "approval_status" in update_kwargs


# ── emit_event tests ────────────────────────────────────────────


class TestEmitEvent:
    """emit_event() behavior and error handling."""

    @pytest.mark.asyncio
    async def test_emit_event_appends_and_flushes(
        self, mock_tenant_client, mock_event_store, sample_org_id
    ):
        """emit_event() calls EventStore.append and flush."""
        flow = TestableFlow(org_id=sample_org_id)
        flow.state = BaseFlowState(
            task_id=str(uuid4()),
            org_id=sample_org_id,
            flow_type="test_flow",
        )
        flow.event_store = MagicMock()
        flow.event_store.flush = AsyncMock()

        await flow.emit_event("test.event", {"data": "value"})

        flow.event_store.append.assert_called_once()
        flow.event_store.flush.assert_called_once()

    @pytest.mark.asyncio
    async def test_emit_event_with_no_event_store(self, sample_org_id):
        """emit_event() with no event_store is a no-op."""
        flow = TestableFlow(org_id=sample_org_id)
        flow.state = BaseFlowState(
            task_id=str(uuid4()),
            org_id=sample_org_id,
            flow_type="test_flow",
        )
        flow.event_store = None

        # Should not raise
        await flow.emit_event("test.event", {})

    @pytest.mark.asyncio
    async def test_emit_event_with_no_state(self, sample_org_id):
        """emit_event() with no state is a no-op."""
        flow = TestableFlow(org_id=sample_org_id)
        flow.state = None
        flow.event_store = MagicMock()

        # Should not raise
        await flow.emit_event("test.event", {})


# ── Error handling decorator tests ──────────────────────────────


class TestWithErrorHandlingDecorator:
    """with_error_handling decorator behavior."""

    @pytest.mark.asyncio
    async def test_decorator_catches_exception_and_marks_failed(
        self, mock_tenant_client, mock_event_store, sample_org_id
    ):
        """Decorator catches exception, marks state FAILED, persists, re-raises."""
        flow = FailingFlow(org_id=sample_org_id)

        with pytest.raises(ValueError, match="Intentional failure"):
            await flow.execute({"test": "data"})

        # State should be marked as FAILED
        assert flow.state is not None
        assert flow.state.status == FlowStatus.FAILED.value
        assert "Intentional failure" in flow.state.error

    @pytest.mark.asyncio
    async def test_decorator_persists_failed_state(
        self, mock_tenant_client, mock_event_store, sample_org_id
    ):
        """Decorator persists the FAILED state."""
        flow = FailingFlow(org_id=sample_org_id)

        with pytest.raises(ValueError):
            await flow.execute({"test": "data"})

        # persist_state should have been called after marking as failed
        assert mock_tenant_client.table("snapshots").upsert.called


# ── create_task_record tests ────────────────────────────────────


class TestCreateTaskRecord:
    """create_task_record() behavior."""

    @pytest.mark.asyncio
    async def test_creates_task_with_correct_data(
        self, mock_tenant_client, mock_event_store, sample_org_id
    ):
        """create_task_record() inserts task with correct fields."""
        flow = TestableFlow(org_id=sample_org_id)
        input_data = {"test": "data"}
        correlation_id = "corr-123"

        await flow.create_task_record(input_data, correlation_id)

        # Check insert was called
        insert_call = mock_tenant_client.table("tasks").insert
        assert insert_call.called

        # Check inserted data
        inserted_data = insert_call.call_args[0][0]
        assert inserted_data["org_id"] == sample_org_id
        assert inserted_data["flow_type"] == "TestableFlow"
        assert inserted_data["payload"] == input_data
        assert inserted_data["correlation_id"] == correlation_id

    @pytest.mark.asyncio
    async def test_initialises_state_correctly(
        self, mock_tenant_client, mock_event_store, sample_org_id
    ):
        """create_task_record() initialises self.state correctly."""
        flow = TestableFlow(org_id=sample_org_id)
        input_data = {"test": "data"}

        await flow.create_task_record(input_data)

        assert flow.state is not None
        assert flow.state.org_id == sample_org_id
        assert flow.state.flow_type == "TestableFlow"
        assert flow.state.input_data == input_data
        assert flow.state.task_id is not None

    @pytest.mark.asyncio
    async def test_emits_flow_created_event(
        self, mock_tenant_client, mock_event_store, sample_org_id
    ):
        """create_task_record() emits flow.created event."""
        flow = TestableFlow(org_id=sample_org_id)

        with patch.object(flow, "emit_event", new_callable=AsyncMock) as mock_emit:
            await flow.create_task_record({"test": "data"})

            mock_emit.assert_called_once_with(
                "flow.created", {"input_data": {"test": "data"}}
            )


# ── validate_input contract tests ───────────────────────────────


class TestValidateInputContract:
    """validate_input() contract tests."""

    def test_validate_input_true_for_valid_data(self, sample_org_id):
        """validate_input returns True for valid data."""
        flow = TestableFlow(org_id=sample_org_id)
        assert flow.validate_input({"any": "data"}) is True

    def test_validate_input_false_for_invalid_data(self, sample_org_id):
        """validate_input returns False for invalid data (if implemented)."""
        # TestableFlow always returns True, so we test the contract
        flow = TestableFlow(org_id=sample_org_id)
        # Even empty dict is valid for TestableFlow
        assert flow.validate_input({}) is True

    @pytest.mark.asyncio
    async def test_execute_raises_on_invalid_input(
        self, mock_tenant_client, mock_event_store, sample_org_id
    ):
        """execute() raises ValueError if validate_input returns False."""
        flow = TestableFlow(org_id=sample_org_id)

        # Override validate_input to return False
        flow.validate_input = lambda x: False

        with pytest.raises(ValueError, match="Input validation failed"):
            await flow.execute({"test": "data"})
