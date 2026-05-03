"""tests/e2e/test_presupuesto_flow.py — Paso 5: PresupuestoFlow registrado.

Verifica registro en FlowRegistry + ejecución via flow.execute().
"""

from __future__ import annotations

import json
import re
from unittest.mock import MagicMock, patch
from uuid import uuid4

import crewai
import pytest

from src.config import get_settings
from src.flows.registry import flow_registry
from src.flows.state import FlowStatus

# Import to trigger @register_flow
import src.flows.presupuesto_flow  # noqa: F401

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

from src.crews import factory as _  # noqa: F401


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


class TestPresupuestoFlow:
    """Paso 5: Flow de presupuesto registrado formalmente."""

    def test_flow_registered(self):
        """PresupuestoFlow está registrado en FlowRegistry."""
        assert flow_registry.has("presupuesto"), "Flow 'presupuesto' not registered!"
        FlowClass = flow_registry.get("presupuesto")
        assert FlowClass.__name__ == "PresupuestoFlow"

    def test_validate_input(self):
        """validate_input rechaza datos incompletos."""
        from src.flows.presupuesto_flow import PresupuestoFlow

        flow = PresupuestoFlow(org_id=str(uuid4()), user_id=str(uuid4()))
        assert flow.validate_input({"tipo_evento": "boda", "pax": 100, "fecha": "2026-01-01"})
        assert not flow.validate_input({"tipo_evento": "boda"})
        assert not flow.validate_input({})

    @pytest.mark.asyncio
    async def test_execute_with_real_llm(
        self, mock_service_client, mock_tenant_client, mock_event_store
    ):
        """PresupuestoFlow.execute() con LLM real completa."""
        from src.flows.presupuesto_flow import PresupuestoFlow

        org_id = str(uuid4())
        agent_config = {**AGENT_CONFIG, "org_id": org_id,
                        "soul_json": {**AGENT_CONFIG["soul_json"]}}

        mock_resp = MagicMock()
        mock_resp.data = agent_config
        mock_service_client.table("agent_catalog").execute.return_value = mock_resp

        with (
            patch("crewai.Crew", _REAL_CREW),
            patch("crewai.Task", _REAL_TASK),
            patch("src.crews.factory.get_settings", return_value=get_settings()),
        ):
            flow = PresupuestoFlow(org_id=org_id, user_id=str(uuid4()))
            state = await flow.execute({
                "tipo_evento": "boda",
                "pax": 150,
                "duracion_horas": 6,
                "provincia": "Tucumán",
                "fecha": "2026-03-15",
                "menu": "premium",
            })

        assert state.status == FlowStatus.COMPLETED.value, f"Got {state.status}"
        assert state.output_data is not None
        assert "result" in state.output_data
        assert "Mocked Crew" not in state.output_data["result"]

        raw = state.output_data["result"]
        try:
            data = json.loads(_extract_json(raw))
        except json.JSONDecodeError:
            data = {"raw": raw[:200]}

        assert "costo" in raw.lower() or "precio" in raw.lower() or "total" in str(data)
