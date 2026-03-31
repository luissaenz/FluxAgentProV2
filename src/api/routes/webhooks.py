"""POST /webhooks/trigger — Entrypoint for external event-driven flow execution."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, BackgroundTasks, Depends
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from uuid import uuid4
import logging

from ...flows.registry import flow_registry
from ..middleware import require_org_id

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/webhooks", tags=["webhooks"])


# ── request / response models ──────────────────────────────────

class WebhookTriggerRequest(BaseModel):
    flow_type: str = Field(..., description="Registered flow name")
    input_data: Dict[str, Any] = Field(default_factory=dict, description="Input payload")
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
        execute_flow,
        flow_type=request.flow_type,
        org_id=org_id,
        input_data=request.input_data,
        correlation_id=correlation_id,
        callback_url=request.callback_url,
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
) -> None:
    """Run a flow in the background — called by ``BackgroundTasks``."""
    try:
        flow_class = flow_registry.get(flow_type)
        flow = flow_class(org_id=org_id)
        await flow.execute(input_data, correlation_id)

        if callback_url:
            await _send_callback(callback_url, flow.state)
    except Exception as exc:
        logger.error("Background flow execution failed: %s", exc)


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
