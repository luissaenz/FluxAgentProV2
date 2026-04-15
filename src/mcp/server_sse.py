"""MCP Server SSE — Transporte HTTP para Claude Web/Mobile.

Implementa el protocolo MCP sobre Server-Sent Events integrado con FastAPI.
"""

import logging
import secrets
from fastapi import APIRouter, Request, Depends, HTTPException
from mcp.server.fastapi import SseServerTransport

from .server import server, mcp_config_var
from .config import MCPConfig
from ..api.middleware import verify_org_membership
from ..db.session import get_service_client

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


@router.post("/generate-pin")
async def generate_pin(auth: dict = Depends(verify_org_membership)):
    """
    Genera y almacena un PIN seguro de conexión MCP para la organización actual.
    """
    org_id = auth["org_id"]
    
    # Generate secure pin (16 bytes URL-safe string)
    pin = secrets.token_urlsafe(16)
    
    try:
        db = get_service_client()
        db.table("secrets").upsert({
            "org_id": org_id,
            "name": "mcp_connection_pin",
            "secret_value": pin
        }, on_conflict="org_id, name").execute()
    except Exception as e:
        logger.error("Error storing MCP PIN for org %s: %s", org_id, e)
        raise HTTPException(status_code=500, detail="Failed to store secure PIN.")
        
    return {"pin": pin}
