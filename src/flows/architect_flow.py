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

from .base_flow import BaseFlow
from .state import BaseFlowState
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

        self.event_store = EventStore(
            self.org_id, 
            self.user_id, 
            correlation_id=self.state.correlation_id
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

        # ── 4. Resolver integraciones contra catálogo real ──────
        from .integration_resolver import IntegrationResolver
        
        resolver = IntegrationResolver(org_id=self.org_id)
        # SUPUESTO: El resolver trabaja con el diccionario del modelo
        resolution = await resolver.resolve(workflow_def.model_dump())
        
        if not resolution.is_ready:
            # ── 5. Buscar en registros externos si hay tools no encontradas ──
            if resolution.not_found:
                from ..mcp.registry_client import MCPRegistryClient
                registry = MCPRegistryClient()

                discovered = {}
                for tool_hint in resolution.not_found:
                    # Extraer keyword básica (ej: "google_sheets_read" -> "google")
                    search_query = tool_hint.replace("_", " ").split(".")[0]
                    try:
                        results = await registry.search(search_query)
                        if results:
                            discovered[tool_hint] = results
                    except Exception as e:
                        logger.warning("ArchitectFlow: Falló búsqueda en registry para '%s': %s", tool_hint, e)

                if discovered:
                    logger.info("ArchitectFlow: Se encontraron integraciones externas para %s", list(discovered.keys()))
                    return {
                        "status": "external_integrations_found",
                        "is_ready": False,
                        "resolution": {
                            "available": resolution.available,
                            "needs_activation": resolution.needs_activation,
                            "not_found": [t for t in resolution.not_found if t not in discovered],
                            "needs_credentials": resolution.needs_credentials,
                            "tool_mapping": resolution.tool_mapping,
                        },
                        "discovered": {
                            hint: [
                                {"name": s.name, "description": s.description, "url": s.url}
                                for s in servers
                            ]
                            for hint, servers in discovered.items()
                        },
                        "message": self._build_discovery_message(discovered),
                    }

            logger.warning("ArchitectFlow: Resolución incompleta para org %s", self.org_id)
            return self._build_resolution_response(resolution)

        # Aplicar mapeos (alucinada -> real)
        mapped_data = resolver.apply_mapping(workflow_def.model_dump(), resolution.tool_mapping)
        workflow_def = WorkflowDefinition(**mapped_data)

        # ── 5. Asegurar flow_type único global ──────────────────
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

        # ── 8. Inyectar catálogo de herramientas ────────────────
        svc = get_service_client()
        available_tools = svc.table("service_tools").select("id").limit(50).execute()
        tools_list = ", ".join([t["id"] for t in available_tools.data]) if available_tools.data else "Ninguna (alucina nombres descriptivos)"

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
8. TOOLS DISPONIBLES EN EL CATÁLOGO (USAR SOLO ESTAS SI ES POSIBLE):
   {tools_list}
   Si necesitás una que no está, usá el nombre más descriptivo posible.
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
        
        # Track tokens
        tokens = 0
        if hasattr(result, "token_usage") and result.token_usage:
            usage = result.token_usage
            tokens = usage.get("total_tokens", 0) if isinstance(usage, dict) else getattr(usage, "total_tokens", 0)
        elif hasattr(result, "usage_metrics") and result.usage_metrics:
            usage = result.usage_metrics
            tokens = usage.get("total_tokens", 0) if isinstance(usage, dict) else getattr(usage, "total_tokens", 0)
        
        if tokens:
            self.state.update_tokens(tokens)
        else:
            self.state.update_tokens(self.state.estimate_tokens(str(result)))

        return result

    def _parse_workflow_definition(self, raw_result: Any) -> WorkflowDefinition:
        """Extraer y validar JSON del resultado del agente."""
        import json

        # Manejar CrewOutput u otros tipos
        if hasattr(raw_result, "raw"):
            raw_text = str(raw_result.raw)
        else:
            raw_text = str(raw_result)

        logger.debug("ArchitectFlow: raw_text a parsear: %s", raw_text)

        # Buscar el bloque JSON { ... }
        json_match = re.search(r"(\{[\s\S]*\})", raw_text)
        if not json_match:
            raise ValueError(
                f"El agente no retornó un objeto JSON. Resultado: '{raw_text[:200]}...'"
            )

        raw_text = json_match.group(1).strip()

        if not raw_text:
            raise ValueError(f"El agente retornó un resultado vacío: '{raw_text}'")

        try:
            data = json.loads(raw_text)
            return WorkflowDefinition(**data)
        except json.JSONDecodeError as e:
            logger.error("Error parseando JSON: %s. Texto: %s", e, raw_text)
            raise ValueError(f"El agente retornó JSON inválido: {e}")
        except Exception as e:
            logger.error("Error validando WorkflowDefinition: %s. Data: %s", e, data if 'data' in dir() else 'N/A')
            raise ValueError(
                f"Validación de WorkflowDefinition falló: {e}\n"
                f"JSON recibido: {raw_text[:500]}"
            )

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

        if existing and existing.data:
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

    def _build_resolution_response(self, resolution: Any) -> Dict[str, Any]:
        """Construir respuesta diagnóstica cuando faltan integraciones o credenciales."""
        message_parts = ["No puedo finalizar la creación del workflow porque faltan dependencias técnicas:\n"]
        
        if resolution.needs_activation:
            message_parts.append("\nServicios que necesitan activación:")
            for svc in resolution.needs_activation:
                message_parts.append(f"  - {svc}: Debe ser habilitado en el Dashboard.")
        
        if resolution.needs_credentials:
            message_parts.append("\nCredenciales faltantes en Vault:")
            for secret in resolution.needs_credentials:
                message_parts.append(f"  - {secret}: Favor de configurar en /settings/vault.")
        
        if resolution.not_found:
            message_parts.append("\nHerramientas no encontradas en el catálogo:")
            for tool in resolution.not_found:
                message_parts.append(f"  - {tool}: El nombre no coincide con ninguna integración conocida.")

        if resolution.tool_mapping:
            message_parts.append("\nHerramientas mapeadas exitosamente:")
            for alucinada, real in resolution.tool_mapping.items():
                message_parts.append(f"  - \"{alucinada}\" -> \"{real}\" ✓")

        return {
            "status": "resolution_required",
            "is_ready": False,
            "resolution": {
                "needs_activation": resolution.needs_activation,
                "needs_credentials": resolution.needs_credentials,
                "not_found": resolution.not_found,
                "tool_mapping": resolution.tool_mapping,
            },
            "message": "\n".join(message_parts),
        }

    def _build_discovery_message(self, discovered: Dict[str, Any]) -> str:
        """Construir mensaje para el usuario cuando se encuentran integraciones externas."""
        parts = ["No encontré algunas herramientas en tu catálogo local, pero encontré estas opciones externas:\n"]
        
        for hint, servers in discovered.items():
            parts.append(f"\nPara '{hint}':")
            for i, srv in enumerate(servers[:3], 1):
                parts.append(f"  {i}. {srv.name} ({srv.url})")
                if srv.description:
                    desc = srv.description[:100] + "..." if len(srv.description) > 100 else srv.description
                    parts.append(f"     > {desc}")
        
        parts.append("\n¿Deseas que intente importar alguna de estas integraciones?")
        return "\n".join(parts)
