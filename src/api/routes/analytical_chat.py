"""src/api/routes/analytical_chat.py — Chat analítico con IA (Intent Classifier + Tools + Synthesizer).

POST /analytical/ask — Recibe pregunta NL, clasifica intención con LLM, ejecuta consulta y responde narrativamente.
GET  /analytical/queries — Lista consultas analíticas disponibles.
"""

from __future__ import annotations

import logging
import time
from typing import Optional, Dict, Any, List
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field

from ..middleware import require_org_id
from ...crews.analytical_crew import AnalyticalCrew
from ...crews.analytical_queries import ALLOWED_ANALYTICAL_QUERIES

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/analytical", tags=["analytical"])


class AnalyticalAskRequest(BaseModel):
    """Request para consulta analítica."""
    question: str = Field(..., min_length=1, description="Pregunta en lenguaje natural")
    query_type: Optional[str] = Field(
        None,
        description="Tipo de consulta específico (opcional, si no se provee se clasifica con LLM)",
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


# ── Rate limiter simple por org ──────────────────────────────────

_rate_limit_store: Dict[str, list] = {}
_RATE_LIMIT_MAX = 10  # requests por minuto
_RATE_LIMIT_WINDOW = 60  # segundos


def _check_rate_limit(org_id: str) -> None:
    """Verificar rate limit: max 10 requests/min por org."""
    now = time.time()

    if org_id not in _rate_limit_store:
        _rate_limit_store[org_id] = []

    # Limpiar timestamps viejos
    _rate_limit_store[org_id] = [
        t for t in _rate_limit_store[org_id] if now - t < _RATE_LIMIT_WINDOW
    ]

    if len(_rate_limit_store[org_id]) >= _RATE_LIMIT_MAX:
        raise HTTPException(
            status_code=429,
            detail={
                "message": "Demasiadas consultas analíticas. Esperá un momento.",
                "retry_after": _RATE_LIMIT_WINDOW,
            },
        )

    _rate_limit_store[org_id].append(now)


@router.post("/ask", response_model=AnalyticalAskResponse)
async def ask_analytical(
    request: AnalyticalAskRequest,
    org_id: str = Depends(require_org_id),
):
    """
    Responder una pregunta analítica en lenguaje natural.

    Phase 4 (upgrade): El asistente analítico usa LLM para:
    1. Clasificar la intención de la pregunta
    2. Ejecutar consultas pre-validadas con herramientas
    3. Sintetizar una respuesta narrativa en Markdown

    Si query_type se proporciona, se usa directamente (override).
    Si no, el sistema clasifica la intención con LLM (fallback: keywords).
    """
    # Rate limiting
    _check_rate_limit(org_id)

    # Si el usuario proporcionó query_type explícito, validarlo
    if request.query_type and request.query_type not in ALLOWED_ANALYTICAL_QUERIES:
        raise HTTPException(
            status_code=400,
            detail={
                "message": f"Query type '{request.query_type}' no es válido.",
                "available_queries": list(ALLOWED_ANALYTICAL_QUERIES.keys()),
            },
        )

    # Ejecutar análisis con el pipeline LLM
    crew = AnalyticalCrew(org_id=org_id)
    try:
        result = await crew.ask(
            question=request.question,
            query_type_hint=request.query_type,
        )
    except Exception as exc:
        logger.error("Error en consulta analítica: %s", exc)
        raise HTTPException(
            status_code=500,
            detail=f"Error ejecutando análisis: {str(exc)}",
        )

    # Si el intent fue unknown, retornar error amigable
    if result["query_type"] == "unknown":
        raise HTTPException(
            status_code=400,
            detail={
                "message": result["summary"],
                "available_queries": list(ALLOWED_ANALYTICAL_QUERIES.keys()),
            },
        )

    return AnalyticalAskResponse(
        question=result["question"],
        query_type=result["query_type"],
        data=result["data"],
        summary=result["summary"],
        metadata=result["metadata"],
    )


@router.get("/queries", response_model=AnalyticalQueriesResponse)
async def list_analytical_queries():
    """Lista todas las consultas analíticas disponibles."""
    queries = [
        AnalyticalQueryInfo(key=key, description=desc)
        for key, desc in QUERY_DESCRIPTIONS.items()
    ]
    return AnalyticalQueriesResponse(queries=queries)
