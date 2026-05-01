"""Integration tests: Handover entre steps con contexto real — Paso 2, Gap 2.

Tests I3.1-I3.3: DynamicWorkflow handover de results entre steps consecutivos.
Mock de BaseCrew para control de outputs y fallos.
Sin DB real, sin LLM, sin MCP.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.flows.dynamic_flow import DynamicWorkflow

# ── Template de 2 steps para handover ────────────────────────────

HANDOVER_TEMPLATE = {
    "name": "Handover Test Workflow",
    "description": "2-step workflow para probar contexto entre steps",
    "flow_type": "handover_test",
    "steps": [
        {
            "id": "step_1",
            "name": "First Step",
            "description": "Execute first analysis",
            "agent_role": "analyst",
            "depends_on": None,
            "requires_approval": False,
        },
        {
            "id": "step_2",
            "name": "Second Step",
            "description": "Process the results from step 1",
            "agent_role": "processor",
            "depends_on": ["step_1"],
            "requires_approval": False,
            "inputs": {"extra": "context"},
        },
    ],
    "agents": [
        {
            "role": "analyst",
            "goal": "Analyze data thoroughly and prepare output for next step",
            "backstory": "You are an expert data analyst.",
            "allowed_tools": [],
            "rules": [],
            "model": "claude-sonnet-4-20250514",
            "max_iter": 5,
        },
        {
            "role": "processor",
            "goal": "Process analysis results from previous step",
            "backstory": "You are a data processing specialist.",
            "allowed_tools": [],
            "rules": [],
            "model": "claude-sonnet-4-20250514",
            "max_iter": 5,
        },
    ],
    "approval_rules": [],
}


# ── I3.1: Step 2 recibe previous_results con output real de step 1 ─────────


@pytest.mark.asyncio
async def test_step_receives_previous_results(
    mock_tenant_client, mock_service_client, mock_event_store, sample_org_id
):
    """I3.1: Step 2 recibe previous_results con el output real de step 1."""
    flow = DynamicWorkflow(org_id=sample_org_id)
    flow._template_definition = HANDOVER_TEMPLATE
    flow._flow_type = "handover_test"
    flow.state = MagicMock()
    flow.state.input_data = {"original_key": "original_value"}
    flow.persist_state = AsyncMock()
    flow.emit_event = AsyncMock()
    flow.get_last_tokens_used = MagicMock(return_value=0)

    # Step 1 retorna "Analysis done"
    mock_crew_step1 = MagicMock()
    mock_crew_step1.run_async = AsyncMock(return_value=MagicMock(raw="Analysis done"))
    mock_crew_step1.get_last_tokens_used = MagicMock(return_value=100)

    # Step 2 retorna "Processing done"
    mock_crew_step2 = MagicMock()
    mock_crew_step2.run_async = AsyncMock(return_value=MagicMock(raw="Processing done"))
    mock_crew_step2.get_last_tokens_used = MagicMock(return_value=200)

    with patch("src.flows.dynamic_flow.BaseCrew") as MockBaseCrew:

        def crew_side_effect(org_id, role):  # noqa: ARG001
            if role == "analyst":
                return mock_crew_step1
            elif role == "processor":
                return mock_crew_step2
            return MagicMock()

        MockBaseCrew.side_effect = crew_side_effect

        result = await flow._run_crew()

    # Ambos steps ejecutados
    assert mock_crew_step1.run_async.called
    assert mock_crew_step2.run_async.called

    # Step 2 recibió previous_results con output de step 1
    step2_inputs = mock_crew_step2.run_async.call_args.kwargs["inputs"]
    assert "previous_results" in step2_inputs
    assert step2_inputs["previous_results"]["step_1"]["result"] == "Analysis done"
    assert step2_inputs["original_input"]["original_key"] == "original_value"

    # Ambos resultados en el dict final
    assert result["step_1"]["result"] == "Analysis done"
    assert result["step_2"]["result"] == "Processing done"


# ── I3.2: Template con 0 steps → retorna {} sin excepción ────────────────


@pytest.mark.asyncio
async def test_empty_steps_no_crash(
    mock_tenant_client, mock_service_client, mock_event_store, sample_org_id
):
    """I3.2: Template con 0 steps retorna {} sin lanzar excepción."""
    empty_template = dict(HANDOVER_TEMPLATE, steps=[])

    flow = DynamicWorkflow(org_id=sample_org_id)
    flow._template_definition = empty_template
    flow._flow_type = "empty_test"
    flow.state = MagicMock()
    flow.state.input_data = {}

    result = await flow._run_crew()

    assert result == {}
    assert isinstance(result, dict)


# ── I3.3: Step 2 falla → step 1 resultado preservado en results ──────────


@pytest.mark.asyncio
async def test_partial_failure_preserves_results(
    mock_tenant_client, mock_service_client, mock_event_store, sample_org_id
):
    """I3.3: Step 2 falla → step 1 resultado preservado, excepción propagada."""
    flow = DynamicWorkflow(org_id=sample_org_id)
    flow._template_definition = HANDOVER_TEMPLATE
    flow._flow_type = "handover_fail"
    flow.state = MagicMock()
    flow.state.input_data = {"test": "data"}
    flow.persist_state = AsyncMock()
    flow.emit_event = AsyncMock()
    flow.get_last_tokens_used = MagicMock(return_value=0)

    # Step 1 retorna OK
    mock_crew_step1 = MagicMock()
    mock_crew_step1.run_async = AsyncMock(return_value=MagicMock(raw="Step 1 output"))
    mock_crew_step1.get_last_tokens_used = MagicMock(return_value=100)

    # Step 2 lanza excepción
    step2_error = RuntimeError("Step 2 failed deliberately")
    mock_crew_step2 = MagicMock()
    mock_crew_step2.run_async = AsyncMock(side_effect=step2_error)

    with patch("src.flows.dynamic_flow.BaseCrew") as MockBaseCrew:

        def crew_side_effect(org_id, role):  # noqa: ARG001
            if role == "analyst":
                return mock_crew_step1
            elif role == "processor":
                return mock_crew_step2
            return MagicMock()

        MockBaseCrew.side_effect = crew_side_effect

        with pytest.raises(RuntimeError, match="Step 2 failed deliberately"):
            await flow._run_crew()

    # Step 1 se ejecutó y persist_state() fue llamado
    assert mock_crew_step1.run_async.called
    assert flow.persist_state.called
    # Nota: persist_state fue llamado después de step 1 completar
    # (antes de que step 2 falle y propague la excepción)
