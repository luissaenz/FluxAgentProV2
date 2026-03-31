"""EventStore — In-memory queue with transactional flush to ``domain_events``.

Events are appended synchronously during flow execution, then flushed in a
single batch insert to guarantee atomicity.
"""

from __future__ import annotations

from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime, timezone
from uuid import uuid4
import logging

from ..db.session import get_tenant_client

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


class EventStore:
    """
    Append-only event store backed by Supabase.

    Usage::

        store = EventStore(org_id, user_id)
        store.append("flow", task_id, "flow.created", {"input": ...})
        await store.flush()   # batch insert
    """

    def __init__(self, org_id: str, user_id: Optional[str] = None) -> None:
        self.org_id = org_id
        self.user_id = user_id
        self._queue: List[DomainEvent] = []
        self._sequence = 0

    # ── public API ──────────────────────────────────────────────

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
