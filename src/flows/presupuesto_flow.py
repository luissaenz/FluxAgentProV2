"""PresupuestoFlow — Flow formal de generación de presupuestos.

Registrado como "presupuesto" en FlowRegistry.
Ejecuta agente presupuestador via BaseCrew con datos del evento.
"""

from __future__ import annotations

import logging
from typing import Any, Dict

# Ensure excel_reader tool is registered
import src.tools.excel_reader  # noqa: F401
from src.crews.base_crew import BaseCrew
from src.flows.base_flow import BaseFlow
from src.flows.registry import register_flow

logger = logging.getLogger(__name__)


@register_flow("presupuesto", category="business")
class PresupuestoFlow(BaseFlow):
    """Genera un presupuesto detallado para un evento.

    Input esperado:
    {
        "tipo_evento": "boda|corporativo|fiesta",
        "pax": 100,
        "duracion_horas": 6,
        "provincia": "Tucumán",
        "fecha": "2026-03-15",
        "menu": "premium|estandar|basico",
        "detalles_adicionales": "opcional"
    }
    """

    def validate_input(self, input_data: Dict[str, Any]) -> bool:
        required = ["tipo_evento", "pax", "fecha", "provincia"]
        return all(k in input_data for k in required)

    async def _run_crew(self) -> Dict[str, Any]:
        crew = BaseCrew(self.org_id, role="presupuestador")

        pax = self.state.input_data.get("pax", 100)
        tipo = self.state.input_data.get("tipo_evento", "evento")
        duracion = self.state.input_data.get("duracion_horas", 5)
        provincia = self.state.input_data.get("provincia", "Tucumán")
        fecha = self.state.input_data.get("fecha", "2026-01-01")
        menu = self.state.input_data.get("menu", "estandar")

        task = (
            f"Generá un presupuesto detallado para este evento:\n"
            f"- Tipo: {tipo}\n- Pax: {pax}\n- Duración: {duracion} horas\n"
            f"- Provincia: {provincia}\n- Fecha: {fecha}\n- Menú: {menu}\n\n"
            f"Usá la herramienta excel_reader para obtener precios reales "
            f"de 'precios_bebidas.xlsx' y datos de consumo de "
            f"'config_consumo_pax.xlsx'.\n\n"
            f"Calculá escandallo (costo total), aplicá márgenes, "
            f"generá 3 opciones de precio. Devolvé SOLO JSON."
        )

        result = await crew.run_async(
            task_description=task,
            inputs=self.state.input_data,
            expected_output="JSON con presupuesto detallado",
        )

        return {"result": str(result), "flow_type": "presupuesto"}
