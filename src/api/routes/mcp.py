"""MCP Router — HTTP JSON-RPC gateway for Model Context Protocol."""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from ..middleware import verify_supabase_jwt, require_org_id
from ...mcp.handlers import (
    handle_execute_flow,
    handle_get_task,
    handle_approve_task,
    handle_reject_task
)
from ...mcp.exceptions import mcp_error_to_response, MethodNotFound, InvalidParams

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

