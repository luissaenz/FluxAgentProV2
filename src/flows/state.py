"""BaseFlowState — Typed Pydantic model that represents flow execution state.

Key design decisions:
- UUIDs are stored as ``str`` but validated on input.
- ``FlowStatus`` uses an Enum with ``use_enum_values`` so serialisation is clean.
- ``extra = "allow"`` lets concrete flows add domain-specific fields.
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
    RESOLUTION_PENDING = "resolution_pending"


class BaseFlowState(BaseModel):
    """Canonical state for any flow — persisted in the ``snapshots`` table."""

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
    correlation_id: str = Field(..., description="ID de correlación para tracing de extremo a extremo")

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

    def resolution_pending(self) -> "BaseFlowState":
        self.status = FlowStatus.RESOLUTION_PENDING
        return self

    def update_tokens(self, tokens: int) -> "BaseFlowState":
        """Acumular tokens usados. Llamar desde _run_crew() de la subclase."""
        self.tokens_used += tokens
        return self

    def estimate_tokens(self, text: Any) -> int:
        """
        Fallback: estimar tokens basados en el tamaño del texto.
        Regla de oro: 1 token ≈ 4 caracteres (promedio en inglés/español).
        """
        if not text:
            return 0
        return len(str(text)) // 4

    # ── serialisation helpers ───────────────────────────────────

    def to_snapshot(self) -> dict:
        """
        Convert to a row suitable for the ``snapshots`` table.

        Compatible with Phase 1 schema (state_json column).
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

        Used by HITL request_approval().
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

        Supports both Phase 1 schema (state_json) and Phase 2+ (state).
        """
        # Phase 1 uses state_json, Phase 2+ uses state
        state_data = data.get("state_json") or data.get("state")
        if not state_data:
            raise ValueError("Snapshot has no state_json or state field")

        # Ensure correlation_id exists for legacy support
        if "correlation_id" not in state_data:
            state_data["correlation_id"] = f"legacy-task-{data.get('task_id', 'unknown')}"
            
        return cls(**state_data)
