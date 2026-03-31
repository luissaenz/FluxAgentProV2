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
    correlation_id: Optional[str] = None

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
        """Convert to a row suitable for the ``snapshots`` table."""
        return {
            "task_id": self.task_id,
            "org_id": self.org_id,
            "flow_type": self.flow_type,
            "status": self.status,
            "state_json": self.model_dump(mode="json"),
        }

    @classmethod
    def from_snapshot(cls, data: dict) -> "BaseFlowState":
        """Reconstruct from a ``snapshots`` row."""
        return cls(**data["state_json"])
