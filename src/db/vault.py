"""Vault — Proxy de secretos para herramientas.

Regla R3: Los secretos nunca llegan al LLM.
Las tools obtienen credenciales internamente y solo retornan
el resultado de la operación.
"""

from __future__ import annotations

from typing import List
import logging

from .session import get_service_client

logger = logging.getLogger(__name__)


class VaultError(Exception):
    """Error al obtener un secreto del vault."""
    pass


def get_secret(org_id: str, secret_name: str) -> str:
    """
    Obtener un secreto cifrado para una organización.

    IMPORTANTE:
    - Usa service_role (bypasea RLS — la tabla secrets solo permite service_role)
    - Retorna el valor en claro. La tool que llama esto es responsable de no loguearlo.
    - Lanza VaultError si el secreto no existe.

    Args:
        org_id: UUID de la organización
        secret_name: Nombre del secreto (ej: "messaging_api_token", "stripe_key")

    Returns:
        El valor del secreto en texto plano.

    Raises:
        VaultError: Si el secreto no existe o no se puede acceder.

    Usage:
        token = get_secret("org_123", "messaging_api_token")
    """
    svc = get_service_client()

    result = (
        svc.table("secrets")
        .select("secret_value")
        .eq("org_id", org_id)
        .eq("name", secret_name)
        .maybe_single()
        .execute()
    )

    if not result.data:
        raise VaultError(
            f"Secreto '{secret_name}' no configurado para org '{org_id}'"
        )

    return result.data["secret_value"]


def list_secrets(org_id: str) -> List[str]:
    """
    Listar los nombres de secretos disponibles para una organización.

    No retorna los valores, solo los nombres (para metadata/UI).

    Returns:
        Lista de nombres de secretos.
    """
    svc = get_service_client()

    result = (
        svc.table("secrets")
        .select("name")
        .eq("org_id", org_id)
        .execute()
    )

    return [row["name"] for row in result.data]


async def get_secret_async(org_id: str, secret_name: str) -> str:
    """Wrapper async de get_secret() para uso en event loops MCP.

    Usa asyncio.to_thread() para no bloquear el event loop.
    Disponible desde Python 3.9 (proyecto requiere >=3.12).

    Args:
        org_id: UUID de la organización
        secret_name: Nombre del secreto

    Returns:
        El valor del secreto en texto plano.

    Raises:
        VaultError: Si el secreto no existe o no se puede acceder.
    """
    import asyncio
    return await asyncio.to_thread(get_secret, org_id, secret_name)
