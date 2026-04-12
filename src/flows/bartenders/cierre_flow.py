"""
src/flows/bartenders/cierre_flow.py

CierreFlow: post-evento → auditoría → feedback → cierre.

Secuencia: A9 (auditoría) → SI margen crítico → HITL → A10 (feedback)

HITL condicional: solo si margen real < 10%.
El Jefe revisa antes de cerrar un evento con ganancia muy baja.

Trigger: POST /bartenders/cierre
Input:   evento_id, costo_real, mermas, compras_emergencia, desvio_climatico,
         rating (opcional)
Output:  evento cerrado con auditoría y próximo contacto programado
"""

from crewai.flow.flow import listen, start

from src.flows.base_flow import BaseFlow
from src.flows.state import BaseFlowState
from src.connectors.supabase_connector import SupabaseMockConnector
from src.flows.registry import register_flow
from src.crews.bartenders.cierre_crews import (
    _guardar_auditoria,
    MARGEN_CRITICO_UMBRAL,
)


# ─── Estado ────────────────────────────────────────────────────────────────

class CierreState(BaseFlowState):
    evento_id:          str   = ""

    # Input del cierre
    costo_real:         int   = 0
    mermas:             int   = 0
    compras_emergencia: int   = 0
    desvio_climatico:   str   = ""
    rating:             int | None = None

    # Calculados
    precio_cobrado:     int   = 0
    ganancia_neta:      int   = 0
    margen_pct:         float = 0.0
    margen_critico:     bool  = False

    # Output
    auditoria_id:       str   = ""
    proxima_contacto:   str   = ""


# ─── Flow ──────────────────────────────────────────────────────────────────
@register_flow("bartenders_cierre", category="cierre", depends_on=["bartenders_reserva"])
class CierreFlow(BaseFlow):
    """
    Flow de cierre post-evento.

    Audita la rentabilidad real, detecta margen crítico,
    y gestiona el cierre relacional con el cliente.

    Si el margen real es < 10%: pausa para que el Jefe revise.
    """

    def validate_input(self, input_data: dict) -> bool:
        required = ["evento_id", "costo_real"]
        for field in required:
            if not input_data.get(field):
                return False
        return True

    @start()
    async def cargar_datos(self):
        """Carga input y obtiene precio cobrado desde cotizaciones."""
        data      = self.state.input_data
        connector = SupabaseMockConnector(self.org_id, self.user_id)

        self.state.evento_id          = data["evento_id"]
        self.state.costo_real         = int(data["costo_real"])
        self.state.mermas             = int(data.get("mermas", 0))
        self.state.compras_emergencia = int(data.get("compras_emergencia", 0))
        self.state.desvio_climatico   = data.get("desvio_climatico", "")
        self.state.rating             = data.get("rating")

        # Obtener precio cobrado desde cotización
        cotizacion = connector.read_one(
            "cotizaciones", {"evento_id": self.state.evento_id}
        )
        if not cotizacion:
            raise ValueError(
                f"No se encontró cotización para {self.state.evento_id}"
            )

        opcion = cotizacion.get("opcion_elegida", "recomendada")
        self.state.precio_cobrado = int(cotizacion.get(f"opcion_{opcion}", 0))

        # Calcular métricas
        self.state.ganancia_neta = self.state.precio_cobrado - self.state.costo_real
        self.state.margen_pct    = (
            round(self.state.ganancia_neta / self.state.precio_cobrado * 100, 2)
            if self.state.precio_cobrado > 0 else 0.0
        )
        self.state.margen_critico = self.state.margen_pct < MARGEN_CRITICO_UMBRAL
        self.state.update_tokens(self.state.estimate_tokens(cotizacion))

        self.logger.info("cierre.datos_cargados",
                         evento_id=self.state.evento_id,
                         margen_pct=self.state.margen_pct,
                         margen_critico=self.state.margen_critico)
        await self.emit_event("cierre.iniciado", {
            "evento_id":  self.state.evento_id,
            "margen_pct": self.state.margen_pct,
        })

    @listen(cargar_datos)
    async def agente_9_auditoria(self):
        """
        A9: registra la auditoría completa.
        Si el margen es crítico (< 10%), pausa para revisión del Jefe.
        """
        connector = SupabaseMockConnector(self.org_id, self.user_id)

        auditoria_id = _guardar_auditoria(
            connector          = connector,
            evento_id          = self.state.evento_id,
            precio_cobrado     = self.state.precio_cobrado,
            costo_real         = self.state.costo_real,
            margen_pct         = self.state.margen_pct,
            mermas             = self.state.mermas,
            compras_emergencia = self.state.compras_emergencia,
            desvio_climatico   = self.state.desvio_climatico,
        )
        self.state.auditoria_id = auditoria_id
        self.state.update_tokens(self.state.estimate_tokens({"auditoria_id": auditoria_id}))

        # Actualizar evento a "ejecutado"
        connector.update("eventos", self.state.evento_id, {
            "status": "ejecutado",
        })

        await self.emit_event("cierre.auditoria_registrada", {
            "auditoria_id": auditoria_id,
            "margen_pct":   self.state.margen_pct,
        })

        self.logger.info("cierre.a9.completado",
                         auditoria_id=auditoria_id,
                         margen_pct=self.state.margen_pct)

        if self.state.margen_critico:
            self.logger.warning("cierre.margen_critico",
                                margen_pct=self.state.margen_pct)

            # HITL: el Jefe revisa antes de cerrar
            await self.request_approval(
                description=(
                    f"MARGEN CRÍTICO — Evento {self.state.evento_id}\n"
                    f"Margen real: {self.state.margen_pct}% "
                    f"(umbral mínimo: {MARGEN_CRITICO_UMBRAL}%)\n\n"
                    f"Precio cobrado: ARS {self.state.precio_cobrado:,}\n"
                    f"Costo real:     ARS {self.state.costo_real:,}\n"
                    f"Ganancia neta:  ARS {self.state.ganancia_neta:,}\n\n"
                    f"¿Aprobar el cierre del evento?"
                ),
                payload={
                    "evento_id":      self.state.evento_id,
                    "auditoria_id":   auditoria_id,
                    "margen_pct":     self.state.margen_pct,
                    "ganancia_neta":  self.state.ganancia_neta,
                    "precio_cobrado": self.state.precio_cobrado,
                    "costo_real":     self.state.costo_real,
                    "tipo":           "margen_critico",
                },
            )
            # FlowSuspendedException corta aquí

    @listen(agente_9_auditoria)
    async def agente_10_feedback(self):
        """
        A10: registra cierre relacional — próximo contacto y mensaje de seguimiento.
        Corre tanto si hubo HITL (y fue aprobado) como si no.
        """
        await self._ejecutar_feedback()

    async def _ejecutar_feedback(self):
        """Lógica de feedback compartida por el path normal y el path post-HITL."""
        connector = SupabaseMockConnector(self.org_id, self.user_id)

        # Calcular próximo contacto (mismo mes, año siguiente)
        evento = connector.read_one("eventos", {"evento_id": self.state.evento_id})
        if not evento:
            return

        from datetime import datetime
        from dateutil.relativedelta import relativedelta
        fecha        = datetime.strptime(str(evento["fecha_evento"]), "%Y-%m-%d").date()
        prox_contacto = (fecha + relativedelta(years=1)).isoformat()

        self.state.proxima_contacto = prox_contacto

        update_data: dict = {
            "proxima_contacto": prox_contacto,
            "status":           "cerrado",
        }
        if self.state.rating is not None:
            update_data["rating"] = self.state.rating

        connector.update("eventos", self.state.evento_id, update_data)

        self.state.output_data = {
            "evento_id":       self.state.evento_id,
            "status":          "cerrado",
            "auditoria_id":    self.state.auditoria_id,
            "margen_pct":      self.state.margen_pct,
            "ganancia_neta":   self.state.ganancia_neta,
            "proxima_contacto": prox_contacto,
        }
        self.state.update_tokens(self.state.estimate_tokens(self.state.output_data))

        self.logger.info("cierre.completado",
                         evento_id=self.state.evento_id,
                         proxima_contacto=prox_contacto)
        await self.emit_event("cierre.completado", {
            "evento_id":        self.state.evento_id,
            "proxima_contacto": prox_contacto,
        })

    async def _on_approved(self, notes: str = ""):
        """
        Jefe aprobó el cierre a pesar del margen crítico.
        Continúa con el feedback.
        """
        self.logger.info("cierre.margen_critico_aprobado",
                         evento_id=self.state.evento_id, notes=notes)
        await self.emit_event("cierre.margen_aprobado", {
            "evento_id": self.state.evento_id,
            "notes":     notes,
        })
        await self._ejecutar_feedback()
        self.state.complete(self.state.output_data)
        await self.persist_state()
        await self.emit_event("flow.completed", {"decision": "approved"})

    async def _on_rejected(self, notes: str = ""):
        """
        Jefe rechazó el cierre — el evento queda en "ejecutado" para revisión manual.
        No se cierra, no se programa próximo contacto.
        """
        self.state.output_data = {
            "evento_id": self.state.evento_id,
            "status":    "ejecutado",  # no se cierra
            "mensaje":   (
                f"Cierre rechazado por el Jefe. "
                f"Evento requiere revisión manual. Motivo: {notes}"
            ),
        }
        self.logger.warning("cierre.rechazado",
                            evento_id=self.state.evento_id, notes=notes)
        await self.emit_event("cierre.rechazado", {
            "evento_id": self.state.evento_id,
            "notes":     notes,
        })
        self.state.fail(f"Rejected by supervisor: {notes}")
        await self.persist_state()
        await self.emit_event("flow.completed", {"decision": "rejected"})


    async def _run_crew(self) -> dict:
        """Ejecuta la secuencia de agentes del flow (cargar_datos → A9 → A10)."""
        await self.cargar_datos()
        await self.agente_9_auditoria()
        await self.agente_10_feedback()

        return self.state.output_data or {}