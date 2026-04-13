"""Health check para integraciones activas del Service Catalog.

Recorre las integraciones con health_check_url definida y actualiza
last_health_check / last_health_status en org_service_integrations.

Ubicación: src/scheduler/ (coherente con bartenders_jobs.py existente).
Corrección vs plan: src/scheduler/ en vez de src/jobs/ (no existe).
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone

import httpx

from src.db.session import get_service_client
from src.db.vault import get_secret

logger = logging.getLogger(__name__)


async def run_health_checks() -> None:
    """Health check para integraciones activas con health_check_url definida."""
    db = get_service_client()

    integrations = (
        db.table("org_service_integrations")
        .select("*, service_catalog!inner(health_check_url, auth_type)")
        .eq("status", "active")
        .not_.is_("service_catalog.health_check_url", "null")
        .execute()
    )

    if not integrations.data:
        logger.info("No active integrations with health_check_url found")
        return

    async with httpx.AsyncClient(timeout=10) as client:
        for integration in integrations.data:
            health_url = integration["service_catalog"]["health_check_url"]
            org_id = integration["org_id"]
            integration_id = integration["id"]

            try:
                secret = None
                secret_names = integration.get("secret_names", [])
                if secret_names:
                    secret = get_secret(org_id, secret_names[0])

                headers = {}
                if secret:
                    headers["Authorization"] = f"Bearer {secret}"

                resp = await client.get(health_url, headers=headers)
                status = "ok" if resp.status_code < 400 else "error"
                error_msg = None if status == "ok" else f"HTTP {resp.status_code}"

            except Exception as e:
                status = "timeout" if "timeout" in str(e).lower() else "error"
                error_msg = str(e)[:200]

            try:
                db.table("org_service_integrations").update({
                    "last_health_check": datetime.now(timezone.utc).isoformat(),
                    "last_health_status": status,
                    "error_message": error_msg,
                }).eq("id", integration_id).execute()
            except Exception as update_err:
                logger.warning(
                    "Failed to update health status for integration %s: %s",
                    integration_id, update_err,
                )
