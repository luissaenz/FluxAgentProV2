"""Database session management with tenant isolation via RLS.

Provides three clients:
- ``get_service_client()``: service-role key, bypasses RLS (vault, system ops)
- ``get_anon_client()``: anon-key client, respects RLS when org_id is set
- ``TenantClient``: context manager that sets app.org_id before each query
"""

from __future__ import annotations

from contextlib import contextmanager
from typing import Optional, Generator
import logging

from supabase import create_client, Client

from ..config import get_settings

logger = logging.getLogger(__name__)

# ── Module-level clients (lazy singletons) ──────────────────────
_service_client: Optional[Client] = None
_anon_client: Optional[Client] = None


def get_service_client() -> Client:
    """
    Return the service-role client (bypasses RLS).

    Use ONLY for:
    - Vault operations (secrets table — RLS allows only service_role SELECT)
    - Event store synchronous writes (append_sync)
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


def get_anon_client() -> Client:
    """
    Return the anon-key client (respects RLS when org_id is set).

    Use for read queries where you want RLS to apply normally.
    For writes with RLS, use TenantClient instead.
    """
    global _anon_client
    if _anon_client is None:
        settings = get_settings()
        _anon_client = create_client(
            settings.supabase_url,
            settings.supabase_anon_key,
        )
    return _anon_client


# ── TenantClient ────────────────────────────────────────────────

class TenantClient:
    """
    Wraps a Supabase client and sets session-level RLS config on enter.

    Usage::

        with TenantClient(org_id, user_id) as db:
            db.table("tasks").select("*").execute()
    """

    def __init__(self, client: Client, org_id: str, user_id: Optional[str] = None):
        self._client = client
        self._org_id = org_id
        self._user_id = user_id

    def __enter__(self) -> "TenantClient":
        """Set tenant config so that RLS policies filter by org."""
        try:
            self._client.rpc("set_config", {
                "p_key": "app.org_id",
                "p_value": self._org_id,
                "p_is_local": True,
            }).execute()

            if self._user_id:
                self._client.rpc("set_config", {
                    "p_key": "app.user_id",
                    "p_value": self._user_id,
                    "p_is_local": True,
                }).execute()

            logger.debug("Tenant config set: org_id=%s, user_id=%s", self._org_id, self._user_id)
        except Exception as exc:
            logger.error("Failed to set tenant config: %s", exc)
            raise
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Best-effort cleanup of session config."""
        try:
            self._client.rpc("set_config", {
                "p_key": "app.org_id",
                "p_value": "",
                "p_is_local": True,
            }).execute()
        except Exception as exc:
            logger.warning("Failed to clear tenant config: %s", exc)

    def table(self, table_name: str):
        """Proxy to supabase.table()."""
        return self._client.table(table_name)

    def rpc(self, func: str, params: dict):
        """Proxy to supabase.rpc()."""
        return self._client.rpc(func, params)


# ── convenience context manager ─────────────────────────────────

@contextmanager
def get_tenant_client(
    org_id: str,
    user_id: Optional[str] = None,
) -> Generator[TenantClient, None, None]:
    """
    Obtain a TenantClient with RLS scoped to *org_id*.

    Uses the service-role client internally to be able to call set_config RPC.

    Usage::

        with get_tenant_client("org_123") as db:
            db.table("tasks").select("*").execute()
    """
    client = TenantClient(get_service_client(), org_id, user_id)
    with client:
        yield client
