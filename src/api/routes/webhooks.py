"""POST /webhooks/trigger — Entrypoint for external event-driven flow execution."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, BackgroundTasks, Depends
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from uuid import uuid4
import logging
import asyncio

from ...flows.registry import flow_registry
from ..middleware import require_org_id

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/webhooks", tags=["webhooks"])


def _run_async_in_background(coro):
    """Wrapper para ejecutar coroutines async en background tasks síncronos."""
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            asyncio.ensure_future(coro)
        else:
            loop.run_until_complete(coro)
    except RuntimeError:
        asyncio.run(coro)


# ── request / response models ──────────────────────────────────


class WebhookTriggerRequest(BaseModel):
    flow_type: str = Field(..., description="Registered flow name")
    input_data: Dict[str, Any] = Field(
        default_factory=dict, description="Input payload"
    )
    callback_url: Optional[str] = Field(None, description="URL for completion callback")


class WebhookTriggerResponse(BaseModel):
    task_id: str
    correlation_id: str
    status: str = "accepted"


# ── route ───────────────────────────────────────────────────────


@router.post(
    "/trigger",
    response_model=WebhookTriggerResponse,
    status_code=202,
)
async def trigger_webhook(
    request: WebhookTriggerRequest,
    background_tasks: BackgroundTasks,
    org_id: str = Depends(require_org_id),
):
    """
    Accept an external trigger, validate the flow exists, and launch
    it in a FastAPI background task.  Returns **202 Accepted** immediately.
    """
    logger.info(
        "Webhook trigger received: flow_type=%s, org_id=%s",
        request.flow_type,
        org_id,
    )

    if not flow_registry.has(request.flow_type):
        raise HTTPException(
            status_code=400,
            detail=(
                f"Flow '{request.flow_type}' not found. "
                f"Available: {flow_registry.list_flows()}"
            ),
        )

    correlation_id = str(uuid4())

    background_tasks.add_task(
        _run_async_in_background,
        execute_flow(
            flow_type=request.flow_type,
            org_id=org_id,
            input_data=request.input_data,
            correlation_id=correlation_id,
            callback_url=request.callback_url,
        ),
    )

    return WebhookTriggerResponse(
        task_id="pending",  # real id assigned inside create_task_record
        correlation_id=correlation_id,
        status="accepted",
    )


# ── background execution ───────────────────────────────────────


async def execute_flow(
    flow_type: str,
    org_id: str,
    input_data: Dict[str, Any],
    correlation_id: str,
    callback_url: Optional[str] = None,
) -> Dict[str, Any]:
    """Run a flow in the background — called by ``BackgroundTasks``.

    Returns a dict with:
      - task_id: str or None
      - error: str or None
      - error_type: str or None

    The caller can determine success by checking if result["error"] is None.
    """
    result: Dict[str, Any] = {"task_id": None, "error": None, "error_type": None}
    flow = None
    try:
        flow_class = flow_registry.get(flow_type)
        flow = flow_class(org_id=org_id)
        task_id = await flow.execute(input_data, correlation_id)
        result["task_id"] = task_id

        if callback_url:
            await _send_callback(callback_url, flow.state)

    except Exception as exc:
        logger.error("Background flow execution failed: %s", exc)
        result["error"] = str(exc)
        result["error_type"] = type(exc).__name__
        # Try to capture task_id from flow state if it was set before the exception
        if flow and hasattr(flow, 'state') and hasattr(flow.state, 'task_id') and flow.state.task_id:
            result["task_id"] = flow.state.task_id

    return result


async def _send_callback(callback_url: str, state) -> None:
    """Best-effort HTTP callback on completion."""
    import httpx

    async with httpx.AsyncClient() as client:
        await client.post(
            callback_url,
            json={
                "task_id": state.task_id,
                "status": state.status,
                "result": state.output_data,
            },
        )
