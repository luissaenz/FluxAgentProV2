"""
src/flows/bartenders/preventa_flow.py

PreventaFlow: consulta → escandallo → 3 opciones de precio.

Secuencia: A1 (requerimientos) → A2 (clima) → A3 (escandallo) → A4 (cotización)

Sin HITL — el flujo es completamente automático.
El resultado son 3 opciones de precio en el payload de la task.

Trigger: POST /bartenders/preventa
Input:   fecha_evento, provincia, localidad, tipo_evento,
         pax, duracion_horas, tipo_menu, restricciones (opcional)
Output:  cotizacion_id + 3 opciones de precio en task.result
"""

from crewai.flow.flow import listen, start
from pydantic import Field

from src.flows.base_flow import BaseFlow
from src.flows.state import BaseFlowState
from src.flows.registry import register_flow
from src.connectors.supabase_connector import SupabaseMockConnector
from src.crews.bartenders.preventa_crews import (
    _registrar_evento,
    _calcular_opciones,
    _guardar_cotizacion,
)


# ─── Estado del flow ───────────────────────────────────────────────────────

class PreventaState(BaseFlowState):
    # Input
    fecha_evento:    str   = ""
    provincia:       str   = ""
    localidad:       str   = ""
    tipo_evento:     str   = ""
    pax:             int   = 0
    duracion_horas:  int   = 0
    tipo_menu:       str   = ""
    restricciones:   str   = ""

    # Resultados intermedios
    evento_id:            str = ""
    factor_climatico_pct: int = 0
    factor_razon:         str = ""
    escandallo_final:     int = 0
    escandallo_desglose:  dict = Field(default_factory=dict)

    # Output final
    cotizacion_id:      str = ""
    opcion_basica:      int = 0
    opcion_recomendada: int = 0
    opcion_premium:     int = 0


# ─── Flow ──────────────────────────────────────────────────────────────────

@register_flow("bartenders_preventa", category="preventa", depends_on=[])
class PreventaFlow(BaseFlow):
    """
    Flow de preventa: captura consulta y genera cotización con 3 opciones.
    Corre 4 agentes en secuencia. Sin pausas HITL.
    Tiempo estimado: 30-60 segundos.
    """

    def validate_input(self, input_data: dict) -> bool:
        required = ["fecha_evento", "provincia", "pax",
                    "duracion_horas", "tipo_menu", "localidad", "tipo_evento"]
        for field in required:
            if not input_data.get(field):
                self.logger.error("preventa.input.missing_field", field=field)
                return False

        pax = int(input_data.get("pax", 0))
        if not (10 <= pax <= 500):
            self.logger.error("preventa.input.pax_invalido", pax=pax)
            return False

        provincias_validas = {"Tucuman", "Salta", "Jujuy", "Catamarca"}
        if input_data.get("provincia") not in provincias_validas:
            self.logger.error("preventa.input.provincia_invalida",
                              provincia=input_data.get("provincia"))
            return False

        menus_validos = {"basico", "estandar", "premium"}
        if input_data.get("tipo_menu") not in menus_validos:
            self.logger.error("preventa.input.menu_invalido",
                              tipo_menu=input_data.get("tipo_menu"))
            return False

        return True

    async def _run_crew(self) -> dict:
        """Ejecuta la secuencia de agentes del flow (A1 → A2 → A3 → A4)."""
        # Los decoradores @start/@listen no se ejecutan automáticamente.
        # Hay que llamar manualmente a cada paso en secuencia.
        await self.cargar_input()
        await self.agente_1_requerimientos()
        await self.agente_2_clima()
        await self.agente_3_escandallo()
        await self.agente_4_cotizacion()

        return self.state.output_data or {}

    @start()
    async def cargar_input(self):
        """Carga el input al estado del flow."""
        data = self.state.input_data
        self.state.fecha_evento   = data["fecha_evento"]
        self.state.provincia      = data["provincia"]
        self.state.localidad      = data["localidad"]
        self.state.tipo_evento    = data["tipo_evento"]
        self.state.pax            = int(data["pax"])
        self.state.duracion_horas = int(data["duracion_horas"])
        self.state.tipo_menu      = data["tipo_menu"]
        self.state.restricciones  = data.get("restricciones", "")

        self.logger.info("preventa.input_cargado",
                         pax=self.state.pax,
                         tipo_menu=self.state.tipo_menu,
                         provincia=self.state.provincia)

    @listen(cargar_input)
    async def agente_1_requerimientos(self):
        """A1: valida datos y registra el evento en DB."""
        connector = SupabaseMockConnector(self.org_id, self.user_id)

        registro = _registrar_evento(connector, {
            "fecha_evento":   self.state.fecha_evento,
            "provincia":      self.state.provincia,
            "localidad":      self.state.localidad,
            "tipo_evento":    self.state.tipo_evento,
            "pax":            self.state.pax,
            "duracion_horas": self.state.duracion_horas,
            "tipo_menu":      self.state.tipo_menu,
            "restricciones":  self.state.restricciones,
        })

        self.state.evento_id = registro["evento_id"]
        self.state.update_tokens(self.state.estimate_tokens(registro))
        self.logger.info("preventa.a1.completado", evento_id=self.state.evento_id)
        await self.emit_event("preventa.evento_registrado",
                        {"evento_id": self.state.evento_id})

    @listen(agente_1_requerimientos)
    async def agente_2_clima(self):
        """A2: determina el factor climático histórico para el mes del evento."""
        connector = SupabaseMockConnector(self.org_id, self.user_id)
        mes       = int(self.state.fecha_evento.split("-")[1])

        config = connector.get_config_one("config_climatico", {"mes": mes})
        if config:
            self.state.factor_climatico_pct = int(config["factor_pct"])
            self.state.factor_razon         = config["razon"]
        else:
            self.state.factor_climatico_pct = 10  # default conservador
            self.state.factor_razon         = "Factor default (mes sin configuración)"

        self.logger.info("preventa.a2.completado",
                         mes=mes,
                         factor_pct=self.state.factor_climatico_pct)
        self.state.update_tokens(self.state.estimate_tokens(config if config else "default"))
        await self.emit_event("preventa.factor_climatico_determinado", {
            "mes":        mes,
            "factor_pct": self.state.factor_climatico_pct,
            "razon":      self.state.factor_razon,
        })

    @listen(agente_2_clima)
    async def agente_3_escandallo(self):
        """A3: calcula el escandallo de 4 bloques (determinista)."""
        from src.tools.bartenders.escandallo_tool import EscandalloTool
        connector = SupabaseMockConnector(self.org_id, self.user_id)
        tool      = EscandalloTool(connector=connector)

        resultado = tool._run(
            evento_id            = self.state.evento_id,
            pax                  = self.state.pax,
            duracion_horas       = self.state.duracion_horas,
            tipo_menu            = self.state.tipo_menu,
            provincia            = self.state.provincia,
            factor_climatico_pct = self.state.factor_climatico_pct,
        )

        self.state.escandallo_final    = resultado.escandallo_final
        self.state.escandallo_desglose = resultado.model_dump()

        self.logger.info("preventa.a3.completado",
                         escandallo=self.state.escandallo_final)
        self.state.update_tokens(self.state.estimate_tokens(resultado))
        await self.emit_event("preventa.escandallo_calculado", {
            "escandallo_final": self.state.escandallo_final,
            "bartenders":       resultado.bartenders_necesarios,
        })

    @listen(agente_3_escandallo)
    async def agente_4_cotizacion(self):
        """A4: genera las 3 opciones y persiste la cotización."""
        connector = SupabaseMockConnector(self.org_id, self.user_id)
        opciones  = _calcular_opciones(self.state.escandallo_final)

        cotizacion_id = _guardar_cotizacion(
            connector         = connector,
            evento_id         = self.state.evento_id,
            escandallo_total  = self.state.escandallo_final,
            opciones          = opciones,
            factor_climatico  = self.state.factor_climatico_pct,
        )

        self.state.cotizacion_id      = cotizacion_id
        self.state.opcion_basica      = opciones["basica"]
        self.state.opcion_recomendada = opciones["recomendada"]
        self.state.opcion_premium     = opciones["premium"]

        self.state.output_data = {
            "evento_id":          self.state.evento_id,
            "cotizacion_id":      cotizacion_id,
            "escandallo_total":   self.state.escandallo_final,
            "opcion_basica":      opciones["basica"],
            "opcion_recomendada": opciones["recomendada"],
            "opcion_premium":     opciones["premium"],
            "factor_climatico":   self.state.factor_climatico_pct,
            "bartenders_necesarios": self.state.escandallo_desglose.get(
                "bartenders_necesarios", 0
            ),
        }

        self.logger.info("preventa.a4.completado",
                         cotizacion_id=cotizacion_id,
                         recomendada=opciones["recomendada"])
        self.state.update_tokens(self.state.estimate_tokens(opciones))
        await self.emit_event("preventa.cotizacion_generada", {
            "cotizacion_id":     cotizacion_id,
            "opcion_recomendada":opciones["recomendada"],
        })
