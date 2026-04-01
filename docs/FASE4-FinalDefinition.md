# Fase 4 — Diseño Conversacional (Generador de Flows)

> **Definición cerrada.** Basada en el código real de Fases 1-3 ya implementado.
> Todo el código propuesto es consistente con los patterns existentes.

---

## Visión del sistema

Un endpoint conversacional permite al usuario describir en lenguaje natural qué
automatización necesita. Un agente especializado ("Architect") extrae la estructura
del workflow y lo persiste en `workflow_templates`. El workflow queda
inmediatamente disponible para ejecución via `POST /webhooks/{org_id}/{flow_type}`.

El sistema soporta el ciclo completo: describir → previsualizar → confirmar →
ejecutar. Los workflows generados se ejecutan con el mismo `BaseFlow` lifecycle
que los workflows hand-coded.

---

## Criterio de éxito

Un workflow generado por chat se ejecuta exitosamente via `POST /webhooks/{org_id}/{flow_type}`
sin necesidad de reiniciar el servidor ni escribir código.

---

## 01 — Stack tecnológico

No se requieren dependencias nuevas. Fase 4 usa exclusivamente lo de Fases 1-3:

- `crewai` — agente Architect
- `supabase`, `psycopg2-binary` — base de datos
- `fastapi`, `pydantic` — API
- `structlog` — logging

---

## 02 — Estructura del proyecto

```
project/
├── src/
│   ├── flows/
│   │   ├── base_flow.py              # existente
│   │   ├── generic_flow.py           # existente
│   │   ├── multi_crew_flow.py        # existente
│   │   ├── architect_flow.py          # ⭐ NUEVO
│   │   ├── workflow_definition.py      # ⭐ NUEVO: modelos de validación
│   │   └── registry.py               # existente
│   │
│   ├── crews/
│   │   ├── base_crew.py              # existente
│   │   └── architect_crew.py         # ⭐ NUEVO: agente Architect
│   │
│   ├── db/
│   │   ├── session.py               # existente
│   │   ├── vault.py                 # existente
│   │   ├── memory.py               # existente
│   │   └── conversation_store.py    # ⭐ NUEVO
│   │
│   ├── guardrails/
│   │   ├── base_guardrail.py       # existente: make_approval_check, check_quota
│   │   └── workflow_guardrails.py  # ⭐ NUEVO: validación de workflows
│   │
│   ├── api/
│   │   ├── main.py                  # existente (registrar routers nuevos)
│   │   └── routes/
│   │       ├── webhooks.py          # existente
│   │       ├── chat.py             # ⭐ NUEVO: endpoint conversacional
│   │       └── workflows.py        # ⭐ NUEVO: CRUD de templates
│   │
│   └── config.py                    # existente
│
├── sql/
│   └── (migrations nuevas abajo)
│
└── tests/
    ├── unit/
    │   └── test_workflow_definition.py   # ⭐ NUEVO
    └── integration/
        └── test_architect_flow.py       # ⭐ NUEVO
```

---

## 03 — Base de datos

### sql/006_workflow_templates.sql

```sql
-- Migration 006: Workflow Templates (Phase 4)
--   Almacena workflows generados por el Architect.
--   Un workflow_template puede ser instanciado múltiples veces.
-- ============================================================

CREATE TABLE workflow_templates (
  id                        UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  org_id                    UUID NOT NULL REFERENCES organizations(id)
                                                       ON DELETE CASCADE,

  -- Identificación
  name                      TEXT NOT NULL,
  description               TEXT,
  flow_type                 TEXT NOT NULL,  -- identificador único GLOBAL

  -- Definición estructurada (Schema en workflow_definition.py)
  definition                JSONB NOT NULL DEFAULT '{}',
  -- Estructura:
  -- {
  --   "name": str,
  --   "description": str,
  --   "steps": [ { "id", "name", "agent_role", "description", "depends_on", "requires_approval", "approval_threshold" } ],
  --   "agents": [ { "role", "goal", "backstory", "allowed_tools", "model", "max_iter" } ],
  --   "approval_rules": [ { "condition", "description" } ]
  -- }

  -- Versionado
  version                   INT DEFAULT 1,

  -- Auditoría
  created_by                TEXT,      -- "architect_flow", "user:uuid"
  conversation_id           UUID,      -- referencia a conversations
  is_validated              BOOLEAN DEFAULT FALSE,
  status                    TEXT DEFAULT 'draft'
                                              CHECK (status IN ('draft','active','archived')),

  -- Métricas
  execution_count           INT DEFAULT 0,
  last_executed            TIMESTAMPTZ,

  is_active                BOOLEAN DEFAULT TRUE,
  created_at              TIMESTAMPTZ DEFAULT now(),
  updated_at              TIMESTAMPTZ DEFAULT now()
);

-- flow_type es único GLOBAL (webhooks lo usan como path: /webhooks/{org_id}/{flow_type})
CREATE UNIQUE INDEX idx_workflow_templates_flow_type
  ON workflow_templates(flow_type);

CREATE INDEX idx_workflow_templates_org_active
  ON workflow_templates(org_id)
  WHERE is_active = TRUE;

ALTER TABLE workflow_templates ENABLE ROW LEVEL SECURITY;

CREATE POLICY "tenant_isolation" ON workflow_templates
  FOR ALL USING (org_id::text = current_setting('app.org_id', TRUE));
```

### sql/007_conversations.sql

```sql
-- Migration 007: Conversations (Phase 4)
--   Persiste el historial de chat del Architect.
-- ============================================================

CREATE TABLE conversations (
  id                        UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  org_id                    UUID NOT NULL REFERENCES organizations(id)
                                                       ON DELETE CASCADE,
  user_id                   TEXT,
  workflow_template_id      UUID REFERENCES workflow_templates(id),
  status                    TEXT DEFAULT 'in_progress'
                                              CHECK (status IN ('in_progress','completed','failed')),
  metadata                  JSONB DEFAULT '{}',
  created_at                TIMESTAMPTZ DEFAULT now(),
  updated_at                TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE conversation_messages (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  conversation_id UUID NOT NULL REFERENCES conversations(id)
                                                 ON DELETE CASCADE,
  role            TEXT NOT NULL CHECK (role IN ('user', 'assistant', 'system')),
  content         TEXT NOT NULL,
  created_at      TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX idx_conversations_org_status
  ON conversations(org_id, status);
CREATE INDEX idx_conversation_messages_conv
  ON conversation_messages(conversation_id);

ALTER TABLE conversations ENABLE ROW LEVEL SECURITY;
ALTER TABLE conversation_messages ENABLE ROW LEVEL SECURITY;

CREATE POLICY "conv_tenant_isolation" ON conversations
  FOR ALL USING (org_id::text = current_setting('app.org_id', TRUE));

CREATE POLICY "conv_msg_tenant_isolation" ON conversation_messages
  FOR ALL USING (
    EXISTS (
      SELECT 1 FROM conversations c
      WHERE c.id = conversation_messages.conversation_id
        AND c.org_id::text = current_setting('app.org_id', TRUE)
    )
  );
```

---

## 04 — Modelos de validación

### src/flows/workflow_definition.py

```python
"""src/flows/workflow_definition.py — Modelos Pydantic para workflows generados.

Validation order:
1. Pydantic field validators (types, ranges)
2. model_validator: cross-field consistency (agent roles, cycles)
"""

from __future__ import annotations

from pydantic import BaseModel, Field, field_validator, model_validator
from typing import Optional


class AgentDefinition(BaseModel):
    """Definición de un agente dentro de un workflow."""
    role: str = Field(..., min_length=1, max_length=100)
    goal: str = Field(..., min_length=10)
    backstory: str = Field(..., min_length=10)
    allowed_tools: list[str] = Field(default_factory=list)
    rules: list[str] = Field(default_factory=list)
    model: str = "claude-sonnet-4-20250514"
    max_iter: int = Field(default=5, ge=1, le=10)

    @field_validator("model")
    @classmethod
    def model_must_be_allowed(cls, v: str) -> str:
        from src.flows.workflow_guardrails import ALLOWED_MODELS
        if v not in ALLOWED_MODELS:
            raise ValueError(f"Modelo '{v}' no permitido. Usar uno de: {ALLOWED_MODELS}")
        return v


class StepDefinition(BaseModel):
    """Definición de un paso dentro de un workflow."""
    id: str = Field(..., min_length=1)
    name: str = Field(..., min_length=1)
    description: str = Field(..., min_length=10)
    agent_role: str
    depends_on: Optional[list[str]] = None
    requires_approval: bool = False
    approval_threshold: Optional[str] = None


class ApprovalRule(BaseModel):
    """Regla de aprobación."""
    condition: str  # ej: "monto > 50000"
    description: str


class WorkflowDefinition(BaseModel):
    """
    Estructura completa de un workflow generado por el Architect.

    Es el output_pydantic del agente Architect:
    si el JSON no valida contra este schema, CrewAI reintenta automáticamente.
    """
    name: str = Field(..., min_length=3, max_length=100)
    description: str = Field(..., min_length=10)
    flow_type: str = Field(..., min_length=3, max_length=50)
    steps: list[StepDefinition] = Field(..., min_length=1)
    agents: list[AgentDefinition] = Field(..., min_length=1)
    approval_rules: list[ApprovalRule] = Field(default_factory=list)

    @field_validator("flow_type")
    @classmethod
    def flow_type_must_be_snake_case(cls, v: str) -> str:
        import re
        if not re.match(r"^[a-z][a-z0-9_]*$", v):
            raise ValueError(
                "flow_type debe ser snake_case, minúsculas, "
                "empezando con letra (ej: 'invoice_approval')"
            )
        return v

    @model_validator(mode="after")
    def each_step_references_valid_agent(self) -> "WorkflowDefinition":
        """Todo step.agent_role debe existir en agents[].role."""
        defined_roles = {a.role for a in self.agents}
        for step in self.steps:
            if step.agent_role not in defined_roles:
                raise ValueError(
                    f"Step '{step.name}' referencia agente '{step.agent_role}' "
                    f"que no existe. Roles definidos: {defined_roles}"
                )
        return self

    @model_validator(mode="after")
    def no_circular_dependencies(self) -> "WorkflowDefinition":
        """El grafo de dependencias no debe tener ciclos."""
        step_ids = {s.id for s in self.steps}
        dep_graph = {s.id: set(s.depends_on or []) for s in self.steps}

        visited: set = set()
        rec_stack: set = set()

        def dfs(node: str) -> bool:
            visited.add(node)
            rec_stack.add(node)
            for dep in dep_graph.get(node, []):
                if dep not in visited:
                    if dfs(dep):
                        return True
                elif dep in rec_stack:
                    return True
            rec_stack.remove(node)
            return False

        for sid in step_ids:
            if sid not in visited and dfs(sid):
                raise ValueError(f"El grafo de dependencias tiene ciclos en step '{sid}'")
        return self
```

### src/flows/workflow_guardrails.py

```python
"""src/flows/workflow_guardrails.py — Validación de seguridad para workflows.

Regla R3: secretos nunca al LLM — validado aquí.
Regla R8: max_iter ≤ 5 — enforced en AgentDefinition.
"""

from __future__ import annotations

import logging
from typing import Optional

from .workflow_definition import WorkflowDefinition

logger = logging.getLogger(__name__)

ALLOWED_MODELS = {
    "claude-sonnet-4-20250514",
    "claude-opus-4-20250514",
    "gpt-4o",
    "gpt-4-turbo",
    "groq/llama-3.3-70b-versatile",
}

DANGEROUS_TOOLS = {
    "execute_shell",
    "delete_database_records",
    "modify_payment_gateway",
    "bypass_authentication",
    "send_raw_sql",
}


class WorkflowValidationError(Exception):
    """Workflow inválido — no se persiste."""
    pass


def validate_workflow(
    workflow_def: WorkflowDefinition,
    org_id: Optional[str] = None,
) -> list[str]:
    """
    Validar un workflow antes de persistirlo.

    Validaciones:
    1. Estáticas (Pydantic ya hizo las estructurales)
    2. Seguridad (herramientas peligrosas, modelos)
    3. Recursos de la org (quota)

    Returns:
        Lista de errores. Lista vacía = válido.

    Raises:
        WorkflowValidationError: si hay errores de validación.
    """
    errors: list[str] = []

    # 1. Seguridad: herramientas peligrosas
    for agent in workflow_def.agents:
        for tool in agent.allowed_tools:
            if tool in DANGEROUS_TOOLS:
                errors.append(
                    f"Agent '{agent.role}' usa herramienta peligrosa: '{tool}'"
                )

    # 2. Recursos de la org
    if org_id:
        errors.extend(_validate_org_quota(org_id, workflow_def))

    if errors:
        raise WorkflowValidationError(errors)

    return errors


def _validate_org_quota(org_id: str, workflow_def: WorkflowDefinition) -> list[str]:
    """Verificar quota de la org para el workflow propuesto."""
    from src.guardrails.base_guardrail import load_org_limits

    errors = []
    limits = load_org_limits(org_id)
    quota = limits.get("quota", {})

    # Estimar: ~5000 tokens por step
    estimated_tokens = len(workflow_def.steps) * 5000
    max_tokens = quota.get("max_tokens_per_month", 5_000_000)

    if estimated_tokens > max_tokens * 0.1:
        errors.append(
            f"Workflow estimado (~{estimated_tokens} tokens) excede 10% "
            f"de quota mensual ({max_tokens})"
        )

    return errors
```

---

## 05 — Architect Flow

### src/flows/architect_flow.py

```python
"""src/flows/architect_flow.py — Genera workflows desde lenguaje natural.

Pattern confirmado con el código real de Fases 1-3:
- Hereda de BaseFlow (lifecycle-based)
- Override de create_task_record para usar ArchitectState
- WorkflowDefinition como output_pydantic del agente
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
```

### src/flows/dynamic_flow.py

```python
"""src/flows/dynamic_flow.py — Flows generados dinámicamente desde templates.

Un DynamicWorkflow es un BaseFlow cuyos steps y agents se cargan desde
la definición en workflow_templates. Se registra en FLOW_REGISTRY
para que POST /webhooks/{org_id}/{flow_type} lo encuentre automáticamente.

Pattern confirmado con MultiCrewFlow real:
- Hereda de BaseFlow
- Override de create_task_record para usar estado extendido
- Métodos internos para cada paso del workflow
- persist_state() después de cada paso (Rule R4)
- emit_event() después de cada paso (Rule R5)
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional, Type

from .base_flow import BaseFlow
from .registry import flow_registry
from ..crews.base_crew import BaseCrew
from ..guardrails.base_guardrail import make_approval_check

logger = logging.getLogger(__name__)


class DynamicWorkflow(BaseFlow):
    """
    Flow cargado desde workflow_templates.

    Se instancia dinámicamente cuando llega un webhook con un flow_type
    que no existe como archivo Python pero sí en workflow_templates.
    """

    _template_definition: Dict[str, Any] = {}
    _flow_type: str = "dynamic"

    @classmethod
    def register(cls, flow_type: str, definition: Dict[str, Any]) -> None:
        """Crear una subclase DynamicWorkflow绑定的 definition y registrarla."""
        template = definition

        class RegisteredFlow(cls):
            _template_definition = template
            _flow_type = flow_type

        RegisteredFlow.__name__ = f"DynamicFlow_{flow_type}"
        RegisteredFlow.__qualname__ = f"DynamicFlow_{flow_type}"

        flow_registry._flows[flow_type.lower()] = RegisteredFlow

    def validate_input(self, input_data: Dict[str, Any]) -> bool:
        return bool(input_data)

    async def _run_crew(self) -> Dict[str, Any]:
        """
        Ejecutar los steps definidos en el template.

        Cada step crea un BaseCrew, lo ejecuta, y persiste el estado.
        Si un step requiere aprobación, se pausa con request_approval().
        """
        template = self._template_definition
        steps = template.get("steps", [])
        approval_rules = template.get("approval_rules", [])
        results: Dict[str, Any] = {}

        for step in steps:
            step_id = step.get("id", f"step_{len(results)}")
            agent_role = step.get("agent_role")
            description = step.get("description", "")

            if not agent_role:
                logger.warning("Step '%s' sin agent_role, omitiendo", step_id)
                continue

            logger.info(
                "DynamicFlow[%s] ejecutando step '%s' con agent '%s'",
                self._flow_type, step_id, agent_role
            )

            crew = BaseCrew(org_id=self.org_id, role=agent_role)
            result = await crew.run_async(
                task_description=description,
                inputs={
                    "step_inputs": step.get("inputs", {}),
                    "previous_results": results,
                    "original_input": self.state.input_data,
                },
            )

            results[step_id] = {"result": str(result.raw)}
            await self.persist_state()
            await self.emit_event(f"step.{step_id}.completed", {
                "output": results[step_id]
            })

            # Evaluar approval_rules
            for rule in approval_rules:
                if self._check_approval_rule(rule, results):
                    await self.request_approval(
                        description=rule.get("description", "Approval required"),
                        payload={"step": step_id, "results": results},
                    )
                    return results  # Flow se pausa aquí

        return results

    def _check_approval_rule(self, rule: Dict[str, Any], results: Dict) -> bool:
        """
        Evaluar condition de una approval_rule.

        Solo soporta operadores básicos: >, <, >=, <=
       -condition es un string como "monto > 50000"
        """
        condition = rule.get("condition", "")
        try:
            if ">" in condition:
                _, threshold = condition.split(">", 1)
                threshold = float(threshold.strip())
                for v in results.values():
                    if isinstance(v, dict) and "result" in v:
                        try:
                            if float(str(v["result"])) > threshold:
                                return True
                        except (ValueError, TypeError):
                            continue
            elif "<" in condition:
                _, threshold = condition.split("<", 1)
                threshold = float(threshold.strip())
                for v in results.values():
                    if isinstance(v, dict) and "result" in v:
                        try:
                            if float(str(v["result"])) < threshold:
                                return True
                        except (ValueError, TypeError):
                            continue
        except (ValueError, TypeError):
            logger.warning("No se pudo evaluar approval_rule: %s", rule)
        return False


def load_dynamic_flows_from_db() -> int:
    """
    Cargar todos los workflows activos desde DB y registrarlos.

    Llamar en startup de FastAPI:
        @app.on_event("startup")
        async def startup():
            load_dynamic_flows_from_db()
    """
    from ..db.session import get_service_client

    svc = get_service_client()
    templates = (
        svc.table("workflow_templates")
        .select("flow_type, definition")
        .eq("is_active", True)
        .execute()
    )

    count = 0
    for t in templates.data or []:
        try:
            DynamicWorkflow.register(
                flow_type=t["flow_type"],
                definition=t["definition"],
            )
            count += 1
        except Exception as exc:
            logger.error(
                "No se pudo cargar dynamic flow %s: %s",
                t["flow_type"], exc
            )

    logger.info("DynamicWorkflow: %d flows cargados desde DB", count)
    return count
```

---

## 06 — Conversation Store

### src/db/conversation_store.py

```python
"""src/db/conversation_store.py — Persistencia de conversaciones del Architect."""

from __future__ import annotations

import uuid
import logging
from typing import Optional

from .session import get_tenant_client, get_service_client

logger = logging.getLogger(__name__)


def create_conversation(org_id: str, user_id: Optional[str] = None) -> str:
    """Crear una nueva conversación y retornar su ID."""
    conversation_id = str(uuid.uuid4())

    with get_tenant_client(org_id, user_id) as db:
        db.table("conversations").insert({
            "id": conversation_id,
            "org_id": org_id,
            "user_id": user_id,
            "status": "in_progress",
        }).execute()

    return conversation_id


def add_message(
    conversation_id: str,
    org_id: str,
    role: str,  # "user" | "assistant" | "system"
    content: str,
) -> None:
    """Agregar un mensaje a una conversación."""
    with get_tenant_client(org_id) as db:
        db.table("conversation_messages").insert({
            "id": str(uuid.uuid4()),
            "conversation_id": conversation_id,
            "role": role,
            "content": content,
        }).execute()

        db.table("conversations").update({
            "updated_at": "now()",
        }).eq("id", conversation_id).execute()


def get_conversation(conversation_id: str, org_id: str) -> dict:
    """Obtener conversación con sus mensajes."""
    from .session import get_service_client

    svc = get_service_client()

    conv = (
        svc.table("conversations")
        .select("*")
        .eq("id", conversation_id)
        .maybe_single()
        .execute()
    )

    if not conv.data:
        return {}

    messages = (
        svc.table("conversation_messages")
        .select("*")
        .eq("conversation_id", conversation_id)
        .order("created_at")
        .execute()
    )

    return {
        **conv.data,
        "messages": messages.data or [],
    }


def link_workflow(
    conversation_id: str,
    org_id: str,
    workflow_template_id: str,
) -> None:
    """Vincular una conversación con el workflow que generó."""
    with get_tenant_client(org_id) as db:
        db.table("conversations").update({
            "workflow_template_id": workflow_template_id,
            "status": "completed",
            "updated_at": "now()",
        }).eq("id", conversation_id).execute()


def update_status(
    conversation_id: str,
    org_id: str,
    status: str,
) -> None:
    """Actualizar el status de una conversación."""
    with get_tenant_client(org_id) as db:
        db.table("conversations").update({
            "status": status,
            "updated_at": "now()",
        }).eq("id", conversation_id).execute()
```

---

## 07 — Endpoint de Chat

### src/api/routes/chat.py

```python
"""src/api/routes/chat.py — Endpoint conversacional del Architect.

POST /chat/architect — Recibe mensaje NL, lanza ArchitectFlow
GET /chat/{conversation_id} — Consulta estado de una conversación
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, BackgroundTasks, Depends
from pydantic import BaseModel, Field
from typing import Optional
import logging

from ....db.conversation_store import (
    create_conversation,
    add_message,
    get_conversation,
    link_workflow,
    update_status,
)
from ....flows.architect_flow import ArchitectFlow
from ....guardrails.base_guardrail import check_quota, QuotaExceededError
from ..middleware import require_org_id

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/chat", tags=["chat"])


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1)
    conversation_id: Optional[str] = None


class ChatResponse(BaseModel):
    conversation_id: str
    status: str  # "generating" | "gathering_requirements" | "failed"
    reply: str
    flow_type: Optional[str] = None


@router.post("/architect", response_model=ChatResponse)
async def architect_chat(
    request: ChatRequest,
    background: BackgroundTasks,
    org_id: str = Depends(require_org_id),
    user_id: Optional[str] = None,
):
    """
    Endpoint conversacional para generar workflows.

    1. Guarda el mensaje del usuario
    2. Clasifica si hay suficiente contexto
    3. Si sí: lanza ArchitectFlow en background
    4. Si no: retorna pregunta de seguimiento
    """
    # Obtener o crear conversación
    conversation_id = request.conversation_id
    if not conversation_id:
        conversation_id = create_conversation(org_id, user_id)
    else:
        # Verificar que la conversación existe y es de esta org
        conv = get_conversation(conversation_id, org_id)
        if not conv:
            raise HTTPException(404, "Conversación no encontrada")

    # Guardar mensaje del usuario
    add_message(conversation_id, org_id, "user", request.message)

    # Verificar quota
    try:
        # check_quota(org_id, "tasks_per_month", current_count)
        pass  # Por implementar con el contador real
    except QuotaExceededError as e:
        raise HTTPException(429, detail=str(e))

    # Clasificar si hay suficiente contexto
    user_messages = [
        m for m in get_conversation(conversation_id, org_id).get("messages", [])
        if m.get("role") == "user"
    ]

    if len(user_messages) >= 2 or len(request.message) > 80:
        # Suficiente contexto → generar
        update_status(conversation_id, org_id, "generating")
        add_message(
            conversation_id, org_id, "assistant",
            "Estoy diseñando tu workflow. Te aviso cuando esté listo."
        )

        background.add_task(
            _run_architect_background,
            org_id=org_id,
            conversation_id=conversation_id,
            description=request.message,
        )

        return ChatResponse(
            conversation_id=conversation_id,
            status="generating",
            reply="Estoy diseñando tu workflow. Te aviso cuando esté listo.",
        )

    # Seguir recopilando información
    reply = _generate_followup(len(user_messages))
    add_message(conversation_id, org_id, "assistant", reply)

    return ChatResponse(
        conversation_id=conversation_id,
        status="gathering_requirements",
        reply=reply,
    )


@router.get("/{conversation_id}", response_model=ChatResponse)
async def get_chat_session(
    conversation_id: str,
    org_id: str = Depends(require_org_id),
):
    """Obtener estado y mensajes de una conversación."""
    conv = get_conversation(conversation_id, org_id)
    if not conv:
        raise HTTPException(404, "Conversación no encontrada")

    last_message = conv["messages"][-1] if conv.get("messages") else {}

    return ChatResponse(
        conversation_id=conversation_id,
        status=conv.get("status", "in_progress"),
        reply=last_message.get("content", ""),
        flow_type=conv.get("workflow_template_id"),
    )


def _generate_followup(message_count: int) -> str:
    """Generar pregunta de seguimiento."""
    if message_count == 1:
        return (
            "Entiendo que necesitas una automatización. "
            "¿Puedes describir los pasos que debería seguir?"
        )
    return (
        "¿Podrías darme más detalles sobre los datos de entrada "
        "y el resultado esperado?"
    )


async def _run_architect_background(
    org_id: str,
    conversation_id: str,
    description: str,
) -> None:
    """Ejecutar ArchitectFlow en background y actualizar conversación."""
    try:
        flow = ArchitectFlow(org_id=org_id)
        result = await flow.execute(
            input_data={
                "description": description,
                "conversation_id": conversation_id,
            },
            correlation_id=conversation_id,
        )

        flow_type = result.output_data.get("flow_type")
        template_id = result.output_data.get("template_id")

        add_message(
            conversation_id, org_id, "assistant",
            f"✅ Workflow '{flow_type}' creado. "
            f"Ejecutalo con POST /webhooks/{org_id}/{flow_type}"
        )

        link_workflow(conversation_id, org_id, template_id)

        logger.info(
            "ArchitectFlow[%s] completó: %s",
            conversation_id, flow_type
        )

    except Exception as exc:
        logger.error("ArchitectFlow[%s] falló: %s", conversation_id, exc)
        update_status(conversation_id, org_id, "failed")
        add_message(
            conversation_id, org_id, "assistant",
            f"❌ No pude generar el workflow: {exc}"
        )
```

---

## 08 — CRUD de Workflows

### src/api/routes/workflows.py

```python
"""src/api/routes/workflows.py — CRUD de workflow_templates."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional

from ....db.session import get_tenant_client
from ....flows.dynamic_flow import DynamicWorkflow
from ..middleware import require_org_id

router = APIRouter(prefix="/workflows", tags=["workflows"])


class WorkflowSummary(BaseModel):
    id: str
    name: str
    flow_type: str
    status: str
    is_active: bool
    execution_count: int


class WorkflowListResponse(BaseModel):
    workflows: list[WorkflowSummary]


@router.get("/", response_model=WorkflowListResponse)
async def list_workflows(
    org_id: str = Depends(require_org_id),
    status: Optional[str] = None,
):
    """Listar todos los workflows activos de una org."""
    with get_tenant_client(org_id) as db:
        query = db.table("workflow_templates").select(
            "id, name, flow_type, status, is_active, execution_count"
        ).eq("org_id", org_id)

        if status:
            query = query.eq("status", status)
        else:
            query = query.eq("is_active", True)

        result = query.execute()

    return WorkflowListResponse(
        workflows=[dict(r) for r in result.data or []]
    )


@router.get("/{flow_type}")
async def get_workflow(
    flow_type: str,
    org_id: str = Depends(require_org_id),
):
    """Obtener definición completa de un workflow."""
    with get_tenant_client(org_id) as db:
        result = (
            db.table("workflow_templates")
            .select("*")
            .eq("flow_type", flow_type)
            .eq("org_id", org_id)
            .maybe_single()
            .execute()
        )

    if not result.data:
        raise HTTPException(404, f"Workflow '{flow_type}' no encontrado")

    return result.data


@router.delete("/{flow_type}")
async def archive_workflow(
    flow_type: str,
    org_id: str = Depends(require_org_id),
):
    """Desactivar (soft-delete) un workflow."""
    with get_tenant_client(org_id) as db:
        db.table("workflow_templates").update({
            "is_active": False,
            "status": "archived",
        }).eq("flow_type", flow_type).eq("org_id", org_id).execute()

    return {"status": "archived", "flow_type": flow_type}
```

---

## 09 — Wiring en main.py

```python
# En src/api/main.py — startup event

from fastapi import FastAPI
import logging

# Eager imports (registran flows al arrancar)
import src.flows.generic_flow
import src.flows.multi_crew_flow

logger = logging.getLogger(__name__)

app = FastAPI(...)

# ... routers existentes ...

# NUEVOS routers
from .routes.chat import router as chat_router
from .routes.workflows import router as workflows_router

app.include_router(chat_router)
app.include_router(workflows_router)


@app.on_event("startup")
async def startup():
    """Cargar workflows generados previamente desde la DB."""
    from src.flows.dynamic_flow import load_dynamic_flows_from_db

    count = load_dynamic_flows_from_db()
    logger.info("Dynamic workflows loaded: %d", count)
```

---

## 10 — Tests

### tests/unit/test_workflow_definition.py

```python
"""tests/unit/test_workflow_definition.py"""

import pytest
from pydantic import ValidationError

from src.flows.workflow_definition import (
    WorkflowDefinition,
    StepDefinition,
    AgentDefinition,
    ApprovalRule,
)


class TestWorkflowDefinition:
    """WorkflowDefinition valida estructura correcta."""

    def test_valid_minimal_workflow(self):
        wf = WorkflowDefinition(
            name="Test Workflow",
            description="Un workflow de prueba válido con un paso y un agente",
            flow_type="test_workflow",
            steps=[
                StepDefinition(
                    id="step_1",
                    name="Hacer algo",
                    description="El agente hace algo útil",
                    agent_role="worker",
                )
            ],
            agents=[
                AgentDefinition(
                    role="worker",
                    goal="Goal text enough length here",
                    backstory="Backstory text enough length here",
                )
            ],
        )
        assert wf.flow_type == "test_workflow"
        assert len(wf.steps) == 1

    def test_rejects_step_with_unknown_agent_role(self):
        with pytest.raises(ValidationError, match="no existe"):
            WorkflowDefinition(
                name="Test",
                description="Test con paso referencing unknown agent",
                flow_type="test_invalid",
                steps=[
                    StepDefinition(
                        id="step_1",
                        name="Paso uno",
                        description="Descripción del paso",
                        agent_role="inexistente",
                    )
                ],
                agents=[
                    AgentDefinition(
                        role="real",
                        goal="Goal text enough length",
                        backstory="Backstory text enough length",
                    )
                ],
            )

    def test_rejects_invalid_flow_type_format(self):
        with pytest.raises(ValidationError, match="snake_case"):
            WorkflowDefinition(
                name="Test",
                description="Test con flow_type inválido",
                flow_type="Invalid-Flow-Type!",
                steps=[
                    StepDefinition(
                        id="s1",
                        name="Paso",
                        description="Descripción suficiente",
                        agent_role="a1",
                    )
                ],
                agents=[
                    AgentDefinition(role="a1", goal="G", backstory="B")
                ],
            )

    def test_rejects_empty_steps(self):
        with pytest.raises(ValidationError):
            WorkflowDefinition(
                name="Test",
                description="Test sin pasos",
                flow_type="empty",
                steps=[],
                agents=[
                    AgentDefinition(role="a1", goal="G", backstory="B")
                ],
            )

    def test_rejects_circular_dependencies(self):
        with pytest.raises(ValidationError, match="ciclos"):
            WorkflowDefinition(
                name="Test",
                description="Test con dependencias circulares",
                flow_type="circular",
                steps=[
                    StepDefinition(
                        id="step_a",
                        name="Step A",
                        description="Descripción A",
                        agent_role="agent",
                        depends_on=["step_b"],
                    ),
                    StepDefinition(
                        id="step_b",
                        name="Step B",
                        description="Descripción B",
                        agent_role="agent",
                        depends_on=["step_a"],
                    ),
                ],
                agents=[
                    AgentDefinition(
                        role="agent",
                        goal="Goal text",
                        backstory="Backstory text",
                    )
                ],
            )


class TestAgentDefinition:
    """AgentDefinition valida rangos y modelos."""

    def test_max_iter_within_limit(self):
        agent = AgentDefinition(
            role="test",
            goal="Goal text enough length",
            backstory="Backstory text enough length",
            max_iter=5,
        )
        assert agent.max_iter == 5

    def test_rejects_max_iter_too_high(self):
        with pytest.raises(ValidationError):
            AgentDefinition(
                role="test",
                goal="Goal text enough length",
                backstory="Backstory text enough length",
                max_iter=10,
            )

    def test_rejects_unknown_model(self):
        with pytest.raises(ValidationError, match="no permitido"):
            AgentDefinition(
                role="test",
                goal="Goal text enough length",
                backstory="Backstory text enough length",
                model="unknown-model",
            )
```

### tests/unit/test_architect_flow.py

```python
"""tests/unit/test_architect_flow.py"""

import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from uuid import uuid4

from src.flows.architect_flow import ArchitectFlow, ArchitectState


class TestArchitectFlow:

    def test_validate_input_rejects_empty(self):
        flow = ArchitectFlow(org_id="org-123")
        assert flow.validate_input({}) is False
        assert flow.validate_input({"description": ""}) is False
        assert flow.validate_input({"description": "abc"}) is False
        assert flow.validate_input({"description": "Este es válido"}) is True

    def test_parse_workflow_definition_extracts_json(self):
        flow = ArchitectFlow(org_id="org-123")

        raw = MagicMock()
        raw.raw = '{"name":"Test","flow_type":"test_flow","steps":[],"agents":[]}'

        result = flow._parse_workflow_definition(raw)
        assert result.name == "Test"
        assert result.flow_type == "test_flow"

    def test_parse_workflow_definition_strips_markdown(self):
        flow = ArchitectFlow(org_id="org-123")

        raw = MagicMock()
        raw.raw = '```json\n{"name":"T","flow_type":"t","steps":[],"agents":[]}\n```'

        result = flow._parse_workflow_definition(raw)
        assert result.name == "T"

    @patch("src.flows.architect_flow.get_service_client")
    def test_ensure_unique_flow_type_adds_suffix(self, mock_svc):
        """Si el flow_type ya existe, se agrega sufijo del org_id."""
        flow = ArchitectFlow(org_id="org-abc-123")

        mock_svc.return_value.table.return_value.select.return_value.eq.return_value.maybe_single.return_value.execute.return_value = (
            MagicMock(data={"id": "existing"})
        )

        result = flow._ensure_unique_flow_type("existing_flow")
        assert result.startswith("existing_flow_")
        assert "orgabc123" in result.replace("-", "")

    @patch("src.flows.architect_flow.get_service_client")
    def test_ensure_unique_flow_type_returns_same_if_new(self, mock_svc):
        """Si el flow_type es nuevo, se retorna sin cambios."""
        flow = ArchitectFlow(org_id="org-123")

        mock_svc.return_value.table.return_value.select.return_value.eq.return_value.maybe_single.return_value.execute.return_value = (
            MagicMock(data=None)
        )

        result = flow._ensure_unique_flow_type("brand_new_flow")
        assert result == "brand_new_flow"
```

---

## 11 — Entregables verificables

| # | Entregable | Criterio |
|---|------------|----------|
| 1 | `sql/006_workflow_templates.sql` | Tabla con `flow_type` global unique, RLS |
| 2 | `sql/007_conversations.sql` | Tablas `conversations` + `conversation_messages` con RLS |
| 3 | `src/flows/workflow_definition.py` | `WorkflowDefinition` valida: snake_case, agent roles, ciclos |
| 4 | `src/flows/workflow_guardrails.py` | Valida: herramientas peligrosas, quota org |
| 5 | `src/flows/architect_flow.py` | `ArchitectFlow` registrado con `@register_flow`. Valida antes de persistir. Registra dinámicamente. |
| 6 | `src/flows/dynamic_flow.py` | `DynamicWorkflow` ejecuta steps desde template. `load_dynamic_flows_from_db()` |
| 7 | `src/db/conversation_store.py` | CRUD de conversaciones con RLS |
| 8 | `src/api/routes/chat.py` | `POST /chat/architect` + `GET /chat/{id}` |
| 9 | `src/api/routes/workflows.py` | `GET /workflows/` + `GET /workflows/{flow_type}` + `DELETE` |
| 10 | `src/api/main.py` | Registra routers nuevos + `load_dynamic_flows_from_db()` en startup |
| 11 | `tests/unit/test_workflow_definition.py` | Tests de validación pasando |
| 12 | `tests/unit/test_architect_flow.py` | Tests de ArchitectFlow pasando |

---

## 12 — Reglas de implementación (Fase 4)

| # | Regla | Aplicación en Fase 4 |
|---|-------|---------------------|
| R1 | Flow es el orquestador | `DynamicWorkflow` orquesta steps secuenciales |
| R2 | `allow_delegation=False` siempre | Agents generados lo tienen hardcodeado |
| R3 | Secretos nunca al LLM | `ArchitectFlow` no pasa secretos al agente |
| R4 | Estado canónico en Supabase | `workflow_templates`, `conversations` son la fuente de verdad |
| R5 | Eventos inmutables | `ArchitectFlow.emit_event()` en cada step completado |
| R6 | `EventStore.append()` bloqueante | `emit_event()` usa `await flush()` |
| R7 | Toda tabla con `org_id` y RLS | Todas las tablas nuevas lo cumplen |
| R8 | `max_iter` explícito | Agents generados lo tienen en `AgentDefinition` (default 5, max 5) |

---

## 13 — Orden de implementación

1. **Schema SQL** — `sql/006`, `sql/007`
2. **conversation_store.py** — utilidad de DB para conversaciones
3. **workflow_definition.py** — modelos Pydantic
4. **workflow_guardrails.py** — validación de seguridad
5. **DynamicWorkflow** — flow dinámico desde template
6. **load_dynamic_flows_from_db()** — carga en startup
7. **ArchitectFlow** — generador con validación completa
8. **chat.py** — endpoint conversacional
9. **workflows.py** — CRUD de templates
10. **main.py** — wiring de routers y startup
11. **Tests**
