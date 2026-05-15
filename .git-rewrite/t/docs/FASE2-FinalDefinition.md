# FASE 2 — Final Definition
## Gobernanza: HITL, Vault y Guardrails

**Versión:** 2.0.0
**Fecha:** 2026-04-01
**Fase anterior:** Fase 1 — Motor Base (scaffold completo)
**Fase siguiente:** Fase 3 — Multi-agente y memoria semántica

---

## Tabla de Contenidos

1. [Visión del sistema](#00--visión-del-sistema)
2. [Stack tecnológico y dependencias](#01--stack-tecnológico)
3. [Estructura de directorios](#02--estructura-del-proyecto)
4. [Migraciones SQL incrementales](#03--migraciones-sql)
5. [BaseFlowState — Extensión HITL](#04--baseflowstate--extensión-hitl)
6. [EventStore — Extensión síncrona](#05--eventstore--extensión-síncrona)
7. [BaseFlow — Extensión HITL](#06--baseflow--extensión-hitl)
8. [Vault: gestión de secretos](#07--vault--gestión-de-secretos)
9. [Tools con Vault integrado](#08--tools--con-vault-integrado)
10. [Guardrails](#09--guardrails)
11. [API: endpoint de aprobaciones](#10--api--endpoint-de-aprobaciones)
12. [API Routes: estructura final](#11--api-routes--estructura-final)
13. [Tests de Fase 2](#12--tests-de-fase-2)
14. [Entregables verificables](#13--entregables-verificables)
15. [Reglas invariantes del proyecto](#14--reglas-invariantes)
16. [Gotchas de CrewAI](#15--gotchas-de-crewai)

---

## 00 — Visión del sistema

### Qué construir

Sistema de gobernanza que garantiza que ninguna acción crítica se ejecuta sin aprobación humana. Los secretos externos nunca son visibles para los agentes. Las reglas de negocio validan operaciones antes de ejecutarse.

### Cómo funciona

- Un Flow llega a un paso que requiere aprobación → serializa su estado en `snapshots` → crea fila en `pending_approvals` → termina
- El supervisor recibe la notificación → decide en `/approvals/{task_id}`
- El sistema restaura el Flow desde el snapshot → continúa o rechaza según decisión
- Las credenciales externas se obtienen via VaultProxy, nunca llegan al LLM
- Los Guardrails evalúan umbrales de negocio antes de solicitar aprobación

### Criterio de éxito

Un Flow puede pausarse y reanudarse correctamente. El LLM mockeado nunca recibe un secreto en claro. Los Guardrails bloquean operaciones que violen reglas de negocio.

---

## 01 — Stack tecnológico

### Dependencias a agregar en `pyproject.toml`

```toml
[project.dependencies]
# ... dependencias existentes de Fase 1 ...

# NUEVAS para Fase 2
pgvector = "^0.3.0"              # Para memory_vectors (Fase 3, se agrega aquí anticipadamente)
openai = "^1.58.0"              # Para embeddings text-embedding-3-small
```

> **Nota:** `psycopg2-binary` y `mcp` se agregarán en Fase 3.

---

## 02 — Estructura del proyecto

**Principio:** Mantener la estructura de Fase 1 y agregar solo lo nuevo. No mover archivos existentes.

```
src/
├── flows/
│   ├── registry.py          # EXISTE (Fase 1)
│   ├── state.py             # MODIFICADO (agregar campos HITL)
│   ├── base_flow.py         # MODIFICADO (agregar request_approval, resume)
│   └── generic_flow.py      # EXISTE (Fase 1)
│
├── crews/
│   ├── generic_crew.py      # EXISTE (Fase 1)
│   └── base_crew.py          # NUEVO (carga soul desde DB, instancia Agent)
│
├── tools/
│   ├── registry.py          # EXISTE (Fase 1)
│   ├── builtin.py           # EXISTE (Fase 1)
│   └── base_tool.py         # NUEVO (OrgBaseTool con vault)
│
├── db/
│   ├── session.py           # MODIFICADO (agregar get_service_client)
│   ├── vault.py             # NUEVO
│   └── memory.py             # NUEVO (Fase 3, se anticipa)
│
├── events/
│   └── store.py             # MODIFICADO (agregar append_sync estático)
│
├── guardrails/              # NUEVO directorio
│   └── base_guardrail.py    # NUEVO
│
└── api/
    ├── main.py               # MODIFICADO (agregar router de approvals)
    ├── middleware.py          # EXISTE (Fase 1)
    └── routes/
        ├── webhooks.py       # EXISTE (Fase 1)
        ├── tasks.py          # EXISTE (Fase 1)
        └── approvals.py      # NUEVO
```

---

## 03 — Migraciones SQL

Todas las migraciones son **incrementales** sobre `001_set_config_rpc.sql`. Se ejecutan en orden numérico.

### `supabase/migrations/002_governance.sql`

```sql
-- ============================================================
-- Migration 002: Gobernanza — HITL, Vault, columnas adicionales
-- Ejecutar DESPUÉS de 001_set_config_rpc.sql
-- ============================================================

-- -----------------------------------------------------------
-- 1. Extender organizations con columnas de Fase 2
-- -----------------------------------------------------------
ALTER TABLE organizations
    ADD COLUMN IF NOT EXISTS config       JSONB DEFAULT '{}',
    ADD COLUMN IF NOT EXISTS billing_plan TEXT DEFAULT 'free',
    ADD COLUMN IF NOT EXISTS quota        JSONB DEFAULT '{"max_tasks_per_month":500,"max_tokens_per_month":5000000}',
    ADD COLUMN IF NOT EXISTS is_active    BOOLEAN DEFAULT TRUE;


-- -----------------------------------------------------------
-- 2. Extender tasks con columnas de Fase 2
-- -----------------------------------------------------------
ALTER TABLE tasks
    ADD COLUMN IF NOT EXISTS flow_id              TEXT,
    ADD COLUMN IF NOT EXISTS assigned_agent_role   TEXT,
    ADD COLUMN IF NOT EXISTS approval_required     BOOLEAN DEFAULT FALSE,
    ADD COLUMN IF NOT EXISTS approval_status      TEXT DEFAULT 'none',
    ADD COLUMN IF NOT EXISTS approval_payload      JSONB,
    ADD COLUMN IF NOT EXISTS idempotency_key       TEXT UNIQUE,
    ADD COLUMN IF NOT EXISTS retries              INTEGER DEFAULT 0,
    ADD COLUMN IF NOT EXISTS max_retries          INTEGER DEFAULT 3,
    ADD COLUMN IF NOT EXISTS tokens_used          INTEGER DEFAULT 0;

-- Backfill flow_id desde id para datos existentes
UPDATE tasks SET flow_id = id::text WHERE flow_id IS NULL;
ALTER TABLE tasks ALTER COLUMN flow_id SET NOT NULL;

-- -----------------------------------------------------------
-- 3. Extender snapshots con columnas de Fase 2 (aggregate)
-- -----------------------------------------------------------
ALTER TABLE snapshots
    ADD COLUMN IF NOT EXISTS aggregate_type TEXT DEFAULT 'flow',
    ADD COLUMN IF NOT EXISTS aggregate_id   TEXT,
    ADD COLUMN IF NOT EXISTS version        BIGINT DEFAULT 0;

-- Backfill aggregate_id desde task_id para datos existentes
UPDATE snapshots SET aggregate_id = task_id::text WHERE aggregate_id IS NULL;


-- -----------------------------------------------------------
-- 4. Tabla: pending_approvals (aprobaciones HITL)
-- -----------------------------------------------------------
CREATE TABLE IF NOT EXISTS pending_approvals (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id      UUID NOT NULL REFERENCES organizations(id),
    task_id     UUID NOT NULL REFERENCES tasks(id),
    flow_type   TEXT NOT NULL,
    description TEXT NOT NULL,
    payload     JSONB NOT NULL,
    status      TEXT DEFAULT 'pending',  -- pending | approved | rejected
    decided_by  TEXT,
    decided_at  TIMESTAMPTZ,
    expires_at  TIMESTAMPTZ,
    created_at  TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_approvals_org_pending
    ON pending_approvals(org_id, status);

ALTER TABLE pending_approvals ENABLE ROW LEVEL SECURITY;

-- RLS: tenant isolation
CREATE POLICY "tenant_isolation_pending_approvals" ON pending_approvals
    FOR ALL USING (org_id::text = current_org_id());


-- -----------------------------------------------------------
-- 5. Tabla: secrets (credenciales cifradas)
-- -----------------------------------------------------------
CREATE TABLE IF NOT EXISTS secrets (
    id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id       UUID NOT NULL REFERENCES organizations(id),
    name         TEXT NOT NULL,
    secret_value TEXT NOT NULL,
    created_at   TIMESTAMPTZ DEFAULT now(),
    UNIQUE(org_id, name)
);

ALTER TABLE secrets ENABLE ROW LEVEL SECURITY;

-- Solo service_role puede SELECT. Agents nunca acceden directamente.
CREATE POLICY "service_role_only_secrets" ON secrets
    FOR SELECT USING (auth.role() = 'service_role');


-- -----------------------------------------------------------
-- 6. Corrección: RLS en domain_events para evitar cross-tenant INSERT
-- -----------------------------------------------------------
DROP POLICY IF EXISTS "append_only_insert" ON domain_events;
DROP POLICY IF EXISTS "domain_events_org_access" ON domain_events;

ALTER TABLE domain_events ENABLE ROW LEVEL SECURITY;

-- INSERT: debe usar el org_id del setting, no permitir任意
CREATE POLICY "tenant_insert_domain_events" ON domain_events
    FOR INSERT WITH CHECK (org_id::text = current_org_id());

-- SELECT: tenant isolation
CREATE POLICY "tenant_select_domain_events" ON domain_events
    FOR SELECT USING (org_id::text = current_org_id());


-- -----------------------------------------------------------
-- 7. Corrección: next_event_sequence con bloqueo de fila
-- -----------------------------------------------------------
CREATE OR REPLACE FUNCTION next_event_sequence(
    p_aggregate_type TEXT,
    p_aggregate_id   TEXT
) RETURNS BIGINT
LANGUAGE plpgsql
AS $$
DECLARE
    next_seq BIGINT;
BEGIN
    SELECT COALESCE(MAX(sequence), 0) + 1 INTO next_seq
      FROM domain_events
     WHERE aggregate_type = p_aggregate_type
       AND aggregate_id   = p_aggregate_id
    FOR UPDATE;  -- Bloquea la fila para evitar race condition
    RETURN next_seq;
END;
$$;
```

---

## 04 — BaseFlowState — Extensión HITL

**Archivo:** `src/flows/state.py`

**Cambios:** Agregar campos de aprobación y método `to_snapshot_v2()`.

```python
"""BaseFlowState — Typed Pydantic model that represents flow execution state.

Extension for Phase 2: Human-in-the-Loop fields.
"""

from __future__ import annotations

from pydantic import BaseModel, Field, field_validator, model_validator
from typing import Optional, Dict, Any
from datetime import datetime, timezone
from uuid import UUID
from enum import Enum


class FlowStatus(str, Enum):
    """All possible states for a flow execution."""

    PENDING = "pending"
    RUNNING = "running"
    AWAITING_APPROVAL = "awaiting_approval"
    COMPLETED = "completed"
    FAILED = "failed"
    PAUSED = "paused"
    CANCELLED = "cancelled"


class BaseFlowState(BaseModel):
    """Canonical state for any flow — persisted in the ``snapshots`` table."""

    # ── Core identity (Fase 1) ─────────────────────────────────
    task_id: str = Field(..., description="UUID of the task")
    org_id: str = Field(..., description="UUID of the organisation")
    user_id: Optional[str] = Field(None, description="UUID of the initiating user")
    flow_type: str = Field(..., description="Registered flow name")
    status: FlowStatus = Field(default=FlowStatus.PENDING)
    input_data: Dict[str, Any] = Field(default_factory=dict)
    output_data: Dict[str, Any] = Field(default_factory=dict)
    error: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    retry_count: int = Field(default=0, ge=0)
    max_retries: int = Field(default=3, ge=0)
    tokens_used: int = Field(default=0, ge=0)
    correlation_id: Optional[str] = None

    # ── HITL: Human-in-the-Loop (Fase 2) ────────────────────────
    approval_payload: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Datos que el supervisor verá al aprobar"
    )
    approval_decision: Optional[str] = Field(
        default=None,
        description="Decisión del supervisor: approved | rejected"
    )
    approval_decided_by: Optional[str] = Field(
        default=None,
        description="Identificador del supervisor que decidió"
    )

    model_config = {"use_enum_values": True, "extra": "allow"}

    # ── validators ──────────────────────────────────────────────

    @field_validator("task_id", "org_id", "user_id", mode="before")
    @classmethod
    def validate_uuid(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        try:
            if isinstance(v, UUID):
                return str(v)
            UUID(v)
            return v
        except ValueError:
            raise ValueError(f"Invalid UUID format: {v}")

    @model_validator(mode="after")
    def touch_updated_at(self) -> "BaseFlowState":
        self.updated_at = datetime.now(timezone.utc)
        return self

    # ── state transitions ───────────────────────────────────────

    def start(self) -> "BaseFlowState":
        self.status = FlowStatus.RUNNING
        self.started_at = datetime.now(timezone.utc)
        return self

    def complete(self, result: Dict[str, Any]) -> "BaseFlowState":
        self.status = FlowStatus.COMPLETED
        self.output_data = result
        self.completed_at = datetime.now(timezone.utc)
        return self

    def fail(self, error: str) -> "BaseFlowState":
        self.status = FlowStatus.FAILED
        self.error = error
        self.completed_at = datetime.now(timezone.utc)
        return self

    def await_approval(self) -> "BaseFlowState":
        self.status = FlowStatus.AWAITING_APPROVAL
        return self

    # ── serialisation helpers ───────────────────────────────────

    def to_snapshot(self) -> dict:
        """
        Convert to a row suitable for the ``snapshots`` table.

        Compatible con el esquema Fase 1 (state_json).
        """
        return {
            "task_id": self.task_id,
            "org_id": self.org_id,
            "flow_type": self.flow_type,
            "status": self.status,
            "state_json": self.model_dump(mode="json"),
        }

    def to_snapshot_v2(self, version: int = 0) -> dict:
        """
        Convert to a row for the Phase 2+ schema (aggregate_* columns).

        Usado por HITL request_approval().
        """
        return {
            "task_id": self.task_id,
            "org_id": self.org_id,
            "flow_type": self.flow_type,
            "status": self.status,
            "state_json": self.model_dump(mode="json"),
            "aggregate_type": "flow",
            "aggregate_id": self.task_id,
            "version": version,
        }

    @classmethod
    def from_snapshot(cls, data: dict) -> "BaseFlowState":
        """
        Reconstruct from a ``snapshots`` row.

        Soporta ambos esquemas: Fase 1 (state_json) y Fase 2+ (state).
        """
        # Fase 1 usa state_json, Fase 2 usa state
        state_data = data.get("state_json") or data.get("state")
        if not state_data:
            raise ValueError("Snapshot has no state_json or state field")
        return cls(**state_data)
```

---

## 05 — EventStore — Extensión Síncrona

**Archivo:** `src/events/store.py`

**Cambios:** Agregar método estático `append_sync()` para escritura directa. Mantener `append()` y `flush()` para compatibilidad con BaseFlow de Fase 1.

```python
"""EventStore — Append-only event store backed by Supabase.

Phase 2 extension: adds append_sync() for direct synchronous writes
(HITL flows that cannot use the queue+flush pattern).
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
            svc = get_service_client()

            # Obtener siguiente secuencia atómica (con FOR UPDATE)
            seq_result = svc.rpc("next_event_sequence", {
                "p_aggregate_type": aggregate_type,
                "p_aggregate_id": aggregate_id
            }).execute()

            sequence = seq_result.data

            # Insertar evento (append-only, RLS valida org_id)
            svc.table("domain_events").insert({
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
```

---

## 06 — BaseFlow — Extensión HITL

**Archivo:** `src/flows/base_flow.py`

**Cambios:** Agregar `request_approval()`, `resume()`, `_on_approved()`, `_on_rejected()`.

```python
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
            on_conflict="aggregate_type,aggregate_id"
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
        Por defecto, solo marca como RUNNING y persiste.
        """
        self.state.status = FlowStatus.RUNNING
        self.state.approval_payload = None  # Limpiar tras usar
        await self.persist_state()
        await self.emit_event("flow.resumed", {"decision": "approved"})

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
```

---

## 07 — Vault — Gestión de Secretos

**Archivo:** `src/db/vault.py`

**Nuevo archivo.**

```python
"""Vault — Proxy de secretos para herramientas.

Regla R3: Los secretos nunca llegan al LLM.
Las tools obtienen credenciales internamente y solo retornan
el resultado de la operación.
"""

from __future__ import annotations

from typing import Optional
import logging

from ..db.session import get_service_client

logger = logging.getLogger(__name__)


class VaultError(Exception):
    """Error al obtener un secreto del vault."""
    pass


def get_secret(org_id: str, secret_name: str) -> str:
    """
    Obtener un secreto cifrado para una organización.

    IMPORTANTE:
    - Usa service_role (bypasea RLS — la tabla secrets solo permite service_role)
    - Retorna el valor en claro. La tool que llama esto es responsable de no loguearlo.
    - Lanza VaultError si el secreto no existe.

    Args:
        org_id: UUID de la organización
        secret_name: Nombre del secreto (ej: "messaging_api_token", "stripe_key")

    Returns:
        El valor del secreto en texto plano.

    Raises:
        VaultError: Si el secreto no existe o no se puede acceder.

    Usage:
        token = get_secret("org_123", "messaging_api_token")
        # Internamente obtiene el token, NO lo retorna al LLM
    """
    svc = get_service_client()

    result = (
        svc.table("secrets")
        .select("secret_value")
        .eq("org_id", org_id)
        .eq("name", secret_name)
        .maybe_single()
        .execute()
    )

    if not result.data:
        raise VaultError(
            f"Secreto '{secret_name}' no configurado para org '{org_id}'"
        )

    return result.data["secret_value"]


def list_secrets(org_id: str) -> list[str]:
    """
    Listar los nombres de secretos disponibles para una organización.

    No retorna los valores, solo los nombres (para metadata/UI).

    Returns:
        Lista de nombres de secretos.
    """
    svc = get_service_client()

    result = (
        svc.table("secrets")
        .select("name")
        .eq("org_id", org_id)
        .execute()
    )

    return [row["name"] for row in result.data]
```

---

## 08 — Tools — Con Vault Integrado

**Archivo:** `src/tools/base_tool.py`

**Nuevo archivo.**

```python
"""OrgBaseTool — Clase base para tools con acceso al vault.

Regla R3: Los secretos nunca llegan al LLM.
Las subclases implementan _run() con lógica específica.
El LLM solo ve el RESULTADO de usar la credencial, no la credencial.
"""

from __future__ import annotations

from crewai.tools import BaseTool
from pydantic import BaseModel
from typing import Type

from ..db.vault import get_secret, VaultError


class OrgBaseTool(BaseTool):
    """
    Clase base para todas las tools del sistema.

    Características:
    - org_id viaja con la tool → RLS automático en queries
    - Método _get_secret() para obtener credenciales sin exponerlas al LLM
    - Las subclases implementan _run() con la lógica específica

    Attributes:
        org_id: UUID de la organización (usado para vault y RLS)
    """

    org_id: str

    def _get_secret(self, secret_name: str) -> str:
        """
        Obtener una credencial del vault.

        REGLA: Solo llamar internamente, nunca retornar el valor al LLM.
        El LLM solo ve el RESULTADO de usar la credencial.

        Args:
            secret_name: Nombre del secreto

        Returns:
            El valor del secreto en texto plano.

        Raises:
            VaultError: Si el secreto no existe.
        """
        return get_secret(self.org_id, secret_name)


# ── Ejemplo: SendMessageTool ────────────────────────────────────

class SendMessageInput(BaseModel):
    """Schema de input para SendMessageTool."""
    to: str
    message: str


class SendMessageTool(OrgBaseTool):
    """
    Envía un mensaje de texto al número especificado.

    El LLM no ve el token de la API de mensajería.
    Solo ve el resultado: "Mensaje enviado a +1234567890".
    """

    name: str = "send_message"
    description: str = "Envía un mensaje de texto al número especificado."
    args_schema: Type[BaseModel] = SendMessageInput

    def _run(self, to: str, message: str) -> str:
        # El LLM no ve el token. La tool lo obtiene internamente.
        try:
            api_token = self._get_secret("messaging_api_token")
        except VaultError as e:
            return f"Error: {e}"

        # ... llamada HTTP con api_token ...
        # mock por ahora:
        return f"Mensaje enviado a {to}"


# ── Ejemplo: SendEmailTool ─────────────────────────────────────

class SendEmailInput(BaseModel):
    """Schema de input para SendEmailTool."""
    to: str
    subject: str
    body: str


class SendEmailTool(OrgBaseTool):
    """
    Envía un email.

    El LLM no ve la contraseña SMTP.
    Solo ve el resultado: "Email enviado a user@example.com".
    """

    name: str = "send_email"
    description: str = "Envía un email al destinatario especificado."
    args_schema: Type[BaseModel] = SendEmailInput

    def _run(self, to: str, subject: str, body: str) -> str:
        try:
            smtp_password = self._get_secret("smtp_password")
        except VaultError as e:
            return f"Error: {e}"

        # ... lógica de envío ...
        return f"Email enviado a {to} con asunto: {subject}"
```

---

## 09 — Guardrails

**Archivo:** `src/guardrails/base_guardrail.py`

**Nuevo archivo.**

```python
"""Guardrails — Validadores de reglas de negocio.

Los guardrails evalúan umbrales y reglas antes de que el Flow
continúe. Se usan en los @router de los Flows para bifurcar
según condiciones de negocio.
"""

from __future__ import annotations

from typing import Callable, Dict, Any
import logging

from ..db.session import get_tenant_client

logger = logging.getLogger(__name__)


# ── Org limits loader ──────────────────────────────────────────

def load_org_limits(org_id: str) -> Dict[str, Any]:
    """
    Cargar límites configurados para la organización.

    Lee desde organizations.config -> limits.

    Returns:
        Dict con los límites de la org. Vacío si no hay config.
    """
    try:
        db = get_tenant_client(org_id)
        result = (
            db.table("organizations")
            .select("config")
            .eq("id", org_id)
            .single()
            .execute()
        )
        return result.data.get("config", {}).get("limits", {})
    except Exception as e:
        logger.warning("Could not load org limits for %s: %s", org_id, e)
        return {}


# ── Approval check factory ─────────────────────────────────────

def make_approval_check(
    amount_field: str,
    threshold_key: str,
    default_threshold: float,
) -> Callable[[float, str], bool]:
    """
    Factory para crear funciones de verificación de aprobación.

    La función retornada compara un valor contra un umbral configurable
    por organización.

    Args:
        amount_field: Nombre del campo en el estado (para logging)
        threshold_key: Clave en organizations.config.limits
        default_threshold: Valor por defecto si no hay config

    Returns:
        Función (value, org_id) -> bool. True si requiere aprobación.

    Usage::

        @router(ejecutar_paso)
        def decidir_aprobacion(self) -> str:
            check = make_approval_check(
                amount_field="monto",
                threshold_key="approval_threshold",
                default_threshold=50_000
            )
            if check(self.state.monto, self.state.org_id):
                return "solicitar_aprobacion"
            return "continuar"
    """
    def check(value: float, org_id: str) -> bool:
        limits = load_org_limits(org_id)
        threshold = limits.get(threshold_key, default_threshold)
        requires_approval = value > threshold

        if requires_approval:
            logger.info(
                "Guardrail triggered: %s=%.2f exceeds threshold=%.2f "
                "(org_id=%s, key=%s)",
                amount_field, value, threshold, org_id, threshold_key
            )

        return requires_approval

    return check


# ── Quota checker ─────────────────────────────────────────────

class QuotaExceededError(Exception):
    """Se lanza cuando una org supera su cuota."""
    pass


def check_quota(org_id: str, quota_type: str, current_usage: int) -> None:
    """
    Verificar que la org no haya excedido su cuota.

    Args:
        org_id: UUID de la organización
        quota_type: Tipo de cuota ("tasks_per_month", "tokens_per_month")
        current_usage: Uso actual

    Raises:
        QuotaExceededError: Si la cuota está agotada.

    Usage::
        check_quota(org_id, "tasks_per_month", tasks_this_month)
    """
    limits = load_org_limits(org_id)
    quota_key = f"max_{quota_type}"
    limit = limits.get(quota_key, float("inf"))

    if current_usage >= limit:
        raise QuotaExceededError(
            f"Cuota '{quota_type}' agotada: {current_usage}/{limit} "
            f"para org {org_id}"
        )
```

---

## 10 — API: Endpoint de Aprobaciones

**Archivo:** `src/api/routes/approvals.py`

**Nuevo archivo.**

```python
"""Routes: Approvals — Procesar decisiones de supervisor (HITL)."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel, field_validator
from typing import Optional

from ....db.session import get_service_client
from ....events.store import EventStore, EventStoreError
from ....flows.registry import flow_registry

router = APIRouter()


class ApprovalDecision(BaseModel):
    """Payload para procesar una decisión de aprobación."""
    org_id: str
    decision: str  # "approved" | "rejected"
    decided_by: str
    notes: str = ""

    @field_validator("decision")
    @classmethod
    def validate_decision(cls, v: str) -> str:
        if v not in ("approved", "rejected"):
            raise ValueError("decision must be 'approved' or 'rejected'")
        return v


@router.post("/{task_id}")
async def process_approval(
    task_id: str,
    body: ApprovalDecision,
    background: BackgroundTasks,
) -> dict:
    """
    Procesar la decisión del supervisor sobre una aprobación pendiente.

    SECUENCIA:
    1. Verificar que la aprobación existe y está pendiente
    2. Marcar la aprobación como resuelta (approved | rejected)
    3. Registrar evento approval.{decision}
    4. Reanudar el Flow en background

    Args:
        task_id: UUID de la tarea que fue pausada
        body: Decisión del supervisor

    Returns:
        {"status": "ok", "task_id": ..., "decision": ...}

    Raises:
        HTTPException 404: Si la aprobación no existe o ya fue procesada
        HTTPException 400: Si el flow_type no está registrado
    """
    svc = get_service_client()

    # 1. Verificar que la aprobación existe y está pendiente
    approval = (
        svc.table("pending_approvals")
        .select("*")
        .eq("task_id", task_id)
        .eq("status", "pending")
        .maybe_single()
        .execute()
    )

    if not approval.data:
        raise HTTPException(
            status_code=404,
            detail="Aprobación no encontrada o ya procesada"
        )

    flow_type = approval.data["flow_type"]

    # 2. Marcar aprobación como resuelta
    svc.table("pending_approvals").update({
        "status": body.decision,
        "decided_by": body.decided_by,
    }).eq("task_id", task_id).execute()

    # 3. Registrar evento (bloqueante — Regla R6)
    try:
        EventStore.append_sync(
            org_id=body.org_id,
            aggregate_type="flow",
            aggregate_id=task_id,
            event_type=f"approval.{body.decision}",
            payload={
                "decided_by": body.decided_by,
                "notes": body.notes,
            },
            actor=f"user:{body.decided_by}"
        )
    except EventStoreError as e:
        logger.error("Failed to emit approval event: %s", e)
        raise HTTPException(status_code=500, detail="No se pudo registrar el evento")

    # 4. Reanudar el Flow en background
    flow_class = flow_registry.get(flow_type)

    if not flow_class:
        raise HTTPException(
            status_code=400,
            detail=f"Flow type '{flow_type}' not found in registry"
        )

    # Crear instancia con org_id del body
    flow = flow_class(org_id=body.org_id)

    background.add_task(
        flow.resume,
        task_id=task_id,
        decision=body.decision,
        decided_by=body.decided_by,
    )

    return {
        "status": "ok",
        "task_id": task_id,
        "decision": body.decision,
    }
```

---

## 11 — API Routes: Estructura Final

**Archivo:** `src/api/main.py`

**Cambios:** Agregar importación del router de approvals.

```python
"""FastAPI application entry point."""

from fastapi import FastAPI
from contextlib import asynccontextmanager

from .routes import webhooks, tasks, approvals
from ..flows.generic_flow import GenericFlow  # Side-effect: register flow


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: nothing needed for now
    yield


app = FastAPI(
    title="FluxAgentPro",
    version="2.0.0",
    lifespan=lifespan,
)

# Routers
app.include_router(webhooks.router, prefix="/webhooks", tags=["webhooks"])
app.include_router(tasks.router, prefix="/tasks", tags=["tasks"])
app.include_router(approvals.router, prefix="/approvals", tags=["approvals"])


@app.get("/health")
async def health():
    return {"status": "ok"}
```

**Corrección de imports en `src/db/session.py`:**

```python
"""Database session management with tenant isolation via RLS."""

from __future__ import annotations

from typing import Optional
from supabase import create_client, Client

from ...config import get_settings

_tenant_client: Optional[Client] = None
_service_client: Optional[Client] = None


def get_supabase_client() -> Client:
    """Return the anon-key client (respects RLS)."""
    global _tenant_client
    if _tenant_client is None:
        settings = get_settings()
        _tenant_client = create_client(
            settings.supabase_url,
            settings.supabase_anon_key,
        )
    return _tenant_client


def get_service_client() -> Client:
    """
    Return the service-role client (bypasses RLS).

    Use ONLY for:
    - Vault operations (secrets table)
    - Event store appends
    - System-level queries

    NEVER expose this to agents or use in agent-facing code.
    """
    global _service_client
    if _service_client is None:
        settings = get_settings()
        _service_client = create_client(
            settings.supabase_url,
            settings.supabase_service_key,
        )
    return _service_client


class TenantClient:
    """
    Context manager that sets app.org_id before each query.

    Usage::

        with TenantClient(org_id, user_id) as db:
            db.table("tasks").select("*").execute()
    """

    def __init__(self, org_id: str, user_id: Optional[str] = None):
        self.org_id = org_id
        self.user_id = user_id
        self._client: Optional[Client] = None

    def __enter__(self) -> Client:
        from supabase import create_client
        settings = get_settings()
        self._client = create_client(
            settings.supabase_url,
            settings.supabase_service_key,  # Service key para set_config
        )
        # Set tenant context (RPC call)
        self._client.rpc("set_config", {
            "p_key": "app.org_id",
            "p_value": self.org_id,
        }).execute()
        if self.user_id:
            self._client.rpc("set_config", {
                "p_key": "app.user_id",
                "p_value": self.user_id,
            }).execute()
        return self._client

    def __exit__(self, *args):
        self._client = None


# Alias for backward compatibility
get_tenant_client = TenantClient
```

---

## 12 — Tests de Fase 2

### `tests/unit/test_vault.py`

```python
"""Tests: Vault — get_secret never exposes secrets to LLM."""

import pytest
from unittest.mock import MagicMock

from src.db.vault import get_secret, VaultError
from src.tools.base_tool import OrgBaseTool, SendMessageTool


class TestGetSecret:
    """get_secret() returns value or raises VaultError."""

    def test_get_secret_returns_value(self, mock_service_client):
        """Cuando el secreto existe → retorna el valor."""
        mock_service_client.table.return_value.select.return_value.eq.return_value.maybe_single.return_value.execute.return_value.data = {
            "secret_value": "sk-12345"
        }

        result = get_secret("org_abc", "api_key")

        assert result == "sk-12345"
        mock_service_client.table.assert_called_with("secrets")

    def test_get_secret_raises_when_not_found(self, mock_service_client):
        """Cuando el secreto no existe → lanza VaultError."""
        mock_service_client.table.return_value.select.return_value.eq.return_value.maybe_single.return_value.execute.return_value.data = None

        with pytest.raises(VaultError) as exc_info:
            get_secret("org_abc", "inexistente")

        assert "no configurado" in str(exc_info.value)


class TestOrgBaseToolSecretIsolation:
    """Tools must never return secrets to the LLM."""

    def test_get_secret_not_in_return_value(self, mock_service_client):
        """_get_secret() no debe estar en el valor de retorno de _run()."""
        mock_service_client.table.return_value.select.return_value.eq.return_value.maybe_single.return_value.execute.return_value.data = {
            "secret_value": "tok_987"
        }

        tool = SendMessageTool(org_id="org_abc")
        result = tool._run(to="+1234567890", message="Hello")

        # El resultado NO contiene el token
        assert "tok_987" not in result
        assert "tok_987" not in str(result)

    def test_secret_parameter_not_in_run_signature(self):
        """_run() no recibe el secreto como parámetro."""
        import inspect
        sig = inspect.signature(SendMessageTool._run)
        params = list(sig.parameters.keys())

        # _run(self, to, message) — sin api_token ni secret
        assert "api_token" not in params
        assert "secret" not in params
```

### `tests/integration/test_hitl_pause_resume.py`

```python
"""Tests: HITL — Flow pauses at request_approval() and resumes."""

import pytest
from unittest.mock import MagicMock, AsyncMock, patch

from src.flows.state import BaseFlowState, FlowStatus
from src.flows.base_flow import BaseFlow


class DummyFlow(BaseFlow):
    """Flow de prueba para HITL."""

    def validate_input(self, input_data):
        return True

    async def _run_crew(self):
        # Simula un paso que requiere aprobación
        if self.state.input_data.get("require_approval"):
            await self.request_approval(
                description="Aprobar operación",
                payload={"monto": self.state.input_data.get("monto", 0)}
            )
        return {"result": "done"}


@pytest.mark.asyncio
async def test_request_approval_creates_pending_approval(mock_service_client, mock_tenant_client):
    """request_approval() crea fila en pending_approvals con status=pending."""

    flow = DummyFlow(org_id="org_test")
    flow.state = BaseFlowState(
        task_id="task_test",
        org_id="org_test",
        flow_type="DummyFlow",
        input_data={"require_approval": True, "monto": 100_000},
    )

    await flow.request_approval(
        description="Aprobar operación",
        payload={"monto": 100_000}
    )

    # Verificar que se creó pending_approval
    mock_service_client.table.return_value.upsert.assert_called()
    mock_tenant_client.table.return_value.insert.assert_called()


@pytest.mark.asyncio
async def test_request_approval_updates_state_to_awaiting(mock_service_client, mock_tenant_client):
    """Tras request_approval(), state.status = AWAITING_APPROVAL."""

    flow = DummyFlow(org_id="org_test")
    flow.state = BaseFlowState(
        task_id="task_test",
        org_id="org_test",
        flow_type="DummyFlow",
    )

    assert flow.state.status == FlowStatus.PENDING

    await flow.request_approval(description="Test", payload={})

    assert flow.state.status == FlowStatus.AWAITING_APPROVAL


@pytest.mark.asyncio
async def test_resume_calls_on_approved(mock_service_client):
    """resume(decision='approved') llama a _on_approved()."""

    mock_service_client.table.return_value.select.return_value.eq.return_value.eq.return_value.maybe_single.return_value.execute.return_value.data = {
        "task_id": "task_test",
        "org_id": "org_test",
        "flow_type": "DummyFlow",
        "status": "awaiting_approval",
        "state_json": {
            "task_id": "task_test",
            "org_id": "org_test",
            "flow_type": "DummyFlow",
            "status": "awaiting_approval",
        },
    }

    flow = DummyFlow(org_id="org_test")
    flow.event_store = MagicMock()

    with patch.object(flow, '_on_approved', new_callable=AsyncMock) as mock_approved:
        await flow.resume(task_id="task_test", decision="approved", decided_by="supervisor1")
        mock_approved.assert_called_once()


@pytest.mark.asyncio
async def test_resume_calls_on_rejected(mock_service_client):
    """resume(decision='rejected') llama a _on_rejected()."""

    mock_service_client.table.return_value.select.return_value.eq.return_value.eq.return_value.maybe_single.return_value.execute.return_value.data = {
        "task_id": "task_test",
        "org_id": "org_test",
        "flow_type": "DummyFlow",
        "status": "awaiting_approval",
        "state_json": {
            "task_id": "task_test",
            "org_id": "org_test",
            "flow_type": "DummyFlow",
            "status": "awaiting_approval",
        },
    }

    flow = DummyFlow(org_id="org_test")
    flow.event_store = MagicMock()

    with patch.object(flow, '_on_rejected', new_callable=AsyncMock) as mock_rejected:
        await flow.resume(task_id="task_test", decision="rejected", decided_by="supervisor1")
        mock_rejected.assert_called_once_with("supervisor1")
```

### `tests/unit/test_guardrails.py`

```python
"""Tests: Guardrails."""

import pytest
from unittest.mock import MagicMock, patch

from src.guardrails.base_guardrail import (
    make_approval_check,
    check_quota,
    QuotaExceededError,
    load_org_limits,
)


class TestMakeApprovalCheck:
    """make_approval_check() crea validators según config de org."""

    def test_above_threshold_returns_true(self):
        """Cuando value > threshold → requiere aprobación."""
        check = make_approval_check("monto", "approval_threshold", 50_000)

        with patch("src.guardrails.base_guardrail.load_org_limits") as mock_load:
            mock_load.return_value = {"approval_threshold": 50_000}

            result = check(60_000, "org_test")

            assert result is True

    def test_below_threshold_returns_false(self):
        """Cuando value <= threshold → no requiere aprobación."""
        check = make_approval_check("monto", "approval_threshold", 50_000)

        with patch("src.guardrails.base_guardrail.load_org_limits") as mock_load:
            mock_load.return_value = {"approval_threshold": 50_000}

            result = check(40_000, "org_test")

            assert result is False

    def test_uses_default_when_no_config(self):
        """Sin config → usa default_threshold."""
        check = make_approval_check("monto", "approval_threshold", 50_000)

        with patch("src.guardrails.base_guardrail.load_org_limits") as mock_load:
            mock_load.return_value = {}  # Sin límites configurados

            result = check(60_000, "org_test")

            assert result is True  # 60k > 50k default


class TestCheckQuota:
    """check_quota() lanza QuotaExceededError cuando se agota."""

    def test_within_quota_does_not_raise(self):
        with patch("src.guardrails.base_guardrail.load_org_limits") as mock_load:
            mock_load.return_value = {"max_tasks_per_month": 100}

            # No debe lanzar
            check_quota("org_test", "tasks_per_month", 50)

    def test_at_quota_raises(self):
        with patch("src.guardrails.base_guardrail.load_org_limits") as mock_load:
            mock_load.return_value = {"max_tasks_per_month": 100}

            with pytest.raises(QuotaExceededError):
                check_quota("org_test", "tasks_per_month", 100)
```

---

## 13 — Entregables Verificables

| # | Entregable | Criterio de éxito |
|---|-----------|-------------------|
| E1 | `request_approval()` pausa el Flow y crea snapshot | Snapshot existe en DB, pending_approval.status="pending" |
| E2 | `resume()` restaura estado y continua | state.approval_decision = decision, Flow completa |
| E3 | Vault nunca expone secretos al LLM | `get_secret()` solo se llama internamente en `_run()` |
| E4 | Guardrails validan umbrales | `make_approval_check()` retorna True cuando value > threshold |
| E5 | `EventStore.append_sync()` es bloqueante | Evento está en DB antes de que el método retorne |
| E6 | RLS aísla tenants | Query sin org_id correcto retorna 0 filas |
| E7 | Tests pasan al 100% | `pytest tests/` → 0 failures |

---

## 14 — Reglas Invariantes

| # | Regla | Consecuencia |
|---|-------|-------------|
| R1 | El Flow es el orquestador. Los agentes no deciden el flujo. | Comportamiento impredecible |
| R2 | `allow_delegation=False` siempre. | Consumo descontrolado |
| R3 | Los secretos nunca llegan al LLM. | Exposición de credenciales |
| R4 | El estado canónico vive en Supabase. | Pérdida de estado |
| R5 | Los eventos son inmutables. Append-only en domain_events. | Pérdida de trazabilidad |
| R6 | `EventStore.append_sync()` es bloqueante. | Eventos perdidos |
| R7 | Toda tabla tiene org_id y RLS. | Filtración cross-tenant |
| R8 | `max_iter` explícito en cada Agent (≤5). | Loops infinitos |

---

## 15 — Gotchas de CrewAI

| Gotcha | Síntoma | Solución |
|--------|---------|----------|
| Flows no tienen pausa nativa | No existe `flow.suspend()` | Serializar estado → snapshot → terminar. `resume()` restaura. |
| `crew.kickoff()` es síncrono | Bloquea event loop en Flows async | Usar `await crew.kickoff_async()` |
| `MCPServerAdapter` como context manager en async | Conexión se cierra antes de ser usada | Usar `MCPPool` con conexiones persistentes (Fase 3) |
| `FlowState` no se persiste automáticamente | Estado se pierde si proceso crashea | Llamar `persist_state()` después de cada paso |
| `output_pydantic` no muestra error claro | Agente reintenta silenciosamente | Agregar `verbose=True` en desarrollo |
| RLS retorna 0 filas sin error si `org_id` no está seteado | Query "funciona" pero retorna vacío | Usar `TenantClient(org_id)` que setea `app.org_id` |

---

## Resumen de Archivos Fase 2

| Archivo | Acción | Contenido |
|---------|--------|-----------|
| `supabase/migrations/002_governance.sql` | CREAR | Tablas pending_approvals, secrets + ALTER tasks/org/snapshots + RLS fixes |
| `src/flows/state.py` | MODIFICAR | Agregar campos HITL + `to_snapshot_v2()` |
| `src/events/store.py` | MODIFICAR | Agregar `append_sync()` estático |
| `src/flows/base_flow.py` | MODIFICAR | Agregar `request_approval()`, `resume()`, `_on_approved()`, `_on_rejected()` |
| `src/db/session.py` | MODIFICAR | Agregar `get_service_client()` + TenantClient como clase |
| `src/db/vault.py` | CREAR | `get_secret()`, `list_secrets()` |
| `src/tools/base_tool.py` | CREAR | `OrgBaseTool`, `SendMessageTool`, `SendEmailTool` |
| `src/guardrails/base_guardrail.py` | CREAR | `make_approval_check()`, `check_quota()`, `load_org_limits()` |
| `src/api/routes/approvals.py` | CREAR | `POST /approvals/{task_id}` |
| `src/api/main.py` | MODIFICAR | Incluir router de approvals |
| `tests/unit/test_vault.py` | CREAR | Tests de vault y aislamiento de secretos |
| `tests/integration/test_hitl_pause_resume.py` | CREAR | Tests de pausa/reanudación |
| `tests/unit/test_guardrails.py` | CREAR | Tests de guardrails |

---

**Próximo paso:** Verificar que `uv sync` instala todas las dependencias, ejecutar `pytest tests/`, y aplicar las migraciones SQL en Supabase antes de comenzar la implementación de código.
