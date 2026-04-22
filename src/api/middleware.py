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

import logging


from fastapi import Header, HTTPException, Request, Depends

from ..mcp.auth import decode_jwt, verify_org_membership as auth_verify_org_membership

logger = logging.getLogger(__name__)

# JWKS client singleton logic moved to src/mcp/auth.py


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


# Verification helpers moved to src/mcp/auth.py (decode_jwt)


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
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Authorization header must start with 'Bearer '")

    token = authorization[len("Bearer "):]
    if not token:
        raise HTTPException(status_code=401, detail="Empty bearer token")

    # Delegate to the centralized auth bridge
    payload = decode_jwt(token)
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
    # Delegate to centralized auth logic while maintaining FastAPI state injection
    result = auth_verify_org_membership(org_id, user["payload"])

    request.state.user_id = result["user_id"]
    request.state.org_id = result["org_id"]
    request.state.org_role = result["role"]

    return result
