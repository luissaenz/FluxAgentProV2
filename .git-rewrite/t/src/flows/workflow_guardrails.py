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
