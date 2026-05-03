"""tests/e2e/test_real_flow_execute.py — Paso 4: Flow.execute() con LLM real.

Pipeline completo: Flow.execute() → create_task → BaseCrew.run_async()
→ LLM real (Groq) → state COMPLETED → event emission.
"""

from __future__ import annotations

import json
import re
from unittest.mock import MagicMock, patch
from uuid import uuid4

import crewai
import pytest

from src.config import get_settings
from src.flows.base_flow import BaseFlow
from src.flows.registry import register_flow
from src.flows.state import FlowStatus

_REAL_CREW = crewai.Crew
_REAL_TASK = crewai.Task


def _has_groq_key() -> bool:
    try:
        s = get_settings()
        return bool(s.groq_api_key)
    except Exception:
        return False


pytestmark = [
    pytest.mark.skipif(not _has_groq_key(), reason="Requiere GROQ_API_KEY"),
    pytest.mark.real_llm,
]

# Force eager import before any patches
from src.crews import factory as _  # noqa: F401


def _extract_json(text: str) -> str:
    match = re.search(r"```(?:json)?\s*\n?(.*?)\n?```", text, re.DOTALL)
    return match.group(1).strip() if match else text.strip()


AGENT_CONFIG = {
    "role": "presupuestador",
    "soul_json": {
        "role": "Cotizador de Eventos",
        "goal": "Generar presupuestos detallados para eventos",
        "backstory": "Sos un experto en cotización de eventos.",
    },
    "allowed_tools": [],
    "model": "groq/llama-3.3-70b-versatile",
    "max_iter": 3,
    "is_active": True,
}


@register_flow("test_exec_real_flow", category="test")
class RealFlow(BaseFlow):
    def validate_input(self, input_data):
        return bool(input_data)

    async def _run_crew(self):
        from src.crews.base_crew import BaseCrew
        crew = BaseCrew(self.org_id, role="presupuestador")
        result = await crew.run_async(
            task_description=(
                "Generá un presupuesto para: Boda, 100 pax, 6h, Tucumán. "
                "Precios de referencia: Gordon Pink $12000/botella, "
                "Beefeater $28000/botella. Consumo 5 cocteles/pax, 50ml c/u. "
                "Mix 50% gin, 20% whisky. Bartender $50000/hora, 1 cada 50 pax. "
                "Devolvé SOLO JSON."
            ),
            inputs={},
            expected_output="JSON budget",
        )
        return {"result": str(result)}


@pytest.mark.asyncio
async def test_flow_execute_completes(
    mock_service_client, mock_tenant_client, mock_event_store
):
    """Flow.execute() con LLM real → state COMPLETED + output."""
    org_id = str(uuid4())
    agent_config = {**AGENT_CONFIG, "org_id": org_id,
                    "soul_json": {**AGENT_CONFIG["soul_json"]}}

    # Configure agent_catalog mock
    mock_resp = MagicMock()
    mock_resp.data = agent_config
    mock_service_client.table("agent_catalog").execute.return_value = mock_resp

    with (
        patch("crewai.Crew", _REAL_CREW),
        patch("crewai.Task", _REAL_TASK),
        patch("src.crews.factory.get_settings", return_value=get_settings()),
    ):
        flow = RealFlow(org_id=org_id, user_id=str(uuid4()))
        state = await flow.execute({"evento": "Boda", "pax": 100})

    assert state.status == FlowStatus.COMPLETED.value, f"Got {state.status}"
    assert state.task_id is not None
    assert state.output_data is not None
    assert "result" in state.output_data

    raw = state.output_data["result"]
    assert "Mocked Crew Result" not in raw, "LLM mock still active!"

    # Try to extract budget data from output
    try:
        data = json.loads(_extract_json(raw))
    except json.JSONDecodeError:
        data = {"fallback": raw[:100]}

    assert "precio" in raw.lower() or "costo" in raw.lower() or "total" in str(data)
