"""ServiceConnectorTool — Tool genérica para integraciones TIPO C.

Lee definiciones de la tabla service_tools, resuelve secretos del Vault,
ejecuta HTTP con httpx, sanitiza output (Regla R3), y audita en domain_events.

Correcciones vs plan original (mcp-analisis-finalV2.md):
  - httpx en vez de requests (pyproject.toml L23)
  - @register_tool decorador (registry.py L110-121)
  - domain_events en vez de activity_logs (001_set_config_rpc.sql L87-97)
"""

from __future__ import annotations

import base64

import httpx
import structlog
from typing import Type
from pydantic import BaseModel, Field

from src.tools.base_tool import OrgBaseTool
from src.tools.registry import register_tool
from src.db.session import get_service_client
from src.db.vault import get_secret, VaultError
from src.mcp.sanitizer import sanitize_output

logger = structlog.get_logger(__name__)


class ServiceConnectorInput(BaseModel):
    """Input genérico para ServiceConnectorTool."""
    tool_id: str = Field(description="ID de la tool (ej: stripe.create_customer)")
    input_data: dict = Field(default_factory=dict, description="Parámetros de la tool")


@register_tool(
    "service_connector",
    description="Ejecuta integraciones TIPO C del Service Catalog",
    timeout_seconds=30,
    retry_count=2,
    tags=["integration", "type_c", "http"],
)
class ServiceConnectorTool(OrgBaseTool):
    """Tool genérica que ejecuta cualquier integración TIPO C
    leyendo su definición de la tabla service_tools.

    Flujo (§10.5.4):
    1. Verificar que la org tiene el servicio activo
    2. Leer definición de la tool (execution, headers, url)
    3. Resolver secreto del Vault (Regla R3)
    4. Ejecutar HTTP con httpx
    5. Retornar resultado sanitizado
    """
    name: str = "service_connector"
    description: str = "Ejecuta una integración TIPO C del Service Catalog"
    args_schema: Type[BaseModel] = ServiceConnectorInput

    def _run(self, tool_id: str, input_data: dict = None) -> str:
        input_data = input_data or {}
        db = get_service_client()  # service_role, bypass RLS

        # 1. Obtener definición de la tool
        tool_result = (
            db.table("service_tools")
            .select("*, service_catalog!inner(id, auth_type, base_url)")
            .eq("id", tool_id)
            .maybe_single()
            .execute()
        )
        if not tool_result.data:
            return f"Error: Tool '{tool_id}' no encontrada en service_tools"

        tool_def = tool_result.data
        service_id = tool_def["service_id"]

        # 2. Verificar que la org tiene el servicio activo
        integration = (
            db.table("org_service_integrations")
            .select("*")
            .eq("org_id", self.org_id)
            .eq("service_id", service_id)
            .eq("status", "active")
            .maybe_single()
            .execute()
        )
        if not integration.data:
            return f"Error: Servicio '{service_id}' no está activo para esta organización"

        # 3. Resolver secreto (REGLA R3)
        secret_names = integration.data.get("secret_names", [])
        secret_value = None
        if secret_names:
            try:
                secret_value = get_secret(self.org_id, secret_names[0])
            except VaultError as e:
                return f"Error: {e}"

        # 4. Ejecutar HTTP con httpx
        execution = tool_def["execution"]
        url = execution["url"]
        method = execution.get("method", "POST").upper()
        headers = dict(execution.get("headers", {}))

        # Resolver URL con path params si hay placeholders
        if "{" in url and input_data:
            try:
                url = url.format(**input_data)
            except KeyError:
                pass  # SUPUESTO: si faltan params, usar la URL tal cual

        # Inyectar auth header según tipo
        if secret_value:
            auth_type = tool_def.get("service_catalog", {}).get("auth_type", "api_key")
            if auth_type == "oauth2":
                headers["Authorization"] = f"Bearer {secret_value}"
            elif auth_type == "basic_auth":
                headers["Authorization"] = f"Basic {base64.b64encode(secret_value.encode()).decode()}"
            else:  # api_key (default)
                headers["Authorization"] = f"Bearer {secret_value}"

        response = None
        try:
            with httpx.Client(timeout=30) as client:
                response = client.request(
                    method=method,
                    url=url,
                    headers=headers,
                    json=input_data if method in ("POST", "PUT", "PATCH") else None,
                    params=input_data if method == "GET" else None,
                )
                response.raise_for_status()
                try:
                    result = response.json()
                except Exception:
                    result = response.text[:500]
        except httpx.HTTPStatusError as e:
            result = f"Error HTTP: {e.response.status_code}"
        except httpx.RequestError as e:
            result = f"Error HTTP: {str(e)}"

        # 5. Sanitizar output (REGLA R3 — última línea de defensa)
        sanitized = sanitize_output(result)

        # 6. Auditar en domain_events (best-effort)
        try:
            db.table("domain_events").insert({
                "org_id": self.org_id,
                "aggregate_type": "service_integration",
                "aggregate_id": tool_id,
                "event_type": "tool_executed",
                "payload": {
                    "tool_id": tool_id,
                    "service_id": service_id,
                    "http_status": response.status_code if response else None,
                    "success": response.is_success if response else False,
                },
                "actor": "service_connector",
                "sequence": 0,
            }).execute()
        except Exception:
            logger.warning("audit_failed", tool_id=tool_id)

        return str(sanitized)
