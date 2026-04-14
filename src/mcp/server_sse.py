"""MCP Server SSE — Transporte HTTP para Claude Web/Mobile.

Implementa el protocolo MCP sobre Server-Sent Events integrado con FastAPI.
"""

import logging
from fastapi import APIRouter, Request, Depends, HTTPException
from mcp.server.fastapi import SseServerTransport

from .server import server, mcp_config_var
from .config import MCPConfig
from ..api.middleware import verify_org_membership

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/mcp", tags=["mcp"])

# El transporte necesita saber la ruta donde recibirá los mensajes POST
transport = SseServerTransport("/api/v1/mcp/messages")

@router.get("/sse")
async def handle_sse(
    request: Request,
    auth: dict = Depends(verify_org_membership)
):
    """
    Establece la conexión SSE con el cliente.
    Requiere autenticación de organización (JWT + X-Org-ID).
    """
    org_id = auth["org_id"]
    logger.info("New SSE connection context for org: %s", org_id)
    
    # Configuramos el contexto para los handlers de este request
    config = MCPConfig(org_id=org_id, transport="sse")
    mcp_config_var.set(config)
    
    async with transport.connect_sse(request.scope, request.receive, request._send) as (read, write):
        await server.run(
            read, 
            write, 
            server.create_initialization_options()
        )

@router.post("/messages")
async def handle_messages(request: Request):
    """
    Recibe mensajes JSON-RPC del cliente y los entrega al servidor MCP.
    """
    return await transport.handle_post_bundle(request.scope, request.receive, request._send)
