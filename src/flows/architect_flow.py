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
  6. complete → Retorna definición JSON para empaquetado como Bundle
"""

from __future__ import annotations

import json
import logging
import uuid
from typing import Any, Dict, Optional

from crewai import Agent, Crew, Process, Task

from src.db.session import get_service_client, get_tenant_client
from src.flows.base_flow import BaseFlow
from src.flows.state import BaseFlowState
from src.utils.llm_parsing import extract_json_from_text, extract_token_usage

from ..services.bundle_manager import BundleManager, BundleManifest
from .registry import register_flow
from .workflow_definition import WorkflowDefinition
from .workflow_guardrails import WorkflowValidationError, validate_workflow

logger = logging.getLogger(__name__)


class ArchitectState(BaseFlowState):
    """Estado del ArchitectFlow."""

    flow_type: str = "architect"
    extracted_definition: Optional[WorkflowDefinition] = None
    workflow_template_id: Optional[str] = None
    agents_created: list[str] = []


@register_flow("architect_flow", category="system")
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

        from ..events.store import EventStore

        task_id = str(uuid4())

        with get_tenant_client(self.org_id, self.user_id) as db:
            db.table("tasks").insert(
                {
                    "id": task_id,
                    "org_id": self.org_id,
                    "flow_type": "architect_flow",
                    "flow_id": task_id,
                    "status": "pending",
                    "payload": input_data,
                    "correlation_id": correlation_id,
                }
            ).execute()

        self.state = ArchitectState(
            task_id=task_id,
            org_id=self.org_id,
            user_id=self.user_id,
            flow_type="architect_flow",
            input_data=input_data,
            correlation_id=correlation_id,
        )

        self.event_store = EventStore(
            self.org_id, self.user_id, correlation_id=self.state.correlation_id
        )
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

        # 5. Generate ZIP Bundle (Roadmap T15.4)
        bm = BundleManager(org_id=self.org_id)
        manifest = BundleManifest(
            name=workflow_def.name,
            version="1.0.0",
            description=workflow_def.description,
            author="SYSTEM-GENERATED", # Identifica que fue creado por el Architect
            flows=[safe_flow_type],
            agents=[a.role for a in workflow_def.agents],
            skills=[]
        )

        bundle_zip = bm.create_bundle(
            manifest=manifest,
            agents=[a.model_dump() for a in workflow_def.agents],
            flows=[{
                "flow_type": safe_flow_type,
                "is_python": False,
                "code_source": json.dumps(workflow_def.model_dump())
            }],
            skills={}
        )

        import base64
        bundle_b64 = base64.b64encode(bundle_zip).decode("utf-8")

        logger.info(
            "ArchitectFlow[%s] generated definition and ZIP bundle for workflow '%s'",
            self.state.task_id,
            safe_flow_type,
        )

        return {
            "flow_type": safe_flow_type,
            "definition": workflow_def.model_dump(),
            "agents": [a.model_dump() for a in workflow_def.agents],
            "steps_count": len(workflow_def.steps),
            "bundle_b64": bundle_b64,
            "message": (
                f"Workflow '{workflow_def.name}' generated exitosamente. "
                "The ZIP bundle is included in 'bundle_b64'. "
                "Para activarlo, impórtelo vía POST /api/bundles/import"
            ),
        }


    async def _execute_architect_agent(self, description: str) -> Any:
        """Ejecutar el agente Architect que produce la definición."""
        from src.config import get_settings
        from src.flows.workflow_guardrails import ALLOWED_MODELS

        settings = get_settings()
        llm = settings.get_llm()

        allowed_models = ", ".join(ALLOWED_MODELS)

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
Analiza esta descripción y produce UNICAMENTE un objeto JSON sin ningún texto adicional.

DESCRIPCIÓN DEL USUARIO:
{description}

SCHEMA EXACTO A SEGUIR ( WorkflowDefinition ):
{{
  "name": "string, min 3 caracteres, nombre descriptivo del workflow",
  "description": "string, min 10 caracteres, explicación detallada",
  "flow_type": "string, snake_case, minúsculas, min 3 caracteres, único globalmente",
  "steps": [
    {{
      "id": "string, identificador único del paso (ej: 'step_1')",
      "name": "string, nombre del paso",
      "description": "string, min 10 caracteres, qué hace este paso",
      "agent_role": "string, debe coincidir exactamente con un role en agents[]",
      "depends_on": [array de strings o null, ids de pasos anteriores de los que depende],
      "requires_approval": boolean, false por defecto
    }}
  ],
  "agents": [
    {{
      "role": "string, identificador único del agente (ej: 'redactor')",
      "goal": "string, min 10 caracteres, objetivo del agente",
      "backstory": "string, min 10 caracteres, trasfondo del agente",
      "allowed_tools": [array de strings, puede estar vacío []],
      "rules": [array de strings, puede estar vacío []],
      "model": "string, uno de: {allowed_models}",
      "max_iter": integer, entre 1 y 5 inclusive
    }}
  ],
  "approval_rules": [
    {{
      "condition": "string, expresión booleana (ej: 'monto > 5000')",
      "description": "string, explicación de la regla"
    }}
  ]
}}

REGLAS CRÍTICAS - EL JSON DEBE CUMPLIRLAS ESTRICTAMENTE:
1. 'flow_type' debe ser snake_case (solo minúsculas, números y guiones bajos)
2. Todo 'agent_role' en 'steps' DEBE existir exactamente en 'agents[].role'
3. El grafo de 'depends_on' no debe tener ciclos (sin dependencias circulares)
4. 'steps' y 'agents' deben tener al menos 1 elemento cada uno
5. El campo 'model' DEBE ser uno de los valores permitidos listados arriba
6. NO agregues campos extra que no estén en el schema
7. Responde SOLO con el objeto JSON, sin markdown, sin backticks, sin texto explicativo
""",
            expected_output="Un objeto JSON puro que cumpla exactamente con el schema de WorkflowDefinition.",
            agent=architect,
        )

        crew = Crew(
            agents=[architect],
            tasks=[task],
            process=Process.sequential,
            verbose=True,
        )

        result = await crew.kickoff_async(inputs={})

        # Track tokens using helper
        tokens = extract_token_usage(result)

        if tokens:
            self.state.update_tokens(tokens)
        else:
            self.state.update_tokens(self.state.estimate_tokens(str(result)))

        return result

    def _parse_workflow_definition(self, raw_result: Any) -> WorkflowDefinition:
        """Extraer y validar JSON del resultado del agente usando helper modular."""
        # Manejar CrewOutput u otros tipos
        raw_text = raw_result.raw if hasattr(raw_result, "raw") else str(raw_result)
        logger.debug("ArchitectFlow: raw_text a parsear: %s", raw_text)

        data = extract_json_from_text(raw_text)
        if not data:
            raise ValueError(
                f"JSON inválido: El agente no retornó un objeto JSON procesable. Resultado: '{raw_text[:200]}...'"
            )

        try:
            return WorkflowDefinition(**data)
        except Exception as e:
            logger.error("Error validando WorkflowDefinition: %s. Data: %s", e, data)
            raise ValueError(
                f"Validación de WorkflowDefinition falló: {e}\n"
                f"JSON recibido: {json.dumps(data, indent=2)[:500]}"
            )

    def _ensure_unique_flow_type(self, flow_type: str) -> str:
        """Si flow_type ya existe globalmente, buscar uno libre con sufijo basado en org_id."""
        svc = get_service_client()
        current_name = flow_type
        attempts = 0

        while attempts < 5:
            existing = (
                svc.table("workflow_templates")
                .select("id")
                .eq("flow_type", current_name)
                .maybe_single()
                .execute()
            )

            if not (existing and existing.data):
                return current_name

            # Si ya existe, generar nuevo nombre con sufijo derivado del org_id
            # Esto ayuda a la colisión entre orgs manteniendo legibilidad
            org_suffix = self.org_id.replace("-", "")[:8]
            import random
            import string

            random_suffix = "".join(
                random.choices(string.ascii_lowercase + string.digits, k=4)
            )
            current_name = f"{flow_type}_{org_suffix}_{random_suffix}"
            attempts += 1
            logger.warning("flow_type ocupado, reintentando con '%s'", current_name)

        return f"{flow_type}_{uuid.uuid4().hex[:8]}"
