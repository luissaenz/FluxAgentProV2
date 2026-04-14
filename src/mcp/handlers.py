"""MCP Handlers for FluxAgentPro.
Implements the core logic for executing flows, checking tasks, and HITL.
"""

import json
import logging
import asyncio
from typing import Any, Dict
from uuid import uuid4

from .sanitizer import sanitize_output
from .exceptions import map_exception_to_mcp_error, FlowNotFoundError
from .auth import create_internal_token
from ..flows.registry import flow_registry
from ..db.session import get_service_client, get_tenant_client, execute_with_retry

logger = logging.getLogger(__name__)

# Execution timeout for immediate response
EXECUTION_TIMEOUT = 5.0

async def handle_execute_flow(arguments: Dict[str, Any], config: Any) -> Dict[str, Any]:
    """
    Executes a flow registered in the system.
    Returns immediate result if fast, or task_id + status='pending' if slow.
    """
    flow_type = arguments.get("flow_type")
    input_data = arguments.get("input_data", {})
    org_id = config.org_id
    user_id = "mcp-system" # Default for MCP operations

    if not flow_type:
        raise ValueError("flow_type is required")

    try:
        flow_class = flow_registry.get(flow_type)
    except ValueError:
        raise FlowNotFoundError(flow_type, flow_registry.list_flows())

    flow_instance = flow_class(org_id=org_id, user_id=user_id)
    correlation_id = f"mcp-{uuid4()}"

    # Start execution
    try:
        # We wrap the execution to allow returning 'pending' if it takes too long
        task = asyncio.create_task(flow_instance.execute(input_data, correlation_id=correlation_id))
        
        try:
            state = await asyncio.wait_for(task, timeout=EXECUTION_TIMEOUT)
            # Completed within timeout
            return {
                "task_id": state.task_id,
                "status": state.status,
                "result": sanitize_output(state.output_data) if state.output_data else None,
            }
        except asyncio.TimeoutError:
            # Took too long, task continues in background
            # Note: Since the flow instance holds references, we must ensure it persists correctly.
            # BaseFlow already persists to DB at each step.
            return {
                "task_id": flow_instance.state.task_id if flow_instance.state else "creating...",
                "status": "pending",
                "message": "Execution is taking longer than 5s. Use get_task to poll for results.",
            }
    except Exception as exc:
        raise map_exception_to_mcp_error(exc)

async def handle_get_task(arguments: Dict[str, Any], config: Any) -> Dict[str, Any]:
    """
    Queries the status and result of a task.
    Bypasses RLS to allow MCP check any task in the org context.
    """
    task_id = arguments.get("task_id")
    if not task_id:
        raise ValueError("task_id is required")

    svc = get_service_client()
    try:
        result = execute_with_retry(
            svc.table("tasks")
            .select("status, result, error")
            .eq("id", task_id)
            .eq("org_id", config.org_id)
            .maybe_single()
        )
        
        if not result.data:
            raise LookupError(f"Task {task_id} not found")
        
        data = result.data
        return {
            "status": data["status"],
            "result": sanitize_output(data["result"]) if data["result"] else None,
            "error": data["error"],
        }
    except Exception as exc:
        raise map_exception_to_mcp_error(exc)

async def handle_approve_task(arguments: Dict[str, Any], config: Any) -> Dict[str, Any]:
    """
    Approves a pending task and resumes its flow.
    """
    task_id = arguments.get("task_id")
    notes = arguments.get("notes", "Approved via MCP")
    
    return await _handle_hitl_decision(task_id, "approved", notes, config)

async def handle_reject_task(arguments: Dict[str, Any], config: Any) -> Dict[str, Any]:
    """
    Rejects a pending task.
    """
    task_id = arguments.get("task_id")
    reason = arguments.get("reason", "Rejected via MCP")
    
    return await _handle_hitl_decision(task_id, "rejected", reason, config)

async def handle_create_workflow(arguments: Dict[str, Any], config: Any) -> Dict[str, Any]:
    """
    Wrapper for ArchitectFlow to create new workflow templates.
    """
    description = arguments.get("description")
    if not description:
        raise ValueError("description is required")
        
    # ArchitectFlow expects description and optionally conversation_id
    input_data = {"description": description}
    
    # We use handle_execute_flow logic but specifically for architect_flow
    new_args = {
        "flow_type": "architect_flow",
        "input_data": input_data
    }
    return await handle_execute_flow(new_args, config)

async def _handle_hitl_decision(task_id: str, decision: str, comment: str, config: Any) -> Dict[str, Any]:
    """Internal helper to process HITL decisions."""
    if not task_id:
        raise ValueError("task_id is required")

    svc = get_service_client()
    
    # 1. Verify existence and state
    task_res = execute_with_retry(
        svc.table("tasks")
        .select("status, flow_type")
        .eq("id", task_id)
        .eq("org_id", config.org_id)
        .maybe_single()
    )
    
    if not task_res.data:
        raise LookupError(f"Task {task_id} not found")
    
    if task_res.data["status"] != "pending_approval":
        raise ValueError(f"Task {task_id} is in status '{task_res.data['status']}', cannot be {decision}")

    # 2. Update pending_approvals record
    # Note: handle as service_role if needed, but here we can use get_service_client
    execute_with_retry(
        svc.table("pending_approvals")
        .update({
            "status": decision,
            "resolved_at": "now()",
            "notes": comment
        })
        .eq("task_id", task_id)
    )

    # 3. Resume Flow
    try:
        flow_class = flow_registry.get(task_res.data["flow_type"])
        flow_instance = flow_class(org_id=config.org_id, user_id="mcp-system")
        
        # Resume is async in BaseFlow
        asyncio.create_task(flow_instance.resume(
            task_id=task_id,
            decision=decision,
            decided_by="mcp-operator"
        ))
        
        return {
            "status": "processing",
            "message": f"Task {task_id} has been {decision}. Flow resumption started in background."
        }
    except Exception as exc:
        raise map_exception_to_mcp_error(exc)
