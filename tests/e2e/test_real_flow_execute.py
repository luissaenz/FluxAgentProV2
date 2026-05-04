"""tests/e2e/test_real_flow_execute.py — Paso 4: Flow.execute() con LLM real.

Pipeline completo: Flow.execute() → create_task_record → BaseCrew.run_async()
→ LLM real (Groq) + excel_reader tool → state COMPLETED → events.

Verify state transitions (PENDING→RUNNING→COMPLETED), event emission,
DB persistence, and real LLM output with tool data.
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
_REAL_AGENT = crewai.Agent


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
    """Extrae JSON de un bloque de código markdown o texto plano."""
    match = re.search(r"```(?:json)?\s*\n?(.*?)\n?```", text, re.DOTALL)
    return match.group(1).strip() if match else text.strip()


AGENT_CONFIG = {
    "role": "presupuestador",
    "soul_json": {
        "role": "Cotizador de Eventos",
        "goal": "Generar presupuestos usando excel_reader con datos reales de precios_bebidas.xlsx",
        "backstory": (
            "Sos un experto en cotizacion de eventos. "
            "SIEMPRE usas la herramienta excel_reader para obtener precios actualizados "
            "del archivo precios_bebidas.xlsx antes de calcular. "
            "Nunca inventes precios ni uses datos de entrenamiento. "
            "Siempre respondes en formato JSON estructurado."
        ),
    },
    "allowed_tools": ["excel_reader"],
    "model": "groq/llama-3.3-70b-versatile",
    "max_iter": 5,
    "is_active": True,
}


@register_flow("test_exec_real_flow_tool", category="test")
class RealFlow(BaseFlow):
    """Flow que ejecuta agente presupuestador con excel_reader tool."""

    def validate_input(self, input_data):
        return bool(input_data)

    async def _run_crew(self):
        from src.crews.base_crew import BaseCrew

        crew = BaseCrew(self.org_id, role="presupuestador")
        result = await crew.run_async(
            task_description=(
                "Genera un presupuesto para este evento:\n"
                "- Tipo: Boda\n- Pax: 100\n- Duracion: 6 horas\n"
                "- Menu: Premium\n- Fecha: 15 Marzo 2026\n- Provincia: Tucuman\n\n"
                "IMPORTANTE: Usa la herramienta excel_reader para leer 'precios_bebidas.xlsx' "
                "y obtener los precios reales de bebidas. NO uses precios inventados.\n\n"
                "Consumo por PAX (premium): 5 cocteles, 50ml c/u\n"
                "Mix: 50% gin, 20% whisky, 15% ron, 10% vodka, 5% tequila\n"
                "Costo hielo/agua/garnish/descartables por PAX: $3500\n"
                "Bartenders: 1 cada 50 PAX a $50000/hora\n"
                "Margen recomendado: 45%\n\n"
                "Devuelve SOLO JSON con:\n"
                "{\n"
                '  "costo_total": 0,\n'
                '  "precio_venta": 0,\n'
                '  "bebidas": [{"nombre": "", "botellas": 0, "subtotal": 0}],\n'
                '  "cantidad_bartenders": 0\n'
                "}"
            ),
            inputs={},
            expected_output="JSON budget with real prices from excel_reader",
        )
        return {"result": str(result)}


@pytest.mark.asyncio
async def test_flow_execute_with_tool(
    mock_service_client, mock_tenant_client, mock_event_store
):
    """Flow.execute() con LLM real + excel_reader tool.

    Verifica:
    - State transitions PENDING → RUNNING → COMPLETED
    - Event emission flow.created + flow.completed
    - DB persistence (tasks insert/update, snapshots upsert)
    - Output contiene datos reales del tool (no mock, no precargados)
    """
    org_id = str(uuid4())
    agent_config = {**AGENT_CONFIG, "org_id": org_id,
                    "soul_json": {**AGENT_CONFIG["soul_json"]}}

    mock_resp = MagicMock()
    mock_resp.data = agent_config
    mock_service_client.table("agent_catalog").execute.return_value = mock_resp

    with (
        patch("crewai.Crew", _REAL_CREW),
        patch("crewai.Task", _REAL_TASK),
        patch("crewai.Agent", _REAL_AGENT),
        patch("src.crews.factory.get_settings", return_value=get_settings()),
    ):
        flow = RealFlow(org_id=org_id, user_id=str(uuid4()))
        state = await flow.execute({"evento": "Boda", "pax": 100})

    # ── State transitions ──
    assert state.status == FlowStatus.COMPLETED.value, f"status={state.status}"
    assert state.task_id is not None, "task_id ausente (create_task_record fallo?)"
    assert state.started_at is not None, "start() no llamado (nunca RUNNING)"
    assert state.completed_at is not None, "complete() no llamado"
    assert state.started_at <= state.completed_at, "linea temporal incorrecta"

    # ── Output ──
    assert state.output_data is not None, "output_data ausente"
    assert "result" in state.output_data, "result key faltante"
    raw = state.output_data["result"]

    # Verify real LLM (no mock)
    assert "Mocked Crew Result" not in raw, "LLM mock aun activo!"
    assert "Mocked LLM" not in raw, "LLM mock aun activo!"
    assert len(raw) > 100, "output sospechosamente corto para LLM real"

    # Extract and validate JSON budget
    try:
        data = json.loads(_extract_json(raw))
    except json.JSONDecodeError:
        data = json.loads(raw.strip())

    assert data["costo_total"] > 0, f"costo_total <= 0: {data}"
    assert data["precio_venta"] > data["costo_total"], "precio_venta debe > costo_total"
    assert len(data["bebidas"]) >= 3, f"<3 bebidas: {data}"
    assert data["cantidad_bartenders"] >= 2, f"<2 bartenders: {data}"

    # ── DB persistence (create_task_record + persist_state) ──
    mock_service_client.table("tasks").insert.assert_called()
    mock_service_client.table("tasks").update.assert_called()
    mock_service_client.table("snapshots").upsert.assert_called()

    # ── Event emission (flow.created + flow.completed) ──
    event_db = mock_event_store.return_value.__enter__.return_value
    event_db.table.assert_any_call("events")
