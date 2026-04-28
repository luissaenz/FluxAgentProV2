"""src/api/routes/flows.py — Endpoints para listing y ejecución de flows registrados."""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional
from uuid import uuid4

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from pydantic import BaseModel

from ...flows.registry import flow_registry
from ..middleware import require_org_id
from .webhooks import execute_flow_instance

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
    validation: Dict[str, Any] = {}


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


# Mapeo de flows a sus schemas de input
# Los schemas de bartenders fueron removidos en Sprint 1 (desacople).
# Para MCP, flow_to_tool.py genera tools con schema vacío si no hay entrada aquí.
FLOW_INPUT_SCHEMAS: Dict[str, Dict[str, Any]] = {}


@router.get("/available", response_model=FlowsListResponse)
async def list_available_flows(
    org_id: str = Depends(require_org_id),
    category: Optional[str] = None,
    exclude_system: bool = False,
):
    """
    Listar todos los flows registrados disponibles para ejecución.
    """
    flows = []

    for flow_type in flow_registry.list_flows():
        meta = flow_registry.get_metadata(flow_type)
        flow_category = meta.get("category")
        
        # Filtrar por categoría si se especifica
        if category and flow_category != category:
            continue
            
        # Excluir system si se solicita
        if exclude_system and flow_category == "system":
            continue

        flows.append(
            FlowInfo(
                flow_type=flow_type,
                name=flow_type.replace("_", " ").title(),
                description=meta.get("description") or f"Flow: {flow_type}",
                input_schema=FLOW_INPUT_SCHEMAS.get(flow_type),
                depends_on=meta.get("depends_on", []),
                category=flow_category,
            )
        )

    return FlowsListResponse(flows=flows)


@router.get("/hierarchy", response_model=FlowHierarchyResponse)
async def get_flow_hierarchy(
    org_id: str = Depends(require_org_id),
):
    """
    Obtener la jerarquía completa de flows con dependencias, categorías y validación.

    Phase 4: Endpoint para visualización de árbol de procesos de negocio.
    Incluye resultados de validación de integridad del grafo de dependencias.
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
    validation = flow_registry.run_full_validation()

    return FlowHierarchyResponse(
        hierarchy=hierarchy,
        categories=categories,
        validation=validation,
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

    # 1. Generate correlation_id for traceability
    correlation_id = f"manual-{flow_type}-{org_id[:8]}-{uuid4().hex[:6]}"

    # 2. Initialize flow and create task record synchronously to get the real task_id
    flow_class = flow_registry.get(flow_type)
    flow = flow_class(org_id=org_id)

    # Validate input (standard procedure)
    if not flow.validate_input(request.input_data):
        raise HTTPException(status_code=400, detail="Input validation failed")

    await flow.create_task_record(request.input_data, correlation_id)
    task_id = flow.state.task_id

    # 3. Hand off the rest of the execution to the background
    background_tasks.add_task(
        execute_flow_instance,
        flow=flow,
        input_data=request.input_data,
        correlation_id=correlation_id,
        callback_url=request.callback_url,
    )

    return RunFlowResponse(
        task_id=task_id,
        correlation_id=correlation_id,
        status="accepted",
    )
