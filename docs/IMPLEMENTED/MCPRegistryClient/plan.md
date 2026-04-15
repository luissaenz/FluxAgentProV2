PASO 1: MCPRegistryClient — Definición
Qué es
Clase Python que busca servidores MCP en registros externos cuando IntegrationResolver retorna tools en not_found. Descubre servidores, extrae sus tools vía tools/list, y las importa al catálogo local (org_mcp_servers para TIPO B, o service_catalog + service_tools para TIPO C).
Dónde se inserta
Flujo actual (post-IntegrationResolver):
  resolve() retorna not_found: ["custom_erp_read"]
    → _build_resolution_response → "Integración no encontrada"
    → FIN (usuario no puede hacer nada)

Flujo nuevo:
  resolve() retorna not_found: ["custom_erp_read"]
    → MCPRegistryClient.search("custom_erp")
      → Encuentra servidor MCP en registry externo
      → Conecta al servidor → tools/list → extrae definiciones
      → Importa a org_mcp_servers (TIPO B) o service_tools (TIPO C)
    → Re-ejecuta resolve() → ahora matchea → is_ready=True
    → Persiste workflow
La integración tiene dos puntos de entrada posibles:
A. Automático dentro de resolve(): Cuando not_found no está vacío, resolver llama a MCPRegistryClient.search() antes de retornar. Si encuentra y el usuario confirma, importa y re-resuelve.
B. Como paso separado post-resolución: ArchitectFlow recibe not_found, le pregunta al usuario "¿Busco esta integración en registros externos?", si dice sí, llama a MCPRegistryClient, importa, y re-ejecuta resolve().
Recomendación: Opción B. Más explícito, el usuario decide si buscar afuera. Evita llamadas a registros externos sin consentimiento.
Interfaz
python# src/mcp/registry_client.py

from dataclasses import dataclass, field

@dataclass
class MCPServerInfo:
    """Servidor MCP descubierto en un registro externo."""
    name: str                    # "Google Sheets MCP"
    source: str                  # "github_registry" | "mcpmarket" | "manual"
    url: str                     # URL del servidor o repo
    command: str | None          # "npx" | "python" | None (si es SSE)
    args: list[str] | None      # ["-y", "@modelcontextprotocol/server-google-sheets"]
    tools: list[dict] = field(default_factory=list)  # tools descubiertas vía tools/list
    description: str = ""
    auth_required: bool = False
    install_instructions: str = ""


class MCPRegistryClient:
    """Busca y descubre servidores MCP en registros externos."""

    async def search(self, query: str) -> list[MCPServerInfo]:
        """Busca servidores MCP que matcheen la query.
        
        Consulta fuentes en orden:
          1. GitHub MCP Registry (registry.modelcontextprotocol.io)
          2. Futuro: mcpmarket.com, smithery.ai
        
        Retorna lista de servidores encontrados, sin instalar nada.
        """

    async def discover_tools(self, server: MCPServerInfo) -> list[dict]:
        """Conecta a un servidor MCP y ejecuta tools/list.
        
        Para servidores Stdio: lanza proceso hijo, hace handshake, obtiene tools.
        Para servidores SSE: conecta al endpoint, hace tools/list.
        
        Retorna lista de Tool definitions (name, description, inputSchema).
        """

    async def import_as_type_b(self, server: MCPServerInfo, org_id: str) -> str:
        """Importa servidor como TIPO B en org_mcp_servers.
        
        Inserta fila con command, args, secret_name.
        El MCPPool existente se encarga de conectar y ejecutar.
        Retorna el ID del registro creado.
        """

    async def import_as_type_c(self, server: MCPServerInfo, org_id: str) -> list[str]:
        """Importa tools del servidor como TIPO C en service_catalog + service_tools.
        
        Crea proveedor en service_catalog si no existe.
        Inserta cada tool en service_tools con execution type="mcp".
        Retorna lista de IDs de tools creadas.
        """
Fuentes de descubrimiento
FuenteURLMétodoQué retornaGitHub MCP Registryhttps://registry.modelcontextprotocol.io/v0.1/serversGET (JSON)Lista de servidores con name, description, repo URLFuturo: mcpmarket.comTBDScraping o APIServidores curados con docsManual (usuario pega URL)N/AUsuario proporciona command+args o URL SSEUn solo servidor
Para MVP, solo GitHub MCP Registry. Las otras fuentes son roadmap.
Lógica interna de search()
pythonasync def search(self, query: str) -> list[MCPServerInfo]:
    """
    1. GET https://registry.modelcontextprotocol.io/v0.1/servers
    2. Filtrar por query en name + description (case-insensitive)
    3. Convertir a MCPServerInfo
    4. Retornar top 5 matches
    """
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(
            "https://registry.modelcontextprotocol.io/v0.1/servers"
        )
        servers = resp.json().get("servers", [])

    results = []
    query_lower = query.lower()
    for srv in servers:
        name = srv.get("name", "").lower()
        desc = srv.get("description", "").lower()
        if query_lower in name or query_lower in desc:
            results.append(MCPServerInfo(
                name=srv.get("name", ""),
                source="github_registry",
                url=srv.get("repository", {}).get("url", ""),
                command=None,  # se resuelve en discover_tools
                args=None,
                description=srv.get("description", ""),
            ))

    return results[:5]
Lógica de discover_tools()
pythonasync def discover_tools(self, server: MCPServerInfo) -> list[dict]:
    """
    Si el servidor tiene command+args (Stdio):
      1. Lanzar proceso: subprocess con command + args
      2. JSON-RPC: enviar initialize → tools/list
      3. Parsear respuesta → lista de tools
      4. Terminar proceso

    Si el servidor tiene URL SSE:
      1. Conectar vía httpx al endpoint SSE
      2. JSON-RPC: tools/list
      3. Parsear respuesta
    
    Para MVP: solo parsear README/docs del repo para extraer 
    lista de tools sin ejecutar el servidor (más seguro).
    """
Decisión importante: Para MVP, discover_tools NO ejecuta el servidor MCP externo. Eso requiere instalar dependencias (npx, pip) y es un riesgo de seguridad. En cambio, parsea la documentación del repo (README) para extraer la lista de tools. La ejecución real la hace MCPPool después de que el admin configure el servidor.
Lógica de import
TIPO B (servidor MCP externo — org_mcp_servers):
pythonasync def import_as_type_b(self, server: MCPServerInfo, org_id: str) -> str:
    db = get_service_client()
    result = db.table("org_mcp_servers").insert({
        "org_id": org_id,
        "name": server.name,
        "command": server.command or "npx",
        "args": server.args or [],
        "is_active": False,  # requiere configuración manual
    }).execute()
    return result.data[0]["id"]
TIPO C (tools REST — service_catalog + service_tools):
pythonasync def import_as_type_c(self, server: MCPServerInfo, org_id: str) -> list[str]:
    db = get_service_client()
    
    # Crear proveedor si no existe
    service_id = server.name.lower().replace(" ", "_")
    db.table("service_catalog").upsert({
        "id": service_id,
        "name": server.name,
        "category": "external_mcp",
        "auth_type": "api_key" if server.auth_required else "none",
        "base_url": server.url,
    }, on_conflict="id").execute()

    # Insertar tools
    tool_ids = []
    for tool in server.tools:
        tool_id = f"{service_id}.{tool['name']}"
        db.table("service_tools").upsert({
            "id": tool_id,
            "service_id": service_id,
            "name": tool["name"],
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
Integración en el flujo
Después de que IntegrationResolver retorna not_found, ArchitectFlow tiene dos opciones:
python# En architect_flow.py — dentro de la lógica post-resolver

if resolution.not_found:
    # Buscar en registros externos
    from src.mcp.registry_client import MCPRegistryClient
    registry = MCPRegistryClient()
    
    discovered = {}
    for tool_hint in resolution.not_found:
        # Extraer keyword de búsqueda del hint
        search_query = tool_hint.replace("_", " ").split(".")[0]
        results = await registry.search(search_query)
        if results:
            discovered[tool_hint] = results

    if discovered:
        # Retornar opciones al usuario para que elija
        return {
            "status": "external_integrations_found",
            "not_found": resolution.not_found,
            "discovered": {
                hint: [{"name": s.name, "description": s.description, "url": s.url} 
                       for s in servers]
                for hint, servers in discovered.items()
            },
            "message": self._build_discovery_message(discovered),
        }
El usuario ve algo como:
Encontré estas integraciones externas que podrían servir:

Para "google_sheets_read":
  1. Google Sheets MCP — Servidor oficial de Google Sheets
     → ¿Querés que lo instale?

Para "custom_crm":
  No encontré nada. ¿Tenés la URL del servidor MCP?
Archivos afectados
ArchivoCambiosrc/mcp/registry_client.pyNUEVO — MCPRegistryClient + MCPServerInfosrc/flows/architect_flow.pyMODIFICAR — agregar paso de búsqueda externa post-resolversrc/flows/integration_resolver.pySIN CAMBIOS — el resolver no llama al registry, ArchitectFlow lo hace
Esfuerzo estimado
TareaTiempoMCPServerInfo dataclass + MCPRegistryClient clase30minsearch() contra GitHub MCP Registry1.5hdiscover_tools() — parseo de README/docs (no ejecución)2himport_as_type_b() + import_as_type_c()1hIntegración en ArchitectFlow (post-resolver)1hTests (mock HTTP de registry + mock DB)1.5hTotal~7.5h
Decisiones clave

No ejecutar servidores MCP externos en discover_tools para MVP — riesgo de seguridad. Solo parsear docs.
Import como TIPO B por defecto — org_mcp_servers ya existe y MCPPool sabe conectar. TIPO C solo si el servidor expone REST puro.
Búsqueda solo en GitHub MCP Registry para MVP — fuente oficial, API estable.
El usuario elige qué instalar — no auto-importar. ArchitectFlow presenta opciones y el usuario confirma.
Servidores importados arrancan con is_active: False — requieren configuración manual (credenciales, etc.) antes de activarse.

