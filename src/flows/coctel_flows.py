"""CoctelPro Demo Flows — Phase 5B.

Four flows for a bartending services company:
- CotizacionFlow: Quote generation with HITL for high discounts / VIP
- LogisticaFlow: Supply calculation with HITL for large events
- ComprasFlow: Purchase orders — always requires HITL
- FinanzasFlow: Income/expense tracking with HITL for low margins
"""

from __future__ import annotations

from typing import Dict, Any
import logging

from .base_flow import BaseFlow
from .registry import register_flow

logger = logging.getLogger(__name__)


@register_flow("cotizacion_flow", category="ventas", depends_on=[])
class CotizacionFlow(BaseFlow):
    """Agente Ventas: cotización con HITL si descuento >15% o cliente VIP."""

    def validate_input(self, input_data: Dict[str, Any]) -> bool:
        return "pax" in input_data and "presupuesto" in input_data

    async def _run_crew(self) -> Dict[str, Any]:
        data = self.state.input_data
        pax = data.get("pax", 0)
        presupuesto = data.get("presupuesto", 0)
        cliente_vip = data.get("vip", False)

        # Calculate discount
        descuento = 0.1 if pax > 100 else 0.05
        if cliente_vip:
            descuento = 0.2

        total = presupuesto * (1 - descuento)

        # HITL if discount > 15% or VIP
        if descuento > 0.15 or cliente_vip:
            await self.request_approval(
                description="Cotización requiere aprobación",
                payload={
                    "evento": data.get("evento", "Evento"),
                    "pax": pax,
                    "presupuesto": presupuesto,
                    "descuento": f"{descuento * 100:.0f}%",
                    "total": total,
                    "cliente_vip": cliente_vip,
                },
            )

        return {"status": "completed", "total": total, "descuento": descuento}


@register_flow("logistica_flow", category="operaciones", depends_on=["cotizacion_flow"])
class LogisticaFlow(BaseFlow):
    """Agente Logística: calcula insumos con HITL para eventos grandes."""

    def validate_input(self, input_data: Dict[str, Any]) -> bool:
        return "pax" in input_data

    async def _run_crew(self) -> Dict[str, Any]:
        data = self.state.input_data
        pax = data.get("pax", 0)
        ubicacion = data.get("ubicacion", "local")

        insumos = self._calcular_insumos(pax, ubicacion)
        total_costo = sum(i["precio"] * i["cantidad"] for i in insumos)

        # HITL for large events or special locations
        if pax > 150 or ubicacion == "exterior":
            await self.request_approval(
                description="Logística requiere aprobación",
                payload={
                    "pax": pax,
                    "ubicacion": ubicacion,
                    "insumos": insumos,
                    "total_costo": total_costo,
                },
            )

        return {"status": "completed", "insumos": insumos, "total_costo": total_costo}

    @staticmethod
    def _calcular_insumos(pax: int, ubicacion: str) -> list:
        """1 bottle per 3 pax, 1 glass per pax, etc."""
        base = [
            {"item": "Botellas de vodka", "cantidad": max(1, pax // 3), "precio": 50},
            {"item": "Vasos", "cantidad": pax, "precio": 1},
            {"item": "Hielo (kg)", "cantidad": max(1, pax // 10), "precio": 5},
        ]
        if ubicacion == "exterior":
            base.append({"item": "Generador eléctrico", "cantidad": 1, "precio": 200})
        return base


@register_flow("compras_flow", category="compras", depends_on=["logistica_flow"])
class ComprasFlow(BaseFlow):
    """Agente Compras: genera órdenes de compra. HITL: SIEMPRE."""

    def validate_input(self, input_data: Dict[str, Any]) -> bool:
        return "insumos" in input_data

    async def _run_crew(self) -> Dict[str, Any]:
        data = self.state.input_data
        insumos = data.get("insumos", [])
        total = sum(i["precio"] * i["cantidad"] for i in insumos)

        # HITL: always — never purchases autonomously
        await self.request_approval(
            description=f"Orden de compra por ${total}",
            payload={
                "insumos": insumos,
                "total": total,
                "proveedor": "proveedor_coctel",
            },
        )

        return {"status": "completed", "total": total}


@register_flow("finanzas_flow", category="finanzas", depends_on=["cotizacion_flow", "compras_flow"])
class FinanzasFlow(BaseFlow):
    """Agente Finanzas: registra ingresos/egresos con HITL si margen < 20%."""

    def validate_input(self, input_data: Dict[str, Any]) -> bool:
        return "ingreso" in input_data and "egreso" in input_data

    async def _run_crew(self) -> Dict[str, Any]:
        data = self.state.input_data
        ingreso = data.get("ingreso", 0)
        egreso = data.get("egreso", 0)

        margen = (ingreso - egreso) / ingreso if ingreso > 0 else 0

        # HITL if margin < 20%
        if margen < 0.2:
            await self.request_approval(
                description="Margen bajo, requiere aprobación",
                payload={
                    "ingreso": ingreso,
                    "egreso": egreso,
                    "margen": f"{margen * 100:.0f}%",
                },
            )

        return {"status": "completed", "margen": margen}
