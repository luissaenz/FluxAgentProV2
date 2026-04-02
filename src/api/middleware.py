"""Middleware helpers — tenant identity extraction + JWT verification + org membership."""

from __future__ import annotations

from fastapi import Header, HTTPException, Request, Depends
from jose import jwt, JWTError
import logging

from ..db.session import get_service_client
from ..config import get_settings

logger = logging.getLogger(__name__)


# ── existing: org_id header extraction ─────────────────────────

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


# ── Phase 5: JWT verification ─────────────────────────────────

async def verify_supabase_jwt(
    authorization: str = Header(..., description="Bearer token from Supabase Auth"),
) -> dict:
    """
    Decode and verify a Supabase Auth JWT.
    Extracts user_id from the 'sub' claim.
    """
    settings = get_settings()
    token = authorization.replace("Bearer ", "")

    try:
        payload = jwt.decode(
            token,
            settings.supabase_jwt_secret,
            algorithms=["HS256"],
            options={"verify_aud": False},
        )

        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(status_code=401, detail="Token missing 'sub' claim")

    except JWTError as e:
        raise HTTPException(status_code=401, detail=f"Invalid token: {e}")

    return {"user_id": user_id, "payload": payload}


# ── Phase 5: org membership verification ──────────────────────

async def verify_org_membership(
    request: Request,
    org_id: str = Depends(require_org_id),
    user: dict = Depends(verify_supabase_jwt),
) -> dict:
    """
    Validate that the authenticated user is a member of the requested org.
    Exception: fap_admin can access any org.

    Sets request.state: user_id, org_id, org_role
    """
    user_id = user["user_id"]
    db = get_service_client()

    # 1. Check if user is fap_admin in ANY org
    admin_check = (
        db.table("org_members")
        .select("role")
        .eq("user_id", user_id)
        .eq("role", "fap_admin")
        .eq("is_active", True)
        .limit(1)
        .execute()
    )

    if admin_check.data:
        request.state.user_id = user_id
        request.state.org_id = org_id
        request.state.org_role = "fap_admin"
        return {"user_id": user_id, "org_id": org_id, "role": "fap_admin"}

    # 2. Check membership in the specific org
    member = (
        db.table("org_members")
        .select("role")
        .eq("org_id", org_id)
        .eq("user_id", user_id)
        .eq("is_active", True)
        .maybe_single()
        .execute()
    )

    if not member.data:
        raise HTTPException(
            status_code=403,
            detail=f"User {user_id} is not a member of org {org_id}",
        )

    request.state.user_id = user_id
    request.state.org_id = org_id
    request.state.org_role = member.data["role"]

    return {
        "user_id": user_id,
        "org_id": org_id,
        "role": member.data["role"],
    }
