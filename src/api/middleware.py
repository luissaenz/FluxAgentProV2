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

import jwt as pyjwt
from jwt import PyJWKClient
from jwt.algorithms import ECAlgorithm
from jwt.exceptions import PyJWKClientConnectionError, PyJWKClientError

from fastapi import Header, HTTPException, Request, Depends

from ..db.session import get_service_client
from ..config import get_settings

logger = logging.getLogger(__name__)

# ── JWKS client singleton ──────────────────────────────────────────────────
# Built lazily on first call so Settings are available.  The client caches the
# full JWKS response for 5 minutes and automatically re-fetches on key-miss.

_jwks_client: PyJWKClient | None = None


def _get_jwks_client() -> PyJWKClient:
    """Return (and lazily create) the module-level PyJWKClient singleton.

    PyJWT's ``PyJWKClient`` is thread-safe and caches the JWKS response
    internally; creating one instance per process is the recommended pattern.

    The Supabase ``/auth/v1/jwks`` endpoint requires an ``apikey`` header
    (the project's anon key).  ``PyJWKClient`` forwards ``headers`` on every
    urllib request it makes, so passing ``apikey`` here handles auth
    transparently — including automatic re-fetch on key rotation.
    """
    global _jwks_client
    if _jwks_client is None:
        settings = get_settings()
        jwks_url = f"{settings.supabase_url}/auth/v1/.well-known/jwks.json"
        _jwks_client = PyJWKClient(
            jwks_url,
            headers={"apikey": settings.supabase_anon_key},
            cache_jwk_set=True,
            lifespan=300,   # 5 minutes — safe, Supabase caches their edge for 10 min
            cache_keys=True,
            max_cached_keys=16,
            timeout=10,
        )
        logger.debug("PyJWKClient initialised: %s", jwks_url)
    return _jwks_client


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


# ── ES256 helper ───────────────────────────────────────────────────────────

def _verify_es256(token: str, issuer: str) -> dict:
    """Verify an ES256-signed Supabase JWT using the project's JWKS endpoint.

    Flow
    ----
    1. Read the ``kid`` from the unverified JWT header.
    2. Ask ``PyJWKClient`` for the matching EC public key (fetches / uses cache).
    3. Decode-and-verify the token with ``pyjwt.decode`` — this performs full
       signature verification, expiry check, and issuer validation.

    Why not use the Dashboard JWT secret?
    --------------------------------------
    The secret shown in Dashboard → Project Settings → API is a shared HMAC
    secret used *only* for HS256-signed tokens.  ES256 tokens are signed with
    Supabase's EC private key; the public counterpart is published via JWKS.
    There is no way to verify an ES256 token locally with the HS256 secret.

    Raises
    ------
    HTTPException 401  on any verification failure.
    """
    client = _get_jwks_client()

    # --- Step 1: locate the right key by kid ---
    try:
        signing_key = client.get_signing_key_from_jwt(token)
    except PyJWKClientConnectionError as e:
        logger.error("Could not reach Supabase JWKS endpoint: %s", e)
        raise HTTPException(
            status_code=503,
            detail="Auth service temporarily unavailable — JWKS fetch failed",
        ) from e
    except PyJWKClientError as e:
        logger.error("JWKS key lookup failed: %s", e)
        raise HTTPException(
            status_code=401,
            detail=f"Token signing key not found: {e}",
        ) from e

    # --- Step 2: full cryptographic verification ---
    try:
        payload = pyjwt.decode(
            token,
            signing_key,           # ECPublicKey object from PyJWT's PyJWK wrapper
            algorithms=["ES256"],
            issuer=issuer,
            options={
                "verify_aud": False,   # Supabase tokens may omit aud
                "verify_exp": True,
                "verify_iss": True,
            },
        )
        return payload
    except pyjwt.ExpiredSignatureError as e:
        raise HTTPException(status_code=401, detail="Token has expired") from e
    except pyjwt.InvalidIssuerError as e:
        raise HTTPException(status_code=401, detail="Token issuer mismatch") from e
    except pyjwt.InvalidTokenError as e:
        raise HTTPException(status_code=401, detail=f"Invalid ES256 token: {e}") from e


def _verify_es256_manual(token: str, issuer: str) -> dict:
    """Alternative ES256 verifier that fetches the JWKS manually (no PyJWKClient).

    Use this if ``PyJWKClient`` is unavailable or if you need more control over
    the HTTP layer (e.g. async httpx).  This uses ``requests`` and then
    ``ECAlgorithm.from_jwk`` directly.

    This is provided as a reference implementation — ``_verify_es256`` above
    using ``PyJWKClient`` is preferred in production because it handles caching
    and key rotation automatically.
    """
    import requests as req_lib

    settings = get_settings()
    jwks_url = f"{settings.supabase_url}/auth/v1/.well-known/jwks.json"

    # Decode header without verifying to get kid
    unverified_header = pyjwt.get_unverified_header(token)
    kid = unverified_header.get("kid")
    if not kid:
        raise HTTPException(status_code=401, detail="JWT missing kid header")

    # Fetch JWKS
    try:
        resp = req_lib.get(
            jwks_url,
            headers={"apikey": settings.supabase_anon_key},
            timeout=10,
        )
        resp.raise_for_status()
        jwks = resp.json()
    except Exception as e:
        logger.error("JWKS fetch error: %s", e)
        raise HTTPException(status_code=503, detail="Could not fetch JWKS") from e

    # Find the key matching kid
    keys = jwks.get("keys", [])
    matching = next((k for k in keys if k.get("kid") == kid), None)
    if not matching:
        raise HTTPException(
            status_code=401,
            detail=f"No JWKS key found for kid={kid!r}",
        )

    # Construct the EC public key object and verify
    try:
        ec_public_key = ECAlgorithm.from_jwk(json.dumps(matching))
        payload = pyjwt.decode(
            token,
            ec_public_key,
            algorithms=["ES256"],
            issuer=issuer,
            options={"verify_aud": False},
        )
        return payload
    except pyjwt.InvalidTokenError as e:
        raise HTTPException(status_code=401, detail=f"ES256 verification failed: {e}") from e


# ── HS256 helper ───────────────────────────────────────────────────────────

def _verify_hs256(token: str, issuer: str) -> dict:
    """Verify a legacy HS256-signed Supabase JWT using the shared JWT secret.

    The secret is found in Dashboard → Project Settings → API → JWT Settings →
    ``JWT Secret``.  Map it to the env var ``SUPABASE_JWT_SECRET``.

    Raises
    ------
    HTTPException 401  on any verification failure.
    """
    settings = get_settings()
    if not settings.supabase_jwt_secret:
        logger.error("HS256 token received but SUPABASE_JWT_SECRET is not set")
        raise HTTPException(
            status_code=500,
            detail="Server misconfiguration: JWT secret not configured",
        )
    try:
        payload = pyjwt.decode(
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
    except pyjwt.ExpiredSignatureError as e:
        raise HTTPException(status_code=401, detail="Token has expired") from e
    except pyjwt.InvalidIssuerError as e:
        raise HTTPException(status_code=401, detail="Token issuer mismatch") from e
    except pyjwt.InvalidTokenError as e:
        raise HTTPException(status_code=401, detail=f"Invalid HS256 token: {e}") from e


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
        header = pyjwt.get_unverified_header(token)
    except pyjwt.DecodeError as e:
        raise HTTPException(status_code=401, detail=f"Malformed JWT header: {e}") from e

    alg = header.get("alg", "").upper()
    logger.debug("JWT header alg=%s kid=%s", alg, header.get("kid"))

    # --- Dispatch to the correct verifier ---
    if alg == "ES256":
        logger.debug("Verifying ES256 token via JWKS")
        payload = _verify_es256(token, issuer)
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
