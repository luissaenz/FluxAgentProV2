"""tests/e2e/test_real_agent_presupuesto.py — Agente real con Groq.

Escenario: agente recibe pedido, consulta sheets, genera presupuesto.
Usa LLM real (Groq). Requiere GROQ_API_KEY en .env.
Marcar: @pytest.mark.real_llm — no corre por defecto.
"""

from __future__ import annotations

import json
import re

import pytest

from src.config import get_settings
from src.tools.excel_reader import ExcelReaderTool


def _extract_json(text: str) -> str:
    """Extract JSON from LLM response (handles markdown code blocks)."""
    match = re.search(r"```(?:json)?\s*\n?(.*?)\n?```", text, re.DOTALL)
    if match:
        return match.group(1).strip()
    return text.strip()


def _has_groq_key() -> bool:
    try:
        s = get_settings()
        return bool(s.groq_api_key)
    except Exception:
        return False


pytestmark = pytest.mark.skipif(
    not _has_groq_key(),
    reason="Requiere GROQ_API_KEY en .env",
)


@pytest.mark.real_llm
@pytest.mark.asyncio
async def test_agente_genera_presupuesto_boda():
    """Agente genera presupuesto para boda de 150 pax en Tucumán."""
    tool = ExcelReaderTool(org_id="test")
    precios = tool._run("precios_bebidas.xlsx")
    consumo = tool._run("config_consumo_pax.xlsx")
    margenes = tool._run("config_margenes.xlsx", sheet_name="Margenes")
    climatico = tool._run("config_margenes.xlsx", sheet_name="Climatico")

    llm = get_settings().get_llm()

    prompt = f"""Eres un agente de presupuestos de eventos. Tu tarea es generar un presupuesto detallado.

DATOS DEL EVENTO:
- Tipo: Boda
- Fecha: 15 Enero 2026
- Provincia: Tucumán
- Pax: 150
- Duración: 5 horas
- Menú: Premium

DATOS DE CONSUMO POR PAX (menú premium):
{consumo}

LISTA DE PRECIOS DE BEBIDAS:
{precios}

MÁRGENES DISPONIBLES:
{margenes}

FACTOR CLIMÁTICO POR MES (NOA):
{climatico}

INSTRUCCIONES:
1. Calculá el escandallo (costo de bebidas por persona × pax)
2. Agregá hielo, agua, garnish, descartables según consumo
3. Calculá el costo total del evento
4. Aplicá el factor climático correspondiente a Enero (20%)
5. Generá 3 opciones de presupuesto aplicando los márgenes disponibles
6. Incluí equipamiento (barra, cristalería) y bartenders necesarios
7. Devolvé SOLO UN JSON VÁLIDO con esta estructura exacta:

{{
  "evento": {{
    "tipo": "boda",
    "pax": 150,
    "fecha": "2026-01-15",
    "factor_climatico_pct": 20
  }},
  "escandallo": {{
    "costo_bebidas": 0,
    "costo_hielo_agua": 0,
    "costo_garnish_des catables": 0,
    "costo_equipamiento": 0,
    "costo_bartenders": 0,
    "costo_total": 0
  }},
  "opciones": [
    {{
      "nombre": "basica",
      "margen_pct": 0,
      "precio_final": 0
    }},
    {{
      "nombre": "recomendada",
      "margen_pct": 0,
      "precio_final": 0
    }},
    {{
      "nombre": "premium",
      "margen_pct": 0,
      "precio_final": 0
    }}
  ],
  "detalle_bebidas": [
    {{"producto": "nombre", "cantidad_ml": 0, "precio_unitario": 0, "subtotal": 0}}
  ]
}}

NO agregues texto fuera del JSON. Solo el JSON."""
    response = await llm.acall(prompt)

    data = json.loads(_extract_json(response))

    assert "evento" in data, f"Missing 'evento' in: {list(data.keys())}"
    assert data["evento"]["pax"] == 150
    assert "escandallo" in data
    assert data["escandallo"]["costo_total"] > 0
    assert "opciones" in data
    assert len(data["opciones"]) >= 2
    for op in data["opciones"]:
        assert "precio_final" in op
        assert op["precio_final"] > 0


@pytest.mark.real_llm
@pytest.mark.asyncio
async def test_agente_calcula_coctelera():
    """Agente calcula cantidad de cocteles y bebidas necesarias."""
    tool = ExcelReaderTool(org_id="test")
    precios = tool._run("precios_bebidas.xlsx")

    llm = get_settings().get_llm()

    prompt = f"""Eres un agente de catering. Calculá los ingredientes necesarios.

PAX: 100
MENU: estandar
COCTELES POR PAX: 5 (según plan estandar)
ML ESPIRITOSO POR COCTEL: 50ml

MIX DE BEBIDAS (estandar):
- Gin: 50%
- Whisky: 20%
- Ron: 15%
- Vodka: 10%
- Tequila: 5%

PRECIOS:
{precios}

Calculá:
1. Total de cocteles = pax × cocteles_por_pax
2. Por bebida: total_ml = total_cocteles × mix_pct × ml_por_coctel
3. Convertí ml a botellas (750ml por botella)
4. Costo por bebida = botellas × precio_unitario
5. Costo total de bebidas

Devolvé SOLO JSON:
{{
  "total_cocteles": 0,
  "bebidas": [
    {{"nombre": "gin", "ml_totales": 0, "botellas": 0, "precio_unitario": 0, "subtotal": 0}}
  ],
  "costo_total_bebidas": 0
}}"""
    response = await llm.acall(prompt)

    data = json.loads(_extract_json(response))
    assert data["total_cocteles"] == 500  # 100 × 5
    assert len(data["bebidas"]) >= 3
    assert data["costo_total_bebidas"] > 0
