"""EventStore — Append-only event store backed by Supabase.

Phase 2 extension: adds append_sync() for direct synchronous writes
(HITL flows that cannot use the queue+flush pattern).

Events are appended synchronously during flow execution, then flushed in a
single batch insert to guarantee atomicity.
"""

from __future__ import annotations

from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime, timezone
from uuid import uuid4
import logging

from ..db.session import get_tenant_client, get_service_client

logger = logging.getLogger(__name__)


@dataclass
class DomainEvent:
    """Immutable domain event waiting in the flush queue."""

    event_id: str = field(default_factory=lambda: str(uuid4()))
    org_id: str = ""
    aggregate_type: str = ""
    aggregate_id: str = ""
    event_type: str = ""
    payload: Dict[str, Any] = field(default_factory=dict)
    actor: Optional[str] = None
    sequence: int = 0
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class EventStoreError(Exception):
    """El Flow debe detenerse si se lanza este error (Regla R6)."""
    pass


class EventStore:
    """
    Append-only event store backed by Supabase.

    Supports two modes:
    - Instance mode (Phase 1): append() to queue + flush() batch insert
    - Static mode (Phase 2): append_sync() direct blocking write

    Usage (Phase 1)::

        store = EventStore(org_id, user_id)
        store.append("flow", task_id, "flow.created", {"input": ...})
        await store.flush()

    Usage (Phase 2 - HITL)::

        EventStore.append_sync(
            org_id=org_id,
            aggregate_type="flow",
            aggregate_id=task_id,
            event_type="approval.requested",
            payload={"description": description},
            actor=f"flow:{flow_class.__name__}"
        )
    """

    def __init__(self, org_id: str, user_id: Optional[str] = None) -> None:
        self.org_id = org_id
        self.user_id = user_id
        self._queue: List[DomainEvent] = []
        self._sequence = 0

    # ── Instance API (Phase 1 — queue + flush) ─────────────────

    def append(
        self,
        aggregate_type: str,
        aggregate_id: str,
        event_type: str,
        payload: Dict[str, Any],
    ) -> None:
        """Enqueue an event (synchronous — no I/O)."""
        self._sequence += 1
        event = DomainEvent(
            org_id=self.org_id,
            aggregate_type=aggregate_type,
            aggregate_id=aggregate_id,
            event_type=event_type,
            payload=payload,
            actor=self.user_id,
            sequence=self._sequence,
        )
        self._queue.append(event)
        logger.debug(
            "Event appended: %s for %s:%s", event_type, aggregate_type, aggregate_id
        )

    async def flush(self) -> None:
        """Batch-insert all queued events into ``domain_events``."""
        if not self._queue:
            return

        with get_tenant_client(self.org_id, self.user_id) as db:
            rows = [
                {
                    "id": e.event_id,
                    "org_id": e.org_id,
                    "aggregate_type": e.aggregate_type,
                    "aggregate_id": e.aggregate_id,
                    "event_type": e.event_type,
                    "payload": e.payload,
                    "actor": e.actor,
                    "sequence": e.sequence,
                }
                for e in self._queue
            ]
            db.table("domain_events").insert(rows).execute()

        logger.info("Flushed %d events to DB", len(self._queue))
        self._queue.clear()

    def clear(self) -> None:
        """Discard pending events without flushing."""
        self._queue.clear()
        self._sequence = 0

    # ── Static API (Phase 2 — direct synchronous write) ─────────

    @staticmethod
    def append_sync(
        org_id: str,
        aggregate_type: str,
        aggregate_id: str,
        event_type: str,
        payload: Dict[str, Any],
        actor: Optional[str] = None,
    ) -> None:
        """
        Escribir un evento inmutable de forma BLOQUEANTE.

        Regla R6: EventStore.append_sync() es bloqueante.
        El Flow no avanza al siguiente paso hasta confirmar el evento en DB.

        Raises:
            EventStoreError: Si no se puede escribir el evento.

        Usage:
            # Dentro de request_approval() o fuera del ciclo de vida del Flow
            EventStore.append_sync(
                org_id=self.state.org_id,
                aggregate_type="flow",
                aggregate_id=self.state.task_id,
                event_type="approval.requested",
                payload={"description": description},
                actor=f"flow:{self.__class__.__name__}"
            )
        """
        try:
            # Use TenantClient to set app.org_id for RLS
            with get_tenant_client(org_id) as db:
                # Obtener siguiente secuencia atómica (con FOR UPDATE)
                seq_result = db.rpc("next_event_sequence", {
                    "p_aggregate_type": aggregate_type,
                    "p_aggregate_id": aggregate_id
                }).execute()

                sequence = seq_result.data

                # Insertar evento (append-only, RLS valida org_id)
                db.table("domain_events").insert({
                    "org_id": org_id,
                    "aggregate_type": aggregate_type,
                    "aggregate_id": aggregate_id,
                    "event_type": event_type,
                    "payload": payload,
                    "actor": actor or "system",
                    "sequence": sequence,
                }).execute()

            logger.debug(
                "Event appended_sync: %s seq=%d agg=%s",
                event_type, sequence, aggregate_id
            )

        except Exception as e:
            logger.error("EventStore.append_sync failed: %s — %s", event_type, e)
            raise EventStoreError(
                f"EventStore write failed for event '{event_type}': {e}"
            )
