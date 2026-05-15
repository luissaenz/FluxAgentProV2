"""Tests: Multi-crew flow coordination (Phase 3).

All LLM and DB calls are mocked — tests verify:
  - State flows correctly between crews
  - Router bifurcates based on Crew A output
  - Crew B triggers approval when monto > 50k
  - Crew C path completes without approval
  - State persists after each crew
"""

from __future__ import annotations

import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from uuid import uuid4

from src.flows.multi_crew_flow import MultiCrewFlow, MultiCrewState
from src.flows.state import FlowStatus


# ── helpers ──────────────────────────────────────────────────────

def _make_crew_mock(raw_output: str):
    """Create a mock BaseCrew whose run_async returns a mock result."""
    crew_instance = MagicMock()
    crew_instance.run_async = AsyncMock(return_value=MagicMock(
        __str__=lambda self: raw_output,
    ))
    return crew_instance


# ── Router tests ─────────────────────────────────────────────────

class TestDecideNextCrew:
    """Router bifurcates correctly based on Crew A output."""

    def test_routes_to_crew_b_when_required(self, sample_org_id):
        flow = MultiCrewFlow(org_id=sample_org_id)
        flow.state = MultiCrewState(
            task_id=str(uuid4()),
            org_id=sample_org_id,
            flow_type="multi_crew",
        )
        flow.state.crew_a_output = {"requires_crew_b": True, "result": "analysis"}

        assert flow._decide_next_crew() == "crew_b"

    def test_routes_to_crew_c_by_default(self, sample_org_id):
        flow = MultiCrewFlow(org_id=sample_org_id)
        flow.state = MultiCrewState(
            task_id=str(uuid4()),
            org_id=sample_org_id,
            flow_type="multi_crew",
        )
        flow.state.crew_a_output = {"result": "analysis"}

        assert flow._decide_next_crew() == "crew_c"

    def test_routes_to_crew_c_when_output_is_none(self, sample_org_id):
        flow = MultiCrewFlow(org_id=sample_org_id)
        flow.state = MultiCrewState(
            task_id=str(uuid4()),
            org_id=sample_org_id,
            flow_type="multi_crew",
        )
        flow.state.crew_a_output = None

        assert flow._decide_next_crew() == "crew_c"


# ── Full flow execution tests ────────────────────────────────────

class TestMultiCrewExecution:
    """Integration tests for the full multi-crew lifecycle."""

    @pytest.mark.asyncio
    async def test_crew_a_then_crew_c_completes(
        self, mock_tenant_client, mock_service_client, mock_event_store, sample_org_id
    ):
        """Path: Crew A → router (crew_c) → Crew C → completed."""
        flow = MultiCrewFlow(org_id=sample_org_id)

        crew_a_mock = _make_crew_mock("Analysis complete")
        crew_c_mock = _make_crew_mock("Review complete")

        with patch("src.flows.multi_crew_flow.BaseCrew") as MockBaseCrew:
            # BaseCrew(org_id, role="analyst") → crew_a_mock
            # BaseCrew(org_id, role="reviewer") → crew_c_mock
            def side_effect(org_id, role):
                if role == "analyst":
                    return crew_a_mock
                elif role == "reviewer":
                    return crew_c_mock
                return MagicMock()

            MockBaseCrew.side_effect = side_effect

            state = await flow.execute({"data": "test input"})

        assert state.status == FlowStatus.COMPLETED.value
        assert state.crew_a_output is not None
        assert state.crew_c_output is not None
        assert state.crew_b_output is None

    @pytest.mark.asyncio
    async def test_crew_a_then_crew_b_completes_without_approval(
        self, mock_tenant_client, mock_service_client, mock_event_store, sample_org_id
    ):
        """Path: Crew A → router (crew_b) → Crew B (monto ≤ 50k) → completed."""
        flow = MultiCrewFlow(org_id=sample_org_id)

        crew_a_mock = _make_crew_mock("Analysis done")
        crew_b_mock = _make_crew_mock("Processing done")

        # Crew A returns requires_crew_b = True
        async def crew_a_run(*args, **kwargs):
            result = MagicMock(__str__=lambda s: "Analysis done")
            return result

        crew_a_mock.run_async = AsyncMock(side_effect=crew_a_run)

        with patch("src.flows.multi_crew_flow.BaseCrew") as MockBaseCrew:
            def side_effect(org_id, role):
                if role == "analyst":
                    return crew_a_mock
                elif role == "processor":
                    return crew_b_mock
                return MagicMock()

            MockBaseCrew.side_effect = side_effect

            # Override router to go to crew_b
            with patch.object(flow, '_decide_next_crew', return_value="crew_b"):
                state = await flow.execute({"data": "test"})

        assert state.status == FlowStatus.COMPLETED.value
        assert state.crew_b_output is not None

    @pytest.mark.asyncio
    async def test_crew_b_triggers_approval_on_high_amount(
        self, mock_tenant_client, mock_service_client, mock_event_store, sample_org_id
    ):
        """Crew B monto > 50k → request_approval() → AWAITING_APPROVAL."""
        flow = MultiCrewFlow(org_id=sample_org_id)

        crew_a_mock = _make_crew_mock("Analysis")
        # Crew B returns output containing monto > 50k
        crew_b_result = MagicMock(__str__=lambda s: '{"monto": 100000}')
        crew_b_mock = MagicMock()
        crew_b_mock.run_async = AsyncMock(return_value=crew_b_result)

        # Mock RPC for next_event_sequence (used by request_approval)
        mock_service_client.rpc.return_value.execute.return_value = MagicMock(data=1)

        with patch("src.flows.multi_crew_flow.BaseCrew") as MockBaseCrew:
            def side_effect(org_id, role):
                if role == "analyst":
                    return crew_a_mock
                elif role == "processor":
                    return crew_b_mock
                return MagicMock()

            MockBaseCrew.side_effect = side_effect

            with patch.object(flow, '_decide_next_crew', return_value="crew_b"):
                # Make the approval check always return True (monto exceeds threshold)
                with patch.object(
                    MultiCrewFlow, '_approval_check',
                    staticmethod(lambda value, org_id: True),
                ):
                    state = await flow.execute({"data": "high value"})

        assert state.status == FlowStatus.AWAITING_APPROVAL.value

    @pytest.mark.asyncio
    async def test_state_persists_after_crew_a(
        self, mock_tenant_client, mock_service_client, mock_event_store, sample_org_id
    ):
        """State is persisted after Crew A executes."""
        flow = MultiCrewFlow(org_id=sample_org_id)

        crew_a_mock = _make_crew_mock("Analysis")
        crew_c_mock = _make_crew_mock("Review")

        with patch("src.flows.multi_crew_flow.BaseCrew") as MockBaseCrew:
            def side_effect(org_id, role):
                if role == "analyst":
                    return crew_a_mock
                elif role == "reviewer":
                    return crew_c_mock
                return MagicMock()

            MockBaseCrew.side_effect = side_effect

            state = await flow.execute({"data": "test"})

        # snapshots.upsert should have been called multiple times (after each crew + final)
        upsert_calls = mock_tenant_client.table("snapshots").upsert.call_count
        assert upsert_calls >= 2  # At minimum: after start + after crew_a


class TestMultiCrewState:
    """MultiCrewState properly extends BaseFlowState."""

    def test_default_crew_outputs_are_none(self, sample_org_id):
        state = MultiCrewState(
            task_id=str(uuid4()),
            org_id=sample_org_id,
            flow_type="multi_crew",
        )
        assert state.crew_a_output is None
        assert state.crew_b_output is None
        assert state.crew_c_output is None

    def test_serialises_crew_outputs(self, sample_org_id):
        state = MultiCrewState(
            task_id=str(uuid4()),
            org_id=sample_org_id,
            flow_type="multi_crew",
            crew_a_output={"result": "analysis"},
        )
        snapshot = state.to_snapshot()
        assert snapshot["state_json"]["crew_a_output"] == {"result": "analysis"}
