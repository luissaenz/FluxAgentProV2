"""src/api/routes/tools.py — Endpoint GET /api/tools/available.

Lists available tools from ToolRegistry (local) and MCP servers.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Dict, List, Literal, Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel

from src.api.middleware import require_org_id
from src.db.session import get_service_client
from src.tools.mcp_pool import MCPConnectionError, MCPPool
from src.tools.registry import tool_registry

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/tools", tags=["tools"])


class ToolInfo(BaseModel):
    """Información de una herramienta disponible."""

    name: str
    description: str
    category: str = "general"
    categories: List[str] = []
    source: Literal["local", "mcp"]
    parameters: Dict[str, Any] = {}
    requires_approval: bool = False
    timeout_seconds: int = 30
    is_active: bool = True


class ToolsListResponse(BaseModel):
    """Respuesta con lista de herramientas disponibles."""

    tools: List[ToolInfo]
    count: int


@router.get("/available", response_model=ToolsListResponse)
async def list_available_tools(
    org_id: str = Depends(require_org_id),
    source: Optional[str] = Query(None, pattern="^(local|mcp)$"),
    category: Optional[str] = Query(None),
) -> ToolsListResponse:
    """Listar todas las herramientas disponibles: locales + MCP.

    Args:
        org_id: UUID de la organización (header X-Org-ID).
        source: Filtrar por origen - \"local\" (ToolRegistry) o \"mcp\" (MCP servers).
        category: Filtrar tools locales por tag/categoría.

    Returns:
        ToolsListResponse con array de herramientas y conteo.
    """
    tools = await _collect_tools(org_id, source, category)
    return ToolsListResponse(tools=tools, count=len(tools))


async def _collect_tools(
    org_id: str,
    source: Optional[str] = None,
    category: Optional[str] = None,
) -> List[ToolInfo]:
    tools: List[ToolInfo] = []

    # Local tools
    if source in (None, "local"):
        for name in tool_registry.list_tools():
            if ":" in name:
                continue
            meta = tool_registry.get_metadata(name)
            if not meta:
                continue
            if category and category not in meta.tags:
                continue
            tools.append(
                ToolInfo(
                    name=name,
                    description=meta.description,
                    category=meta.tags[0] if meta.tags else "general",
                    categories=meta.tags,
                    source="local",
                    parameters=meta.parameters,
                    requires_approval=meta.requires_approval,
                    timeout_seconds=meta.timeout_seconds,
                    is_active=True,
                )
            )

    # MCP servers
    if source in (None, "mcp"):
        try:
            mcp_tools = await _fetch_mcp_tools(org_id)
            tools.extend(mcp_tools)
        except Exception:
            logger.exception("Error fetching MCP tools")
            # Degradado graceful — retornar tools locales

    return tools


async def _fetch_mcp_tools(org_id: str) -> List[ToolInfo]:
    """Fetch tools from all active MCP servers for the org."""
    db = get_service_client()
    result = (
        db.table("org_mcp_servers")
        .select("name")
        .eq("org_id", org_id)
        .eq("is_active", True)
        .execute()
    )
    servers = result.data or []

    async def _fetch(server_name: str) -> List[ToolInfo]:
        try:
            pool = MCPPool.get()
            mcp_tools = await pool.get_tools(org_id, server_name, timeout=5)
            return [
                ToolInfo(
                    name=f"mcp:{server_name}:{getattr(t, 'name', str(t))}",
                    description=getattr(t, "description", ""),
                    category=server_name,
                    categories=["mcp", server_name],
                    source="mcp",
                    parameters={},
                    requires_approval=False,
                    timeout_seconds=30,
                    is_active=True,
                )
                for t in mcp_tools
            ]
        except MCPConnectionError:
            logger.warning("MCP server '%s' unreachable — skipping", server_name)
            return []
        except Exception:
            logger.exception("MCP server '%s' error — skipping", server_name)
            return []

    results = await asyncio.gather(*[_fetch(s["name"]) for s in servers], return_exceptions=False)
    tools: List[ToolInfo] = []
    for result in results:
        if isinstance(result, list):
            tools.extend(result)
    return tools
