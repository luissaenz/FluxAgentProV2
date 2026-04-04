"""
src/flows/bartenders/alerta_flow.py

AlertaClimaFlow: monitoreo climático T-7 días → compra de emergencia.

Secuencia: A5 (pronóstico real) → SI ALERTA → A7 (orden de compra) → HITL

HITL OBLIGATORIO: toda compra de emergencia requiere aprobación del Jefe.
Nunca se compra de forma autónoma.

Trigger: APScheduler (automático T-7 días antes del evento)
         o POST /bartenders/alerta (trigger manual para demo)
Input:   evento_id
Output:  orden_compra creada (pendiente de aprobación) o sin acción
"""

from crewai.flow.flow import Flow, listen, start
from pydantic import BaseModel, Field
from typing import Any

from src.flows.base_flow import BaseFlow
from src.flows.state import BaseFlowState, FlowStatus
from src.connectors.supabase_connector import SupabaseMockConnector
from src.flows.registry import register_flow
from src.crews.bartenders.reserva_crews import _calcular_items_orden, _guardar_orden
from src.tools.bartenders.clima_tool import PronosticoRealTool
from src.tools.bartenders.inventario_tool import CalcularStockNecesarioTool


# ─── Estado ────────────────────────────────────────────────────────────────

class AlertaState(BaseFlowState):
    evento_id:         str   = ""

    # Datos del evento
    provincia:         str   = ""
    fecha_evento:      str   = ""
    pax:               int   = 0
    tipo_menu:         str   = ""

    # Resultado A5
    alerta_roja:       bool  = False
    desvio_pct:        float = 0.0
    temp_historica:    float = 0.0
    temp_pronosticada: float = 0.0
    descripcion_clima: str   = ""

    # Orden generada por A7
    orden_id:          str   = ""
    total_compra:      int   = 0
    items_orden:       list  = Field(default_factory=list)


# ─── Flow ──────────────────────────────────────────────────────────────────
@register_flow("bartenders_alerta")
class AlertaClimaFlow(BaseFlow):
    """
    Flow de alerta climática.

    Corre automáticamente 7 días antes de cada evento confirmado.
    Si detecta desvío > 10%: genera orden de compra y pausa para HITL.
    Si no hay desvío: completa sin acción (task completed, sin HITL).

    Es el showcase principal de HITL en la demo:
    el Jefe ve una card ámbar en el Kanban con el monto y los items.
    """

    def validate_input(self, input_data: dict) -> bool:
        return bool(input_data.get("evento_id"))

    @start()
    async def cargar_evento(self):
        """Carga datos del evento desde DB."""
        connector = SupabaseMockConnector(self.org_id, self.user_id)
        evento_id = self.state.input_data["evento_id"]

        evento = connector.read_one("eventos", {"evento_id": evento_id})
        if not evento:
            raise ValueError(f"Evento {evento_id} no encontrado")
        if evento.get("status") not in ("confirmado", "coordinado"):
            raise ValueError(
                f"Evento {evento_id} no está confirmado (status={evento['status']})"
            )

        self.state.evento_id   = evento_id
        self.state.provincia   = evento["provincia"]
        self.state.fecha_evento = str(evento["fecha_evento"])
        self.state.pax         = int(evento["pax"])
        self.state.tipo_menu   = evento["tipo_menu"]

        self.logger.info("alerta.evento_cargado", evento_id=evento_id)
        await self.emit_event("alerta.iniciada", {"evento_id": evento_id})

    @listen(cargar_evento)
    async def agente_5_pronostico(self):
        """
        A5: verifica el pronóstico real vs histórico.
        Si desvío > 10%: activa alerta_roja para que A7 genere la orden.
        """
        connector = SupabaseMockConnector(self.org_id, self.user_id)
        tool      = PronosticoRealTool(connector=connector)

        resultado = tool._run(
            evento_id    = self.state.evento_id,
            provincia    = self.state.provincia,
            fecha_evento = self.state.fecha_evento,
        )

        self.state.alerta_roja        = resultado.alerta_roja
        self.state.desvio_pct         = resultado.desvio_pct
        self.state.temp_historica     = resultado.temp_historica
        self.state.temp_pronosticada  = resultado.temp_pronosticada
        self.state.descripcion_clima  = resultado.descripcion

        await self.emit_event("alerta.pronostico_verificado", {
            "alerta_roja":       resultado.alerta_roja,
            "desvio_pct":        resultado.desvio_pct,
            "temp_pronosticada": resultado.temp_pronosticada,
        })

        self.logger.info("alerta.a5.completado",
                         alerta=resultado.alerta_roja,
                         desvio=resultado.desvio_pct)

    @listen(agente_5_pronostico)
    async def evaluar_alerta(self):
        """
        Router: si no hay alerta, el flow termina aquí sin acción.
        Si hay alerta, continúa con A7.
        """
        if not self.state.alerta_roja:
            self.state.output_data = {
                "evento_id":   self.state.evento_id,
                "alerta_roja": False,
                "accion":      "sin_accion",
                "mensaje":     (
                    f"Temperatura pronosticada {self.state.temp_pronosticada}°C "
                    f"dentro del rango normal. No se requiere compra de emergencia."
                ),
            }
            self.logger.info("alerta.sin_accion", evento_id=self.state.evento_id)
            # El flow termina aquí — task completed sin HITL
            return

        self.logger.warning("alerta.roja_detectada",
                            desvio_pct=self.state.desvio_pct,
                            temp_pronosticada=self.state.temp_pronosticada)

    @listen(evaluar_alerta)
    async def agente_7_orden_emergencia(self):
        """
        A7: calcula los items adicionales y crea la orden de compra.
        Solo corre si alerta_roja=True.
        Luego el flow pausa para HITL del Jefe.
        """
        if not self.state.alerta_roja:
            return  # evaluar_alerta ya terminó el flow

        connector  = SupabaseMockConnector(self.org_id, self.user_id)
        calc_tool  = CalcularStockNecesarioTool(connector=connector)

        # Calcular stock base del evento
        stock_base = calc_tool._run(
            evento_id = self.state.evento_id,
            pax       = self.state.pax,
            tipo_menu = self.state.tipo_menu,
        )
        items_base = [i.model_dump() for i in stock_base.items]

        # Calcular items de la orden con factores de emergencia climática
        items_orden, total = _calcular_items_orden(
            connector      = connector,
            motivo         = "alerta_climatica",
            items_base     = items_base,
        )

        # Persistir orden con status="pendiente"
        orden_id = _guardar_orden(
            connector = connector,
            evento_id = self.state.evento_id,
            motivo    = "alerta_climatica",
            items     = items_orden,
            total     = total,
        )

        self.state.orden_id     = orden_id
        self.state.total_compra = total
        self.state.items_orden  = items_orden

        await self.emit_event("alerta.orden_generada", {
            "orden_id": orden_id,
            "total":    total,
        })

        self.logger.info("alerta.a7.orden_creada",
                         orden_id=orden_id, total=total)

        # ── HITL OBLIGATORIO ─────────────────────────────────────────────
        # Toda compra de emergencia requiere aprobación del Jefe.
        # El flow se pausa aquí hasta que se llame a POST /approvals/{task_id}
        self.request_approval(
            description=(
                f"ALERTA ROJA — Evento {self.state.evento_id}\n"
                f"Temperatura pronosticada: {self.state.temp_pronosticada}°C "
                f"(histórico: {self.state.temp_historica}°C, "
                f"desvío: +{self.state.desvio_pct:.1f}%)\n\n"
                f"Se requiere compra de emergencia por ARS {total:,}.\n"
                f"¿Aprobar la compra?"
            ),
            payload={
                "evento_id":         self.state.evento_id,
                "orden_id":          orden_id,
                "total_ars":         total,
                "items":             items_orden,
                "desvio_pct":        self.state.desvio_pct,
                "temp_historica":    self.state.temp_historica,
                "temp_pronosticada": self.state.temp_pronosticada,
                "tipo":              "compra_emergencia_clima",
            },
        )
        # FlowSuspendedException corta el DAG aquí

    async def _on_approved(self, notes: str = ""):
        """
        Jefe aprobó la compra de emergencia.
        Actualiza la orden a status="aprobada" y el evento a "coordinado".
        """
        connector = SupabaseMockConnector(self.org_id, self.user_id)

        connector.update("ordenes_compra", self.state.orden_id, {
            "status": "aprobada",
        })
        connector.update("eventos", self.state.evento_id, {
            "status": "coordinado",
        })

        self.state.output_data = {
            "evento_id":   self.state.evento_id,
            "alerta_roja": True,
            "accion":      "compra_aprobada",
            "orden_id":    self.state.orden_id,
            "total_ars":   self.state.total_compra,
            "mensaje":     (
                f"Compra de emergencia aprobada. "
                f"Orden {self.state.orden_id} por ARS {self.state.total_compra:,} confirmada."
            ),
        }

        self.logger.info("alerta.compra_aprobada",
                         orden_id=self.state.orden_id,
                         total=self.state.total_compra,
                         notes=notes)
        await self.emit_event("alerta.compra_aprobada", {
            "orden_id": self.state.orden_id,
            "total":    self.state.total_compra,
        })

    async def _on_rejected(self, notes: str = ""):
        """
        Jefe rechazó la compra.
        La orden queda como "rechazada". El evento sigue confirmado
        pero sin el stock adicional — el Jefe asumió el riesgo.
        """
        connector = SupabaseMockConnector(self.org_id, self.user_id)

        connector.update("ordenes_compra", self.state.orden_id, {
            "status": "rechazada",
        })

        self.state.output_data = {
            "evento_id":   self.state.evento_id,
            "alerta_roja": True,
            "accion":      "compra_rechazada",
            "orden_id":    self.state.orden_id,
            "mensaje":     (
                f"Compra de emergencia rechazada por el Jefe. "
                f"El evento continúa sin stock adicional. Motivo: {notes}"
            ),
        }

        self.logger.warning("alerta.compra_rechazada",
                            orden_id=self.state.orden_id, notes=notes)
        await self.emit_event("alerta.compra_rechazada", {
            "orden_id": self.state.orden_id,
            "notes":    notes,
        })


    async def _run_crew(self) -> dict:
        """CrewAI Flow implementation — not used, flows use @start/@listen instead."""
        return {}