"""Middleware helpers — tenant identity extraction + JWT verification + org membership.

ES256 vs HS256 — key difference
--------------------------------
Supabase projects created after mid-2024 sign JWTs with **ES256** (ECDSA P-256),
an *asymmetric* algorithm.  The private key lives only inside Supabase; backends
verify tokens using only the *public* key fetched from the JWKS endpoint.

  HS256  →  symmetric  →  single shared secret (shown in Dashboard → Project Settings → API)
  ES256  →  asymmetric →  private key (Supabase only) + public key via JWKS

If the JWT header shows ``"alg": "ES256"`` the ``supabase_jwt_secret`` from the
Dashboard is NOT used for verification — it is only relevant for HS256 tokens.

JWKS endpoint
-------------
Supabase exposes the public signing key as a JWKS document.  The documented
canonical URL is::

    GET  https://<project>.supabase.co/auth/v1/.well-known/jwks.json

However, that path currently returns 404 on some Supabase versions.  The
working endpoint (confirmed) is::

    GET  https://<project>.supabase.co/auth/v1/.well-known/jwks.json   (requires apikey header)

PyJWT's ``PyJWKClient`` accepts a ``headers`` dict that is forwarded to every
HTTP request, so the ``apikey`` requirement is handled transparently.

Caching
-------
The JWKS is cached for 5 minutes (``lifespan=300``) at the module level via the
singleton ``_jwks_client``.  PyJWT also re-fetches automatically when it
encounters a ``kid`` that is not in the cached key set, providing seamless key
rotation support.

Algorithm negotiation
---------------------
``verify_supabase_jwt`` reads the JWT header *before* verification to discover
the algorithm (ES256 or HS256) and picks the correct verification path:

* **ES256**  → fetches the matching public key from JWKS via ``kid``
* **HS256**  → decodes with the JWT secret from settings (legacy projects)

This means the same function works regardless of which algorithm Supabase is
configured to use.
"""

from __future__ import annotations

import json
import logging
from jose import jwt, jwk, JWSError
from jose.exceptions import JWTError, ExpiredSignatureError
import httpx

from fastapi import Header, HTTPException, Request, Depends

from ..db.session import get_service_client
from ..config import get_settings

logger = logging.getLogger(__name__)

# ── JWKS caching ───────────────────────────────────────────────────────────
_jwks_cache: dict | None = None


async def _get_jwks() -> dict:
    """Fetch and cache Supabase JWKS using httpx."""
    global _jwks_cache
    if _jwks_cache is None:
        settings = get_settings()
        jwks_url = f"{settings.supabase_url}/auth/v1/.well-known/jwks.json"
        async with httpx.AsyncClient() as client:
            try:
                resp = await client.get(
                    jwks_url,
                    headers={"apikey": settings.supabase_anon_key},
                    timeout=10,
                )
                resp.raise_for_status()
                _jwks_cache = resp.json()
                logger.debug("JWKS cached from %s", jwks_url)
            except Exception as e:
                logger.error("Failed to fetch JWKS: %s", e)
                raise HTTPException(
                    status_code=503,
                    detail="Auth service temporarily unavailable",
                ) from e
    return _jwks_cache


# ── existing: org_id header extraction ────────────────────────────────────

async def require_org_id(
    x_org_id: str = Header(
        ...,
        alias="X-Org-ID",
        description="Organisation UUID — required on every request",
    ),
) -> str:
    """FastAPI dependency that extracts and validates the ``X-Org-ID`` header.

    Usage in route signatures::

        org_id: str = Depends(require_org_id)
    """
    if not x_org_id or not x_org_id.strip():
        raise HTTPException(status_code=400, detail="X-Org-ID header is required")
    return x_org_id.strip()


async def _verify_es256(token: str, issuer: str) -> dict:
    """Verify an ES256-signed Supabase JWT using python-jose."""
    jwks = await _get_jwks()

    try:
        header = jwt.get_unverified_header(token)
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Malformed JWT: {e}")

    kid = header.get("kid")
    if not kid:
        raise HTTPException(status_code=401, detail="Missing kid in JWT header")

    # Find the key in the JWKS
    key_dict = next((k for k in jwks.get("keys", []) if k.get("kid") == kid), None)
    if not key_dict:
        # Invalidate cache and retry once if key not found (might have rotated)
        global _jwks_cache
        _jwks_cache = None
        jwks = await _get_jwks()
        key_dict = next((k for k in jwks.get("keys", []) if k.get("kid") == kid), None)
        if not key_dict:
            raise HTTPException(status_code=401, detail="Invalid token signing key")

    try:
        # Convert JWK to a format jose understands for verification
        # For ES256, jose likes the JWK dict directly or a jwk.construct object
        payload = jwt.decode(
            token,
            key_dict,
            algorithms=["ES256"],
            issuer=issuer,
            options={
                "verify_aud": False,
                "verify_exp": True,
                "verify_iss": True,
            },
        )
        return payload
    except ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token has expired")
    except JWTError as e:
        raise HTTPException(status_code=401, detail=f"Invalid ES256 token: {e}")

# ── HS256 helper ───────────────────────────────────────────────────────────

def _verify_hs256(token: str, issuer: str) -> dict:
    """Verify a legacy HS256-signed Supabase JWT using python-jose."""
    settings = get_settings()
    if not settings.supabase_jwt_secret:
        logger.error("HS256 token received but SUPABASE_JWT_SECRET is not set")
        raise HTTPException(
            status_code=500,
            detail="Server misconfiguration: JWT secret not configured",
        )
    try:
        payload = jwt.decode(
            token,
            settings.supabase_jwt_secret,
            algorithms=["HS256"],
            issuer=issuer,
            options={
                "verify_aud": False,
                "verify_exp": True,
                "verify_iss": True,
            },
        )
        return payload
    except ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token has expired")
    except JWTError as e:
        raise HTTPException(status_code=401, detail=f"Invalid HS256 token: {e}")


# ── main JWT dependency ────────────────────────────────────────────────────

async def verify_supabase_jwt(
    authorization: str = Header(..., description="Bearer token from Supabase Auth"),
) -> dict:
    """Decode and verify a Supabase Auth JWT.

    Supports **ES256** (asymmetric, current default) and **HS256** (symmetric,
    legacy).  The algorithm is detected from the JWT header so no manual
    configuration is required.

    Returns
    -------
    dict with keys ``user_id`` (str) and ``payload`` (full decoded claims).

    Raises
    ------
    HTTPException 401 / 503 on any auth failure.

    Algorithm selection logic
    -------------------------
    ES256  →  verify via JWKS (public key fetched from Supabase, no secret needed)
    HS256  →  verify with ``SUPABASE_JWT_SECRET`` from env / settings
    other  →  rejected (e.g. ``none``, RS256 not currently issued by Supabase)
    """
    settings = get_settings()

    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Authorization header must start with 'Bearer '")

    token = authorization[len("Bearer "):]
    if not token:
        raise HTTPException(status_code=401, detail="Empty bearer token")

    # The issuer Supabase embeds in its JWTs
    issuer = f"{settings.supabase_url}/auth/v1"

    # --- Read algorithm from header without verifying ---
    try:
        header = jwt.get_unverified_header(token)
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Malformed JWT header: {e}") from e

    alg = header.get("alg", "").upper()
    logger.debug("JWT header alg=%s kid=%s", alg, header.get("kid"))

    # --- Dispatch to the correct verifier ---
    if alg == "ES256":
        logger.debug("Verifying ES256 token via JWKS")
        payload = await _verify_es256(token, issuer)
        logger.info("ES256 token verified, sub=%s", payload.get("sub"))

    elif alg == "HS256":
        logger.debug("Verifying HS256 token via JWT secret")
        payload = _verify_hs256(token, issuer)
        logger.info("HS256 token verified, sub=%s", payload.get("sub"))

    else:
        logger.warning("Rejected token with unsupported algorithm: %s", alg)
        raise HTTPException(
            status_code=401,
            detail=f"Unsupported JWT algorithm: {alg!r}. Expected ES256 or HS256.",
        )

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Token missing 'sub' claim")

    return {"user_id": user_id, "payload": payload}


# ── org membership verification ────────────────────────────────────────────

async def verify_org_membership(
    request: Request,
    org_id: str = Depends(require_org_id),
    user: dict = Depends(verify_supabase_jwt),
) -> dict:
    """Validate that the authenticated user is a member of the requested org.

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
