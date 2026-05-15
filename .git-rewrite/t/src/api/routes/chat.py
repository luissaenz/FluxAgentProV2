"""src/api/routes/chat.py — Endpoint conversacional del Architect.

POST /chat/architect — Recibe mensaje NL, lanza ArchitectFlow
GET /chat/{conversation_id} — Consulta estado de una conversación
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, BackgroundTasks, Depends
from pydantic import BaseModel, Field
from typing import Optional
import logging

from ...db.conversation_store import (
    create_conversation,
    add_message,
    get_conversation,
    link_workflow,
    update_status,
)
from ...flows.architect_flow import ArchitectFlow
from ...guardrails.base_guardrail import check_quota, QuotaExceededError
from ..middleware import require_org_id

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/chat", tags=["chat"])


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1)
    conversation_id: Optional[str] = None


class ChatResponse(BaseModel):
    conversation_id: str
    status: str  # "generating" | "gathering_requirements" | "failed"
    reply: str
    flow_type: Optional[str] = None


@router.post("/architect", response_model=ChatResponse)
async def architect_chat(
    request: ChatRequest,
    background: BackgroundTasks,
    org_id: str = Depends(require_org_id),
    user_id: Optional[str] = None,
):
    """
    Endpoint conversacional para generar workflows.

    1. Guarda el mensaje del usuario
    2. Clasifica si hay suficiente contexto
    3. Si sí: lanza ArchitectFlow en background
    4. Si no: retorna pregunta de seguimiento
    """
    # Obtener o crear conversación
    conversation_id = request.conversation_id
    if not conversation_id:
        conversation_id = create_conversation(org_id, user_id)
    else:
        # Verificar que la conversación existe y es de esta org
        conv = get_conversation(conversation_id, org_id)
        if not conv:
            raise HTTPException(404, "Conversación no encontrada")

    # Guardar mensaje del usuario
    add_message(conversation_id, org_id, "user", request.message)

    # Verificar quota
    try:
        # check_quota(org_id, "tasks_per_month", current_count)
        pass  # Por implementar con el contador real
    except QuotaExceededError as e:
        raise HTTPException(429, detail=str(e))

    # Clasificar si hay suficiente contexto
    user_messages = [
        m for m in get_conversation(conversation_id, org_id).get("messages", [])
        if m.get("role") == "user"
    ]

    if len(user_messages) >= 2 or len(request.message) > 80:
        # Suficiente contexto → generar
        update_status(conversation_id, org_id, "generating")
        add_message(
            conversation_id, org_id, "assistant",
            "Estoy diseñando tu workflow. Te aviso cuando esté listo."
        )

        background.add_task(
            _run_architect_background,
            org_id=org_id,
            conversation_id=conversation_id,
            description=request.message,
        )

        return ChatResponse(
            conversation_id=conversation_id,
            status="generating",
            reply="Estoy diseñando tu workflow. Te aviso cuando esté listo.",
        )

    # Seguir recopilando información
    reply = _generate_followup(len(user_messages))
    add_message(conversation_id, org_id, "assistant", reply)

    return ChatResponse(
        conversation_id=conversation_id,
        status="gathering_requirements",
        reply=reply,
    )


@router.get("/{conversation_id}", response_model=ChatResponse)
async def get_chat_session(
    conversation_id: str,
    org_id: str = Depends(require_org_id),
):
    """Obtener estado y mensajes de una conversación."""
    conv = get_conversation(conversation_id, org_id)
    if not conv:
        raise HTTPException(404, "Conversación no encontrada")

    last_message = conv["messages"][-1] if conv.get("messages") else {}

    return ChatResponse(
        conversation_id=conversation_id,
        status=conv.get("status", "in_progress"),
        reply=last_message.get("content", ""),
        flow_type=conv.get("workflow_template_id"),
    )


def _generate_followup(message_count: int) -> str:
    """Generar pregunta de seguimiento."""
    if message_count == 1:
        return (
            "Entiendo que necesitas una automatización. "
            "¿Puedes describir los pasos que debería seguir?"
        )
    return (
        "¿Podrías darme más detalles sobre los datos de entrada "
        "y el resultado esperado?"
    )


async def _run_architect_background(
    org_id: str,
    conversation_id: str,
    description: str,
) -> None:
    """Ejecutar ArchitectFlow en background y actualizar conversación."""
    try:
        flow = ArchitectFlow(org_id=org_id)
        result = await flow.execute(
            input_data={
                "description": description,
                "conversation_id": conversation_id,
            },
            correlation_id=conversation_id,
        )

        flow_type = result.output_data.get("flow_type")
        template_id = result.output_data.get("template_id")

        add_message(
            conversation_id, org_id, "assistant",
            f"Workflow '{flow_type}' creado. "
            f"Ejecutalo con POST /webhooks/{org_id}/{flow_type}"
        )

        link_workflow(conversation_id, org_id, template_id)

        logger.info(
            "ArchitectFlow[%s] completó: %s",
            conversation_id, flow_type
        )

    except Exception as exc:
        logger.error("ArchitectFlow[%s] falló: %s", conversation_id, exc)
        update_status(conversation_id, org_id, "failed")
        add_message(
            conversation_id, org_id, "assistant",
            f"No pude generar el workflow: {exc}"
        )
