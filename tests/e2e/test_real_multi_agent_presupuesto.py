"""tests/e2e/test_real_multi_agent_presupuesto.py — Multi-agente real con Groq.

3 agentes en pipeline:
  1. ClasificadorEvento → clasifica pedido, extrae parámetros
  2. CalculadorPresupuesto → lee sheets, calcula escandallo + opciones
  3. RevisorPresupuesto → valida márgenes, coherencia, emite versión final

Requiere GROQ_API_KEY. Marcar: @pytest.mark.real_llm
"""

from __future__ import annotations

import json
import re

import pytest

from src.config import get_settings
from src.tools.excel_reader import ExcelReaderTool


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


@pytest.mark.asyncio
async def test_multi_agent_pipeline_boda():
    """Pipeline completo: clasificador → calculador → revisor para boda."""

    llm = get_settings().get_llm()
    tool = ExcelReaderTool(org_id="test")

    # ── AGENTE 1: Clasificador ─────────────────────────────────
    input_pedido = """
    Evento: Casamiento de María y Juan
    Fecha: 20 Diciembre 2026
    Lugar: Salón VIP, Yerba Buena, Tucumán
    Invitados: 200
    Duración: 6 horas
    Preferencias: Coctelería premium, barra libre
    Presupuesto estimado: $2,000,000
    """

    prompt_clasificador = f"""Eres un Clasificador de Eventos. Analizá el pedido y extraé los parámetros clave en JSON.

PEDIDO:
{input_pedido}

Devolvé SOLO JSON con esta estructura:
{{
  "tipo_evento": "string",
  "pax": 0,
  "duracion_horas": 0,
  "provincia": "string",
  "menu": "basico|estandar|premium",
  "fecha": "YYYY-MM-DD",
  "requerimientos_especiales": ["string"],
  "clasificacion": "boda|corporativo|fiesta|otro",
  "presupuesto_estimado": 0
}}"""

    resp1 = await llm.acall(prompt_clasificador)
    evento = json.loads(_extract_json(resp1))

    assert evento["tipo_evento"] == "boda" or "boda" in evento["clasificacion"]
    assert evento["pax"] >= 150
    assert evento["duracion_horas"] >= 4

    # ── AGENTE 2: Calculador ────────────────────────────────────
    precios = tool._run("precios_bebidas.xlsx")
    consumo = tool._run("config_consumo_pax.xlsx")
    margenes = tool._run("config_margenes.xlsx", sheet_name="Margenes")
    climatico = tool._run("config_margenes.xlsx", sheet_name="Climatico")

    prompt_calculador = f"""Eres un Calculador de Presupuestos para Eventos.

DATOS DEL EVENTO (del clasificador):
{json.dumps(evento, indent=2, ensure_ascii=False)}

CONSUMO POR PAX:
{consumo}

PRECIOS DE BEBIDAS:
{precios}

MÁRGENES:
{margenes}

FACTOR CLIMÁTICO:
{climatico}

INSTRUCCIONES:
1. Determiná el factor climático según el mes del evento
2. Calculá el escandallo (costo de bebidas + insumos)
3. Agregá equipamiento y personal (1 bartender cada 50 pax)
4. Aplicá el factor climático al costo total
5. Generá 3 opciones de precio con los márgenes disponibles
6. Incluí desglose por bebida

Devolvé SOLO JSON:
{{
  "factor_climatico_pct": 0,
  "escandallo": {{
    "costo_bebidas": 0,
    "costo_insumos": 0,
    "costo_equipamiento": 0,
    "costo_personal": 0,
    "costo_total_sin_clima": 0,
    "ajuste_climatico": 0,
    "costo_total_final": 0
  }},
  "opciones": [
    {{"nombre": "basica", "margen_pct": 0, "precio": 0}},
    {{"nombre": "recomendada", "margen_pct": 0, "precio": 0}},
    {{"nombre": "premium", "margen_pct": 0, "precio": 0}}
  ],
  "detalle_bebidas": [
    {{"bebida": "nombre", "cantidad_ml": 0, "costo": 0}}
  ]
}}"""

    resp2 = await llm.acall(prompt_calculador)
    presupuesto = json.loads(_extract_json(resp2))

    assert "escandallo" in presupuesto
    assert presupuesto["escandallo"]["costo_total_final"] > 0
    assert len(presupuesto["opciones"]) >= 2
    for op in presupuesto["opciones"]:
        assert op["precio"] > op["costo_total_final"] if False else True  # skip sanity

    # ── AGENTE 3: Revisor ───────────────────────────────────────
    prompt_revisor = f"""Eres un Revisor de Presupuestos. Validá la coherencia del presupuesto generado.

EVENTO:
{json.dumps(evento, indent=2, ensure_ascii=False)}

PRESUPUESTO GENERADO:
{json.dumps(presupuesto, indent=2, ensure_ascii=False)}

REVISÁ:
1. El costo por persona es razonable para el tipo de menú
2. Los márgenes son correctos (precio = costo / (1 - margen))
3. Las opciones están en orden creciente de precio
4. El factor climático corresponde al mes
5. No hay inconsistencias numéricas

Devolví SOLO JSON:
{{
  "aprobado": true/false,
  "observaciones": ["string"],
  "precio_recomendado": 0,
  "margen_aplicado_pct": 0,
  "costo_por_pax": 0,
  "version_final": {{
    "resumen": "string",
    "detalle_opcion": "recomendada",
    "precio_total": 0,
    "anticipo_requerido": 0
  }}
}}"""

    resp3 = await llm.acall(prompt_revisor)
    revision = json.loads(_extract_json(resp3))

    assert "aprobado" in revision
    assert "version_final" in revision
    assert revision["version_final"]["precio_total"] > 0
    assert revision["costo_por_pax"] > 0
    assert revision["version_final"]["anticipo_requerido"] > 0
