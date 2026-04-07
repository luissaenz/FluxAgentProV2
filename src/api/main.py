"""FastAPI application — root entry point.

Importing ``generic_flow`` at module level triggers its ``@register_flow``
decorator, ensuring it is available before the first request arrives.
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import logging

# ── eager flow registration (import triggers @register_flow) ─────
import src.flows.generic_flow  # noqa: F401
import src.flows.architect_flow  # noqa: F401
import src.flows.coctel_flows  # noqa: F401  — Phase 5B CoctelPro
import src.tools.builtin  # noqa: F401

from .routes.webhooks import router as webhooks_router
from .routes.tasks import router as tasks_router
from .routes.approvals import router as approvals_router
from .routes.chat import router as chat_router
from .routes.workflows import router as workflows_router
from .routes.bartenders import router as bartenders_router
from .routes.flow_metrics import router as flow_metrics_router
from .routes.flows import router as flows_router
from src.flows.bartenders.registry_wiring import register_bartenders_flows
from src.scheduler.bartenders_jobs import scheduler

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

    # Phase 6: Bartenders NOA — registro de flows y scheduler
    register_bartenders_flows()
    scheduler.start()

    try:
        count = load_dynamic_flows_from_db()
        logger.info("Dynamic workflows loaded: %d", count)
    except Exception as exc:
        logger.warning("Could not load dynamic flows from DB: %s", exc)

    yield

    # Shutdown — parar scheduler
    scheduler.shutdown(wait=False)


# ── app ─────────────────────────────────────────────────────────

app = FastAPI(
    title="FluxAgentPro-v2",
    description="AI Agent Orchestration Engine — Phase 4 Conversational",
    version="4.0.0",
    lifespan=lifespan,
)

# ── CORS (Phase 5: Dashboard on localhost:3000) ─────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(webhooks_router)
app.include_router(tasks_router)
app.include_router(approvals_router)
app.include_router(chat_router)
app.include_router(workflows_router)
app.include_router(bartenders_router)  # Phase 6: Bartenders NOA
app.include_router(flow_metrics_router)
app.include_router(flows_router)  # Semana 2: flows disponibles y ejecución


@app.get("/health")
async def health():
    """Basic liveness probe."""
    return {"status": "ok"}
