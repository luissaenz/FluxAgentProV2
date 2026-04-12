"""OrgBaseTool — Clase base para tools con acceso al vault.

Regla R3: Los secretos nunca llegan al LLM.
Las subclases implementan _run() con lógica específica.
El LLM solo ve el RESULTADO de usar la credencial, no la credencial.
"""

from __future__ import annotations

from crewai.tools import BaseTool
from pydantic import BaseModel
from typing import Type

from ..db.vault import get_secret, VaultError


class OrgBaseTool(BaseTool):
    """
    Clase base para todas las tools del sistema.

    Características:
    - org_id viaja con la tool → RLS automático en queries
    - Método _get_secret() para obtener credenciales sin exponerlas al LLM
    - Las subclases implementan _run() con la lógica específica

    Attributes:
        org_id: UUID de la organización (usado para vault y RLS)
    """

    org_id: str

    def _get_secret(self, secret_name: str) -> str:
        """
        Obtener una credencial del vault.

        REGLA: Solo llamar internamente, nunca retornar el valor al LLM.
        El LLM solo ve el RESULTADO de usar la credencial.

        Args:
            secret_name: Nombre del secreto

        Returns:
            El valor del secreto en texto plano.

        Raises:
            VaultError: Si el secreto no existe.
        """
        return get_secret(self.org_id, secret_name)


# ── Ejemplo: SendMessageTool ──────────────────────────────────

class SendMessageInput(BaseModel):
    """Schema de input para SendMessageTool."""
    to: str
    message: str


class SendMessageTool(OrgBaseTool):
    """
    Envía un mensaje de texto al número especificado.

    El LLM no ve el token de la API de mensajería.
    Solo ve el resultado: "Mensaje enviado a +1234567890".
    """

    name: str = "send_message"
    description: str = "Envía un mensaje de texto al número especificado."
    args_schema: Type[BaseModel] = SendMessageInput

    def _run(self, to: str, message: str) -> str:
        # El LLM no ve el token. La tool lo obtiene internamente.
        try:
            self._get_secret("messaging_api_token")
        except VaultError as e:
            return f"Error: {e}"

        # ... llamada HTTP con api_token ...
        # mock por ahora:
        return f"Mensaje enviado a {to}"


# ── Ejemplo: SendEmailTool ─────────────────────────────────────

class SendEmailInput(BaseModel):
    """Schema de input para SendEmailTool."""
    to: str
    subject: str
    body: str


class SendEmailTool(OrgBaseTool):
    """
    Envía un email.

    El LLM no ve la contraseña SMTP.
    Solo ve el resultado: "Email enviado a user@example.com".
    """

    name: str = "send_email"
    description: str = "Envía un email al destinatario especificado."
    args_schema: Type[BaseModel] = SendEmailInput

    def _run(self, to: str, subject: str, body: str) -> str:
        try:
            self._get_secret("smtp_password")
        except VaultError as e:
            return f"Error: {e}"

        # ... lógica de envío ...
        return f"Email enviado a {to} con asunto: {subject}"
