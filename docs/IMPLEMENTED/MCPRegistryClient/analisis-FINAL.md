# � ANÁLISIS FINAL UNIFICADO — MCPRegistryClient (Paso 2)

**Autor:** Unificador
**Fuentes:** `analisis-atg.md`, `analisis-kilo.md`, `analisis-oc.md`
**Fecha:** 2026-04-15

---

## 0. Evaluación de Análisis

| Agente | §0 elementos | Discrepancias | Score |
|:---|:---|:---|:---|
| **Kilo** | 16 | 2 (discover_tools sin spec concreta, API puede cambiar) | **4** |
| **OC** | 15 | 3 (is_active DEFAULT TRUE, SSE vs Stdio, URL validation) | **4** |
| **ATG** | 12 | 3 (execution JSONB format, get_service_client path, flow principal) | **3** |

### Discrepancias Consolidadas

| # | Discrepancia | Resolución |
|:---|:---|:---|
| 1 | `org_mcp_servers.is_active` tiene DEFAULT TRUE en migración 005. Import debe forzar FALSE. | Usar valor explícito `is_active: False` en insert. (OC) |
| 2 | `discover_tools()` sin especificación concreta de parseo de README | Usar regex para extraer bloques de tools de README.md del repo. Fallback: usar solo name+description del registry. (ATG, Kilo) |
| 3 | `execution` en service_tools es JSONB libre — formato `{"type": "mcp", "server": name}` no validado | Mantener formato propuesto. Coherente con execution.type existente ("http") en ServiceConnectorTool. (ATG) |

---

## 1. Resumen Ejecutivo

MCPRegistryClient busca servidores MCP en registros externos cuando IntegrationResolver retorna tools en `not_found`. Descubre servidores, extrae metadata de tools desde docs (sin ejecutar), y los importa al catálogo local. Se integra en ArchitectFlow como paso posterior al resolver, solo si el usuario confirma la búsqueda externa.

---

## 2. Diseño Funcional

### Happy Path

1. IntegrationResolver retorna `not_found: ["calendar_create_event"]`
2. ArchitectFlow pregunta al usuario: "¿Busco integraciones externas?"
3. Usuario confirma → MCPRegistryClient.search("calendar")
4. Registry retorna: `[{name: "Google Calendar MCP", ...}]`
5. Sistema muestra opciones al usuario
6. Usuario elige instalar como TIPO B
7. `import_as_type_b()` → org_mcp_servers con is_active=False
8. Re-ejecutar resolve() → ahora matchea → workflow se persiste

### Edge Cases

| Escenario | Comportamiento |
|:---|:---|
| Registry no retorna resultados | "No encontré integraciones externas. ¿Tenés la URL del servidor MCP?" |
| Usuario rechaza | Retornar al estado anterior con diagnóstico original |
| Error HTTP / timeout | "Error conectando al registro. Configurá manualmente." Timeout: 10s. |
| Servidor ya existe (mismo name+org) | Upsert, no duplicar |
| README sin tools parseables | Usar solo name+description del registry como fallback |
| Múltiples resultados | Presentar top 5, usuario elige |

### Manejo de Errores

| Error | Qué ve el usuario | Qué se loggea |
|:---|:---|:---|
| Timeout red | "No se pudo contactar el registro externo" | logger.warning con URL y timeout |
| JSON inválido | Lista vacía de resultados | logger.error con response body |
| Parseo README falla | Tools con solo name+description | logger.warning, usa fallback |

---

## 3. Diseño Técnico

### Componentes

```
src/mcp/registry_client.py    ← NUEVO: MCPRegistryClient + MCPServerInfo
src/flows/architect_flow.py    ← MODIFICAR: paso post-resolver para búsqueda externa
```

IntegrationResolver NO se modifica.

### 3.1 — MCPServerInfo

```python
@dataclass
class MCPServerInfo:
    name: str                           # "Google Sheets MCP"
    source: str                         # "github_registry"
    url: str                            # URL del repo
    command: str | None = None          # "npx" | "python" | None (SSE)
    args: list[str] | None = None      # ["-y", "@modelcontextprotocol/server-google-sheets"]
    tools: list[dict] = field(default_factory=list)
    description: str = ""
    auth_required: bool = False
    install_instructions: str = ""
```

### 3.2 — MCPRegistryClient

```python
class MCPRegistryClient:
    REGISTRY_URL = "https://registry.modelcontextprotocol.io/v0.1/servers"
    TIMEOUT = 10  # seconds

    async def search(self, query: str) -> list[MCPServerInfo]:
        """Busca en GitHub MCP Registry. Retorna max 5 resultados."""
        async with httpx.AsyncClient(timeout=self.TIMEOUT) as client:
            resp = await client.get(self.REGISTRY_URL)
            resp.raise_for_status()
            servers = resp.json().get("servers", [])

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
        return results[:5]

    async def discover_tools(self, server: MCPServerInfo) -> list[dict]:
        """Parsea README del repo para extraer tools. NO ejecuta servidor.
        
        Estrategia:
          1. Fetch README.md del repo (via raw GitHub URL)
          2. Buscar patrones: headers con "Tools", tablas markdown, listas con descriptions
          3. Extraer name + description de cada tool
          4. Fallback: retornar tool genérica con name=server.name
        """
        # Construir URL raw del README
        repo_url = server.url.rstrip("/")
        raw_url = repo_url.replace("github.com", "raw.githubusercontent.com") + "/main/README.md"

        try:
            async with httpx.AsyncClient(timeout=self.TIMEOUT) as client:
                resp = await client.get(raw_url)
                if resp.status_code != 200:
                    return [{"name": server.name, "description": server.description}]
                readme = resp.text
        except httpx.RequestError:
            return [{"name": server.name, "description": server.description}]

        return self._parse_tools_from_readme(readme, server.name)

    def _parse_tools_from_readme(self, readme: str, server_name: str) -> list[dict]:
        """Extrae tools de un README markdown.
        
        Busca patrones comunes:
          - Tablas con columnas Tool/Name + Description
          - Headers ### seguidos de descripción
          - Listas con backticks (`tool_name`)
        """
        tools = []
        lines = readme.split("\n")
        in_tools_section = False

        for i, line in enumerate(lines):
            lower = line.lower().strip()
            # Detectar sección de tools
            if any(kw in lower for kw in ["## tools", "## available tools", "### tools"]):
                in_tools_section = True
                continue
            # Salir de sección al encontrar otro header de mismo nivel
            if in_tools_section and line.startswith("## ") and "tool" not in lower:
                break
            # Parsear líneas dentro de la sección
            if in_tools_section:
                # Patrón: `tool_name` — description
                # Patrón: | tool_name | description |
                if "`" in line:
                    import re
                    match = re.search(r"`(\w+)`\s*[-—:]\s*(.+)", line)
                    if match:
                        tools.append({
                            "name": match.group(1),
                            "description": match.group(2).strip(),
                        })
                elif "|" in line and not line.strip().startswith("|---"):
                    parts = [p.strip() for p in line.split("|") if p.strip()]
                    if len(parts) >= 2 and not parts[0].lower().startswith("tool"):
                        tools.append({
                            "name": parts[0].strip("`"),
                            "description": parts[1] if len(parts) > 1 else "",
                        })

        if not tools:
            tools.append({"name": server_name, "description": server.description if hasattr(server, 'description') else ""})

        return tools

    async def import_as_type_b(self, server: MCPServerInfo, org_id: str) -> str:
        """Importa como servidor MCP externo en org_mcp_servers."""
        db = get_service_client()
        result = db.table("org_mcp_servers").upsert({
            "org_id": org_id,
            "name": server.name,
            "command": server.command or "npx",
            "args": server.args or [],
            "is_active": False,  # Explícito — DEFAULT es TRUE en migración
        }, on_conflict="org_id,name").execute()
        return str(result.data[0]["id"])

    async def import_as_type_c(self, server: MCPServerInfo, org_id: str) -> list[str]:
        """Importa tools como TIPO C en service_catalog + service_tools."""
        db = get_service_client()
        service_id = server.name.lower().replace(" ", "_").replace("-", "_")

        # Proveedor
        db.table("service_catalog").upsert({
            "id": service_id,
            "name": server.name,
            "category": "external_mcp",
            "auth_type": "api_key" if server.auth_required else "none",
            "base_url": server.url,
        }, on_conflict="id").execute()

        # Tools
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
```

### 3.3 — Integración en ArchitectFlow

Después de `_build_resolution_response` (L454+), agregar paso de búsqueda externa:

```python
# architect_flow.py — después de resolver, si hay not_found

if resolution.not_found:
    from src.mcp.registry_client import MCPRegistryClient
    registry = MCPRegistryClient()

    discovered = {}
    for tool_hint in resolution.not_found:
        search_query = tool_hint.replace("_", " ").split(".")[0]
        try:
            results = await registry.search(search_query)
            if results:
                discovered[tool_hint] = results
        except Exception as e:
            logger.warning("Registry search failed for '%s': %s", tool_hint, e)

    if discovered:
        return {
            "status": "external_integrations_found",
            "is_ready": False,
            "resolution": {
                "available": resolution.available,
                "needs_activation": resolution.needs_activation,
                "not_found": [t for t in resolution.not_found if t not in discovered],
                "needs_credentials": resolution.needs_credentials,
                "tool_mapping": resolution.tool_mapping,
            },
            "discovered": {
                hint: [{"name": s.name, "description": s.description, "url": s.url}
                       for s in servers]
                for hint, servers in discovered.items()
            },
            "message": _build_discovery_message(discovered),
        }

# Si no hay discovered, retornar resolución original
return self._build_resolution_response(resolution)
```

---

## 4. Decisiones

| # | Decisión | Justificación |
|:---|:---|:---|
| D1 | **discover_tools parsea README, no ejecuta servidor** | Seguridad: ejecutar servidor MCP externo requiere instalar deps (npx/pip), riesgo de código arbitrario. |
| D2 | **Import como TIPO B por defecto** | org_mcp_servers existe, MCPPool sabe conectar. TIPO C solo si se necesitan tools como REST. |
| D3 | **is_active=False explícito** | Migración 005 tiene DEFAULT TRUE. Forzar FALSE para requerir configuración manual. (OC) |
| D4 | **Solo GitHub MCP Registry para MVP** | Fuente oficial, API JSON. mcpmarket/smithery son roadmap. |
| D5 | **Usuario confirma antes de importar** | No auto-importar sin consentimiento. |
| D6 | **Top 5 resultados, timeout 10s** | Balance entre opciones y rendimiento. |
| D7 | **Fallback en discover_tools** | Si README no es parseable, retornar tool con name=server_name. Nunca retornar vacío. |

---

## 5. Criterios de Aceptación MVP

| # | Criterio | Verificación |
|:---|:---|:---|
| F1 | `search("google")` retorna lista de MCPServerInfo desde GitHub Registry | Test con HTTP real o mock |
| F2 | `discover_tools()` extrae tools de un README sin ejecutar servidor | Test con README fixture |
| F3 | `import_as_type_b()` inserta en org_mcp_servers con is_active=False | Query DB post-insert |
| F4 | `import_as_type_c()` crea proveedor + tools en service_catalog/service_tools | Query DB post-insert |
| T1 | Timeout HTTP no excede 10s | Test con mock lento |
| T2 | Error de red no lanza excepción no manejada | Test con mock que falla |
| T3 | Duplicado hace upsert, no insert duplicado | Insert 2x mismo name → 1 row |
| T4 | ArchitectFlow retorna `external_integrations_found` cuando hay matches | Mock registry + assert status |
| T5 | IntegrationResolver sin cambios | Diff del archivo = 0 |
| R1 | README no parseable → fallback a name+description | Test con README vacío |
| R2 | Registry vacío → mensaje "No encontré" | Test con mock vacío |

---

## 6. Plan de Implementación

| # | Tarea | Complejidad | Tiempo | Deps |
|:---|:---|:---|:---|:---|
| 1 | MCPServerInfo dataclass + MCPRegistryClient clase base | Baja | 30min | — |
| 2 | `search()` contra GitHub MCP Registry | Media | 1.5h | httpx |
| 3 | `discover_tools()` — parseo README con regex | Media | 2h | T2 |
| 4 | `import_as_type_b()` + `import_as_type_c()` | Media | 1h | DB schema |
| 5 | Integración en ArchitectFlow post-resolver | Media | 1h | T1-T4 |
| 6 | Tests unitarios (mock HTTP + mock DB) | Media | 1.5h | T1-T5 |
| **Total** | | | **~7.5h** | |

---

## 7. Riesgos

| # | Riesgo | Prob. | Impacto | Mitigación |
|:---|:---|:---|:---|:---|
| R1 | API del registry cambia formato | Media | Alto | Validar schema de response. Versionar endpoint. |
| R2 | README no sigue convenciones → parseo falla | Alta | Medio | Fallback a name+description del registry. Nunca vacío. |
| R3 | Inyección de comandos vía args importados | Baja | Crítico | NO ejecutar servidor en discover_tools. Sanitizar args. |
| R4 | Latencia de llamada HTTP ralentiza ArchitectFlow | Media | Bajo | Solo si usuario confirma. Timeout 10s. |
| R5 | is_active DEFAULT TRUE en migración crea servidor activo accidentalmente | Media | Alto | Valor explícito False en insert. (OC) |

---

## 8. � Roadmap

- mcpmarket.com y smithery.ai como fuentes adicionales
- Ejecución real de servidores en sandbox (Docker/Wasm) para discover_tools
- Cache local de registry (TTL ~1h)
- Auto-activación post-configuración de credenciales
- Health check de servidores importados

---

*3 análisis evaluados, 3 discrepancias resueltas. Estimación: ~7.5h.*
