"""src/flows/architect_flow.py — Genera workflows desde lenguaje natural.

Pattern confirmado con el código real de Fases 1-3:
- Hereda de BaseFlow (lifecycle-based)
- Override de create_task_record para usar ArchitectState
- WorkflowDefinition como output_pydantic del agente Architect
- Validación con workflow_guardrails antes de persistir
- Registro dinámico en FLOW_REGISTRY

Flujo:
  1. validate_input
  2. create_task_record
  3. _run_crew → Ejecuta agente Architect
  4. _parse_and_validate → WorkflowDefinition (Pydantic)
  5. validate_workflow → seguridad + quota
  6. _persist_template → workflow_templates
  7. _persist_agents → agent_catalog
  8. _register_dynamic_flow → FLOW_REGISTRY
  9. complete
"""

from __future__ import annotations

import re
import uuid
import logging
from typing import Any, Dict, Optional

from crewai import Agent, Crew, Process, Task

from .base_flow import BaseFlow, with_error_handling
from .state import BaseFlowState, FlowStatus
from .registry import register_flow
from .workflow_definition import WorkflowDefinition
from .workflow_guardrails import validate_workflow, WorkflowValidationError
from ..db.session import get_tenant_client, get_service_client

logger = logging.getLogger(__name__)


class ArchitectState(BaseFlowState):
    """Estado del ArchitectFlow."""
    flow_type: str = "architect"
    extracted_definition: Optional[WorkflowDefinition] = None
    workflow_template_id: Optional[str] = None
    agents_created: list[str] = []


@register_flow("architect_flow")
class ArchitectFlow(BaseFlow):
    """
    Flow conversacional que genera nuevos workflows desde NL.

    Input: {"description": "...", "conversation_id": "..."}
    Output: {"flow_type": "...", "template_id": "...", "agents_created": [...]}

    Critico: este flow NO debe hacer await de request_approval
    para pausar — el usuario genera workflows, no los ejecuta.
    """

    def validate_input(self, input_data: Dict[str, Any]) -> bool:
        if "description" not in input_data:
            logger.error("Falta 'description' en input_data")
            return False
        if not isinstance(input_data["description"], str):
            logger.error("'description' debe ser string")
            return False
        if len(input_data["description"].strip()) < 10:
            logger.error("'description' demasiado corta")
            return False
        return True

    async def create_task_record(
        self,
        input_data: Dict[str, Any],
        correlation_id: Optional[str] = None,
    ) -> None:
        """Override para usar ArchitectState."""
        from uuid import uuid4
        from ..db.session import get_tenant_client
        from ..events.store import EventStore

        task_id = str(uuid4())

        with get_tenant_client(self.org_id, self.user_id) as db:
            db.table("tasks").insert({
                "id": task_id,
                "org_id": self.org_id,
                "flow_type": "architect_flow",
                "flow_id": task_id,
                "status": "pending",
                "payload": input_data,
                "correlation_id": correlation_id,
            }).execute()

        self.state = ArchitectState(
            task_id=task_id,
            org_id=self.org_id,
            user_id=self.user_id,
            flow_type="architect_flow",
            input_data=input_data,
            correlation_id=correlation_id,
        )

        self.event_store = EventStore(self.org_id, self.user_id)
        await self.emit_event("flow.created", {"input_data": input_data})

    async def _run_crew(self) -> Dict[str, Any]:
        """
        Ejecutar el ciclo completo de generación.

        El agente Architect recibe la descripción NL y produce un JSON.
        Ese JSON se valida con WorkflowDefinition (Pydantic).
        """
        description = self.state.input_data.get("description", "")

        # ── 1. Ejecutar agente Architect ─────────────────────────
        raw_result = await self._execute_architect_agent(description)

        # ── 2. Parsear a WorkflowDefinition ─────────────────────
        workflow_def = self._parse_workflow_definition(raw_result)
        self.state.extracted_definition = workflow_def

        # ── 3. Validación de seguridad + quota ─────────────────
        try:
            validate_workflow(workflow_def, org_id=self.org_id)
        except WorkflowValidationError as e:
            raise ValueError(f"Workflow inválido: {e}")

        # ── 4. Asegurar flow_type único global ──────────────────
        safe_flow_type = self._ensure_unique_flow_type(workflow_def.flow_type)
        workflow_def.flow_type = safe_flow_type

        # ── 5. Persistir template ──────────────────────────────
        template_id = await self._persist_template(workflow_def)
        self.state.workflow_template_id = template_id

        # ── 6. Persistir agentes ────────────────────────────────
        agents_created = await self._persist_agents(workflow_def)
        self.state.agents_created = agents_created

        # ── 7. Registrar dinámicamente ─────────────────────────
        self._register_dynamic_flow(safe_flow_type, workflow_def)

        logger.info(
            "ArchitectFlow[%s] creó workflow '%s' con %d agentes",
            self.state.task_id, safe_flow_type, len(agents_created)
        )

        return {
            "flow_type": safe_flow_type,
            "template_id": template_id,
            "agents_created": agents_created,
            "steps_count": len(workflow_def.steps),
            "message": (
                f"Workflow '{workflow_def.name}' creado. "
                f"Ejecutalo con POST /webhooks/{self.org_id}/{safe_flow_type}"
            ),
        }

    async def _execute_architect_agent(self, description: str) -> Any:
        """Ejecutar el agente Architect que produce la definición."""
        from src.config import get_settings

        settings = get_settings()
        llm = settings.get_llm()

        architect = Agent(
            role="Workflow Architect",
            goal=(
                "Analizar la descripción NL y producir una definición de "
                "workflow válida como JSON estructurado."
            ),
            backstory=(
                "Eres un arquitecto de sistemas especializado en transformar "
                "requisitos de negocio en workflows ejecutables por agentes IA."
            ),
            verbose=True,
            allow_delegation=False,
            llm=llm,
            max_iter=5,
        )

        task = Task(
            description=f"""
Analiza esta descripción y produce un WorkflowDefinition JSON válido:

DESCRIPCIÓN DEL USUARIO:
{description}

REGLAS:
- flow_type: snake_case, minúsculas, único globalmente (ej: "invoice_approval_v2")
- Cada step debe referenciar un agent_role que exista en la lista agents
- Dependencias entre steps no deben formar ciclos (DAG)
- max_iter de cada agente ≤ 5
- Solo modelos permitidos: claude-sonnet-4-20250514, gpt-4o, groq/llama-3.3-70b-versatile

Responde SOLO con JSON válido, sin markdown ni explicación.
""",
            expected_output="JSON del WorkflowDefinition",
            agent=architect,
        )

        crew = Crew(
            agents=[architect],
            tasks=[task],
            process=Process.sequential,
            verbose=True,
        )

        return await crew.kickoff_async(inputs={})

    def _parse_workflow_definition(self, raw_result: Any) -> WorkflowDefinition:
        """Extraer y validar JSON del resultado del agente."""
        import json

        raw_text = str(raw_result.raw if hasattr(raw_result, "raw") else raw_result)

        # Limpiar markdown code blocks
        raw_text = re.sub(r"```json\s*", "", raw_text)
        raw_text = re.sub(r"```\s*$", "", raw_text)
        raw_text = raw_text.strip()

        try:
            data = json.loads(raw_text)
            return WorkflowDefinition(**data)
        except json.JSONDecodeError as e:
            raise ValueError(f"El agente retornó JSON inválido: {e}")
        except Exception as e:
            raise ValueError(f"Validación de WorkflowDefinition falló: {e}")

    def _ensure_unique_flow_type(self, flow_type: str) -> str:
        """Si flow_type ya existe globalmente, agregar sufijo."""
        svc = get_service_client()

        existing = (
            svc.table("workflow_templates")
            .select("id")
            .eq("flow_type", flow_type)
            .maybe_single()
            .execute()
        )

        if existing.data:
            suffix = self.org_id.replace("-", "")[:8]
            safe = f"{flow_type}_{suffix}"
            logger.warning(
                "flow_type '%s' ya existe, usando '%s'", flow_type, safe
            )
            return safe

        return flow_type

    async def _persist_template(
        self, workflow_def: WorkflowDefinition
    ) -> str:
        """Insertar workflow_templates y retornar el ID."""
        conversation_id = self.state.input_data.get("conversation_id")
        template_id = str(uuid.uuid4())

        with get_tenant_client(self.org_id, self.state.user_id) as db:
            db.table("workflow_templates").insert({
                "id": template_id,
                "org_id": self.org_id,
                "name": workflow_def.name,
                "description": workflow_def.description,
                "flow_type": workflow_def.flow_type,
                "definition": workflow_def.model_dump(),
                "version": 1,
                "status": "active",
                "is_validated": True,
                "is_active": True,
                "created_by": "architect_flow",
                "conversation_id": conversation_id,
            }).execute()

        return template_id

    async def _persist_agents(
        self, workflow_def: WorkflowDefinition
    ) -> list[str]:
        """Insertar agentes en agent_catalog (upsert). Retorna roles creados."""
        created = []

        with get_tenant_client(self.org_id, self.state.user_id) as db:
            for agent_def in workflow_def.agents:
                existing = (
                    db.table("agent_catalog")
                    .select("id")
                    .eq("org_id", self.org_id)
                    .eq("role", agent_def.role)
                    .maybe_single()
                    .execute()
                )

                action = "skipped" if existing.data else "created"

                db.table("agent_catalog").upsert({
                    "org_id": self.org_id,
                    "name": agent_def.role,
                    "role": agent_def.role,
                    "soul_json": {
                        "role": agent_def.role,
                        "goal": agent_def.goal,
                        "backstory": agent_def.backstory,
                        "rules": agent_def.rules,
                    },
                    "allowed_tools": agent_def.allowed_tools,
                    "model": agent_def.model,
                    "max_iter": agent_def.max_iter,
                    "is_active": True,
                }, on_conflict="org_id,role").execute()

                if action == "created":
                    created.append(agent_def.role)

        return created

    def _register_dynamic_flow(
        self, flow_type: str, workflow_def: WorkflowDefinition
    ) -> None:
        """Registrar el workflow generado dinámicamente en FLOW_REGISTRY."""
        from .dynamic_flow import DynamicWorkflow

        DynamicWorkflow.register(
            flow_type=flow_type,
            definition=workflow_def.model_dump(),
        )
        logger.info("DynamicFlow '%s' registrado en FLOW_REGISTRY", flow_type)
