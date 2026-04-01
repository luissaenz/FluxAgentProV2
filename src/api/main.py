"""FastAPI application — root entry point.

Importing ``generic_flow`` at module level triggers its ``@register_flow``
decorator, ensuring it is available before the first request arrives.
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from fastapi import FastAPI
import logging

# ── eager flow registration (import triggers @register_flow) ─────
import src.flows.generic_flow   # noqa: F401
import src.flows.architect_flow   # noqa: F401
import src.tools.builtin        # noqa: F401

from .routes.webhooks import router as webhooks_router
from .routes.tasks import router as tasks_router
from .routes.approvals import router as approvals_router
from .routes.chat import router as chat_router
from .routes.workflows import router as workflows_router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

logger = logging.getLogger(__name__)


# ── lifespan ─────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(_app: FastAPI):
    """Cargar workflows generados previamente desde la DB al arrancar."""
    from src.flows.dynamic_flow import load_dynamic_flows_from_db

    try:
        count = load_dynamic_flows_from_db()
        logger.info("Dynamic workflows loaded: %d", count)
    except Exception as exc:
        logger.warning("Could not load dynamic flows from DB: %s", exc)

    yield


# ── app ─────────────────────────────────────────────────────────

app = FastAPI(
    title="FluxAgentPro-v2",
    description="AI Agent Orchestration Engine — Phase 4 Conversational",
    version="4.0.0",
    lifespan=lifespan,
)

app.include_router(webhooks_router)
app.include_router(tasks_router)
app.include_router(approvals_router)
app.include_router(chat_router)
app.include_router(workflows_router)


@app.get("/health")
async def health():
    """Basic liveness probe."""
    return {"status": "ok"}
