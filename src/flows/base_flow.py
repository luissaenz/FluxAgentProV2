"""BaseFlow — Abstract base class defining the complete flow lifecycle.

Phase 2 extension: Human-in-the-Loop (HITL) pause and resume.

Lifecycle: validate_input → create_task_record → start → _run_crew
                                                        ↓
                                           [si requiere aprobación]
                                           request_approval() → pausar
                                                        ↓
                                           [supervisor decide]
                                           resume() → continuar o rechazar
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
from ..db.session import get_tenant_client, get_service_client
from ..events.store import EventStore, EventStoreError

logger = logging.getLogger(__name__)


# ── error-handling decorator ───────────────────────────────────

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


# ── BaseFlow ───────────────────────────────────────────────────

class BaseFlow(ABC):
    """
    Abstract orchestrator for a single flow execution.

    Phase 2 adds HITL: the flow can pause at an approval point,
    serialize its state, and resume after supervisor decision.

    Subclasses must implement:
    - ``validate_input(input_data) -> bool``
    - ``_run_crew() -> Dict[str, Any]``
    - ``_on_approved()`` — optional hook for post-approval logic
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

            # Phase 2: If the flow was paused for approval during _run_crew,
            # we must NOT mark it as complete.
            if self.state.status == FlowStatus.AWAITING_APPROVAL:
                logger.info(
                    "Flow %s paused for approval. Sequential execution stopped.",
                    self.state.task_id
                )
                await self.persist_state()
                return self.state

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
                    "flow_id": task_id,
                    "status": "pending",
                    "payload": input_data,
                    "correlation_id": correlation_id,
                    "max_retries": self.extra_kwargs.get("max_retries", 3),
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
        """
        Upsert into ``snapshots`` and update ``tasks``.

        Uses the Phase 1 schema (state_json). For HITL, use _persist_state_v2().
        """
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
                    "approval_required": self.state.approval_payload is not None,
                    "approval_status": (
                        "pending"
                        if self.state.status == FlowStatus.AWAITING_APPROVAL.value
                        else "none"
                    ),
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

    # ── HITL: Human-in-the-Loop ─────────────────────────────────

    async def request_approval(self, description: str, payload: dict) -> None:
        """
        Pausar el Flow y solicitar aprobación al supervisor.

        SECUENCIA:
        1. Serializar FlowState → snapshot en DB (esquema v2 con aggregate_*)
        2. Crear fila en pending_approvals
        3. Actualizar task.status = "pending_approval"
        4. Emitir evento "approval.requested" (bloqueante)
        5. Retornar — el Flow termina aquí

        El Flow se detiene cuando este método retorna.
        La reanudación ocurre vía POST /approvals/{task_id}.

        Args:
            description: Texto legible para el supervisor
            payload: Datos que el supervisor necesita ver para decidir
        """
        # 1. Marcar estado como awaiting approval
        self.state.await_approval()
        self.state.approval_payload = payload

        svc = get_service_client()

        # 2. Guardar snapshot con esquema v2 (aggregate_*)
        seq = svc.rpc("next_event_sequence", {
            "p_aggregate_type": "flow",
            "p_aggregate_id": self.state.task_id
        }).execute().data

        svc.table("snapshots").upsert(
            self.state.to_snapshot_v2(version=seq),
            on_conflict="task_id"
        ).execute()

        # 3. Crear pending_approval (usa tenant client para RLS)
        with get_tenant_client(self.org_id, self.user_id) as db:
            db.table("pending_approvals").insert({
                "org_id": self.org_id,
                "task_id": self.state.task_id,
                "flow_type": self.flow_type,
                "description": description,
                "payload": payload,
            }).execute()

        # 4. Actualizar task
        await self.persist_state()

        # 5. Emitir evento bloqueante
        # Regla R6: el Flow no avanza hasta confirmar el evento
        try:
            EventStore.append_sync(
                org_id=self.org_id,
                aggregate_type="flow",
                aggregate_id=self.state.task_id,
                event_type="approval.requested",
                payload={"description": description},
                actor=f"flow:{self.__class__.__name__}"
            )
        except EventStoreError:
            # El Flow debe detenerse si no se puede registrar el evento
            logger.error("Cannot emit approval.requested event — halting flow")
            raise

        # El método retorna → el paso del Flow termina → el proceso puede finalizar

    async def resume(self, task_id: str, decision: str, decided_by: str) -> None:
        """
        Reanudar un Flow pausado después de la decisión del supervisor.

        Llamado desde POST /approvals/{task_id} después de que el supervisor decide.

        Args:
            task_id: ID de la tarea a reanudar
            decision: "approved" | "rejected"
            decided_by: Identificador del supervisor que decidió
        """
        svc = get_service_client()

        # 1. Restaurar snapshot
        snapshot = (
            svc.table("snapshots")
            .select("*")
            .eq("aggregate_id", task_id)
            .eq("aggregate_type", "flow")
            .maybe_single()
            .execute()
        )

        if not snapshot.data:
            raise ValueError(f"No snapshot found for task {task_id}")

        # 2. Reconstruir estado
        self.state = BaseFlowState.from_snapshot(snapshot.data)
        self.state.approval_decision = decision
        self.state.approval_decided_by = decided_by

        # 3. Actualizar event_store
        self.event_store = EventStore(self.org_id, self.user_id)

        # 4. Emitir evento de decisión
        try:
            EventStore.append_sync(
                org_id=self.org_id,
                aggregate_type="flow",
                aggregate_id=self.state.task_id,
                event_type=f"approval.{decision}",
                payload={"decided_by": decided_by},
                actor=f"user:{decided_by}"
            )
        except EventStoreError:
            logger.error("Cannot emit approval.%s event", decision)
            raise

        # 5. Continuar según decisión
        if decision == "approved":
            await self._on_approved()
        else:
            await self._on_rejected(decided_by)

    async def _on_approved(self) -> None:
        """
        Hook: se llama después de que el supervisor aprueba.

        Override en subclases para definir qué hacer post-aprobación.
        Por defecto, marca como COMPLETED y persiste.
        """
        self.state.approval_payload = None  # Limpiar tras usar
        self.state.complete({"approval": "accepted"})
        await self.persist_state()
        await self.emit_event("flow.completed", {"decision": "approved"})

    async def _on_rejected(self, decided_by: str) -> None:
        """
        Hook: se llama después de que el supervisor rechaza.

        Override en subclases para definir qué hacer tras rechazo.
        Por defecto, marca el Flow como FAILED.
        """
        self.state.fail(f"Rejected by supervisor: {decided_by}")
        await self.persist_state()
        await self.emit_event("flow.rejected", {"decided_by": decided_by})

    # ── Properties ─────────────────────────────────────────────

    @property
    def flow_type(self) -> str:
        """Return the flow type name for DB records."""
        return self.__class__.__name__
