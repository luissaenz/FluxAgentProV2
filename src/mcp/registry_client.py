"""src/mcp/registry_client.py — Buscador de servidores MCP en registros externos."""

import re
import logging
import httpx
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from ..db.session import get_service_client

logger = logging.getLogger(__name__)

@dataclass
class MCPServerInfo:
    """Servidor MCP descubierto en un registro externo."""
    name: str                           # "Google Sheets MCP"
    source: str                         # "github_registry"
    url: str                            # URL del repo
    command: str | None = None          # "npx" | "python" | None (SSE)
    args: list[str] | None = None      # ["-y", "@modelcontextprotocol/server-google-sheets"]
    tools: list[dict] = field(default_factory=list)
    description: str = ""
    auth_required: bool = False
    install_instructions: str = ""

class MCPRegistryClient:
    """Busca y descubre servidores MCP en registros externos (GitHub Registry)."""
    
    REGISTRY_URL = "https://registry.modelcontextprotocol.io/v0.1/servers"
    TIMEOUT = 10  # segundos

    async def search(self, query: str) -> List[MCPServerInfo]:
        """Busca en GitHub MCP Registry. Retorna max 5 resultados."""
        logger.info("Buscando servidores MCP para: '%s'", query)
        try:
            async with httpx.AsyncClient(timeout=self.TIMEOUT) as client:
                resp = await client.get(self.REGISTRY_URL)
                resp.raise_for_status()
                data = resp.json()
                servers = data.get("servers", [])
        except Exception as e:
            logger.error("Error consultando GitHub MCP Registry: %s", e)
            return []

        query_lower = query.lower()
        results = []
        for srv in servers:
            name = srv.get("name", "").lower()
            desc = srv.get("description", "").lower()
            if query_lower in name or query_lower in desc:
                results.append(MCPServerInfo(
                    name=srv.get("name", ""),
                    source="github_registry",
                    url=srv.get("repository", {}).get("url", ""),
                    description=srv.get("description", ""),
                ))
        
        logger.info("Encontrados %d servidores para '%s'", len(results), query)
        return results[:5]

    async def discover_tools(self, server: MCPServerInfo) -> List[Dict[str, Any]]:
        """Parsea README del repo para extraer tools. NO ejecuta servidor.
        
        Estrategia:
          1. Fetch README.md del repo (via raw GitHub URL)
          2. Buscar patrones: headers con 'Tools', tablas markdown, etc.
          3. Extraer name + description de cada tool.
          4. Fallback: retornar tool genérica con name=server.name.
        """
        # Construir URL raw del README (Asumiendo GitHub)
        repo_url = server.url.rstrip("/")
        # SUPUESTO: El repo es de GitHub y la rama principal es 'main' o 'master'
        raw_base = repo_url.replace("github.com", "raw.githubusercontent.com")
        
        # Intentar con 'main' y luego 'master'
        readme_urls = [f"{raw_base}/main/README.md", f"{raw_base}/master/README.md"]
        readme_text = None

        async with httpx.AsyncClient(timeout=self.TIMEOUT) as client:
            for url in readme_urls:
                try:
                    resp = await client.get(url)
                    if resp.status_code == 200:
                        readme_text = resp.text
                        break
                except httpx.RequestError:
                    continue

        if not readme_text:
            logger.warning("No se pudo obtener README para %s, usando fallback", server.name)
            return [{"name": server.name, "description": server.description}]

        return self._parse_tools_from_readme(readme_text, server.name, server.description)

    def _parse_tools_from_readme(self, readme: str, server_name: str, fallback_desc: str) -> List[Dict[str, Any]]:
        """Extrae tools de un README markdown usando regex."""
        tools = []
        lines = readme.split("\n")
        in_tools_section = False

        for line in lines:
            lower = line.lower().strip()
            # Detectar inicio de sección de tools
            if any(kw in lower for kw in ["## tools", "## available tools", "### tools"]):
                in_tools_section = True
                continue
            
            # Salir de sección si encontramos otro header principal
            if in_tools_section and line.startswith("## ") and "tool" not in lower:
                in_tools_section = False
            
            if in_tools_section:
                # Patrón 1: `tool_name` — description
                match = re.search(r"`([\w_.-]+)`\s*[-—:]\s*(.+)", line)
                if match:
                    tools.append({
                        "name": match.group(1),
                        "description": match.group(2).strip(),
                    })
                    continue
                
                # Patrón 2: | tool_name | description |
                if "|" in line and not line.strip().startswith("|---"):
                    parts = [p.strip() for p in line.split("|") if p.strip()]
                    # Omitir header de tabla (Tool | Description)
                    if len(parts) >= 2 and not parts[0].lower().startswith("tool"):
                        tools.append({
                            "name": parts[0].strip("`"),
                            "description": parts[1].strip() if len(parts) > 1 else "",
                        })

        if not tools:
            # Fallback si no se encontró nada parseable
            tools.append({"name": server_name, "description": fallback_desc})

        return tools

    async def import_as_type_b(self, server: MCPServerInfo, org_id: str) -> str:
        """Importa como servidor MCP externo en org_mcp_servers."""
        db = get_service_client()
        # SUPUESTO: El server ya tiene tools llenas si se va a importar como Tipo C, 
        # pero para Tipo B (Stdio) solo necesitamos command y args.
        result = db.table("org_mcp_servers").upsert({
            "org_id": org_id,
            "name": server.name,
            "command": server.command or "npx",
            "args": server.args or [],
            "is_active": False,  # D3: Forzar FALSE para configuración manual
        }, on_conflict="org_id,name").execute()
        
        if not result.data:
            raise RuntimeError(f"Fallo al importar servidor {server.name} como Tipo B")
            
        return str(result.data[0]["id"])

    async def import_as_type_c(self, server: MCPServerInfo, org_id: str) -> List[str]:
        """Importa tools como TIPO C en service_catalog + service_tools."""
        db = get_service_client()
        service_id = server.name.lower().replace(" ", "_").replace("-", "_")

        # 1. Crear/Actualizar Proveedor (service_catalog)
        db.table("service_catalog").upsert({
            "id": service_id,
            "name": server.name,
            "category": "external_mcp",
            "auth_type": "api_key" if server.auth_required else "none",
            "base_url": server.url,
        }, on_conflict="id").execute()

        # 2. Insertar cada Tool (service_tools)
        tool_ids = []
        for tool in server.tools:
            tool_name = tool["name"]
            tool_id = f"{service_id}.{tool_name}"
            # D3: execution format unificado
            db.table("service_tools").upsert({
                "id": tool_id,
                "service_id": service_id,
                "name": tool_name,
                "input_schema": tool.get("inputSchema", {}),
                "output_schema": {},
                "execution": {"type": "mcp", "server": server.name},
                "tool_profile": {
                    "description": tool.get("description", ""),
                    "risk_level": "medium",
                    "requires_approval": False,
                },
            }, on_conflict="id").execute()
            tool_ids.append(tool_id)

        return tool_ids
