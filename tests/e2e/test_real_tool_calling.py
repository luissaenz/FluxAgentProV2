"""tests/e2e/test_real_tool_calling.py — Paso 3: Tool calling real.

Agente con ExcelReaderTool via BaseCrew.run_async().
LLM real (Groq) debe llamar la herramienta para obtener datos.
Verifica que el output contenga datos reales de las sheets.
"""

from __future__ import annotations

import json
import re
from unittest.mock import MagicMock, patch
from uuid import uuid4

import crewai
import pytest

from src.config import get_settings
from src.crews.base_crew import BaseCrew

# Force eager import of factory BEFORE any patches
from src.crews import factory as _  # noqa: F401

# Save real classes before any patches
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


def _extract_json(text: str) -> str:
    match = re.search(r"```(?:json)?\s*\n?(.*?)\n?```", text, re.DOTALL)
    return match.group(1).strip() if match else text.strip()


AGENT_CONFIG = {
    "role": "presupuestador",
    "soul_json": {
        "role": "Cotizador de Eventos",
        "goal": "Usar el excel_reader para obtener precios reales y generar presupuestos",
        "backstory": (
            "Sos un experto en cotización de eventos. "
            "SIEMPRE usás la herramienta excel_reader para obtener datos actualizados "
            "de precios y consumos antes de calcular. "
            "Nunca inventás precios ni usás datos de entrenamiento."
        ),
    },
    "allowed_tools": ["excel_reader"],
    "model": "groq/llama-3.3-70b-versatile",
    "max_iter": 5,
    "is_active": True,
}


@pytest.mark.asyncio
async def test_agent_uses_excel_reader_tool():
    """Agente llama excel_reader para obtener precios reales."""

    org_id = str(uuid4())
    agent_config = {**AGENT_CONFIG, "org_id": org_id,
                    "soul_json": {**AGENT_CONFIG["soul_json"], "org_id": org_id}}

    with (
        patch("crewai.Crew", _REAL_CREW),
        patch("crewai.Task", _REAL_TASK),
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
                    "Usá la herramienta excel_reader para leer el archivo "
                    "'precios_bebidas.xlsx'. Obtené los precios reales y luego "
                    "calculá cuánto cuesta preparar 1000 cocteles si cada coctel "
                    "usa 50ml de Gordon's Pink. "
                    "Cada botella tiene 700ml. "
                    "Devolvé SOLO JSON con: {'precio_botella': 0, 'botellas_necesarias': 0, 'costo_total': 0}"
                ),
                inputs={},
                expected_output="JSON with calculation",
            )

        raw = str(result)

    assert "Mocked Crew Result" not in raw, "LLM mock still active!"
    assert "12000" in raw or "gordon" in raw.lower(), "Tool data not in response"

    try:
        data = json.loads(_extract_json(raw))
    except json.JSONDecodeError:
        # Try extracting just the JSON portion
        data = json.loads(raw.strip())

    assert "costo_total" in data or "cost" in raw.lower()
    assert data.get("precio_botella", 0) > 0 or data.get("botellas_necesarias", 0) > 0
