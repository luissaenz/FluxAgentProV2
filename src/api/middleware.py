"""Middleware helpers — tenant identity extraction from request headers."""

from __future__ import annotations

from fastapi import Header, HTTPException


async def require_org_id(
    x_org_id: str = Header(
        ...,
        alias="X-Org-ID",
        description="Organisation UUID — required on every request",
    ),
) -> str:
    """
    FastAPI dependency that extracts and validates the ``X-Org-ID`` header.

    Usage in route signatures::

        org_id: str = Depends(require_org_id)
    """
    if not x_org_id or not x_org_id.strip():
        raise HTTPException(status_code=400, detail="X-Org-ID header is required")
    return x_org_id.strip()
