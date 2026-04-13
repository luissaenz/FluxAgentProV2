"""REST endpoints para el Service Catalog TIPO C.

Correcciones vs plan:
  - verify_org_membership en vez de get_current_user (inexistente)
  - require_org_id para endpoints ligeros (/available, /tools)
"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from src.api.middleware import require_org_id, verify_org_membership
from src.db.session import get_service_client

router = APIRouter(prefix="/api/integrations", tags=["integrations"])


@router.get("/available")
async def list_available_services(org_id: str = Depends(require_org_id)):
    """Retorna el catálogo global de servicios (para Dashboard UI)."""
    db = get_service_client()
    result = db.table("service_catalog").select("*").execute()
    return {"services": result.data}


@router.get("/active")
async def list_active_integrations(user=Depends(verify_org_membership)):
    """Retorna las integraciones activas de la org del usuario autenticado."""
    org_id = user["org_id"]
    db = get_service_client()
    result = (
        db.table("org_service_integrations")
        .select("*, service_catalog(name, category, logo_url)")
        .eq("org_id", org_id)
        .eq("status", "active")
        .execute()
    )
    return {"integrations": result.data}


@router.get("/tools/{service_id}")
async def list_service_tools(service_id: str, org_id: str = Depends(require_org_id)):
    """Retorna las tools disponibles para un servicio."""
    db = get_service_client()
    result = (
        db.table("service_tools")
        .select("id, name, tool_profile")
        .eq("service_id", service_id)
        .execute()
    )
    return {"tools": result.data}
