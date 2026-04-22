"""MCP Handlers — Implementation of JSON-RPC methods for FluxAgentPro.

Key handlers:
- handle_execute_flow: Starts a workflow.
- handle_get_task: Polls for workflow status.
- handle_approve_task / handle_reject_task: HITL decision points.
"""

from __future__ import annotations

import logging
import datetime
from typing import Any, Dict, Optional
from uuid import uuid4

from ..flows.registry import flow_registry
from ..flows.state import BaseFlowState
from ..db.session import get_service_client
from .exceptions import MethodNotFound, NotFound
from .auth import verify_org_membership

logger = logging.getLogger(__name__)


async def handle_execute_flow(
    org_id: str,
    flow_type: str,
    input_data: Dict[str, Any],
    claims: Dict[str, Any],
    correlation_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Execute a registered flow.

    Args:
        org_id: Organization UUID.
        flow_type: Name of the registered flow (snake_case).
        input_data: Payload for the flow.
        claims: Decoded JWT claims for authorization.
        correlation_id: Optional tracing ID for end-to-end observability.

    Returns:
        dict: {task_id, status, correlation_id}
    """
    # 1. Authorize
    auth_info = verify_org_membership(org_id, claims)
    user_id = auth_info["user_id"]

    # 2. Check flow existence
    if not flow_registry.has(flow_type):
        available = flow_registry.list_flows()
        raise MethodNotFound(
            f"Flow '{flow_type}' not found. Available: {available}"
        )

    # 3. Prepare execution context
    if not correlation_id:
        correlation_id = f"mcp-{flow_type}-{uuid4().hex[:8]}"

    # 4. Instantiate and execute via the Registry
    # Flow.execute() handles task creation in DB (tasks table) and initial state persistence.
    flow_class = flow_registry.get(flow_type)
    flow = flow_class(org_id=org_id, user_id=user_id)

    # Note: For long-running flows in production, this should be dispatched to a worker.
    # Currently running in the current event loop.
    state = await flow.execute(input_data, correlation_id=correlation_id)

    return {
        "task_id": state.task_id,
        "status": state.status,
        "correlation_id": correlation_id
    }


async def handle_get_task(
    org_id: str,
    task_id: str,
    claims: Dict[str, Any],
) -> Dict[str, Any]:
    """Retrieve the current state of a task from snapshots.

    Args:
        org_id: Organization UUID.
        task_id: Task UUID.
        claims: Decoded JWT claims.

    Returns:
        dict: Serialized BaseFlowState.
    """
    # 1. Authorize
    verify_org_membership(org_id, claims)

    # 2. Query snapshot (source of truth for state serialization)
    svc = get_service_client()
    snapshot = (
        svc.table("snapshots")
        .select("*")
        .eq("task_id", task_id)
        .eq("org_id", org_id)
        .maybe_single()
        .execute()
    )

    if not snapshot.data:
        # Fallback: check tasks table to see if it even exists
        task = (
            svc.table("tasks")
            .select("status")
            .eq("id", task_id)
            .eq("org_id", org_id)
            .maybe_single()
            .execute()
        )
        if not task.data:
            raise NotFound(f"Task {task_id} not found for org {org_id}")
        
        # If task exists but no snapshot, it might be in early 'pending' state
        return {
            "task_id": task_id,
            "status": task.data["status"],
            "message": "Snapshot not yet generated"
        }

    # 3. Reconstruct and format response
    state = BaseFlowState.from_snapshot(snapshot.data)
    return state.model_dump(mode="json")


async def handle_approve_task(
    org_id: str,
    task_id: str,
    claims: Dict[str, Any],
) -> Dict[str, Any]:
    """Approve a task awaiting human intervention."""
    return await _process_decision(org_id, task_id, claims, "approved")


async def handle_reject_task(
    org_id: str,
    task_id: str,
    claims: Dict[str, Any],
) -> Dict[str, Any]:
    """Reject a task awaiting human intervention."""
    return await _process_decision(org_id, task_id, claims, "rejected")


async def _process_decision(
    org_id: str,
    task_id: str,
    claims: Dict[str, Any],
    decision: str
) -> Dict[str, Any]:
    """Common logic for HITL decisions. Updates DB and resumes flow."""
    # 1. Authorize
    auth_info = verify_org_membership(org_id, claims)
    user_id = auth_info["user_id"]

    # 2. Validate existence and pending status in pending_approvals
    svc = get_service_client()
    pending = (
        svc.table("pending_approvals")
        .select("*")
        .eq("task_id", task_id)
        .eq("org_id", org_id)
        .eq("status", "pending")
        .maybe_single()
        .execute()
    )

    if not pending.data:
        raise NotFound(f"No pending approval found for task {task_id} with status 'pending'")

    # 3. Update pending_approvals record
    svc.table("pending_approvals").update({
        "status": decision,
        "decided_by": user_id,
        "decided_at": datetime.datetime.now(datetime.timezone.utc).isoformat()
    }).eq("id", pending.data["id"]).execute()

    # 4. Resume flow execution
    # We retrieve the flow_type from the pending record to instantiate the right class
    flow_type = pending.data["flow_type"]
    flow_class = flow_registry.get(flow_type)
    flow = flow_class(org_id=org_id, user_id=user_id)

    # resume() restores state from snapshot, emits domain events, and continues logic
    await flow.resume(task_id=task_id, decision=decision, decided_by=user_id)

    return {
        "task_id": task_id,
        "status": flow.state.status if flow.state else "processed",
        "decision": decision
    }

