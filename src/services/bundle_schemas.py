"""src/services/bundle_schemas.py — Pydantic models for FAP-Bundle v2.

These models are used for validating manifest.json and bundle content.
"""

from __future__ import annotations

from typing import Dict, List, Optional

from pydantic import BaseModel, Field, field_validator


class BundleInfo(BaseModel):
    """Basic metadata about the bundle."""

    name: str = Field(..., min_length=3, max_length=100)
    description: Optional[str] = None
    version: str = Field(default="1.0.0")


class BundleManifest(BaseModel):
    """Schema for manifest.json at the root of the ZIP."""

    version: str = Field(default="2.0")
    bundle_info: Optional[BundleInfo] = None

    # Map of relative_path -> sha256_hash
    hashes: Dict[str, str] = Field(
        ..., description="Map of relative file paths to their SHA256 hashes"
    )

    @field_validator("hashes")
    @classmethod
    def hashes_must_be_valid(cls, v: Dict[str, str]) -> Dict[str, str]:
        for path, h in v.items():
            if not h.startswith("sha256:"):
                raise ValueError(f"Hash for {path} must start with 'sha256:'")
            if len(h) != 7 + 64:  # sha256: + 64 hex chars
                raise ValueError(f"Invalid SHA256 hash length for {path}")
        return v


class BundleContent(BaseModel):
    """Container for the parsed content of a bundle."""

    manifest: BundleManifest
    agents: List[Dict] = Field(default_factory=list)
    flows: List[Dict] = Field(default_factory=list)
    skills: Dict[str, str] = Field(
        default_factory=dict, description="Map of filename -> source_code"
    )

    # Stats for limit validation
    size_bytes: int = 0
    bundle_hash: str = ""


class BundleRPCPayload(BaseModel):
    """Payload expected by the PostgreSQL function import_bundle_atomic."""

    bundle_name: str
    bundle_hash: str
    agents: List[Dict] = Field(default_factory=list)
    flows: List[Dict] = Field(default_factory=list)
    skills: Dict[str, str] = Field(default_factory=dict)


class BundleRPCResult(BaseModel):
    """Response returned by the PostgreSQL function import_bundle_atomic."""

    status: str
    bundle_id: str
    agents_count: int = 0
    flows_count: int = 0
    skills_count: int = 0
    error: Optional[str] = None


class BundleValidationResult(BaseModel):
    """Result of a dry-run bundle validation."""

    status: str = "success"
    bundle_info: Optional[BundleInfo] = None
    agents_count: int = 0
    flows_count: int = 0
    skills_count: int = 0
    security_report: Optional[Dict] = None
    warnings: List[str] = Field(default_factory=list)
    error: Optional[str] = None
