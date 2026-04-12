"""src/api/routes/flows.py — Endpoints para listing y ejecución de flows registrados."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, BackgroundTasks, Depends
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
from uuid import uuid4
import logging

from ...flows.registry import flow_registry
from .webhooks import execute_flow
from ..middleware import require_org_id

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/flows", tags=["flows"])


class FlowInfo(BaseModel):
    """Información de un flow registrado."""

    flow_type: str
    name: str
    description: Optional[str] = None
    input_schema: Optional[Dict[str, Any]] = None
    depends_on: List[str] = []
    category: Optional[str] = None


class FlowHierarchyNode(BaseModel):
    """Nodo en la jerarquía de flows."""

    flow_type: str
    name: str
    category: Optional[str] = None
    depends_on: List[str] = []


class FlowHierarchyResponse(BaseModel):
    """Respuesta con la jerarquía completa de flows."""

    hierarchy: Dict[str, FlowHierarchyNode]
    categories: Dict[str, List[str]]


class FlowsListResponse(BaseModel):
    """Respuesta con lista de flows disponibles."""

    flows: List[FlowInfo]


class RunFlowRequest(BaseModel):
    """Request para ejecutar un flow."""

    input_data: Dict[str, Any] = {}
    callback_url: Optional[str] = None


class RunFlowResponse(BaseModel):
    """Respuesta al ejecutar un flow."""

    task_id: str
    correlation_id: str
    status: str


# Mapeo de flows a sus schemas de input (definidos manualmente o desde los flows)
FLOW_INPUT_SCHEMAS: Dict[str, Dict[str, Any]] = {
    "bartenders_preventa": {
        "type": "object",
        "required": [
            "fecha_evento",
            "provincia",
            "localidad",
            "tipo_evento",
            "pax",
            "duracion_horas",
            "tipo_menu",
        ],
        "properties": {
            "fecha_evento": {"type": "string", "example": "2026-07-20"},
            "provincia": {
                "type": "string",
                "enum": ["Tucuman", "Salta", "Jujuy", "Catamarca"],
            },
            "localidad": {"type": "string"},
            "tipo_evento": {
                "type": "string",
                "enum": ["boda", "corporativo", "fiesta", "otro"],
            },
            "pax": {"type": "integer", "minimum": 10, "maximum": 500},
            "duracion_horas": {"type": "integer", "minimum": 1, "maximum": 24},
            "tipo_menu": {"type": "string", "enum": ["basico", "estandar", "premium"]},
            "restricciones": {"type": "string"},
        },
    },
    "bartenders_reserva": {
        "type": "object",
        "required": ["evento_id", "cotizacion_id", "opcion_elegida"],
        "properties": {
            "evento_id": {"type": "string"},
            "cotizacion_id": {"type": "string"},
            "opcion_elegida": {
                "type": "string",
                "enum": ["basica", "recomendada", "premium"],
            },
        },
    },
    "bartenders_alerta": {
        "type": "object",
        "required": ["evento_id"],
        "properties": {
            "evento_id": {"type": "string"},
        },
    },
    "bartenders_cierre": {
        "type": "object",
        "required": ["evento_id", "costo_real"],
        "properties": {
            "evento_id": {"type": "string"},
            "costo_real": {"type": "integer"},
            "mermas": {"type": "integer", "default": 0},
            "compras_emergencia": {"type": "integer", "default": 0},
            "desvio_climatico": {"type": "string"},
            "rating": {"type": "integer", "minimum": 1, "maximum": 5},
        },
    },
}


@router.get("/available", response_model=FlowsListResponse)
async def list_available_flows(
    org_id: str = Depends(require_org_id),
):
    """
    Listar todos los flows registrados disponibles para ejecución.
    """
    flows = []

    for flow_type in flow_registry.list_flows():
        meta = flow_registry.get_metadata(flow_type)
        flows.append(
            FlowInfo(
                flow_type=flow_type,
                name=flow_type.replace("_", " ").title(),
                description=f"Flow: {flow_type}",
                input_schema=FLOW_INPUT_SCHEMAS.get(flow_type),
                depends_on=meta.get("depends_on", []),
                category=meta.get("category"),
            )
        )

    return FlowsListResponse(flows=flows)


@router.get("/hierarchy", response_model=FlowHierarchyResponse)
async def get_flow_hierarchy(
    org_id: str = Depends(require_org_id),
):
    """
    Obtener la jerarquía completa de flows con dependencias y categorías.

    Phase 4: Endpoint para visualización de árbol de procesos de negocio.
    """
    hierarchy = {}
    for flow_type, meta in flow_registry.get_hierarchy().items():
        hierarchy[flow_type] = FlowHierarchyNode(
            flow_type=flow_type,
            name=flow_type.replace("_", " ").title(),
            category=meta.get("category"),
            depends_on=meta.get("depends_on", []),
        )

    categories = flow_registry.get_flows_by_category()

    return FlowHierarchyResponse(
        hierarchy=hierarchy,
        categories=categories,
    )


@router.post("/{flow_type}/run", response_model=RunFlowResponse)
async def run_flow(
    flow_type: str,
    request: RunFlowRequest,
    background_tasks: BackgroundTasks,
    org_id: str = Depends(require_org_id),
):
    """
    Ejecutar un flow específico con los datos de entrada.
    Retorna 202 Accepted inmediatamente - el flow corre en background.
    """
    if not flow_registry.has(flow_type):
        raise HTTPException(
            status_code=404,
            detail=f"Flow '{flow_type}' no encontrado. Disponibles: {flow_registry.list_flows()}",
        )

    # SUPUESTO: correlation_id debe ser único por ejecución para trazabilidad correcta.
    # Formato: manual-{flow_type}-{org_prefix}-{short_uuid}
    correlation_id = f"manual-{flow_type}-{org_id[:8]}-{uuid4().hex[:6]}"

    background_tasks.add_task(
        execute_flow,
        flow_type=flow_type,
        org_id=org_id,
        input_data=request.input_data,
        correlation_id=correlation_id,
        callback_url=request.callback_url,
    )

    return RunFlowResponse(
        task_id=correlation_id,
        correlation_id=correlation_id,
        status="accepted",
    )
