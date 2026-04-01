"""FastAPI application — root entry point.

Importing ``generic_flow`` at module level triggers its ``@register_flow``
decorator, ensuring it is available before the first request arrives.
"""

from __future__ import annotations

from fastapi import FastAPI
import logging

# ── eager flow registration (import triggers @register_flow) ─────
import src.flows.generic_flow  # noqa: F401
import src.tools.builtin       # noqa: F401

from .routes.webhooks import router as webhooks_router
from .routes.tasks import router as tasks_router
from .routes.approvals import router as approvals_router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

logger = logging.getLogger(__name__)

# ── app ─────────────────────────────────────────────────────────

app = FastAPI(
    title="FluxAgentPro-v2",
    description="AI Agent Orchestration Engine — Phase 2 Governance",
    version="2.0.0",
)

app.include_router(webhooks_router)
app.include_router(tasks_router)
app.include_router(approvals_router)


@app.get("/health")
async def health():
    """Basic liveness probe."""
    return {"status": "ok"}
