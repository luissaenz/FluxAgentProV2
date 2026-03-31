"""TenantClient — Context manager that injects RLS tenant context via set_config RPC."""

from __future__ import annotations

from contextlib import contextmanager
from typing import Optional, Generator
import logging

from supabase import create_client, Client

from ..config import get_settings

logger = logging.getLogger(__name__)

# ── Module-level Supabase client (lazy singleton) ──────────────
_supabase_client: Optional[Client] = None


def get_supabase_client() -> Client:
    """Return a module-level Supabase client, creating it on first call."""
    global _supabase_client
    if _supabase_client is None:
        settings = get_settings()
        _supabase_client = create_client(
            settings.supabase_url,
            settings.supabase_service_key,
        )
    return _supabase_client


# ── TenantClient ───────────────────────────────────────────────

class TenantClient:
    """Wraps a Supabase client and sets session-level RLS config on enter."""

    def __init__(self, supabase: Client, org_id: str, user_id: Optional[str] = None):
        self._client = supabase
        self._org_id = org_id
        self._user_id = user_id

    # -- context manager protocol ---------------------------------

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

    # -- proxied helpers ------------------------------------------

    def table(self, table_name: str):
        """Proxy to supabase.table()."""
        return self._client.table(table_name)

    def rpc(self, func: str, params: dict):
        """Proxy to supabase.rpc()."""
        return self._client.rpc(func, params)


# ── convenience context manager ────────────────────────────────

@contextmanager
def get_tenant_client(
    org_id: str,
    user_id: Optional[str] = None,
) -> Generator[TenantClient, None, None]:
    """
    Obtain a TenantClient with RLS scoped to *org_id*.

    Usage::

        with get_tenant_client("org_123") as db:
            db.table("tasks").select("*").execute()
    """
    client = TenantClient(get_supabase_client(), org_id, user_id)
    with client:
        yield client
