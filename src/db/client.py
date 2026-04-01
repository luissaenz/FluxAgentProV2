"""src/db/client.py — Compatibility shim.

The real client lives in src/db/session.py.
This file re-exports everything that Phase 3 documentation expects from src.db.client.
"""

from src.db.session import (
    get_service_client,
    get_tenant_client,
    get_anon_client,
    TenantClient,
)

__all__ = ["get_service_client", "get_tenant_client", "get_anon_client", "TenantClient"]
