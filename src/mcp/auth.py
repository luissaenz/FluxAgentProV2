# src/mcp/auth.py
"""Authentication utilities for MCP.
Provides:
- `decode_jwt(token: str) -> dict` – verifies JWT (ES256 or HS256) using Supabase JWKS or secret.
- `verify_org_membership(org_id: str, user_claims: dict) -> None` – raises 403 if user not member.
- `_get_jwks_client() -> PyJWKClient` – singleton JWKS client with 1 hour cache.
"""

from __future__ import annotations

import logging
from typing import Optional

import jwt as pyjwt
from jwt import PyJWKClient
from jwt.exceptions import PyJWKClientConnectionError, PyJWKClientError
from fastapi import HTTPException

from ..config import get_settings
from ..db.session import get_service_client, execute_with_retry

logger = logging.getLogger(__name__)

# Singleton JWKS client
_jwks_client: Optional[PyJWKClient] = None


def _get_jwks_client() -> PyJWKClient:
    """Return a lazily‑initialised JWKS client.
    Cache lifespan is 3600 seconds (1 h) as required by the plan.
    """
    global _jwks_client
    if _jwks_client is None:
        settings = get_settings()
        jwks_url = f"{settings.supabase_url}/auth/v1/.well-known/jwks.json"
        _jwks_client = PyJWKClient(
            jwks_url,
            headers={"apikey": settings.supabase_anon_key},
            cache_jwk_set=True,
            lifespan=3600,  # 1 hour cache
            cache_keys=True,
            max_cached_keys=16,
            timeout=10,
        )
        logger.debug("Initialized PyJWKClient for %s", jwks_url)
    return _jwks_client


def _verify_es256(token: str, issuer: str) -> dict:
    """Verify an ES256‑signed token using JWKS.
    Raises HTTPException 401 on failure.
    """
    client = _get_jwks_client()
    try:
        signing_key = client.get_signing_key_from_jwt(token)
    except (PyJWKClientConnectionError, PyJWKClientError) as e:
        logger.error("JWKS fetch/lookup error: %s", e)
        raise HTTPException(status_code=401, detail="Invalid token signature") from e
    try:
        payload = pyjwt.decode(
            token,
            signing_key.key,
            algorithms=["ES256"],
            issuer=issuer,
            options={"verify_aud": False, "verify_exp": True, "verify_iss": True},
        )
        return payload
    except pyjwt.PyJWTError as e:
        raise HTTPException(status_code=401, detail=str(e)) from e


def _verify_hs256(token: str, secret: str, issuer: str) -> dict:
    """Verify an HS256‑signed token using the Supabase secret.
    """
    try:
        payload = pyjwt.decode(
            token,
            secret,
            algorithms=["HS256"],
            issuer=issuer,
            options={"verify_aud": False, "verify_exp": True, "verify_iss": True},
        )
        return payload
    except pyjwt.PyJWTError as e:
        raise HTTPException(status_code=401, detail=str(e)) from e


def decode_jwt(token: str) -> dict:
    """Decode and verify a Supabase JWT.
    Supports both ES256 (asymmetric) and HS256 (symmetric) algorithms.
    """
    settings = get_settings()
    # Peek at header to decide algorithm
    try:
        unverified_header = pyjwt.get_unverified_header(token)
    except pyjwt.PyJWTError as e:
        raise HTTPException(status_code=401, detail="Malformed token") from e
    alg = unverified_header.get("alg")
    issuer = f"{settings.supabase_url}/auth/v1"
    if alg == "ES256":
        return _verify_es256(token, issuer)
    elif alg == "HS256":
        return _verify_hs256(token, settings.supabase_jwt_secret, issuer)
    else:
        raise HTTPException(status_code=401, detail="Unsupported algorithm")


def verify_org_membership(org_id: str, claims: dict) -> dict:
    """Ensure the authenticated user is a member of the requested org.
    Supports cross-org access for 'fap_admin' role.

    Args:
        org_id: The UUID of the organization to access.
        claims: Decoded JWT claims (must contain 'sub' as user_id).

    Returns:
        dict: {user_id, org_id, role}

    Raises:
        HTTPException 403 if membership invalid.
    """
    user_id = claims.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Token missing 'sub' claim")

    db = get_service_client()

    # 1. Check if user is fap_admin in ANY org (cross-org support)
    admin_query = (
        db.table("org_members")
        .select("role")
        .eq("user_id", user_id)
        .eq("role", "fap_admin")
        .eq("is_active", True)
        .limit(1)
    )
    admin_check = execute_with_retry(admin_query)

    if admin_check.data:
        return {"user_id": user_id, "org_id": org_id, "role": "fap_admin"}

    # 2. Check membership in the specific org
    member_query = (
        db.table("org_members")
        .select("role")
        .eq("org_id", org_id)
        .eq("user_id", user_id)
        .eq("is_active", True)
        .maybe_single()
    )
    member = execute_with_retry(member_query)

    if not member.data:
        logger.warning("Access denied: User %s is not in Org %s", user_id, org_id)
        raise HTTPException(
            status_code=403,
            detail=f"User {user_id} is not a member of org {org_id}",
        )

    return {
        "user_id": user_id,
        "org_id": org_id,
        "role": member.data["role"],
    }
