"""tests/e2e/test_real_agent_pipeline.py — Agente real via pipeline CrewAI.

Ejecuta BaseCrew.run_async() con LLM real (Groq) y tool ExcelReader.
Requiere GROQ_API_KEY. Marcar: @pytest.mark.real_llm
"""

from __future__ import annotations

import json
import re
from unittest.mock import MagicMock, patch
from uuid import uuid4

import crewai

# Save real classes BEFORE any patches (global_llm_mock runs AFTER import)
_REAL_CREW = crewai.Crew
_REAL_TASK = crewai.Task
_REAL_AGENT = crewai.Agent

import pytest

from src.config import get_settings

# Force eager import of factory BEFORE any patches
from src.crews import factory as _  # noqa: F401
from src.crews.base_crew import BaseCrew


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
    "org_id": None,
    "role": "presupuestador",
    "soul_json": {
        "role": "Cotizador de Eventos",
        "goal": "Generar presupuestos detallados para eventos usando excel_reader para precios reales",
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


@pytest.mark.asyncio
async def test_agent_presupuesto_via_crewai():
    """BaseCrew.run_async() con LLM real + CrewAI real genera presupuesto."""

    org_id = str(uuid4())
    agent_config = {**AGENT_CONFIG, "org_id": org_id}

    # Restore real Crew classes (global_llm_mock patches them)
    with (
        patch("crewai.Crew", _REAL_CREW),
        patch("crewai.Task", _REAL_TASK),
        patch("crewai.Agent", _REAL_AGENT),
    ):
        # Patch DB for agent_catalog lookup — build proper chain
        chain = MagicMock()
        chain.select.return_value = chain
        chain.eq.return_value = chain
        chain.maybe_single.return_value = chain
        mock_resp = MagicMock()
        mock_resp.data = agent_config
        chain.execute.return_value = mock_resp

        svc = MagicMock()
        svc.table.return_value = chain

        with (
            patch("src.crews.base_crew.get_service_client", return_value=svc),
            patch("src.crews.factory.get_settings", return_value=get_settings()),
        ):
            crew = BaseCrew(org_id=org_id, role="presupuestador")
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
                expected_output="JSON structure with the budget",
            )

        raw = str(result)

    # Verify real LLM was used (not mocked result)
    assert "Mocked Crew Result" not in raw, "LLM mock still active!"

    # Extract and validate JSON
    try:
        data = json.loads(_extract_json(raw))
    except json.JSONDecodeError:
        # Try parsing raw directly
        data = json.loads(raw.strip())

    assert data["costo_total"] > 0
    assert data["precio_venta"] > data["costo_total"]
    assert len(data["bebidas"]) >= 3
    assert data["cantidad_bartenders"] >= 2
