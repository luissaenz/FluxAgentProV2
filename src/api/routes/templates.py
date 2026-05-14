"""src/api/routes/templates.py — Endpoints CRUD para templates de agentes.

GET /api/templates      — listar con filtro ?category=
GET /api/templates/{id} — detalle con soul_json completo

Correcciones vs plan:
  - Endpoints SIN require_org_id (lectura publica, patron integrations.py)
  - Router registrado en main.py (no __init__.py)
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from src.db.session import get_service_client

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/templates", tags=["templates"])


class TemplateInfo(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    category: str
    suggested_tools: List[str] = []
    max_iter: int = 5
    is_system: bool = False
    created_at: Optional[str] = None


class TemplateListResponse(BaseModel):
    templates: List[TemplateInfo]
    count: int


class TemplateDetailResponse(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    category: str
    soul_json: Dict[str, Any]
    suggested_tools: List[str] = []
    max_iter: int = 5
    is_system: bool = False
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


@router.get("", response_model=TemplateListResponse)
async def list_templates(
    category: Optional[str] = Query(None),
) -> TemplateListResponse:
    """Listar templates. ?category= opcional. Sin auth."""
    db = get_service_client()
    query = db.table("agent_templates").select("*")
    if category:
        query = query.eq("category", category)
    data = query.execute()
    return TemplateListResponse(
        templates=[TemplateInfo(**t) for t in data.data],
        count=len(data.data),
    )


@router.get("/{template_id}", response_model=TemplateDetailResponse)
async def get_template(template_id: str) -> TemplateDetailResponse:
    """Obtener template por ID. 404 si no existe."""
    db = get_service_client()
    result = (
        db.table("agent_templates")
        .select("*")
        .eq("id", template_id)
        .maybe_single()
        .execute()
    )
    if not result.data:
        raise HTTPException(404, "Template not found")
    return TemplateDetailResponse(**result.data)
