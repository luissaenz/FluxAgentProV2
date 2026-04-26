"""AgentWizardFlow — Interactive step-by-step agent profile builder.

Collects:
1. Name + Goal
2. Input Schema
3. Internal Process
4. Output Schema
5. Required Credentials
"""

from __future__ import annotations

import logging
import asyncio
import json
from typing import Any, Dict, Optional, List, ClassVar
from pydantic import Field

from .base_flow import BaseFlow, with_error_handling
from .state import BaseFlowState, FlowStatus
from .registry import register_flow
from ..db.session import get_tenant_client
from ..config import get_settings
from crewai import LLM

logger = logging.getLogger(__name__)


class AgentWizardState(BaseFlowState):
    """State for the Agent Wizard."""
    current_step: int = 0
    collected_data: Dict[str, Any] = Field(default_factory=dict)
    
    # Steps definition (ClassVar to avoid Pydantic field error)
    STEPS: ClassVar[List[str]] = [
        "Nombre y Objetivo del Agente (ej: 'Analista de Ventas - Extraer KPIs')",
        "Datos de Entrada (¿Qué información recibirá para trabajar? ej: JSON de facturas)",
        "Proceso (Instrucciones lógicas paso a paso para el agente)",
        "Datos de Salida y Formato (¿Qué debe entregar y en qué estructura?)",
        "Credenciales Necesarias (Listado de tokens o llaves requeridas)",
    ]


@register_flow("agent_wizard", category="system", description="Wizard interactivo para crear agentes")
class AgentWizardFlow(BaseFlow):
    """
    Flow interactivo que guía al usuario en la creación de un perfil de agente.
    Usa el sistema de aprobaciones para recibir feedback (HITL).
    """

    def validate_input(self, input_data: Dict[str, Any]) -> bool:
        return True

    @property
    def state_class(self):
        return AgentWizardState

    @with_error_handling
    async def execute(
        self,
        input_data: Dict[str, Any],
        correlation_id: Optional[str] = None,
    ) -> AgentWizardState:
        """Inicializar el wizard."""
        if self.state is None:
            await self.create_task_record(input_data, correlation_id)
        
        self.state.start()
        await self.persist_state()
        
        # Iniciar primer paso
        await self._ask_current_step()
        return self.state

    async def _ask_current_step(self) -> None:
        """Solicitar información para el paso actual."""
        step_idx = self.state.current_step
        if step_idx >= len(AgentWizardState.STEPS):
            await self._finalise()
            return

        question = AgentWizardState.STEPS[step_idx]
        logger.info("Wizard Step %d: %s", step_idx, question)
        
        # Define específicos para el primer paso si es necesario
        fields = None
        if step_idx == 0:
            fields = [
                {"id": "agent_name", "label": "Nombre del Agente", "type": "text", "placeholder": "ej: Analista de Ventas"},
                {"id": "agent_goal", "label": "Objetivo del Agente", "type": "textarea", "placeholder": "ej: Extraer KPIs de facturas PDF y guardarlos en Excel"}
            ]
        
        await self.request_approval(
            description=question,
            payload={
                "step": step_idx,
                "question": question,
                "fields": fields,
                "progress": f"{step_idx + 1}/{len(AgentWizardState.STEPS)}",
                "current_data": self.state.collected_data
            }
        )

    async def _on_approved(self) -> None:
        """Manejador de la respuesta del usuario (Aprobación = Siguiente Paso)."""
        # 1. Recuperar la respuesta de las notas
        answer = getattr(self.state, "last_notes", "")
        step_idx = self.state.current_step
        
        if not answer or answer.strip() == "":
            logger.warning("Respuesta vacía en paso %d, reintentando pregunta", step_idx)
            # Podríamos volver a preguntar o fallar. Aquí reintentamos.
            await self._ask_current_step()
            return

        # 2. Refinamiento Inteligente para el Paso 3 (Proceso)
        if step_idx == 2:
            logger.info("Refinando proceso del agente con LLM...")
            answer = await self._refine_process_with_llm(answer)

        # 3. Guardar la respuesta en el estado
        step_keys = ["name_goal", "inputs", "process", "outputs", "credentials"]
        current_key = step_keys[step_idx]
        
        try:
            # Intentar parsear como JSON si viene del formulario dinámico
            parsed = json.loads(answer)
            if isinstance(parsed, dict):
                for k, v in parsed.items():
                    self.state.collected_data[k] = v
                # Compatibilidad con el campo antiguo name_goal
                if "agent_name" in parsed and "agent_goal" in parsed:
                    self.state.collected_data["name_goal"] = f"{parsed['agent_name']} - {parsed['agent_goal']}"
            else:
                self.state.collected_data[current_key] = answer
        except (json.JSONDecodeError, TypeError):
            # Fallback a texto plano
            self.state.collected_data[current_key] = answer
        
        
        # 4. Avanzar paso
        self.state.current_step += 1
        self.state.status = FlowStatus.RUNNING
        await self.persist_state()
        
        # 5. Ir al siguiente o finalizar
        await self._ask_current_step()

    async def _refine_process_with_llm(self, raw_process: str) -> str:
        """
        Usa un LLM para intentar convertir el proceso en instrucciones determinísticas.
        Si no es posible, genera una versión refinada de 'agente libre'.
        """
        settings = get_settings()
        llm = LLM(
            model=settings.groq_model,
            temperature=0.2,
            max_completion_tokens=1000,
            api_key=settings.groq_api_key,
        )

        system_prompt = (
            "Eres un experto en ingeniería de prompts y diseño de flujos de agentes de FluxAgentPro.\n"
            "Tu objetivo es convertir las instrucciones de un usuario para un agente en un 'PROCESO DETERMINÍSTICO' si es posible.\n"
            "Un proceso determinístico es una secuencia lógica, estructurada y sin ambigüedades (paso 1, paso 2, condicionales, etc.) que un agente puede seguir mecánicamente.\n"
            "Si las instrucciones son demasiado vagas, creativas o abstractas para ser determinísticas, genera una versión optimizada de 'AGENTE LIBRE' (instrucciones claras, profesionales y potentes pero flexibles).\n\n"
            "REGLAS:\n"
            "1. Analiza el texto del usuario.\n"
            "2. Si detectas una secuencia lógica o pasos claros, estructúrala como 'PROCESO DETERMINÍSTICO'.\n"
            "3. Si detectas algo muy abierto, estructúralo como 'AGENTE LIBRE'.\n"
            "4. Responde en español.\n"
            "5. NO incluyas preámbulos ni explicaciones extras. Responde solo con el proceso refinado."
        )

        loop = asyncio.get_running_loop()
        try:
            # Ejecutar en thread pool para no bloquear el event loop (crewai.LLM.call es síncrono)
            response = await loop.run_in_executor(
                None,
                lambda: llm.call(messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": raw_process},
                ]),
            )
            
            if isinstance(response, str) and response.strip():
                logger.info("Proceso refinado exitosamente.")
                return response.strip()
            
            return raw_process
        except Exception as exc:
            logger.error("Error refinando proceso con LLM: %s", exc)
            return raw_process

    async def _finalise(self) -> None:
        """Guardar el agente en el catálogo y finalizar."""
        data = self.state.collected_data
        
        # Extraer rol del nombre (fallback simple)
        full_name = data.get("name_goal", "unknown")
        role = full_name.split("-")[0].strip().lower().replace(" ", "_")
        
        with get_tenant_client(self.org_id, self.user_id) as db:
            db.table("agent_catalog").upsert({
                "org_id": self.org_id,
                "role": role,
                "soul_json": {
                    "role": role,
                    "name": data.get("agent_name", role),
                    "goal": data.get("agent_goal", data.get("name_goal")),
                    "backstory": data.get("process"),
                    "input_contract": data.get("inputs"),
                    "output_contract": data.get("outputs"),
                },
                "is_active": True,
            }, on_conflict="org_id,role").execute()

        result = {
            "message": "Agente creado exitosamente",
            "agent_role": role,
            "summary": data
        }
        self.state.complete(result)
        await self.emit_event("agent_wizard.completed", result)
        await self.persist_state()
        logger.info("AgentWizardFlow[%s] finalizado. Agente '%s' creado.", self.state.task_id, role)

    async def _run_crew(self) -> Dict[str, Any]:
        """No usado directamente en este flow HITL."""
        return self.state.output_data
