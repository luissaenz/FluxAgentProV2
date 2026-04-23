"""MCP Router — HTTP JSON-RPC gateway for Model Context Protocol."""

from __future__ import annotations

import logging
import asyncio
import json
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse

from ..middleware import verify_supabase_jwt, require_org_id
from ...mcp.handlers import (
    handle_execute_flow,
    handle_get_task,
    handle_approve_task,
    handle_reject_task
)
from ...mcp.exceptions import mcp_error_to_response, MethodNotFound, InvalidParams
from ...mcp.sse import sse_manager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["mcp"])


class JSONRPCRequest(BaseModel):
    jsonrpc: str = "2.0"
    method: str
    params: Dict[str, Any] = {}
    id: Optional[Any] = None


@router.post("/mcp")
async def mcp_gateway(
    request: JSONRPCRequest,
    org_id: str = Depends(require_org_id),
    auth: dict = Depends(verify_supabase_jwt),
):
    """Entry point for JSON-RPC MCP requests over HTTP.
    
    Validates JWT and Org visibility before dispatching to handlers.
    """
    request_id = request.id
    claims = auth["payload"]

    try:
        if request.method == "execute_flow":
            flow_type = request.params.get("flow_type")
            input_data = request.params.get("input_data", {})
            correlation_id = request.params.get("correlation_id")
            
            if not flow_type:
                raise InvalidParams("Missing 'flow_type' in params")

            result = await handle_execute_flow(
                org_id=org_id,
                flow_type=flow_type,
                input_data=input_data,
                claims=claims,
                correlation_id=correlation_id
            )
        
        elif request.method == "get_task":
            task_id = request.params.get("task_id")
            if not task_id:
                raise InvalidParams("Missing 'task_id' in params")
            
            result = await handle_get_task(
                org_id=org_id,
                task_id=task_id,
                claims=claims
            )

        elif request.method == "approve_task":
            task_id = request.params.get("task_id")
            if not task_id:
                raise InvalidParams("Missing 'task_id' in params")
            
            result = await handle_approve_task(
                org_id=org_id,
                task_id=task_id,
                claims=claims
            )

        elif request.method == "reject_task":
            task_id = request.params.get("task_id")
            if not task_id:
                raise InvalidParams("Missing 'task_id' in params")
            
            result = await handle_reject_task(
                org_id=org_id,
                task_id=task_id,
                claims=claims
            )
        
        else:
            raise MethodNotFound(f"Method '{request.method}' not supported")

        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": result
        }

    except Exception as exc:
        return mcp_error_to_response(exc, request_id)


@router.get("/mcp/sse")
async def mcp_sse_endpoint(
    request: Request,
    org_id: str = Depends(require_org_id),
    auth: dict = Depends(verify_supabase_jwt),
):
    """Establish an SSE connection for MCP events.
    
    According to MCP spec, the first event must be 'endpoint' to inform
    the client where to send POST requests.
    """
    queue = await sse_manager.connect(org_id)

    async def event_generator():
        try:
            # 1. MCP Handshake: Inform the client where to POST JSON-RPC requests
            # We point back to the same router's /mcp endpoint
            yield {
                "event": "endpoint",
                "data": f"/api/v1/mcp?org_id={org_id}"
            }

            # 2. Listen for broadcasted events
            while True:
                if await request.is_disconnected():
                    break
                
                message = await queue.get()
                # If message data is a dict, serialize to JSON string for SSE
                if isinstance(message.get("data"), dict):
                    message["data"] = json.dumps(message["data"], default=str)
                
                yield message

        except asyncio.CancelledError:
            logger.info("SSE connection cancelled for org_id=%s", org_id)
        finally:
            await sse_manager.disconnect(org_id, queue)

    return EventSourceResponse(event_generator())

