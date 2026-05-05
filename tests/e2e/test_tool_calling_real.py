"""tests/e2e/test_tool_calling_real.py — Tool calling real SIN patches CrewAI.

Test E2E que NO parchea crewai.Crew / Task / Agent.
LLM real (Groq) debe llamar excel_reader tool activamente.
Requiere GROQ_API_KEY.

Correcciones al plan v3.2:
- Plan no contemplaba test sin patches de CrewAI — creado aca.
- Usa BaseCrew con ToolCallTracer interno para verificar tool calling.
"""

from __future__ import annotations

import json
import re
from unittest.mock import MagicMock, patch
from uuid import uuid4

import crewai
import pytest

from src.config import get_settings

# Force eager import of factory BEFORE any patches
from src.crews import factory as _  # noqa: F401
from src.crews.base_crew import BaseCrew

# Save real classes at module level (before autouse global_llm_mock patches them)
_REAL_CREW = crewai.Crew
_REAL_TASK = crewai.Task
_REAL_AGENT = crewai.Agent


def _has_groq_key() -> bool:
    try:
        s = get_settings()
        return bool(s.groq_api_key)
    except Exception:
        return False


def _can_init_llm() -> bool:
    if not _has_groq_key():
        return False
    try:
        from crewai import LLM
        LLM(model="groq/llama-3.3-70b-versatile", api_key="test")
        return True
    except ImportError:
        return False
    except Exception:
        return False


pytestmark = [
    pytest.mark.skipif(not _can_init_llm(), reason="Requiere GROQ_API_KEY o litellm"),
    pytest.mark.real_llm,
]


def _extract_json(text: str) -> str:
    match = re.search(r"```(?:json)?\s*\n?(.*?)\n?```", text, re.DOTALL)
    return match.group(1).strip() if match else text.strip()


AGENT_CONFIG = {
    "role": "presupuestador",
    "soul_json": {
        "role": "Cotizador de Eventos",
        "goal": "Usar el excel_reader para obtener precios reales y generar presupuestos",
        "backstory": (
            "Sos un experto en cotizacion de eventos. "
            "SIEMPRE usas la herramienta excel_reader para obtener datos actualizados "
            "de precios y consumos antes de calcular. "
            "Nunca inventes precios ni uses datos de entrenamiento."
        ),
    },
    "allowed_tools": ["excel_reader"],
    "model": "groq/llama-3.3-70b-versatile",
    "max_iter": 5,
    "is_active": True,
}


@pytest.mark.asyncio
async def test_presupuestador_calls_excel_reader():
    """BaseCrew.run_async() sin patches de CrewAI — tool calling real.

    Verifica que el LLM llame excel_reader tool activamente
    y que el output contenga datos reales del xlsx.
    """
    org_id = str(uuid4())
    agent_config = {**AGENT_CONFIG, "org_id": org_id,
                    "soul_json": {**AGENT_CONFIG["soul_json"], "org_id": org_id}}

    # Counter-patch global_llm_mock: restore real CrewAI classes
    with (
        patch("crewai.Crew", _REAL_CREW),
        patch("crewai.Task", _REAL_TASK),
        patch("crewai.Agent", _REAL_AGENT),
    ):
        # Mock DB for agent_catalog
        chain = MagicMock()
        chain.select.return_value = chain
        chain.eq.return_value = chain
        chain.maybe_single.return_value = chain
        resp = MagicMock()
        resp.data = agent_config
        chain.execute.return_value = resp

        svc = MagicMock()
        svc.table.return_value = chain

        with (
            patch("src.crews.base_crew.get_service_client", return_value=svc),
            patch("src.crews.factory.get_settings", return_value=get_settings()),
        ):
            crew = BaseCrew(org_id=org_id, role="presupuestador")
            result = await crew.run_async(
                task_description=(
                    "Usa la herramienta excel_reader para leer el archivo "
                    "'precios_bebidas.xlsx'. Obtene los precios reales y luego "
                    "calcula cuanto cuesta preparar 1000 cocteles si cada coctel "
                    "usa 50ml de Gordon's Pink. "
                    "Cada botella tiene 700ml. "
                    "Devuelve SOLO JSON con: {'precio_botella': 0, 'botellas_necesarias': 0, 'costo_total': 0}"
                ),
                inputs={},
                expected_output="JSON with calculation",
            )

        raw = str(result)

    # Verify tool was actually called (not just data in prompt)
    tool_calls = crew.get_last_tool_calls()
    assert tool_calls.get("excel_reader", 0) >= 1, (
        f"excel_reader was called {tool_calls.get('excel_reader', 0)} times, expected >=1"
    )

    # Verify output contains real data from xlsx (not invented)
    assert "gordon" in raw.lower() or "12000" in raw, "Tool data not in response"

    try:
        data = json.loads(_extract_json(raw))
    except json.JSONDecodeError:
        data = json.loads(raw.strip())

    assert "costo_total" in data or "cost" in raw.lower()
    assert data.get("precio_botella", 0) > 0 or data.get("botellas_necesarias", 0) > 0
