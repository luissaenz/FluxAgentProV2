"""src/db/conversation_store.py — Persistencia de conversaciones del Architect."""

from __future__ import annotations

import uuid
import logging
from typing import Optional

from .session import get_tenant_client, get_service_client

logger = logging.getLogger(__name__)


def create_conversation(org_id: str, user_id: Optional[str] = None) -> str:
    """Crear una nueva conversación y retornar su ID."""
    conversation_id = str(uuid.uuid4())

    with get_tenant_client(org_id, user_id) as db:
        db.table("conversations").insert({
            "id": conversation_id,
            "org_id": org_id,
            "user_id": user_id,
            "status": "in_progress",
        }).execute()

    return conversation_id


def add_message(
    conversation_id: str,
    org_id: str,
    role: str,  # "user" | "assistant" | "system"
    content: str,
) -> None:
    """Agregar un mensaje a una conversación."""
    with get_tenant_client(org_id) as db:
        db.table("conversation_messages").insert({
            "id": str(uuid.uuid4()),
            "conversation_id": conversation_id,
            "role": role,
            "content": content,
        }).execute()

        db.table("conversations").update({
            "updated_at": "now()",
        }).eq("id", conversation_id).execute()


def get_conversation(conversation_id: str, org_id: str) -> dict:
    """Obtener conversación con sus mensajes."""
    svc = get_service_client()

    conv = (
        svc.table("conversations")
        .select("*")
        .eq("id", conversation_id)
        .maybe_single()
        .execute()
    )

    if not conv.data:
        return {}

    messages = (
        svc.table("conversation_messages")
        .select("*")
        .eq("conversation_id", conversation_id)
        .order("created_at")
        .execute()
    )

    return {
        **conv.data,
        "messages": messages.data or [],
    }


def link_workflow(
    conversation_id: str,
    org_id: str,
    workflow_template_id: str,
) -> None:
    """Vincular una conversación con el workflow que generó."""
    with get_tenant_client(org_id) as db:
        db.table("conversations").update({
            "workflow_template_id": workflow_template_id,
            "status": "completed",
            "updated_at": "now()",
        }).eq("id", conversation_id).execute()


def update_status(
    conversation_id: str,
    org_id: str,
    status: str,
) -> None:
    """Actualizar el status de una conversación."""
    with get_tenant_client(org_id) as db:
        db.table("conversations").update({
            "status": status,
            "updated_at": "now()",
        }).eq("id", conversation_id).execute()
