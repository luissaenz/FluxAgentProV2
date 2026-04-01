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
    max_iter: int = Field(default=5, ge=1, le=5)

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
