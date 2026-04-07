import pytest
import sys
from unittest.mock import MagicMock, patch

# Mock universal para evitar dependencias externas
for m in ["crewai", "crewai.flow", "crewai.project", "structlog"]:
    sys.modules[m] = MagicMock()

from uuid import uuid4
import asyncio
import os

# PYTHONPATH
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

# Importamos lo necesario
from src.flows.state import BaseFlowState, FlowStatus

@pytest.mark.asyncio
async def test_base_flow_state_token_tracking():
    """Verifica que el estado base maneja correctamente los tokens."""
    state = BaseFlowState(
        task_id=str(uuid4()),
        org_id=str(uuid4()),
        flow_type="test"
    )
    
    assert state.tokens_used == 0
    state.update_tokens(100)
    assert state.tokens_used == 100
    
    # Estimación
    assert state.estimate_tokens("Hola") == 1 # 4 chars // 4 = 1
    assert state.estimate_tokens("A" * 40) == 10 # 40 // 4 = 10

@pytest.mark.asyncio
async def test_generic_flow_logic_mocked():
    """Prueba la lógica de GenericFlow mockeando el crew."""
    # Mock de create_generic_crew
    mock_crew_instance = MagicMock()
    mock_result = MagicMock()
    # Usando token_usage que es el patrón que implementamos
    mock_result.token_usage = MagicMock(total_tokens=250)
    mock_crew_instance.kickoff_async = MagicMock(return_value=mock_result)

    with patch("src.flows.generic_flow.create_generic_crew", return_value=mock_crew_instance):
        from src.flows.generic_flow import GenericFlow
        
        flow = GenericFlow(org_id=str(uuid4()))
        flow.state = BaseFlowState(
            task_id=str(uuid4()),
            org_id=flow.org_id,
            flow_type="GenericFlow"
        )
        flow.state.input_data = {"text": "hello"}
        
        await flow._run_crew()
        
        # Verificamos que GenericFlow extrajo los tokens del mock_result
        assert flow.state.tokens_used == 250

@pytest.mark.asyncio
async def test_preventa_flow_logic_mocked():
    """Prueba la acumulación de tokens en PreventaFlow."""
    # Usamos patch para evitar errores de importación circular o dependencias faltantes
    with patch("src.flows.bartenders.preventa_flow._registrar_evento", return_value={"evento_id": "123"}), \
         patch("src.flows.bartenders.preventa_flow._get_clima_config", return_value={"factor_pct": 5}):
        
        from src.flows.bartenders.preventa_flow import BartendersPreventaFlow
        
        flow = BartendersPreventaFlow(org_id=str(uuid4()))
        flow.state = BaseFlowState(
            task_id=str(uuid4()),
            org_id=flow.org_id,
            flow_type="PreventaFlow"
        )
        
        await flow.agente_1_requerimientos()
        await flow.agente_2_clima()
        
        # 60 (A1) + 40 (A2) = 100 (acumulados estimativamente)
        assert flow.state.tokens_used == 100
