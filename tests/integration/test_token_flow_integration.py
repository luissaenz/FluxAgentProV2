import sys
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Mock universal para evitar dependencias externas
for m in ["crewai", "crewai.flow", "crewai.project", "structlog"]:
    sys.modules[m] = MagicMock()

import os
from uuid import uuid4

# PYTHONPATH
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

# Importamos lo necesario
from src.flows.state import BaseFlowState


@pytest.mark.asyncio
async def test_base_flow_state_token_tracking():
    """Verifica que el estado base maneja correctamente los tokens."""
    state = BaseFlowState(
        correlation_id="test-corr-id",
        task_id=str(uuid4()),
        org_id=str(uuid4()),
        flow_type="test",
    )

    assert state.tokens_used == 0
    state.update_tokens(100)
    assert state.tokens_used == 100

    # Estimación
    assert state.estimate_tokens("Hola") == 1  # 4 chars // 4 = 1
    assert state.estimate_tokens("A" * 40) == 10  # 40 // 4 = 10


@pytest.mark.asyncio
async def test_generic_flow_logic_mocked():
    """Prueba la lógica de GenericFlow mockeando el crew."""
    # Mock de create_generic_crew
    mock_crew_instance = MagicMock()
    mock_result = MagicMock()
    # Usando token_usage que es el patrón que implementamos
    mock_result.token_usage = MagicMock(total_tokens=250)
    # kickoff_async debe ser AsyncMock para poder ser 'awaited'
    mock_crew_instance.kickoff_async = AsyncMock(return_value=mock_result)

    with patch(
        "src.flows.generic_flow.create_generic_crew", return_value=mock_crew_instance
    ):
        from src.flows.generic_flow import GenericFlow

        flow = GenericFlow(org_id=str(uuid4()))
        flow.state = BaseFlowState(
            correlation_id="test-corr-id",
            task_id=str(uuid4()),
            org_id=flow.org_id,
            flow_type="GenericFlow",
        )
        flow.state.input_data = {"text": "hello"}

        await flow._run_crew()

        # Verificamos que GenericFlow extrajo los tokens del mock_result
        assert flow.state.tokens_used == 250
