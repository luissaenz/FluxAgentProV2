"""MCPConfig — Configuración del servidor MCP con Pydantic BaseSettings."""

from pydantic_settings import BaseSettings


class MCPConfig(BaseSettings):
    """Configuración del servidor MCP de FAP.

    Variables de entorno con prefijo MCP_ (ej: MCP_TRANSPORT=sse).
    CLI args (--org-id) sobreescriben los env vars.
    """
    enabled: bool = True
    transport: str = "stdio"       # stdio | sse (SSE → Sprint 4)
    host: str = "127.0.0.1"       # Solo SSE
    port: int = 8765              # Solo SSE
    require_auth: bool = False    # Sprint 3
    allowed_orgs: list[str] = []  # Vacío = todas
    org_id: str = ""              # Recibido vía --org-id CLI

    model_config = {"env_prefix": "MCP_"}
