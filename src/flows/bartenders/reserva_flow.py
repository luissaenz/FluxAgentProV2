"""
src/flows/bartenders/reserva_flow.py

ReservaFlow: cotización aceptada → reserva stock → asigna bartenders.

Secuencia: A6 (inventario) → A8 (staffing)
HITL opcional: si falta stock → request_approval("compra_emergencia_stock")

Trigger: POST /bartenders/reserva
Input:   evento_id, cotizacion_id, opcion_elegida
Output:  bartenders asignados + stock reservado
"""

from crewai.flow.flow import Flow, listen, start
from pydantic import BaseModel, Field
from typing import Any

from src.flows.base_flow import BaseFlow
from src.flows.state import BaseFlowState, FlowStatus
from src.connectors.supabase_connector import SupabaseMockConnector
from src.crews.bartenders.reserva_crews import (
    _seleccionar_bartenders,
    _generar_hoja_de_ruta,
)
from src.tools.bartenders.inventario_tool import (
    CalcularStockNecesarioTool,
    ReservarStockTool,
)


# ─── Estado ────────────────────────────────────────────────────────────────

class ReservaState(BaseFlowState):
    evento_id:      str = ""
    cotizacion_id:  str = ""
    opcion_elegida: str = "recomendada"

    # Datos del evento (cargados desde DB)
    pax:            int = 0
    tipo_menu:      str = ""
    fecha_evento:   str = ""
    duracion_horas: int = 0
    provincia:      str = ""
    localidad:      str = ""

    # Resultados
    stock_reservado:    bool  = False
    items_a_comprar:    list  = Field(default_factory=list)
    bartenders_ids:     list  = Field(default_factory=list)
    hoja_de_ruta:       str   = ""


# ─── Flow ──────────────────────────────────────────────────────────────────

class ReservaFlow(BaseFlow):
    """
    Flow de reserva: confirma cotización, reserva stock y asigna equipo.

    HITL puede activarse si hay faltante de stock.
    En ese caso el flow pausa y espera aprobación del Jefe
    para proceder con una compra de emergencia.
    """

    def validate_input(self, input_data: dict) -> bool:
        required = ["evento_id", "cotizacion_id", "opcion_elegida"]
        for field in required:
            if not input_data.get(field):
                return False
        if input_data["opcion_elegida"] not in ("basica", "recomendada", "premium"):
            return False
        return True

    @start()
    async def cargar_evento(self):
        """Carga los datos del evento desde DB para usarlos en los siguientes pasos."""
        data      = self.state.input_data
        connector = SupabaseMockConnector(self.org_id, self.user_id)

        self.state.evento_id      = data["evento_id"]
        self.state.cotizacion_id  = data["cotizacion_id"]
        self.state.opcion_elegida = data["opcion_elegida"]

        evento = connector.read_one("eventos", {"evento_id": self.state.evento_id})
        if not evento:
            raise ValueError(f"Evento {self.state.evento_id} no encontrado")

        self.state.pax            = int(evento["pax"])
        self.state.tipo_menu      = evento["tipo_menu"]
        self.state.fecha_evento   = str(evento["fecha_evento"])
        self.state.duracion_horas = int(evento["duracion_horas"])
        self.state.provincia      = evento["provincia"]
        self.state.localidad      = evento["localidad"]

        # Registrar opción elegida en cotizaciones
        connector.update("cotizaciones", self.state.cotizacion_id, {
            "opcion_elegida": self.state.opcion_elegida,
            "status":         "aceptada",
        })

        self.logger.info("reserva.evento_cargado",
                         evento_id=self.state.evento_id,
                         pax=self.state.pax)
        await self.emit_event("reserva.iniciada", {"evento_id": self.state.evento_id})

    @listen(cargar_evento)
    async def agente_6_inventario(self):
        """
        A6: calcula stock necesario e intenta reservarlo.
        Si hay faltante → pausa el flow para que el Jefe apruebe la compra.
        """
        connector = SupabaseMockConnector(self.org_id, self.user_id)
        calc_tool = CalcularStockNecesarioTool(connector=connector)
        res_tool  = ReservarStockTool(connector=connector)

        # Calcular stock necesario
        stock_necesario = calc_tool._run(
            evento_id = self.state.evento_id,
            pax       = self.state.pax,
            tipo_menu = self.state.tipo_menu,
        )

        # Intentar reservar
        resultado = res_tool._run(
            evento_id = self.state.evento_id,
            items     = [i.model_dump() for i in stock_necesario.items],
        )

        self.state.stock_reservado = not resultado.alerta_faltante
        self.state.items_a_comprar = [
            i.model_dump() for i in resultado.items_a_comprar
        ]

        await self.emit_event("reserva.stock_procesado", {
            "exitosas": len(resultado.reservas_exitosas),
            "fallidas": len(resultado.reservas_fallidas),
            "alerta":   resultado.alerta_faltante,
        })

        if resultado.alerta_faltante:
            self.logger.warning("reserva.faltante_stock",
                                items=self.state.items_a_comprar)

            # HITL: el Jefe decide si aprobar la compra de emergencia
            self.request_approval(
                description=(
                    f"Faltante de stock para evento {self.state.evento_id}. "
                    f"Se necesita comprar: "
                    f"{[i['nombre'] for i in self.state.items_a_comprar]}. "
                    f"¿Aprobar compra de emergencia?"
                ),
                payload={
                    "evento_id":      self.state.evento_id,
                    "items_faltantes": self.state.items_a_comprar,
                    "tipo":           "compra_emergencia_stock",
                },
            )
            # Si llega aquí: FlowSuspendedException corta el DAG

        self.logger.info("reserva.a6.completado",
                         stock_ok=self.state.stock_reservado)

    @listen(agente_6_inventario)
    async def agente_8_staffing(self):
        """
        A8: selecciona el equipo de bartenders y genera la hoja de ruta.
        Solo corre si el stock fue reservado exitosamente.
        """
        connector = SupabaseMockConnector(self.org_id, self.user_id)

        asignados, necesita_head = _seleccionar_bartenders(
            connector = connector,
            pax       = self.state.pax,
            tipo_menu = self.state.tipo_menu,
        )

        # Marcar como no disponibles
        for b in asignados:
            connector.update("bartenders_disponibles", b["bartender_id"], {
                "disponible":            False,
                "fecha_proxima_reserva": self.state.fecha_evento,
            })

        hoja = _generar_hoja_de_ruta(
            asignados      = asignados,
            fecha_evento   = self.state.fecha_evento,
            duracion_horas = self.state.duracion_horas,
            provincia      = self.state.provincia,
            localidad      = self.state.localidad,
        )

        self.state.bartenders_ids = [b["bartender_id"] for b in asignados]
        self.state.hoja_de_ruta   = hoja

        # Actualizar evento a confirmado
        connector.update("eventos", self.state.evento_id, {
            "status": "confirmado",
        })

        self.state.output_data = {
            "evento_id":      self.state.evento_id,
            "status":         "confirmado",
            "bartenders":     [b["nombre"] for b in asignados],
            "necesita_head":  necesita_head,
            "stock_ok":       self.state.stock_reservado,
            "hoja_de_ruta":   hoja,
        }

        self.logger.info("reserva.a8.completado",
                         bartenders=len(asignados))
        await self.emit_event("reserva.completada", {
            "evento_id":  self.state.evento_id,
            "bartenders": len(asignados),
        })

    async def _on_approved(self, notes: str = ""):
        """
        Callback si el Jefe aprueba la compra de emergencia de stock.
        Continúa con el staffing.
        """
        self.logger.info("reserva.compra_aprobada",
                         evento_id=self.state.evento_id, notes=notes)
        await self.emit_event("reserva.compra_emergencia_aprobada", {
            "evento_id": self.state.evento_id,
            "notes":     notes,
        })
        # El flow reanuda desde agente_8_staffing
        self.agente_8_staffing()

    async def _on_rejected(self, notes: str = ""):
        """
        Callback si el Jefe rechaza la compra de emergencia.
        El evento queda en estado 'cotizado' sin confirmar.
        """
        self.logger.warning("reserva.compra_rechazada",
                            evento_id=self.state.evento_id, notes=notes)
        connector = SupabaseMockConnector(self.org_id, self.user_id)
        connector.update("eventos", self.state.evento_id, {
            "status": "cotizado",  # vuelve a cotizado, sin confirmar
        })
        await self.emit_event("reserva.compra_emergencia_rechazada", {
            "evento_id": self.state.evento_id,
            "notes":     notes,
        })
