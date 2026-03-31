"""BaseFlow — Abstract base class defining the complete flow lifecycle.

Lifecycle:  validate_input → create_task_record → start → _run_crew → complete/fail

The ``@with_error_handling`` decorator ensures that any unhandled exception
during execution marks the state as FAILED and persists it before re-raising.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional, Dict, Any
from datetime import datetime, timezone
from functools import wraps
from uuid import uuid4
import logging
import traceback

from .state import BaseFlowState, FlowStatus
from ..db.session import get_tenant_client
from ..events.store import EventStore

logger = logging.getLogger(__name__)


# ── error-handling decorator ────────────────────────────────────

def with_error_handling(func):
    """Decorator: on exception → mark state as FAILED, persist, re-raise."""

    @wraps(func)
    async def wrapper(self: "BaseFlow", *args, **kwargs):
        try:
            return await func(self, *args, **kwargs)
        except Exception as exc:
            logger.error("Error in %s: %s", func.__name__, exc)
            logger.error(traceback.format_exc())
            if self.state is not None:
                self.state.fail(str(exc))
                try:
                    await self.persist_state()
                except Exception:
                    logger.error("Failed to persist FAILED state")
            raise

    return wrapper


# ── BaseFlow ────────────────────────────────────────────────────

class BaseFlow(ABC):
    """
    Abstract orchestrator for a single flow execution.

    Subclasses must implement:
    - ``validate_input(input_data) -> bool``
    - ``_run_crew() -> Dict[str, Any]``
    """

    def __init__(
        self,
        org_id: str,
        user_id: Optional[str] = None,
        **kwargs: Any,
    ) -> None:
        self.org_id = org_id
        self.user_id = user_id
        self.state: Optional[BaseFlowState] = None
        self.event_store: Optional[EventStore] = None
        self.extra_kwargs = kwargs

    # ── abstract contract ───────────────────────────────────────

    @abstractmethod
    def validate_input(self, input_data: Dict[str, Any]) -> bool:
        """Return True if *input_data* is valid for this flow."""

    @abstractmethod
    async def _run_crew(self) -> Dict[str, Any]:
        """Execute the CrewAI crew and return the result dict."""

    # ── lifecycle ───────────────────────────────────────────────

    @with_error_handling
    async def execute(
        self,
        input_data: Dict[str, Any],
        correlation_id: Optional[str] = None,
    ) -> BaseFlowState:
        """
        Full lifecycle:
        1. validate input
        2. create task record
        3. start (set RUNNING)
        4. run crew
        5. complete or fail
        """
        logger.info(
            "Starting flow %s for org %s", self.__class__.__name__, self.org_id
        )

        # 1. Validate
        if not self.validate_input(input_data):
            raise ValueError("Input validation failed")

        # 2. Create task row + initialise state
        await self.create_task_record(input_data, correlation_id)

        # 3. Mark as RUNNING
        self.state.start()
        await self.persist_state()

        # 4. Execute crew
        try:
            result = await self._run_crew()

            # 5. Complete
            self.state.complete(result)
            await self.emit_event("flow.completed", {"result": result})
        except Exception as exc:
            logger.error("Flow failed: %s", exc)
            raise

        await self.persist_state()
        return self.state

    # ── persistence helpers ─────────────────────────────────────

    async def create_task_record(
        self,
        input_data: Dict[str, Any],
        correlation_id: Optional[str] = None,
    ) -> None:
        """Insert a row into ``tasks`` and initialise ``self.state``."""
        task_id = str(uuid4())

        with get_tenant_client(self.org_id, self.user_id) as db:
            db.table("tasks").insert(
                {
                    "id": task_id,
                    "org_id": self.org_id,
                    "flow_type": self.__class__.__name__,
                    "status": "pending",
                    "payload": input_data,
                    "correlation_id": correlation_id,
                }
            ).execute()

        self.state = BaseFlowState(
            task_id=task_id,
            org_id=self.org_id,
            user_id=self.user_id,
            flow_type=self.__class__.__name__,
            input_data=input_data,
            correlation_id=correlation_id,
        )

        self.event_store = EventStore(self.org_id, self.user_id)
        await self.emit_event("flow.created", {"input_data": input_data})

    async def persist_state(self) -> None:
        """Upsert into ``snapshots`` and update ``tasks``."""
        if self.state is None:
            return

        with get_tenant_client(self.org_id, self.user_id) as db:
            snapshot = self.state.to_snapshot()
            db.table("snapshots").upsert(snapshot).execute()

            db.table("tasks").update(
                {
                    "status": self.state.status,
                    "result": self.state.output_data if self.state.output_data else None,
                    "error": self.state.error,
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                }
            ).eq("id", self.state.task_id).execute()

    async def emit_event(
        self, event_type: str, payload: Dict[str, Any]
    ) -> None:
        """Append a domain event and flush to DB."""
        if self.event_store and self.state:
            self.event_store.append(
                aggregate_type="flow",
                aggregate_id=self.state.task_id,
                event_type=event_type,
                payload=payload,
            )
            await self.event_store.flush()
