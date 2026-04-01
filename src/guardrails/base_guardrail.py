"""Guardrails — Validadores de reglas de negocio.

Los guardrails evalúan umbrales y reglas antes de que el Flow
continúe. Se usan en los @router de los Flows para bifurcar
según condiciones de negocio.
"""

from __future__ import annotations

from typing import Callable, Dict, Any
import logging

from ..db.session import get_tenant_client

logger = logging.getLogger(__name__)


# ── Org limits loader ──────────────────────────────────────────

def load_org_limits(org_id: str) -> Dict[str, Any]:
    """
    Cargar límites configurados para la organización.

    Lee desde organizations.config -> limits.

    Returns:
        Dict con los límites de la org. Vacío si no hay config o error.
    """
    try:
        with get_tenant_client(org_id) as db:
            result = (
                db.table("organizations")
                .select("config")
                .eq("id", org_id)
                .single()
                .execute()
            )
            return result.data.get("config", {}).get("limits", {})
    except Exception as e:
        logger.warning("Could not load org limits for %s: %s", org_id, e)
        return {}


# ── Approval check factory ─────────────────────────────────────

def make_approval_check(
    amount_field: str,
    threshold_key: str,
    default_threshold: float,
) -> Callable[[float, str], bool]:
    """
    Factory para crear funciones de verificación de aprobación.

    La función retornada compara un valor contra un umbral configurable
    por organización.

    Args:
        amount_field: Nombre del campo en el estado (para logging)
        threshold_key: Clave en organizations.config.limits
        default_threshold: Valor por defecto si no hay config

    Returns:
        Función (value, org_id) -> bool. True si requiere aprobación.

    Usage::

        @router(ejecutar_paso)
        def decidir_aprobacion(self) -> str:
            check = make_approval_check(
                amount_field="monto",
                threshold_key="approval_threshold",
                default_threshold=50_000
            )
            if check(self.state.monto, self.state.org_id):
                return "solicitar_aprobacion"
            return "continuar"
    """
    def check(value: float, org_id: str) -> bool:
        limits = load_org_limits(org_id)
        threshold = limits.get(threshold_key, default_threshold)
        requires_approval = value > threshold

        if requires_approval:
            logger.info(
                "Guardrail triggered: %s=%.2f exceeds threshold=%.2f "
                "(org_id=%s, key=%s)",
                amount_field, value, threshold, org_id, threshold_key
            )

        return requires_approval

    return check


# ── Quota checker ─────────────────────────────────────────────

class QuotaExceededError(Exception):
    """Se lanza cuando una org supera su cuota."""
    pass


def check_quota(org_id: str, quota_type: str, current_usage: int) -> None:
    """
    Verificar que la org no haya excedido su cuota.

    Args:
        org_id: UUID de la organización
        quota_type: Tipo de cuota ("tasks_per_month", "tokens_per_month")
        current_usage: Uso actual

    Raises:
        QuotaExceededError: Si la cuota está agotada.

    Usage::
        check_quota(org_id, "tasks_per_month", tasks_this_month)
    """
    limits = load_org_limits(org_id)
    quota_key = f"max_{quota_type}"
    limit = limits.get(quota_key, float("inf"))

    if current_usage >= limit:
        raise QuotaExceededError(
            f"Cuota '{quota_type}' agotada: {current_usage}/{limit} "
            f"para org {org_id}"
        )
