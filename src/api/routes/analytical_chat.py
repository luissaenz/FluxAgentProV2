"""src/api/routes/analytical_chat.py — Chat analítico con acceso a SQL y EventStore.

POST /analytical/ask — Recibe pregunta NL, ejecuta análisis y responde.
GET  /analytical/queries — Lista consultas analíticas disponibles.
"""

from __future__ import annotations

import logging
from typing import Optional, Dict, Any, List
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field

from ..middleware import require_org_id
from ...crews.analytical_crew import AnalyticalCrew, ALLOWED_ANALYTICAL_QUERIES

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/analytical", tags=["analytical"])


class AnalyticalAskRequest(BaseModel):
    """Request para consulta analítica."""
    question: str = Field(..., min_length=1, description="Pregunta en lenguaje natural")
    query_type: Optional[str] = Field(
        None,
        description="Tipo de consulta específico (opcional, si no se provee se infiere de la pregunta)",
    )


class AnalyticalAskResponse(BaseModel):
    """Respuesta del asistente analítico."""
    question: str
    query_type: str
    data: List[Dict[str, Any]]
    summary: str
    metadata: Dict[str, Any]


class AnalyticalQueryInfo(BaseModel):
    """Información de una consulta analítica disponible."""
    key: str
    description: str


class AnalyticalQueriesResponse(BaseModel):
    """Lista de consultas analíticas disponibles."""
    queries: List[AnalyticalQueryInfo]


# Metadata descriptiva de cada consulta disponible
QUERY_DESCRIPTIONS: Dict[str, str] = {
    "agent_success_rate": "Tasa de éxito de agentes en los últimos 7 días",
    "tickets_by_status": "Distribución de tickets por estado",
    "flow_token_consumption": "Consumo de tokens por tipo de flow",
    "recent_events_summary": "Resumen de eventos de dominio en las últimas 24h",
    "tasks_by_flow_type": "Tareas agrupadas por flow type y estado",
}


@router.post("/ask", response_model=AnalyticalAskResponse)
async def ask_analytical(
    request: AnalyticalAskRequest,
    org_id: str = Depends(require_org_id),
):
    """
    Responder una pregunta analítica en lenguaje natural.

    Phase 4: El asistente analítico ejecuta consultas pre-validadas sobre
    datos históricos de la organización.

    En MVP, el usuario puede:
    1. Especificar query_type directamente (recomendado)
    2. O dejar que el sistema infiera de la pregunta (simple keyword matching)
    """
    # Determinar query_type
    query_type = request.query_type
    if not query_type:
        query_type = _infer_query_type(request.question)

    if query_type not in ALLOWED_ANALYTICAL_QUERIES:
        raise HTTPException(
            status_code=400,
            detail={
                "message": f"No se pudo determinar el tipo de consulta para: '{request.question}'",
                "available_queries": list(ALLOWED_ANALYTICAL_QUERIES.keys()),
                "hint": "Especificá query_type explícitamente o reformulá tu pregunta.",
            },
        )

    # Ejecutar análisis
    crew = AnalyticalCrew(org_id=org_id)
    try:
        result = await crew.analyze(query_type=query_type)
    except Exception as exc:
        logger.error("Error en consulta analítica %s: %s", query_type, exc)
        raise HTTPException(
            status_code=500,
            detail=f"Error ejecutando análisis: {str(exc)}",
        )

    # Generar resumen narrativo
    summary = _generate_summary(query_type, result)

    return AnalyticalAskResponse(
        question=request.question,
        query_type=query_type,
        data=result.get("data", []),
        summary=summary,
        metadata=result.get("metadata", {}),
    )


@router.get("/queries", response_model=AnalyticalQueriesResponse)
async def list_analytical_queries():
    """Lista todas las consultas analíticas disponibles."""
    queries = [
        AnalyticalQueryInfo(key=key, description=desc)
        for key, desc in QUERY_DESCRIPTIONS.items()
    ]
    return AnalyticalQueriesResponse(queries=queries)


# ── Helpers ───────────────────────────────────────────────────────

def _infer_query_type(question: str) -> str:
    """Inferir tipo de consulta a partir de keywords en la pregunta.

    SUPUESTO: Para MVP usamos matching simple por keywords.
    En producción se usaría un LLM para clasificación de intents.
    """
    q = question.lower()

    if any(kw in q for kw in ["agente", "agent", "éxito", "success", "mejor", "tasa"]):
        return "agent_success_rate"
    if any(kw in q for kw in ["ticket", "estado", "status", "distribución"]):
        return "tickets_by_status"
    if any(kw in q for kw in ["token", "consumo", "gasto", "costo", "llm"]):
        return "flow_token_consumption"
    if any(kw in q for kw in ["evento", "event", "reciente", "recent", "24", "hoy"]):
        return "recent_events_summary"
    if any(kw in q for kw in ["tarea", "task", "flow", "tipo"]):
        return "tasks_by_flow_type"

    # Default: retornar None para que el endpoint lance error útil
    return "unknown"


def _generate_summary(query_type: str, result: Dict[str, Any]) -> str:
    """Generar resumen narrativo de los resultados."""
    data = result.get("data", [])
    row_count = len(data) if isinstance(data, list) else 0

    if query_type == "agent_success_rate":
        if not data:
            return "No hay datos de agentes en los últimos 7 días."
        top = data[0] if data else {}
        return (
            f"El agente con mayor tasa de éxito es **{top.get('role', 'N/A')}** "
            f"con {top.get('success_rate', 0)}% de éxito "
            f"({top.get('completed_tasks', 0)}/{top.get('total_tasks', 0)} tareas)."
        )

    if query_type == "tickets_by_status":
        if not data:
            return "No hay tickets registrados."
        total = sum(d.get("count", 0) for d in data)
        done = next((d["count"] for d in data if d.get("status") == "done"), 0)
        return (
            f"Hay **{total} tickets** en total. "
            f"**{done}** completados exitosamente."
        )

    if query_type == "flow_token_consumption":
        if not data:
            return "No hay datos de consumo de tokens."
        total_tokens = sum(d.get("total_tokens", 0) for d in data)
        return (
            f"El consumo total de tokens es de **{total_tokens:,}**. "
            f"El flow con mayor consumo es **{data[0].get('flow_type', 'N/A')}** "
            f"con {data[0].get('total_tokens', 0):,} tokens."
        )

    if query_type == "recent_events_summary":
        if not data:
            return "No hay eventos en las últimas 24 horas."
        total = sum(d.get("count", 0) for d in data)
        return (
            f"Se registraron **{total} eventos** en las últimas 24 horas, "
            f"de **{row_count} tipos** diferentes."
        )

    if query_type == "tasks_by_flow_type":
        if not data:
            return "No hay tareas registradas."
        total = sum(d.get("count", 0) for d in data)
        return f"Hay **{total} tareas** registradas en **{row_count} combinaciones** de flow/estado."

    return f"Consulta ejecutada: {row_count} filas retornadas."
